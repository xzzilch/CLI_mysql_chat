import hashlib
import unittest
from unittest.mock import Mock, patch

import chat_backend


class PasswordAuthTests(unittest.TestCase):
    def test_verifier_is_salted_and_fixed_length(self):
        first = chat_backend._derive_password_verifier("correct horse battery", b"a" * 16)
        second = chat_backend._derive_password_verifier("correct horse battery", b"b" * 16)

        self.assertEqual(len(first), 32)
        self.assertNotEqual(first, second)
        with self.assertRaises(ValueError):
            chat_backend._derive_password_verifier("short", b"a" * 16)

    def test_registration_sends_salt_and_verifier_not_plaintext(self):
        connection = Mock()
        cursor = connection.cursor.return_value
        with patch.object(chat_backend, "get_conn", return_value=connection):
            self.assertTrue(
                chat_backend.reg_user("alice", "5550100", "correct horse battery")
            )

        args = cursor.callproc.call_args.args[1]
        self.assertEqual(args[:2], ["alice", "5550100"])
        self.assertEqual(len(args[2]), 16)
        self.assertEqual(len(args[3]), 32)
        self.assertNotIn("correct horse battery", args)
        connection.commit.assert_called_once()
        cursor.close.assert_called_once()
        connection.close.assert_called_once()

    def test_login_uses_challenge_response_and_returns_session_token(self):
        salt = b"s" * 16
        nonce = b"n" * 32
        token = b"t" * 32
        challenge_result = Mock()
        challenge_result.fetchone.return_value = {
            "password_salt": salt,
            "challenge_nonce": nonce,
        }
        login_result = Mock()
        login_result.fetchone.return_value = {
            "status": "Login Successful!",
            "session_token": token,
        }
        cursor = Mock()
        cursor.stored_results.side_effect = [[challenge_result], [login_result]]
        connection = Mock()
        connection.cursor.return_value = cursor

        with patch.object(chat_backend, "get_conn", return_value=connection):
            result = chat_backend.login("alice", "correct horse battery")

        verifier = chat_backend._derive_password_verifier("correct horse battery", salt)
        expected_response = hashlib.sha256(nonce + verifier).digest()
        self.assertEqual(result, (connection, cursor, token))
        self.assertEqual(
            cursor.callproc.call_args_list[0].args,
            ("BeginUserLogin", ["alice"]),
        )
        self.assertEqual(
            cursor.callproc.call_args_list[1].args,
            ("CompleteUserLogin", [expected_response]),
        )
        self.assertNotIn("correct horse battery", repr(cursor.callproc.call_args_list))


if __name__ == "__main__":
    unittest.main()
