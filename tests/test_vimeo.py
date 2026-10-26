"""Synthetic fixtures only; no credentials, no real Vimeo videos."""
import copy
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import sync_vimeo as sync
import import_csv as csv_import
import build_release as release


def video(ident='123', tags=('BNSC', '前庭', 'リハビリ')):
    return dict(uri='/videos/' + ident + ':fakehashABC', user={'uri': '/users/42'},
                name='架空のテスト動画', description='前庭のテスト説明', duration=125,
                tags=[{'name': t} for t in tags], created_time='2026-10-26T00:00:00+00:00',
                pictures={'sizes': [{'width': 640, 'link': 'https://i.vimeocdn.com/video/999-test_640.jpg?tracking=x'}]},
                link='https://vimeo.com/' + ident + '/fakehashABC',
                player_embed_url='https://player.vimeo.com/video/' + ident + '?h=fakehashABC')


class FakeVimeo:
    token = 'fake-api-token-SECRET'
    def __init__(self, videos, fail_detail=False, scope='public private', mutate=False):
        self.videos, self.calls = videos, []
        self.fail_detail, self.scope, self.mutate = fail_detail, scope, mutate
        self.inventory_calls = 0
    def get(self, path):
        self.calls.append(path)
        if path == '/oauth/verify': return {'scope': self.scope}
        if path.startswith('/me?'): return {'uri': '/users/42'}
        if path.startswith('/me/videos?'):
            self.inventory_calls += 1
            videos = self.videos if not self.mutate or self.inventory_calls == 1 else []
            return {'total': len(videos), 'data': copy.deepcopy(videos), 'paging': {'next': None}}
        if path.startswith('/videos/'):
            if self.fail_detail: raise sync.SyncError('Vimeo API HTTP 429。')
            ident = urlsplit(path).path.rsplit('/', 1)[1]
            return copy.deepcopy(next(v for v in self.videos if sync.video_id(v) == ident))
        raise AssertionError('Unexpected endpoint')


class VimeoSyncTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.csv = self.root / 'contents.csv'
        self.output = self.root / 'data.json'
        self.csv.write_text(','.join(csv_import.HEADERS + ['status']) + '\n', encoding='utf-8')
    def run_sync(self, videos, **kwargs):
        return sync.synchronize(FakeVimeo(videos, **kwargs), '42', self.csv, self.output)
    def test_tag_approval_and_stable_id(self):
        payload = self.run_sync([video(), video('456', tags=('other',))])
        self.assertEqual([v['id'] for v in payload['items']], ['vimeo-123'])
        self.assertEqual(payload['items'][0]['category'], 'リハビリ')
        self.assertEqual(payload['items'][0]['duration_seconds'], 125)
        self.assertEqual(payload['items'][0]['duration_minutes'], 3)
    def test_tag_removal_including_last_video(self):
        self.run_sync([video()])
        self.assertEqual(self.run_sync([video(tags=('前庭',))])['items'], [])
        self.assertTrue(json.loads(self.output.read_text())['vimeo_sync']['complete'])
    def test_title_description_and_tags_updated_without_duplicate(self):
        self.run_sync([video()])
        changed = video(tags=('BNSC', '小脳'))
        changed.update(name='更新したタイトル', description='更新した概要')
        payload = self.run_sync([changed])
        self.assertEqual(len(payload['items']), 1)
        self.assertEqual(payload['items'][0]['id'], 'vimeo-123')
        self.assertEqual(payload['items'][0]['title'], '更新したタイトル')
        self.assertEqual(payload['items'][0]['summary'], '更新した概要')
        self.assertEqual(payload['items'][0]['tags'], ['小脳'])
    def test_partial_failure_keeps_previous_bytes(self):
        self.run_sync([video()])
        before = self.output.read_bytes()
        with self.assertRaises(sync.SyncError): self.run_sync([video()], fail_detail=True)
        self.assertEqual(self.output.read_bytes(), before)
    def test_mid_sync_inventory_change_keeps_previous(self):
        self.run_sync([video()])
        before = self.output.read_bytes()
        with self.assertRaises(sync.SyncError): self.run_sync([video()], mutate=True)
        self.assertEqual(self.output.read_bytes(), before)
    def test_private_scope_required_even_when_zero_results(self):
        with self.assertRaises(sync.SyncError): self.run_sync([], scope='public')
        self.assertFalse(self.output.exists())
    def test_wrong_account(self):
        with self.assertRaises(sync.SyncError): sync.collect(FakeVimeo([]), '99')
    def test_duplicate_id_rejected(self):
        with self.assertRaises(sync.SyncError): self.run_sync([video(), video()])
    def test_missing_tag_data_is_not_treated_as_removal(self):
        v = video(); del v['tags']
        with self.assertRaises(sync.SyncError): self.run_sync([v])
    def test_no_playback_hash_or_token_in_any_public_fields(self):
        v = video()
        v.update(description='<a href="https://vimeo.com/123/fakehashABC">説明</a> https://player.vimeo.com/video/123?h=fakehashABC fakehashABC fake-api-token-SECRET',
                 name='テスト fakehashABC')
        v['tags'].append({'name': 'fakehashABC'})
        payload = self.run_sync([v])
        text = self.output.read_text()
        for private in ('fakehashABC', FakeVimeo.token, 'player.vimeo.com', 'https://vimeo.com', 'tracking=x'):
            self.assertNotIn(private, text)
        self.assertEqual(payload['items'][0]['url'], '')
        self.assertNotIn('link', payload['items'][0])
    def test_check_mode_writes_nothing(self):
        sync.synchronize(FakeVimeo([video()]), '42', self.csv, self.output, check=True)
        self.assertFalse(self.output.exists())
    def test_csv_management_unchanged(self):
        with self.csv.open('a', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            for ident, status in [('real', 'published'), ('draft', 'draft'), ('demo', 'demo')]:
                w.writerow([ident, 'テスト記事', '研究解説', 'リハビリ', '', '', '', 0, '', 'https://community.camp-fire.jp/', status])
        payload = self.run_sync([video()])
        self.assertEqual([i['id'] for i in payload['items']], ['real', 'vimeo-123'])
    def test_csv_import_keeps_vimeo(self):
        self.output = self.root / 'data' / 'contents.json'
        self.run_sync([video()])
        with patch.object(csv_import, 'ROOT', self.root), patch.object(sys, 'argv', ['import_csv.py']):
            csv_import.main()
        self.assertEqual(json.loads(self.output.read_text())['items'][0]['id'], 'vimeo-123')
    def test_empty_synced_release_is_allowed_for_removals(self):
        (self.root / 'data').mkdir()
        (self.root / 'data' / 'contents.json').write_text(json.dumps(self.run_sync([])))
        (self.root / 'assets').mkdir()
        for name in ('index.html', 'app.js', 'styles.css'): (self.root / name).write_text('test')
        with patch.object(release, 'ROOT', self.root), patch.object(sys, 'argv', ['build_release.py', '--synced']):
            release.main()
        self.assertEqual(json.loads((self.root / 'dist/data/contents.json').read_text())['items'], [])
        self.assertFalse((self.root / 'dist/contents.csv').exists())
    def test_pagination_total_and_foreign_next_rejected(self):
        for page in [dict(total=2, data=[video()], paging={'next': None}),
                     dict(total=1, data=[video()], paging={'next': 'https://evil.example/me/videos?page=2'})]:
            with patch.object(FakeVimeo, 'get', return_value=page):
                with self.assertRaises(sync.SyncError): sync.inventory(FakeVimeo([]), '/users/42')
    def test_two_page_inventory(self):
        pages = [dict(total=2, data=[video()], paging={'next': '/me/videos?page=2'}),
                 dict(total=2, data=[video('456')], paging={'next': None})]
        with patch.object(FakeVimeo, 'get', side_effect=pages):
            self.assertEqual(len(sync.inventory(FakeVimeo([]), '/users/42')), 2)
    def test_http_error_has_no_sensitive_body_or_url(self):
        client = sync.Vimeo(FakeVimeo.token)
        with patch.object(client.opener, 'open', side_effect=HTTPError('https://secret', 401, 'private body', {}, None)):
            with self.assertRaisesRegex(sync.SyncError, 'HTTP 401') as exc: client.get('/me')
            self.assertNotIn('secret', str(exc.exception))
            self.assertNotIn('private body', str(exc.exception))
    def test_api_rejects_absolute_url_before_sending_token(self):
        with self.assertRaises(sync.SyncError): sync.Vimeo('test').get('https://evil.example/')


if __name__ == '__main__': unittest.main()
