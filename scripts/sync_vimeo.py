#!/usr/bin/env python3
"""Vimeo -> public search metadata. Playback export is explicit; API credentials are never exported."""
import argparse
import html
import json
import math
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlencode, parse_qs
from urllib.request import Request, build_opener, HTTPRedirectHandler

from import_csv import ROOT, CATEGORIES, parse_csv, public_payload

API = 'https://api.vimeo.com'


class SyncError(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SyncError('APIリダイレクトを拒否しました。')


class Vimeo:
    def __init__(self, token):
        self.token = token
        self.opener = build_opener(NoRedirect())

    def get(self, path):
        parsed = urlsplit(path)
        if parsed.scheme or parsed.netloc or not path.startswith('/') or path.startswith('//'):
            raise SyncError('不正なAPIパスです。')
        request = Request(API + path, headers={
            'Authorization': 'Bearer ' + self.token,
            'Accept': 'application/vnd.vimeo.*+json;version=3.4',
            'User-Agent': 'BNSC-Library-Sync/1.0'})
        try:
            with self.opener.open(request, timeout=45) as response:
                data = json.load(response)
        except HTTPError as exc:
            # Never print error body, request headers or URLs (may contain private data).
            raise SyncError(f'Vimeo API HTTP {exc.code}。公開データは更新しません。') from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise SyncError('Vimeo API通信またはJSON解析に失敗しました。') from None
        if not isinstance(data, dict):
            raise SyncError('Vimeo API応答形式が不正です。')
        return data


def video_id(video):
    match = re.fullmatch(r'/videos/(\d+)(?::[A-Za-z0-9]+)?', video.get('uri', ''))
    if not match:
        raise SyncError('動画IDが不正です。')
    return match[1]


def tag_names(video):
    tags = video.get('tags')
    if not isinstance(tags, list) or any(not isinstance(t, dict) or not isinstance(t.get('name'), str) for t in tags):
        raise SyncError('タグ情報が不完全です。')
    return sorted(set(t['name'] for t in tags))


def inventory(client, owner, diagnose=False):
    path = '/me/videos?' + urlencode({'per_page': 100, 'sort': 'date', 'direction': 'asc', 'fields': 'uri,tags,user.uri,privacy.view'})
    seen_pages, videos = set(), {}
    total = None
    unlisted = 0
    while path:
        if path in seen_pages or len(seen_pages) >= 10000:
            raise SyncError('ページネーションが不正です。')
        seen_pages.add(path)
        page = client.get(path)
        if type(page.get('total')) is not int or not isinstance(page.get('data'), list) or not isinstance(page.get('paging'), dict) or 'next' not in page['paging']:
            raise SyncError('一覧応答が不完全です。')
        if total is not None and total != page['total']:
            raise SyncError('取得中に動画一覧が変更されました。次回再試行します。')
        total = page['total']
        for video in page['data']:
            if not isinstance(video, dict) or video.get('user', {}).get('uri') != owner:
                raise SyncError('所有アカウントが一致しません。')
            ident = video_id(video)
            if ident in videos:
                raise SyncError('一覧の重複を検出しました。次回再試行します。')
            videos[ident] = tag_names(video)
            unlisted += video.get('privacy', {}).get('view') == 'unlisted'
        following = page['paging']['next']
        if following is not None:
            if not isinstance(following, str) or not following:
                raise SyncError('次ページ情報が不正です。')
            parts = urlsplit(following)
            if (parts.scheme and parts.scheme != 'https') or (parts.netloc and parts.netloc != 'api.vimeo.com') or parts.path != '/me/videos' or parts.fragment:
                raise SyncError('外部の次ページURLを拒否しました。')
            path = parts.path + '?' + parts.query
        else:
            path = None
    if len(videos) != total:
        raise SyncError('全動画の取得を確認できませんでした。')
    if diagnose:
        print('DIAGNOSTIC ' + json.dumps({
            'pages': len(seen_pages), 'api_total': total, 'fetched': len(videos),
            'all_owners_match': True, 'unlisted_count': unlisted,
            'videos_with_tags': sum(bool(tags) for tags in videos.values()),
            'exact_BNSC': sum('BNSC' in tags for tags in videos.values()),
            'case_insensitive_BNSC': sum(any(t.casefold() == 'bnsc' for t in tags) for tags in videos.values()),
            'normalized_BNSC': sum(any(unicodedata.normalize('NFKC', t).strip().casefold() == 'bnsc' for t in tags) for tags in videos.values()),
        }, sort_keys=True))
    return videos


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)


