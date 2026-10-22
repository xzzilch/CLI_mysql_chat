# Contributing

## Before opening a pull request

- Keep changes focused and explain user-visible behavior changes.
- Never commit passwords, tokens, certificates, database dumps, or populated `.env` files.
- Update the README when setup or runtime behavior changes.
- Add or update dependency-free tests where practical.
- Run the local checks:

```sh
python -m unittest discover -s tests -v
python -m py_compile chat_backend.py chat_cli.py terminal_ui.py provision_database.py port_utils.py migrate_passwords.py
```

Changes that modify `text_service_schema.sql` should describe the provisioning impact and whether existing installations require a schema migration or rerun.
