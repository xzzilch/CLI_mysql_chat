# Security Policy

## Supported versions

Security reports are accepted for the current `main` branch. No release support policy is established yet.

## Reporting a vulnerability

Please do not open a public issue containing credentials, exploit details, or personal data. Contact the repository owner privately through the GitHub account that owns this repository and include:

- A description of the affected component and impact.
- Steps to reproduce using a local or otherwise authorized environment.
- Any suggested mitigation.

Do not include real passwords, session tokens, production data, or database dumps in a report.

## Known security limitation

The schema stores per-user PBKDF2-HMAC-SHA256 password verifiers and uses challenge-response login. The verifier is still credential-equivalent if both the database contents and a client DB account are compromised; keep DB access restricted and use TLS for remote connections. A stronger boundary would require authentication in a separate trusted service or a reviewed PAKE/SCRAM implementation.

Existing installations must run `migrate_passwords.py` before applying the updated schema. Do not run the schema update against a legacy database until the migration has completed and a backup is available.
