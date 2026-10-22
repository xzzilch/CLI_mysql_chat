# MySQL Text Service

A small terminal chat client backed by MySQL stored procedures. The interactive chat screen uses Python's standard-library `curses` module; there are no extra TUI packages.

This project was built primarily with AI coding agents.

## Requirements

- Python 3.10 or later
- MySQL Connector/Python 9.2 or later for `HOSTONLY.py` multi-statement provisioning (`fetchsets()` is used there)
- A MySQL-compatible server with permission to create a database, tables, views, stored procedures, and the `client_user` account during provisioning

Install the Python connector in the environment used to run the scripts:

```sh
python -m pip install -r requirements.txt
```

## Provision the database

Set a strong client database password in the environment. It must be 16 to 128 characters and use only ASCII letters, digits, and `!@#$%^&*()_+=.-`. Do not put it in source files or commit it.

```sh
read -rsp 'Client DB password: ' TEXTSERVICE_DB_PASSWORD
export TEXTSERVICE_DB_PASSWORD
printf '\n'
python HOSTONLY.py
```

`HOSTONLY.py` prompts for the server host, port, administrator username, and administrator password. The client database account created by the schema is `client_user`; the app uses the password supplied through `TEXTSERVICE_DB_PASSWORD`. Provisioning is non-destructive to existing database contents, but it replaces the stored procedures and resets the `client_user` password to the supplied value.

The schema lives in `text_service_schema.sql`. `DB_METADATA.json` contains the database name used by the SQL formatting helper; the current schema selects `text_service_db`.

### Existing installations

Before applying the new schema to a database created by an older version, back it up and run the one-time password migration:

```sh
python migrate_passwords.py
```

The migration prompts for a database administrator account, derives salted PBKDF2 verifiers locally, and removes the legacy plaintext password column only after all accounts have been migrated. Existing accounts are preserved. If any existing password is outside the supported 12-255 character range, migration stops without changing credentials; resolve those accounts with the administrator before retrying. After migration succeeds, run `python HOSTONLY.py` to install the new authentication procedures. For a new database, run `HOSTONLY.py` directly.

## Run the client

Keep `TEXTSERVICE_DB_PASSWORD` set in the same shell, then start:

```sh
python msgcli.py
```

Optional connection settings:

- `TEXTSERVICE_DB_HOST`: database host; defaults to `localhost`.
- `TEXTSERVICE_DB_PORT`: database port; defaults to `3306` and must be between 1 and 65535.
- `TEXTSERVICE_DB_USER`: client account; defaults to `client_user`.
- `TEXTSERVICE_DB_SSL_CA`: CA certificate path. Required for non-local hosts; the client verifies the server certificate and hostname.

For example, configure a remote host without embedding credentials in a command or file:

```sh
export TEXTSERVICE_DB_HOST=db.example.net
export TEXTSERVICE_DB_SSL_CA=/path/to/database-ca.pem
python msgcli.py
```

The login and registration application passwords are entered with terminal echo disabled. Registration requires a username (up to 50 characters), phone number (up to 20 characters), and an application password of at least 12 characters.

## Chat controls

- Type a message and press Enter to send.
- `/help` shows available commands.
- `/quit` or `/exit` leaves the chat; Escape also exits the curses screen.
- Up/Down scroll the transcript.
- If the program is run without a TTY, it uses a basic line-oriented chat prompt instead.

## Security notes

Protected database operations require a random token issued at login and bound server-side to the active database connection. The client account is granted stored-procedure execution rather than direct table or view access. For remote connections, the Python client requires TLS certificate and hostname verification.

Application passwords are stored as per-user PBKDF2-HMAC-SHA256 verifiers (600,000 iterations) and verified using a short-lived challenge-response exchange; plaintext application passwords are not sent to the database. Treat the verifier as a credential if both the database and a client DB account are compromised. Existing installations must complete the documented migration before applying the updated schema. The chat feature has no transport-level message encryption beyond the configured database connection.

## Checks

Run the unit tests and compile the project modules with:

```sh
python -m unittest discover -s tests -v
python -m py_compile chat_functions.py msgcli.py terminal_ui.py HOSTONLY.py openports.py migrate_passwords.py
```

A live login/chat/provisioning check additionally requires a running database server and a provisioned schema.

## Contributing and security reports

See [CONTRIBUTING.md](CONTRIBUTING.md) for the pull request checklist and [SECURITY.md](SECURITY.md) for vulnerability reporting guidance.

## License

No license has been selected yet. Until a license is added, do not assume the repository grants permission to reuse or redistribute its code.
