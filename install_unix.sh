#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' "Python 3.10 or later is required. Install Python 3 and try again."
    exit 1
fi
if ! python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
    printf '%s\n' "Python 3.10 or later is required."
    exit 1
fi

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

printf '\n%s\n' "Installation complete." "Start the chat with ./start_chat_unix.sh" \
    "To provision a new database: .venv/bin/python provision_database.py"
