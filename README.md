# MySQL Text Service

A small terminal chat client backed by MySQL stored procedures. The interactive chat screen uses Python's standard-library `curses` module; there are no extra TUI packages.

This project was built primarily with AI coding agents.

## Quick Start

There are two prerequisites: Python 3.10+ and access to a running MySQL-compatible server. This project installs its Python dependencies, but **does not install or start the database server**. Database provisioning requires an administrator account allowed to create a database, user, tables, views, procedures, and grants.

You do not need Git or a GitHub account. Either download and extract the [project ZIP](https://github.com/xzzilch/CLI_mysql_chat/archive/refs/heads/main.zip) in your browser, or use the two commands below. On Windows, install Python from [python.org](https://www.python.org/downloads/) and enable **Add Python to PATH**.

### macOS / Linux

First command downloads the ZIP and installs Python dependencies. Second command provisions a **new** database and starts the client:

```sh
curl -fL https://github.com/xzzilch/CLI_mysql_chat/archive/refs/heads/main.zip -o cli-chat.zip && unzip -q -o cli-chat.zip && cd CLI_mysql_chat-main && chmod +x install_unix.sh start_chat_unix.sh && ./install_unix.sh
.venv/bin/python provision_database.py && ./start_chat_unix.sh
```

For an already-provisioned database, use this as the second command instead:

```sh
./start_chat_unix.sh
```

### Windows PowerShell

First command downloads the ZIP and installs Python dependencies. Second command provisions a **new** database and starts the client:

```powershell
$ErrorActionPreference = 'Stop'; Invoke-WebRequest https://github.com/xzzilch/CLI_mysql_chat/archive/refs/heads/main.zip -OutFile cli-chat.zip; Expand-Archive cli-chat.zip -DestinationPath . -Force; Set-Location CLI_mysql_chat-main; .\install_windows.bat
& .\.venv\Scripts\python.exe provision_database.py; if ($LASTEXITCODE -ne 0) { throw 'Database provisioning failed; chat was not started.' }; & .\start_chat_windows.bat
```

For an already-provisioned database, use this as the second command instead:

```powershell
& .\start_chat_windows.bat
```

The installers create a project-local `.venv`; they do not modify system-wide Python packages. Windows also installs `windows-curses` so the terminal UI can run there. If you used the browser ZIP download, extract it first, run `install_windows.bat` or `./install_unix.sh`, then follow the matching database and launch commands above.

## Database Setup

For a new installation, `provision_database.py` first prompts (with password input hidden) for a new password for the app's `client_user`, then asks for the database host, port, and administrator username/password. The client password must be 16-128 characters and use only letters, numbers, and `!@#$%^&*()_+=.-`. The database name is `text_service_db`.

Provisioning preserves existing table data, but replaces the stored procedures and resets the `client_user` password. Keep that password available: the client prompts for it at startup unless `TEXTSERVICE_DB_PASSWORD` is set.

For an older installation that still stores plaintext application passwords, **back up the database first**, then run the migration before provisioning the new procedures:

```sh
.venv/bin/python migrate_passwords.py
.venv/bin/python provision_database.py
```

On Windows, replace `.venv/bin/python` with `.venv\Scripts\python.exe`. The migration asks for a database administrator login, derives salted password verifiers locally, and drops the legacy plaintext column only after all accounts have migrated. Existing accounts are preserved. If any existing password is outside the supported 12-255 character range, migration stops; resolve that account before retrying. Do not run the migration against a new database or an already-migrated database.

## Run the client

Start the chat after the database is provisioned:

```sh
./start_chat_unix.sh
```

On Windows, double-click `start_chat_windows.bat`. At first launch, the app securely prompts for the `client_user` database password. Registration or login then asks for an application username/password; registration also asks for a phone number.

The default database endpoint is `localhost:3306`. To connect to a remote server, set these environment variables before starting the client:

- `TEXTSERVICE_DB_HOST`: database host; defaults to `localhost`.
- `TEXTSERVICE_DB_PORT`: database port; defaults to `3306` and must be between 1 and 65535.
- `TEXTSERVICE_DB_USER`: client account; defaults to `client_user`.
- `TEXTSERVICE_DB_SSL_CA`: CA certificate path. Required for non-local hosts; the client verifies the server certificate and hostname.

For example, configure a remote host without embedding credentials in a command or file:

```sh
export TEXTSERVICE_DB_HOST=db.example.net
export TEXTSERVICE_DB_PORT=3306
export TEXTSERVICE_DB_SSL_CA=/path/to/database-ca.pem
./start_chat_unix.sh
```

PowerShell equivalent:

```powershell
$env:TEXTSERVICE_DB_HOST = 'db.example.net'
$env:TEXTSERVICE_DB_PORT = '3306'
$env:TEXTSERVICE_DB_SSL_CA = 'C:\path\to\database-ca.pem'
& .\start_chat_windows.bat
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

From the project folder, run the tests and compile the modules with:

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m py_compile chat_backend.py chat_cli.py terminal_ui.py provision_database.py port_utils.py migrate_passwords.py
```

On Windows use `.venv\Scripts\python.exe` in place of `.venv/bin/python`. A live login/chat/provisioning check additionally requires a running database server and a provisioned schema.

## Troubleshooting

- **Python not found or version too old:** install Python 3.10 or later, enable **Add Python to PATH** on Windows, then rerun the installer.
- **Download or package install fails:** confirm internet access, close and reopen the terminal after installing Python, then rerun `install_unix.sh` or `install_windows.bat`.
- **Can't connect to MySQL:** confirm the database service is running, the host and port are correct, and the account can connect from this machine. The app does not install the database server.
- **Remote connection asks for TLS CA:** set `TEXTSERVICE_DB_SSL_CA` to the database provider's CA certificate. Remote TLS certificate and hostname verification are required.
- **Client DB password rejected:** enter the password created during provisioning. It must be 16-128 characters and use only the documented allowed characters. If lost, rerun provisioning with an administrator account to reset it.
- **Schema setup fails on an older database:** make a backup; run `migrate_passwords.py` first only if the old schema has a plaintext `password` column, then run `provision_database.py`.
- **Terminal UI is cramped or unavailable:** enlarge the terminal to at least 40 columns by 8 rows. On Windows, launch from Windows Terminal or PowerShell using the provided `.bat` file.
- **ZIP command fails:** download the ZIP using the browser link in Quick Start, extract it, and run the included platform installer.

## Contributing and security reports

See [CONTRIBUTING.md](CONTRIBUTING.md) for the pull request checklist and [SECURITY.md](SECURITY.md) for vulnerability reporting guidance.

## License

No license has been selected yet. Until a license is added, do not assume the repository grants permission to reuse or redistribute its code.
