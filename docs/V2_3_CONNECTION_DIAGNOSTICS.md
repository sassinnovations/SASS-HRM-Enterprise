# SASS HRM Enterprise v2.3 — SQLite warning and release mismatch remediation

## Why SQLite appeared in Company setup
The v2.2 backend rejects SQLite except when explicitly put into isolated test mode (`SASS_HRM_TESTING=1`). Seeing SQLite on the screenshot therefore suggests a legacy/testing API on port 8000 or a different application copy serving the browser. The UI was rendering the value reported by the API; switching only the display text would conceal a database error and **would not migrate data**.

## Improvements
- API `/api/health` reports `version=2.3.0` and actual connected database engine. It fails if the database is unreachable.
- Admin setup reports API version, database engine, readiness checks and targeted links for incomplete setup categories.
- Company profile saving and CSV preview/commit are disabled in Company setup unless the reported engine is MySQL **and** backend release matches `2.3.0`; other modules still require normal server authorization.
- `DIAGNOSE_CONNECTION.bat` inspects Windows processes listening on ports 5173/8000/3307, both health endpoints and Docker Compose status without killing processes or changing records.
- Docker's read-only HTTP smoke test rejects a stale/wrong API version even if it reports healthy.
- Administrator bootstrap now asks for an explicit work email instead of shipping a person's address in a reusable template.

## Windows instructions
1. Save a separate copy of your old project and run `BACKUP_MYSQL.bat` if you have an existing MySQL database. Do not erase your MySQL Docker volume.
2. Run `DIAGNOSE_CONNECTION.bat`. If an old Vite/Python backend owns port 5173/8000, stop it from the terminal that launched it. Do not randomly terminate other programs.
3. Use the **same existing credentials** from `.env` and `server/.env` for an existing installation. The delivered ZIP does not contain secrets. First-time installs can use `SETUP_SASS_HRM.bat` to generate them.
4. Use `START_HERE.bat` to build MySQL 8.4, Python API, and React/nginx together. Open `http://localhost:5173` after all services are healthy.
5. Confirm `/api/health` at both ports displays `status: ok`, `database: mysql`, `version: 2.3.0`; then open Company setup & import and click Refresh checks.
6. Complete organization profile, departments, leave entitlements, approved policies and SMTP provider configuration, then import a reviewed sample-free CSV.

## Verification and limits
Python regressions use isolated SQLite synthetic databases; they do not prove live MySQL mutations. This workspace cannot run the Docker Engine or perform real browser/database integration. Frontend build also requires npm packages, which may require npm network access. The 7 readiness indicators are initial operational checks, **not** proof of privacy, security, payroll tax compliance or deployment fitness. No seeded/demo employee records are added. Always test a backup restoration outside your live MySQL volume.
