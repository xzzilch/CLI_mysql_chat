#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
    printf '%s\n' "Run ./install_unix.sh first."
    exit 1
fi
exec .venv/bin/python chat_cli.py
