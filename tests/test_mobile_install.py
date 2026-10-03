import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class MobileInstallationTest(unittest.TestCase):
    def test_download_exact_signed_apk(self):
        from ui.mobile_install import android_apk, APK_SHA256, APK_NAME
        import hashlib
        payload = android_apk()
        self.assertEqual(payload[:2], b'PK')
        self.assertEqual(hashlib.sha256(payload).hexdigest(), APK_SHA256)
        self.assertEqual(APK_NAME, 'USAER-02E-Android-1.0.0.apk')

    def test_corrupt_apk_is_not_served(self):
        from ui import mobile_install
        with patch.object(Path, 'read_bytes', return_value=b'not an APK'):
            with self.assertRaises(ValueError):
                mobile_install.android_apk()

    def test_visible_controls_do_not_require_login_or_google(self):
        from streamlit.testing.v1 import AppTest
        test = AppTest.from_string('from ui.mobile_install import installation_help\ninstallation_help()').run()
        self.assertEqual(len(test.exception), 0)
        downloads = test.get('download_button')
        self.assertEqual(len(downloads), 1)
        self.assertEqual(downloads[0].label, 'Descargar APK para Android')
        self.assertEqual(test.get('popover')[0].proto.popover.label, 'Instalar en iPhone / iPad')
        self.assertTrue(any('Añadir a pantalla de inicio' in item.value for item in test.markdown))

    def test_missing_apk_keeps_verified_download_fallback(self):
        from streamlit.testing.v1 import AppTest
        from ui import mobile_install
        with patch.object(mobile_install, 'android_apk', side_effect=OSError):
            test = AppTest.from_string('from ui.mobile_install import installation_help\ninstallation_help()').run()
        self.assertEqual(len(test.exception), 0)
        links = test.get('link_button')
        self.assertTrue(any(item.label == 'Descargar APK para Android' for item in links))

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
