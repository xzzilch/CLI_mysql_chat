import os
from getpass import getpass

import mysql.connector

from chat_backend import _derive_password_verifier


def _connection_settings():
    host = os.environ.get("TEXTSERVICE_DB_HOST", "localhost").strip()
    try:
        port = int(os.environ.get("TEXTSERVICE_DB_PORT", "3306"))
    except ValueError:
        raise ValueError("TEXTSERVICE_DB_PORT must be a number from 1 to 65535") from None
    if not 1 <= port <= 65535:
        raise ValueError("TEXTSERVICE_DB_PORT must be a number from 1 to 65535")

    settings = {
        "host": host,
        "port": port,
        "user": input("Database administrator username: ").strip(),
        "password": getpass("Database administrator password: "),
        "database": "text_service_db",
        "connection_timeout": 5,
    }
    if host not in {"localhost", "127.0.0.1", "::1"}:
        ca_file = os.environ.get("TEXTSERVICE_DB_SSL_CA")
        if not ca_file:
            raise ValueError("TEXTSERVICE_DB_SSL_CA is required for remote database connections")
        settings.update(ssl_ca=ca_file, ssl_verify_cert=True, ssl_verify_identity=True)
    return settings


def migrate():
    connection = None
    cursor = None
    try:
        connection = mysql.connector.connect(**_connection_settings())
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SHOW COLUMNS FROM users")
        columns = {row["Field"] for row in cursor.fetchall()}
        if "password" not in columns:
            if {"password_salt", "password_verifier"}.issubset(columns):
                print("Password migration is already complete.")
                return True
            raise RuntimeError("users table has neither legacy nor verifier password columns")

        if "password_salt" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN password_salt BINARY(16) NULL")
        if "password_verifier" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN password_verifier BINARY(32) NULL")

        cursor.execute(
            "SELECT user_id, username, password FROM users "
            "WHERE password_salt IS NULL OR password_verifier IS NULL"
        )
        pending = cursor.fetchall()
        migrated = []
        for row in pending:
            try:
                salt = os.urandom(16)
                verifier = _derive_password_verifier(row["password"], salt)
            except (TypeError, ValueError):
                raise ValueError(
                    f"Cannot migrate password for account {row['username']!r}; "
                    "it must be between 12 and 255 characters. No credentials were changed."
                ) from None
            migrated.append((salt, verifier, row["user_id"]))

        if migrated:
            cursor.executemany(
                "UPDATE users SET password_salt = %s, password_verifier = %s WHERE user_id = %s",
                migrated,
            )
        connection.commit()

        cursor.execute(
            "SELECT COUNT(*) AS missing FROM users "
            "WHERE password_salt IS NULL OR password_verifier IS NULL"
        )
        if cursor.fetchone()["missing"]:
            raise RuntimeError("Some accounts still lack migrated password verifiers; legacy column retained")

        cursor.execute("ALTER TABLE users MODIFY password_salt BINARY(16) NOT NULL")
        cursor.execute("ALTER TABLE users MODIFY password_verifier BINARY(32) NOT NULL")
        cursor.execute("ALTER TABLE users DROP COLUMN password")
        connection.commit()
        print(f"Migrated {len(migrated)} account password(s); plaintext password column removed.")
        return True
    except (mysql.connector.Error, OSError, RuntimeError, ValueError) as error:
        if connection and connection.is_connected():
            connection.rollback()
        print(f"Password migration failed: {error}")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


if __name__ == "__main__":
    raise SystemExit(0 if migrate() else 1)
