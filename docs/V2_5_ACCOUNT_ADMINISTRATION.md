# SASS HRM Enterprise v2.5.0 — Identity and Account Administration

This release **preserves every existing v2.4 HRM menu/module and MySQL volume**, and adds role-checked account administration and password recovery. It does not ship credentials, real accounts, seeded staff, tokens or generated databases.

## Security and database passwords

- **Fresh Windows installation:** Run `SETUP_SASS_HRM.bat` *once*. It calls `scripts/setup-real.ps1` to generate distinct high-entropy MySQL application/root passwords and a 96-character random JWT signing secret, saving them only in `.env` and `server/.env` (which are gitignored and omitted from this ZIP).
- **Existing installation:** Keep the original `.env`, `server/.env`, and Docker MySQL named volume. Make a backup before applying code changes. Never overwrite/reset secrets arbitrarily: existing MySQL user passwords remain those configured when the volume was initialized, and abruptly replacing `JWT_SECRET` logs users out. Never use `docker compose down -v` on a real deployment.
- `MYSQL_PASSWORD` in root `.env` and `server/.env` must agree. They are not account passwords. Individual employee passwords are salted PBKDF2-HMAC-SHA256 hashes (350,000 iterations), not database environment variables.
- Secrets are not shown in API responses. `JWT_SECRET` must be at least 40 characters long. Every signed JWT includes issuer, expiry, employee ID and a session version; backend permissions and account status are checked on every authenticated request.
- To verify credentials without revealing secrets use `CHECK_SECURITY_SETUP.bat`; after Docker startup use `CHECK_CONNECTION.bat`, `CHECK_MYSQL.bat`, `DIAGNOSE_CONNECTION.bat` and `/api/health` after Docker is running. Do not post contents of `.env` into issue reports.

## Administrator first-time setup

1. Install/start Docker Desktop in **Linux containers** mode, then run `SETUP_SASS_HRM.bat` for *fresh installs only*.
2. Run `START_MYSQL.bat` (or `START_DOCKER_FULL.bat`, after Docker is ready). You must have a working MySQL engine for a real deployment.
3. Run `CREATE_ADMIN.bat` one time on a completely empty database. You enter the first administrator's email/name and choose a new, non-shared strong password **at the terminal prompt**; no default SASS login is provided.
4. Use `START_DOCKER_FULL.bat`, open `http://localhost:5173` and sign in with your administrator's email/password. Configure your SMTP provider before emailing invitations or resetting passwords.
5. On the left navigation open **Account administration**. Create inactive staff, managers and further HR administrators, then send one-time invitation emails to each intended person.

**Do not** rerun the fresh-install script or first-account bootstrap over existing staff data. No user account is created or changed automatically by updating the ZIP.

## Administrative features (backend permissions enforced)

| Feature | Where | Role/security |
|---|---|---|
| Create employee, manager and HR admin sign-in records | Account administration → Create account | HR admin; starts inactive, no displayed password |
| Send activation invitation | Account administration → Email invite | HR admin; SMTP/TLS delivery, 48-hour single-use token, only token hash stored |
| Activate invitation | Login → Activate employee account | Invitation token + chosen 12+ character password |
| Assign HR admin / manager / employee role | Account administration → Change role | HR admin; invalidates existing JWT sessions; protects last admin and reporting lines |
| Suspend/reactivate identity | Account administration | HR admin; invalidates sessions; prevents suspension of last admin |
| Force logout on all devices | Account administration → Revoke sessions | HR admin; server-side session version increment |
| Developer diagnostics access | Account administration → Grant/Remove developer access | HR admin except self; diagnostics are read-only; grant requires admin role |
| Reset forgotten password | Login → Reset password | Work email + SMTP, 30-minute single-use token; old sessions invalidated |
| Change own password | Settings | Requires current password; old sessions invalidated |
| Sign out all devices | Sidebar / Settings → Sign out | Signed-in user; revokes previously issued JWTs |
| Identity audit entries | Audit trail | HR admin; creates audit events for account actions |

**Important:** `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` and `PUBLIC_APP_URL` in `server/.env` must be configured with a secure email provider before invitations and password reset emails work. Reset responses do not reveal whether an email is registered. No password or token is returned in the API.

## API additions

- `POST /api/admin/accounts/create`
- `PATCH /api/admin/accounts/{employee_id}/role`
- `POST /api/admin/accounts/{employee_id}/revoke-sessions`
- `PATCH /api/admin/accounts/{employee_id}/developer`
- `POST /api/auth/logout`
- `POST /api/auth/password-reset/request`
- `POST /api/auth/password-reset/confirm`

The `password_reset_tokens` table is **additive** and is installed automatically in MySQL using `CREATE TABLE IF NOT EXISTS` on startup. No existing employee rows are modified by schema installation.

## Verification & boundaries

- `server/accounts_v25_test.py` tests admin and employee permissions, duplicate accounts, activation and reset one-time secrets, developer role checks, JWT revocation, password changes and audit logging on isolated test-only SQLite.
- Existing backend regression tests and TypeScript (`tsc --noEmit`) are run separately.
- A real **Docker/MySQL** startup, SMTP provider connection, browser UI clickthrough and full frontend production build still require the deployed environment. The project should not be called production-ready without security review, HTTPS, backups, controlled migrations and enterprise MFA/SSO integration. Rate limits on password resets should also be backed by an edge/IP level limiter in publicly accessible deployments.
