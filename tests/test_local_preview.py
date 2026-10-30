import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_local_preview import build

class LocalPreviewTest(unittest.TestCase):
    def test_embedded_data_is_safe_and_self_contained(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source, output = folder/'data.json', folder/'preview.html'
            source.write_text(json.dumps({'items':[{'id':'test','title':'</script><script>test</script>', 'url':''}]}))
            self.assertEqual(build(source, output), 1)
            html = output.read_text()
            self.assertIn('id="bnsc-embedded-data"', html)
            self.assertIn('\\u003c/script\\u003e', html)
            self.assertNotIn('window.fetch =', html)
            self.assertNotIn('src="./app.js"', html)
            self.assertNotIn('href="./"', html)
            self.assertIn('"expected_items": 1', html)
    def test_refuses_empty_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/'data.json'
            source.write_text('{"items":[]}')
            with self.assertRaises(ValueError): build(source, Path(folder)/'out.html')
    def test_refuses_private_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/'data.json'
            source.write_text(json.dumps({'items':[{'access_token':'synthetic'}]}))
            with self.assertRaises(ValueError): build(source, Path(folder)/'out.html')
