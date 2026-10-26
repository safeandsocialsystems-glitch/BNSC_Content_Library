import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

MOD_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'import_csv.py'
spec = importlib.util.spec_from_file_location('bnsc_import', MOD_PATH)
imp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imp)

class ImportCsvTest(unittest.TestCase):
    def test_demo_rows_parse(self):
        data = imp.parse_csv(Path(__file__).resolve().parents[1] / 'examples' / 'demo_contents.csv')
        self.assertEqual(len(data), 10)
        self.assertEqual(data[0]['type'], '動画')
        self.assertIn('前庭', data[0]['tags'])
    def test_reject_external_video_url(self):
        self.assertFalse(imp.is_allowed_url('https://vimeo.com/12345'))
        self.assertFalse(imp.is_allowed_url('javascript:alert(1)'))
        self.assertFalse(imp.is_allowed_url('https://community.camp-fire.jp.evil.example/'))
        self.assertTrue(imp.is_allowed_url('https://community.camp-fire.jp/projects/view/666070'))
    def parse_row(self, **changes):
        row = dict(id='real-001', title='検証用タイトル', type='動画', category='リハビリ',
                   summary='', tags='', keywords='', duration_minutes='', published_at='', url='', status='draft')
        row.update(changes)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'input.csv'
            with path.open('w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=list(row))
                writer.writeheader()
                writer.writerow(row)
            return imp.parse_csv(path)

    def test_draft_not_in_public_index(self):
        self.assertEqual(imp.public_payload(self.parse_row())['items'], [])

    def test_legacy_defaults_to_draft(self):
        self.assertEqual(self.parse_row(status='')[0]['status'], 'draft')

    def test_published_requires_url(self):
        with self.assertRaisesRegex(ValueError, '投稿URL'):
            self.parse_row(status='published')

    def test_demo_cannot_be_published(self):
        with self.assertRaisesRegex(ValueError, '実コンテンツ'):
            self.parse_row(id='DEMO-01', status='published', url='https://community.camp-fire.jp/')

    def test_published_only_and_no_management_status(self):
        # Synthetic URL is used only for validation, never written to production data.
        items = self.parse_row(status='published', url='https://community.camp-fire.jp/') + self.parse_row()
        payload = imp.public_payload(items)
        self.assertFalse(payload['demo'])
        self.assertEqual(len(payload['items']), 1)
        self.assertNotIn('status', payload['items'][0])

    def test_malformed_url(self):
        for url in ('https://community.camp-fire.jp:bad/', 'https://[', 'https://community.camp-fire.jp/?token=secret'):
            self.assertFalse(imp.is_allowed_url(url))

    def test_invalid_date(self):
        with self.assertRaisesRegex(ValueError, 'YYYY-MM-DD'):
            self.parse_row(published_at='20261025')

    def test_empty_production(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'empty.csv'
            path.write_text(','.join(imp.HEADERS) + '\n', encoding='utf-8')
            self.assertEqual(imp.public_payload(imp.parse_csv(path)), {'demo': False, 'items': []})

    def test_reject_duplicate_ids(self):
        source = Path(__file__).resolve().parents[1] / 'examples' / 'demo_contents.csv'
        with source.open(encoding='utf-8-sig', newline='') as f:
            rows = list(csv.reader(f))
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'bad.csv'
            with path.open('w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(rows[:2] + rows[1:2])
            with self.assertRaisesRegex(ValueError, '重複'):
                imp.parse_csv(path)

if __name__ == '__main__': unittest.main()
