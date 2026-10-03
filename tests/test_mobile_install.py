import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MobileInstallationTest(unittest.TestCase):
    def test_manifest_stays_on_existing_origin(self):
        manifest = json.loads((ROOT / 'static/usaer-manifest.json').read_text())
        self.assertEqual(manifest['start_url'], '/')
        self.assertEqual(manifest['scope'], '/')
        self.assertEqual(manifest['display'], 'standalone')
        self.assertFalse(manifest['prefer_related_applications'])
        for icon in manifest['icons']:
            self.assertNotIn('/', icon['src'])
            self.assertTrue((ROOT / 'static' / Path(icon['src']).name).exists())

    def test_no_credentials_or_private_cache(self):
        html = (ROOT / 'ui/mobile_install.html').read_text()
        for banned in ['localStorage', 'sessionStorage', 'serviceWorker', 'fetch(',
                       'credentials_json', 'token_json', 'GEMINI_API_KEY']:
            self.assertNotIn(banned, html)

    def test_static_serving_does_not_change_upload_limits(self):
        config = (ROOT / '.streamlit/config.toml').read_text()
        self.assertIn('enableStaticServing = true', config)
        self.assertIn('maxUploadSize = 400', config)
        self.assertIn('maxMessageSize = 400', config)


if __name__ == '__main__':
    unittest.main()
