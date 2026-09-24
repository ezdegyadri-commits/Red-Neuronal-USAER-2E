from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from data.google import retry_google


class FakeAPIError(Exception):
    def __init__(self, status):
        super().__init__("Google API request failed")
        self.response = SimpleNamespace(status_code=status)


class GoogleRetryTest(unittest.TestCase):
    def test_retry_google_retries_temporary_server_errors(self):
        operation = Mock(side_effect=[FakeAPIError(503), "ok"])
        with patch("data.google.time.sleep"), patch("data.google.random.uniform", return_value=0):
            result = retry_google(operation)
        self.assertEqual(result, "ok")
        self.assertEqual(operation.call_count, 2)

    def test_retry_google_does_not_retry_permission_errors(self):
        operation = Mock(side_effect=FakeAPIError(403))
        with patch("data.google.time.sleep") as sleep:
            with self.assertRaises(FakeAPIError):
                retry_google(operation)
        self.assertEqual(operation.call_count, 1)
        sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
