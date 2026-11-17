# SASS HRM Enterprise v4.6.0 — Account sign-up and admin approval

## What changed

The public sign-in screen includes **Create account**, accessible at `/sign-up`.
Applicants provide their name, sign-in email, optional work email, department, designation, location, work mode, requested account role, and password + confirmation. No account is immediately activated.

Publicly selectable requests: **Employee**, **HR Sub-Admin**, **HR Administrator**. These are only requests; the role does not grant any access until approval by an already authenticated administrator. Developer Admin is not publicly selectable.

An administrator opens **People Management → Account Provisioning** to review pending requests. After independently confirming the applicant's identity and authority, HR can approve or reject. An approved request creates an active `employees` record and a role record in `account_access_tiers` using the already hashed password. Login by sign-in or work email is supported by the existing system. Staff code and MySQL employee ID are assigned on approval. A rejection does not create a login account. Reviewed request password hashes are replaced with `REDACTED`.

## MySQL changes

Two **additive** tables now ship in the enhanced package: `account_signup_requests` and `account_signup_settings`. The latter is managed from People Management → Account Provisioning and stores signup availability, allowed roles and an optional email-domain restriction. Original request table: `account_signup_requests` with a request ID, name, requested role, email identities, work details, salted password hash, status, timestamps, reviewer, and linked employee ID. Total expected source schema in the enhanced package is **107 MySQL tables**. The full project schema lives in `server/mysql_schema.sql` and `database/01_application_schema.sql`; standalone add-only SQL is `database/03_signup_requests_v46_ADD_ONLY.sql`.

Do not run a fresh-install schema over your populated database. Your previously reported database was incomplete (88 of 104 older tables, missing `employees.work_email`). Back up and repair existing schema first with the guarded v4.4.1 workflow before upgrading to v4.6. **No local MySQL data was accessed or modified during this build.**

## Browser workflow

1. Start the **verified** Docker stack and sign in to a valid administrator account.
2. On `/sign-in`, select **Create account** or directly open `/sign-up`.
3. Enter details, requested role, password, and confirmation. Submit. A generic pending-review confirmation appears; no automatic login.
4. As an administrator open **People Management → Account Provisioning**. Review the applicant's provided identity using independent company records. Do not approve unsolicited administrator requests.
5. Select **Verify & approve** or **Reject**. Approved accounts receive an employee code and can sign in using the password set during sign-up.
6. Test employee sign-in and ensure employees and HR Sub-Admins cannot access privileged administrator APIs.

## Security and production considerations

- No anonymous administrator creation or public promotion is permitted.
- Passwords are PBKDF2 salted hashes; never return them through APIs or browser storage.
- Lists and decisions require `require_hr`; submissions are unauthenticated by design.
- Public success responses are generic, including for existing accounts, to avoid enumerating employees.
- Same-email pending requests are deduplicated; same-email requests are limited across a 24-hour window.
- Approval of a request older than 14 days is refused.
- Real-world identity verification is an operational requirement; the confirmation prompt is not proof of identity.
- Prior to exposure on the public Internet, deploy rate limiting or a CAPTCHA, verified organizational email ownership, TLS and a security review. **Public signup without email verification is not production-ready.**
- This source release was checked using isolated SQLite backend and static TypeScript checks. A full Vite build and live MySQL/docker/browser test still need verification on your installation.

## Additional signup settings patch (2026-10-29)

The sign-in screen now displays an explicit **Create Employee / HR / Admin account** action. The signup form uses selectable role cards and reads the server's public signup policy. Logged-in HR administrators can enable/disable all signup, choose eligible roles and configure an allowed email domain; the API checks this policy on every public submission. The settings are in `account_signup_settings`, with add-only DDL in `database/04_signup_settings_v47_ADD_ONLY.sql`. The request queue includes Expired status. Admin-role approvals now require a written authorization-verification note. See root `SIGNUP_INSTALL_GUIDE.md` for safe upgrade instructions.
