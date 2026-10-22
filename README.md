# MySQL Text Service

A small terminal chat client backed by MySQL stored procedures. The interactive chat screen uses Python's standard-library `curses` module; there are no extra TUI packages.

This project was built primarily with AI coding agents.

## Easy install

No Git command or GitHub account is required. You can either download the [project ZIP](https://github.com/xzzilch/CLI_mysql_chat/archive/refs/heads/main.zip) in your browser and extract it, or use the two-command setup below. Python 3.10 or later and an internet connection are required. On Windows, install Python from [python.org](https://www.python.org/downloads/) and enable **Add Python to PATH**.

### macOS/Linux

Run this first line to download, extract, and install. Run the second line for a new database; if your database is already provisioned, replace it with `./start_chat_unix.sh`.

```sh
curl -fL https://github.com/xzzilch/CLI_mysql_chat/archive/refs/heads/main.zip -o cli-chat.zip && project_dir=$(unzip -Z1 cli-chat.zip | sed -n '1s,/.*,,p') && unzip -q -o cli-chat.zip && cd "$project_dir" && chmod +x install_unix.sh start_chat_unix.sh && ./install_unix.sh
.venv/bin/python provision_database.py && ./start_chat_unix.sh
```

### Windows PowerShell

Run this first line to download, extract, and install. Run the second line for a new database; if your database is already provisioned, replace it with `& .\start_chat_windows.bat`.

```powershell
$ErrorActionPreference = 'Stop'; Invoke-WebRequest https://github.com/xzzilch/CLI_mysql_chat/archive/refs/heads/main.zip -OutFile cli-chat.zip; Expand-Archive cli-chat.zip -DestinationPath . -Force; Set-Location CLI_mysql_chat-main; .\install_windows.bat
& .\.venv\Scripts\python.exe provision_database.py; if ($?) { & .\start_chat_windows.bat }
```

The installer creates a local `.venv` and installs dependencies without changing system-wide Python packages. It does not provision a database automatically because that step needs administrator credentials. During provisioning, it securely prompts for the database administrator and client DB passwords; chat startup prompts for the client DB password if it has not been configured in the environment.

If you downloaded the ZIP in a browser instead, extract it, run `install_windows.bat` on Windows or `./install_unix.sh` on macOS/Linux, then use the appropriate provision/start commands above.

The TUI uses Python's standard library; Windows installs the small `windows-curses` compatibility package automatically.

## Database setup

You need access to a MySQL-compatible database. For a new database, run the provisioning tool from the extracted project folder:

```sh
.venv/bin/python provision_database.py
```

On Windows use:

```bat
.venv\Scripts\python.exe provision_database.py
```

The setup prompts for the database administrator account and the new client DB password. Passwords are entered without showing them on screen. The client password must be 16-128 characters using letters, numbers, and `!@#$%^&*()_+=.-`. Provisioning is non-destructive to existing database contents, but it replaces stored procedures and resets the `client_user` password.

The schema lives in `text_service_schema.sql`. `DB_METADATA.json` contains the database name used by the SQL formatting helper; the current schema selects `text_service_db`.

### Existing installations

For an existing database created by an older version, back it up and run the one-time password migration before provisioning the new schema:

```sh
.venv/bin/python migrate_passwords.py
```

On Windows use `.venv\Scripts\python.exe migrate_passwords.py`. The migration prompts for database administrator credentials, derives salted PBKDF2 verifiers locally, and removes the old plaintext password column only after all accounts are migrated. Existing accounts are preserved. If a password is outside the supported 12-255 character range, migration stops; resolve that account before retrying. After migration succeeds, run the provisioning tool.

## Run the client

Start the chat:

```sh
./start_chat_unix.sh
```

On Windows, double-click `start_chat_windows.bat`. The first launch prompts for the client DB password; you can also set `TEXTSERVICE_DB_PASSWORD` ahead of time. Optional connection settings are:

- `TEXTSERVICE_DB_HOST`: database host; defaults to `localhost`.
- `TEXTSERVICE_DB_PORT`: database port; defaults to `3306` and must be between 1 and 65535.
- `TEXTSERVICE_DB_USER`: client account; defaults to `client_user`.
- `TEXTSERVICE_DB_SSL_CA`: CA certificate path. Required for non-local hosts; the client verifies the server certificate and hostname.

For example, configure a remote host without embedding credentials in a command or file:

```sh
export TEXTSERVICE_DB_HOST=db.example.net
export TEXTSERVICE_DB_SSL_CA=/path/to/database-ca.pem
python chat_cli.py
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
python -m py_compile chat_backend.py chat_cli.py terminal_ui.py provision_database.py port_utils.py migrate_passwords.py
```

A live login/chat/provisioning check additionally requires a running database server and a provisioned schema.

## Contributing and security reports

See [CONTRIBUTING.md](CONTRIBUTING.md) for the pull request checklist and [SECURITY.md](SECURITY.md) for vulnerability reporting guidance.

## License

No license has been selected yet. Until a license is added, do not assume the repository grants permission to reuse or redistribute its code.
