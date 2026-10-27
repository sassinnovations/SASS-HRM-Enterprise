# SASS HRM v4.5.0 — Account Security Center

## Upgrade details

This release preserves the v4.4.1 source modules, existing 70 individual URLs,
existing database rows, and the single top-bar **Refresh data** action. It adds
**two individual pages** and one MySQL table, without seeded users.

| Page | URL | Access |
| --- | --- | --- |
| My Account Security | `/settings/account-security` | Every authenticated employee |
| Administrator Sign-in Review | `/people/account-security-review` | Active HR administrators only |

The self-service page lists up to 30 successful account sign-ins and allows
revocation of all prior JWTs, including the current session. The administrator
page supports search by name, staff code, or sign-in email, filters for active,
inactive, or accounts with no recorded login, and shows limited login history.

**Privacy:** The activity table contains only employee ID and successful login
timestamp. It does not store passwords, hashes, tokens, IP addresses, device
fingerprints or geolocation. Events are pruned for an account on its next
successful sign-in; they are not a continuous device/session inventory. Existing
sessions remain protected by the existing JWT session-version checks.

**Limitations:** No MFA, SSO, real-time login alarms, scheduled cleanup, or device-level
session selection is provided. Login history starts after installing v4.5.
Admin sign-in review is informational: HR should not infer an employee's
performance or attendance from login counts.

## Backup and migration for an existing installation

1. Confirm you have a verified restore-capable MySQL backup and preserved `.env`.
2. Run `CHECK_FULL_MYSQL_SCHEMA.bat` in the extracted project **read-only**.
3. Earlier deployment reported 88/104 tables and `employees.work_email` absent.
   **Fix and verify the old mismatch using the separate safe v4.4.1 migration**
   before relying on new features. The expected v4.5 schema is 105 tables,
   including all earlier tables.
4. For only the new security table, inspect
   `database/02_account_security_activity_v45_UPGRADE.sql`. Check selected
   database is `sass_hrm`. Apply only with authorization, after a backup.
   On startup, the API's existing MySQL schema manager also attempts additive
   `CREATE TABLE IF NOT EXISTS` for the expected schema.
5. Re-run the read-only schema checker and verify 105 expected tables and no
   missing columns. Do not run fresh-install SQL on an existing database.
6. Start the project with `START_DOCKER_FULL.bat` and visit the URLs above.

## Verification

`CHECK_SECURITY_CENTER_V45.bat` tests new security scope and revocation,
MySQL schema source coverage, navigation, single refresh, and packaging.
The isolated test creates disposable SQLite state: it does **not** change live
MySQL. Runtime validation still requires login/revocation in your own Docker
browser and verification that the MySQL schema repair completed successfully.

## Manual smoke test

- Create two employee accounts with valid passwords using Account Provisioning.
- Sign in twice on one employee account: its Security Center should show two
  recent successful sign-ins.
- Sign in with the other account: it must not see the first account's records.
- An employee must receive 403 on the admin review endpoint.
- Administrator review should show only limited account metadata.
- Click **Sign out all sessions**: existing tokens should stop working and
  the browser should return to the login screen.
- Sign in again and verify new activity; press the single **Refresh data** control.
- Verify unauthorized direct URLs show Access Restricted, not administrator data.