def public_text(value, secrets):
    if not isinstance(value, str):
        raise SyncError('テキストの形式が不正です。')
    parser = PlainText()
    parser.feed(value)
    text = html.unescape(' '.join(parser.parts))
    # Descriptions are public summaries, never a vehicle for private playback links.
    text = re.sub(r'(?i)(?:https?://|www\.|(?:player\.)?vimeo\.com/)[^\s<>]+', '[リンク省略]', text)
    for secret in secrets:
        if secret:
            text = text.replace(secret, '[非公開情報省略]')
    return text.strip()


def private_values(video, token):
    values = [token]
    uri = video.get('uri', '')
    if ':' in uri:
        values.append(uri.split(':', 1)[1])
    for key in ('link', 'player_embed_url'):
        raw = video.get(key)
        if not isinstance(raw, str):
            continue
        parts = urlsplit(raw)
        values.extend(parse_qs(parts.query).get('h', []))
        match = re.fullmatch(r'/\d+/([A-Za-z0-9]+)', parts.path)
        if match:
            values.append(match[1])
    return values


def convert(video, owner, token, additional_secrets=()):
    ident = video_id(video)
    if video.get('user', {}).get('uri') != owner or 'BNSC' not in tag_names(video):
        raise SyncError('取得中に所有者または承認タグが変更されました。')
    secrets = private_values(video, token) + list(additional_secrets)
    title = public_text(video.get('name'), secrets)
    if not title:
        raise SyncError('動画タイトルが空です。')
    duration = video.get('duration')
    if type(duration) is not int or duration < 0:
        raise SyncError('再生時間が不正です。')
    tags = [public_text(t, secrets) for t in tag_names(video) if t != 'BNSC']
    pictures = video.get('pictures')
    if not isinstance(pictures, dict) or not isinstance(pictures.get('sizes'), list):
        raise SyncError('サムネイル情報が不完全です。')
    thumbnail = ''
    for size in pictures['sizes']:
        link = size.get('link', '')
        p = urlsplit(link)
        if p.scheme == 'https' and p.netloc == 'i.vimeocdn.com' and p.path.startswith('/video/') and not p.fragment and not any(s and s in link for s in secrets):
            thumbnail = 'https://i.vimeocdn.com' + p.path
            if size.get('width', 0) >= 640:
                break
    created = video.get('created_time')
    try:
        published = datetime.fromisoformat(created.replace('Z', '+00:00')).date().isoformat()
    except (ValueError, AttributeError):
        raise SyncError('動画作成日時が不正です。') from None
    return dict(id='vimeo-' + ident, source='vimeo', vimeo_id=ident, title=title,
                type='動画', category=next((t for t in tags if t in CATEGORIES), '脳機能・神経科学'),
                summary=public_text(video.get('description') or '', secrets), tags=tags, keywords=[],
                duration_minutes=math.ceil(duration / 60), duration_seconds=duration,
                published_at=published, thumbnail_url=thumbnail, url='')


def playback_url(video, token):
    """Export only the approved Vimeo embed URL, never raw API responses."""
    ident = video_id(video)
    raw = video.get('player_embed_url', '')
    if not isinstance(raw, str) or not raw or (token and token in raw):
        raise SyncError('再生URLが未設定または不正です。')
    parts = urlsplit(raw)
    if (parts.scheme != 'https' or parts.netloc != 'player.vimeo.com'
            or parts.path != '/video/' + ident or parts.fragment):
        raise SyncError('再生URLの取得元が不正です。')
    hashes = parse_qs(parts.query, keep_blank_values=True).get('h', [])
    if len(hashes) > 1 or (hashes and not re.fullmatch(r'[A-Za-z0-9]+', hashes[0])):
        raise SyncError('再生パラメーターが不正です。')
    # Known unlisted hash must not silently be lost, otherwise the player fails.
    expected = private_values(video, '')[1:]
    if expected and (not hashes or any(h != hashes[0] for h in expected)):
        raise SyncError('限定公開動画の再生パラメーターが一致しません。')
    params = {'h': hashes[0], 'dnt': '1'} if hashes else {'dnt': '1'}
    return 'https://player.vimeo.com/video/' + ident + '?' + urlencode(params)


