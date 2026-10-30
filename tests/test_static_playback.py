"""Synthetic fixtures only: no live credentials or actual videos."""
import json
import unittest
from test_vimeo import FakeVimeo, video
import sync_vimeo as sync

class StaticPlaybackTest(unittest.TestCase):
    def test_explicit_playback_keeps_hash_but_never_token_or_raw_link(self):
        client=FakeVimeo([video()])
        items=sync.collect(client,'42',include_playback=True)
        self.assertEqual(items[0]['embed_url'],'https://player.vimeo.com/video/123?h=fakehashABC&dnt=1')
        self.assertNotIn(client.token,json.dumps(items))
        self.assertEqual(items[0]['url'],'')
    def test_default_metadata_still_excludes_playback(self):
        self.assertNotIn('fakehashABC',json.dumps(sync.collect(FakeVimeo([video()]),'42')))
    def test_rejects_malicious_or_incomplete_player(self):
        for raw in ['https://evil.test/video/123?h=fakehashABC','https://player.vimeo.com/video/999?h=fakehashABC',
                    'https://player.vimeo.com/video/123','https://player.vimeo.com/video/123?h=fake-api-token-SECRET',
                    'https://player.vimeo.com/video/123?h=fakehashABC&h=another']:
            v=video();v['player_embed_url']=raw
            with self.assertRaises(sync.SyncError): sync.collect(FakeVimeo([v]),'42',include_playback=True)
    def test_last_tag_removed_produces_empty_snapshot(self):
        self.assertEqual(sync.collect(FakeVimeo([video(tags=('other',))]),'42',include_playback=True),[])
    def test_failed_playback_leaves_existing_file(self):
        import tempfile
        from pathlib import Path
        from import_csv import HEADERS
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);csv=root/'contents.csv';out=root/'contents.json'
            csv.write_text(','.join(HEADERS+['status'])+'\n');out.write_text('previous snapshot')
            v=video();v['player_embed_url']=''
            with self.assertRaises(sync.SyncError): sync.synchronize(FakeVimeo([v]),'42',csv,out,include_playback=True)
            self.assertEqual(out.read_text(),'previous snapshot')
