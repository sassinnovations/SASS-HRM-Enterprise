# SASS HRM — Employee / HR / Administrator signup + MySQL setup

This is the **existing v4.6 SASS HRM project with an expanded signup-settings patch**, not a new application or a database reset. It keeps existing screens and modules.

## What is included

- `/sign-in` has **Create Employee / HR / Admin account** immediately under Sign In.
- `/sign-up` shows three explicit role choices and a full applicant form (name, sign-in email, work email, role, designation, department, location, work mode, password and confirmation).
- New requests go into the **MySQL** `account_signup_requests` table with status `Pending`, a salted password hash, dates and review fields. They do **not** create a login yet.
- An existing HR Administrator opens **People Management → Account Provisioning** to review an applicant, approve or reject it. Admin approvals require a written note of the independent identity check. Approval inserts an active `employees` record and matching `account_access_tiers` record; the signup request is updated to `Approved` and its duplicate password hash is cleared. Employees receive a generated `SASS-...` staff ID and database-generated numeric ID.
- HR Sub-Admin is stored as the limited `manager` role, not full administrator.
- **Public sign-up settings** are on that same Account Provisioning page: enable/disable public signup, individually allow Employee / HR Sub-Admin / HR Administrator requests, and optionally restrict sign-in and work emails to one company domain. Settings persist in `account_signup_settings` and are checked **server-side**, not just hidden in the browser.
- Expired pending signup requests older than 14 days are redacted and marked `Expired` when the applicant retries, allowing a new application. Administrators can filter their review list by status.

## IMPORTANT: Existing installations — preserve all data

1. Stop editing configuration while the stack is running. Make a **verified backup** of the existing MySQL database with `BACKUP_MYSQL.bat` and retain a copy of your existing project `.env`, `server/.env`, and Docker named MySQL volume. Verify that a backup can be restored separately.
2. Extract this ZIP to **a new folder**. Do not copy the example `.env` values over your existing secrets or reset MySQL. Transfer your **existing** environment configuration according to `docs/V4_4_1_SAFE_SCHEMA_REPAIR.md`. The database name and credentials must match between configuration files; do not blindly overwrite a live MySQL user password.
3. Start Docker Desktop. In VS Code, open the extracted `SASS_HRM_Enterprise` folder and run `CHECK_FULL_MYSQL_SCHEMA.bat` to inspect the current database. If your existing schema is incomplete, follow the guarded additive-repair workflow described in the documentation. **Do not use `02_FRESH_INSTALL_ALL_IN_ONE.sql` on a populated database.**
4. The new policy table's standalone DDL is `database/04_signup_settings_v47_ADD_ONLY.sql`. The existing signup-request table's additive DDL is `database/03_signup_requests_v46_ADD_ONLY.sql`. The full bundled DDL also includes both and is applied at service initialization. Use the guarded installer only after backup and preflight. Do not apply SQL blindly if prerequisite tables or columns are missing.
5. Start or rebuild with `START_DOCKER_FULL.bat`. In a local development deployment, open **http://localhost:5173/sign-in** and click **Create Employee / HR / Admin account**, or open **http://localhost:5173/sign-up** directly.
6. Submit the form for one account type. This displays an acknowledgement but does not yet permit sign-in.
7. Log in with an **existing authorized HR administrator** account. If this is a truly empty installation with no administrator, use `CREATE_ADMIN.bat` to bootstrap one according to the README. On **People Management → Account Provisioning**, review identity, save sign-up settings if desired, and choose **Verify & approve** or **Reject**. Do not approve an unsolicited administrator request.
8. After approval, sign in using the new account's email and selected password. Rejected or pending requests cannot sign in.

## MySQL Workbench verification (read-only queries)

Use your configured local MySQL Workbench connection (Docker example uses host `127.0.0.1`, port `3307`; verify your `.env` for the correct host, port, database and app user). Avoid printing or exporting password hashes.

```sql
USE sass_hrm;
SELECT id, name, email, work_email, requested_role, department, designation,
       location, work_mode, status, created_at, reviewed_at, reviewed_by, employee_id
FROM account_signup_requests ORDER BY id DESC LIMIT 20;

SELECT enabled, allow_employee, allow_hr_subadmin, allow_admin,
       allowed_email_domain, updated_at, updated_by
FROM account_signup_settings WHERE id = 1;

SELECT e.id, e.code, e.name, e.email, e.work_email, e.role, e.account_active,
       t.tier AS requested_access_tier
FROM employees AS e LEFT JOIN account_access_tiers AS t ON t.employee_id=e.id
ORDER BY e.id DESC LIMIT 20;
```

## Run isolated verification

Double-click `CHECK_SIGNUP_V46.bat` to run the expanded signup tests plus schema, page routing, and refresh checks. They use temporary test data and do not touch your live MySQL database. `CHECK_FULL_MYSQL_SCHEMA.bat` and `VERIFY_LIVE_MYSQL.bat` are for the actual installation.

## Safety and limits

- **Admin registration is a request, not an anonymous administrator creation**. Never allow public signup to grant admin access directly.
- Raw passwords are never stored. Both the request and approved employee use PBKDF2 salted hashes; the copy in a reviewed request is redacted.
- Company email domain restrictions are **not email ownership verification**. Verify identity and corporate authorization with independent records before approval.
- Before public Internet exposure, add verified email ownership, application gateway rate limiting and/or CAPTCHA, TLS, secure secrets and deployment security review. This build is **not certified for production Internet exposure**.
- This package was tested with SQLite-isolated FastAPI signup flows and source-level checks. The actual MySQL/Docker browser environment was not available here. Run the live scripts on your computer before using real employee data.