def collect(client, account_id, diagnose=False, include_playback=False):
    if not re.fullmatch(r'\d+', account_id):
        raise SyncError('VIMEO_USER_ID に自分の数値ユーザーIDを設定してください。')
    auth = client.get('/oauth/verify')
    if not {'public', 'private'}.issubset(set(auth.get('scope', '').split())):
        raise SyncError('トークンには public と private の読み取り権限が必要です。')
    owner = '/users/' + account_id
    if client.get('/me?fields=uri').get('uri') != owner:
        raise SyncError('トークンの所有者が VIMEO_USER_ID と一致しません。')
    if diagnose:
        print('DIAGNOSTIC account_matches_config=true public_scope=true private_scope=true')
    before = inventory(client, owner, diagnose)
    raw_videos = []
    for ident, tags in sorted(before.items()):
        if 'BNSC' not in tags:
            continue
        video = client.get('/videos/' + ident + '?' + urlencode({'fields': 'uri,user.uri,name,description,duration,tags,pictures,created_time,link,player_embed_url'}))
        if video_id(video) != ident or tag_names(video) != tags:
            raise SyncError('取得中に動画が変更されました。次回再試行します。')
        raw_videos.append(video)
    if inventory(client, owner) != before:
        raise SyncError('取得中に動画一覧・タグが変更されました。次回再試行します。')
    secrets = [secret for video in raw_videos for secret in private_values(video, client.token)]
    items = [convert(video, owner, client.token, secrets) for video in raw_videos]
    encoded = json.dumps(items, ensure_ascii=False)
    if any(secret and secret in encoded for secret in secrets):
        raise SyncError('非公開情報の混入を検出しました。更新を停止します。')
    if include_playback:
        for item, video in zip(items, raw_videos):
            item['embed_url'] = playback_url(video, client.token)
        if client.token and client.token in json.dumps(items, ensure_ascii=False):
            raise SyncError('認証情報の混入を検出しました。')
    return items


def merged_payload(csv_path, vimeo_items):
    payload = public_payload(parse_csv(csv_path))
    if any(item['id'].startswith('vimeo-') for item in payload['items']):
        raise SyncError('CSVのidに予約接頭辞 vimeo- は使用できません。')
    payload['items'].extend(vimeo_items)
    payload['vimeo_sync'] = {'complete': True, 'synced_at': datetime.now(timezone.utc).isoformat(), 'count': len(vimeo_items)}
    return payload


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def synchronize(client, account_id, csv_path, output, check=False, diagnose=False, include_playback=False):
    items = collect(client, account_id, diagnose, include_playback)
    payload = merged_payload(csv_path, items)
    if not check:
        atomic_write(output, payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--token-file', type=Path, help='公開フォルダー外のトークンファイル')
    parser.add_argument('--check', action='store_true', help='実API接続・全件検証のみ。ファイル変更なし')
    parser.add_argument('--diagnose', action='store_true', help='--check専用: 秘密情報を含まない集計のみ出力')
    parser.add_argument('--include-playback', action='store_true', help='閲覧者に公開するVimeo埋め込みURLを含める')
    args = parser.parse_args()
    if args.diagnose and not args.check:
        raise SyncError('--diagnose は --check と併用してください。')
    token = os.environ.get('VIMEO_ACCESS_TOKEN', '').strip()
    if args.token_file:
        resolved = args.token_file.resolve()
        if ROOT == resolved or ROOT in resolved.parents:
            raise SyncError('トークンファイルは公開フォルダーの外に保存してください。')
        token = resolved.read_text().strip()
    if not token:
        raise SyncError('VIMEO_ACCESS_TOKEN または --token-file が未設定です。')
    payload = synchronize(Vimeo(token), os.environ.get('VIMEO_USER_ID', ''), ROOT / 'contents.csv', ROOT / 'data' / 'contents.json', args.check, args.diagnose, args.include_playback)
    print(f'Vimeo全件検証成功: BNSC {payload["vimeo_sync"]["count"]}件 / 検索対象 {len(payload["items"])}件 / ' + ('接続テストのみ' if args.check else '検索JSON更新完了'))


if __name__ == '__main__':
    try:
        main()
    except SyncError as exc:
        print(f'同期失敗: {exc} 既存JSONは維持しました。', file=sys.stderr)
        sys.exit(1)
    except (ValueError, OSError, TypeError, KeyError, AttributeError):
        # Validation messages can contain user input; do not log any API-derived strings.
        print('同期失敗: 認証設定・API権限・通信・応答形式・CSVを確認してください。既存JSONは維持しました。', file=sys.stderr)
        sys.exit(1)
