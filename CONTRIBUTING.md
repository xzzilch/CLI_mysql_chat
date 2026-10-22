# Contributing

## Before opening a pull request

- Keep changes focused and explain user-visible behavior changes.
- Never commit passwords, tokens, certificates, database dumps, or populated `.env` files.
- Update the README when setup or runtime behavior changes.
- Add or update dependency-free tests where practical.
- Run the local checks:

```sh
python -m unittest discover -s tests -v
python -m py_compile chat_functions.py msgcli.py terminal_ui.py HOSTONLY.py openports.py
```

Changes that modify `text_service_schema.sql` should describe the provisioning impact and whether existing installations require a schema migration or rerun.
