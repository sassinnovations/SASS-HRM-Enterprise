# SASS HRM v4.3.0 — MySQL Account Identity & Administration

## Supported account tiers

- **HR Administrator (`admin`)**: full HR administration, account provisioning.
- **Developer Administrator (`developer_admin`)**: an administrator with a separately granted, auditable developer-diagnostics entitlement, not a shared account or a second database.
- **HR Sub-Admin (`hr_subadmin`)**: stored as a manager with limited team scope; cannot use full administrator account APIs.
- **Manager (`manager`)**: limited team scope.
- **Employee (`employee`)**: own employee services.

All tiers share the `employees` table. `account_access_tiers` records the display tier and `developer_grants` holds separate developer access. An authenticated HR administrator can create and edit accounts, change roles, reset a user's password or send a one-time invitation. There is **no public privileged registration**.

## Saved account fields

- `employees.id`: auto-increment MySQL ID (never entered manually).
- `employees.code`: unique SASS staff code.
- `employees.email`: sign-in email.
- `employees.work_email`: separate unique work email; defaults to sign-in email for existing or simple accounts.
- `employees.name`, `designation`, `department`, `location`, `work_mode`: editable workplace information.
- `employees.password_hash`: salted, iterated PBKDF2-SHA256 credential hash; never returned by the API, and cannot be retrieved as a readable password.
- `employees.account_active` and `session_version`: deactivate accounts and invalidate old login sessions.

Users can sign in with either the sign-in email or work email and their own password. Accounts persist after sign-out and server restart because data is stored in the configured database. An account edit that changes either email invalidates earlier JWT sessions. Password changes invalidate earlier JWT sessions too. The login page can optionally remember **email addresses only**, not passwords. Password-reset email requires SMTP configuration and sends a token to the primary sign-in address.

## Safe database upgrade

1. Back up the existing MySQL database and keep existing private `.env` files and Docker volumes.
2. Extract v4.3 into a separate folder. Do not reset your database or replace the volume.
3. Start the API using the existing Docker configuration: the MySQL adapter adds `work_email`, backfills older accounts from `email`, creates a unique index, and records migration 22.
4. Check `GET /api/admin/database/status` as an administrator and verify the server reports release 4.3.0.
5. Alternatively, with API containers stopped, review and run `database/UPGRADE_V4_3_ACCOUNT_IDENTITY_ONLY.sql` against your **existing** selected database. Do not run this at the same time as the API migration.
6. For a brand-new installation only, `database/02_FRESH_INSTALL_ALL_IN_ONE.sql` defines the current complete schema. Never execute it on a populated database.
7. Sign in as an existing administrator, open **People Management → Account provisioning**, create or edit an account, select its role, verify email login, then verify password update and access restrictions.

## Limitations and security

- Do not store plaintext passwords in MySQL, docs, browser storage, source code, or exported CSV. Passwords cannot be displayed back to admins.
- MySQL 8.4 and browser functionality require testing on the actual running Docker installation. Source-level tests are not a substitute.
- This is an incremental identity workflow, not complete enterprise SSO/MFA or an external identity-provider integration.
- Role and privilege changes invalidate sessions; developer access is administrator-only and auditable.
- Staff created through CSV import remain inactive until activated through the existing invitation process.
