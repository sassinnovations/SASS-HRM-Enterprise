# SASS HRM v3.3 — reusable accounts, passwords and role selection

## Existing account creation

Sign in using a previously created administrator, open **People Management → Account provisioning**, then **Create account with password**. Enter the user’s work email and name, department, location, role, and a strong unique password twice. The new account becomes active immediately, and the user can sign in repeatedly with the same email and password until they change it or an administrator resets it.

Only existing authenticated administrators may create accounts, promote another administrator, or reset someone else’s password. The initial administrator for an empty installation still comes from `CREATE_ADMIN.bat`. The public login page never grants privileged roles.

## Effective roles

| Selection | Stored authorization | Scope |
|---|---|---|
| Administrator | admin | Full administrative HR functionality (including role and account changes) |
| HR Sub-Admin | manager, plus `hr_subadmin` access tier | Existing manager/team-level functionality; **no** organization-wide HR admin APIs, payroll configuration, or account creation |
| Manager | manager | Existing manager/team-level functionality |
| Employee | employee | Personal, employee-scoped functionality |

The role tier is persisted in `account_access_tiers` and returned through `/api/auth/me` and the account admin listing, but server-side authorization uses the original validated role. The restricted HR Sub-Admin option is **not** the same as an unrestricted HR administrator.

## Password security

Passwords are stored as salted PBKDF2-SHA256 hashes in the employee table. They are never returned by API responses, cannot be read back, and are not written into the ZIP or browser storage. The create-account dialog validates confirmation locally and discards it after submitting. Passwords are reusable for sign-in; they do not have to be reset every time.

**Set password** on an account is a privileged reset: it activates the account, revokes previous JWT sessions, expires outstanding invitations and recovery tokens, and writes an audit event without recording the password itself. A user who knows their existing password can change it in **My Settings**.

## Login account selection

The login page has an optional **Remember this account email on this device** checkbox. When enabled, it remembers only email addresses in that browser’s local storage, allowing users to select an email before signing in. Users still type their passwords, or use their own trusted browser password manager. Do not choose it on a shared/public computer. Saved account emails can be removed from the login screen.

## Safe upgrade for existing HRM

1. Back up your persistent MySQL data and protect existing `.env` and `server/.env` files.
2. Extract the v3.3 ZIP to a new folder; restore only your own private configs. Never remove volumes or reset MySQL just for this upgrade.
3. Start Docker Desktop and run `START_DOCKER_FULL.bat`. The new `account_access_tiers` table is additive; no stored employees or passwords are rewritten.
4. Verify the API reports v3.3.0 from `/api/health` and sign in with your existing administrator.
5. Test creating an employee and an HR Sub-Admin, sign in independently, and verify their restricted permissions. Use `CHECK_ACCOUNTS_V33.bat` for isolated security regression tests.

**Remaining validation:** live Docker/MySQL startup, external SMTP delivery, TLS configuration for hosted use, browser navigation, and a full Vite production build require execution in your environment. Do not collect employee credentials over plain HTTP on a public website.
