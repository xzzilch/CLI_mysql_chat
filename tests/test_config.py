import os
import unittest
from unittest.mock import patch

import chat_backend


class DatabaseConfigTests(unittest.TestCase):
    def test_local_config_uses_expected_defaults(self):
        with patch.dict(os.environ, {"TEXTSERVICE_DB_PASSWORD": "StrongPassphrase2026!"}, clear=True):
            config = chat_backend.get_db_config()

        self.assertEqual(config["host"], "localhost")
        self.assertEqual(config["port"], 3306)
        self.assertEqual(config["user"], "client_user")
        self.assertEqual(config["database"], "text_service_db")
        self.assertNotIn("ssl_ca", config)

    def test_remote_config_requires_ca_certificate(self):
        env = {
            "TEXTSERVICE_DB_PASSWORD": "StrongPassphrase2026!",
            "TEXTSERVICE_DB_HOST": "db.example.test",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(ValueError, "TEXTSERVICE_DB_SSL_CA"):
                chat_backend.get_db_config()

    def test_remote_config_verifies_certificate_and_hostname(self):
        env = {
            "TEXTSERVICE_DB_PASSWORD": "StrongPassphrase2026!",
            "TEXTSERVICE_DB_HOST": "db.example.test",
            "TEXTSERVICE_DB_SSL_CA": "/tmp/test-ca.pem",
        }
        with patch.dict(os.environ, env, clear=True):
            config = chat_backend.get_db_config()

        self.assertTrue(config["ssl_verify_cert"])
        self.assertTrue(config["ssl_verify_identity"])

    def test_invalid_password_is_rejected(self):
        with patch.dict(os.environ, {"TEXTSERVICE_DB_PASSWORD": "short"}, clear=True):
            with self.assertRaisesRegex(ValueError, "TEXTSERVICE_DB_PASSWORD"):
                chat_backend.get_db_config()

    def test_invalid_port_is_rejected(self):
        env = {
            "TEXTSERVICE_DB_PASSWORD": "StrongPassphrase2026!",
            "TEXTSERVICE_DB_PORT": "70000",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(ValueError, "TEXTSERVICE_DB_PORT"):
                chat_backend.get_db_config()


class InputValidationTests(unittest.TestCase):
    def test_username_is_trimmed(self):
        self.assertEqual(chat_backend._validate_identity(" alice "), "alice")

    def test_blank_and_oversized_username_are_rejected(self):
        with self.assertRaises(ValueError):
            chat_backend._validate_identity("  ")
        with self.assertRaises(ValueError):
            chat_backend._validate_identity("a" * 51)

    def test_message_validation_rejects_blank_and_oversized_values(self):
        with self.assertRaises(ValueError):
            chat_backend.send_txt(None, None, "bob", "  ", b"token")
        with self.assertRaises(ValueError):
            chat_backend.send_txt(None, None, "bob", "x" * 65536, b"token")


if __name__ == "__main__":
    unittest.main()
