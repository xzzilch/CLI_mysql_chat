from pathlib import Path
import unittest

from mysql.connector._scripting import split_multi_statement


ROOT = Path(__file__).resolve().parents[1]


class SchemaProvisioningTests(unittest.TestCase):
    def test_connector_keeps_procedure_bodies_intact(self):
        schema = (ROOT / "text_service_schema.sql").read_bytes()
        partitions = split_multi_statement(schema, map_results=True)
        statements = [
            statement.decode().strip()
            for partition in partitions
            for statement in partition["single_stmts"]
        ]
        procedures = [
            statement for statement in statements
            if statement.upper().startswith("CREATE PROCEDURE")
        ]

        self.assertEqual(len(procedures), 10)
        self.assertTrue(all(statement.endswith("END") for statement in procedures))

    def test_schema_setup_does_not_drop_the_database(self):
        schema = (ROOT / "text_service_schema.sql").read_text(encoding="utf-8")
        self.assertNotIn("DROP DATABASE", schema.upper())
        self.assertIn("USE text_service_db;", schema)

    def test_login_schema_never_compares_plaintext_passwords(self):
        schema = (ROOT / "text_service_schema.sql").read_text(encoding="utf-8")
        self.assertIn("password_verifier BINARY(32) NOT NULL", schema)
        self.assertIn("DROP PROCEDURE IF EXISTS UserLogin", schema)
        self.assertIn("CREATE PROCEDURE BeginUserLogin", schema)
        self.assertIn("CREATE PROCEDURE CompleteUserLogin", schema)
        self.assertNotIn("AND password = p_password", schema)


if __name__ == "__main__":
    unittest.main()
