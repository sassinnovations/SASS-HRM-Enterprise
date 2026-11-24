# First SASS HRM administrator with developer diagnostics

This release preconfigures the nonsecret initial administrator email: **satyanath.yalamanchili@sassinnovations.com**. It does **not** preset a password or publish credential files. The previous password supplied in chat is too short (the minimum is 12 characters) and should not be reused.

## Windows setup

1. `SETUP_SASS_HRM.bat` to generate database and session signing secrets locally.
2. `START_MYSQL.bat` to start a new MySQL 8.4 database. Wait for the health check.
3. `CREATE_ADMIN.bat` to create one administrator. Supply a full display name, office location and a **new unique password** at the hidden terminal prompt. Passwords must contain 12 or more characters, including letters and digits.
4. `START_HERE.bat`; sign in with the configured work email and your new password.
5. In the sidebar, open **Developer console**. This shows only limited health/diagnostic data. HR administration remains available through the normal Admin screens.

The bootstrap uses `--developer`, which stores a dedicated `developer_grants` permission associated with the administrator's employee record. The backend validates this grant on every read-only developer API request. Merely knowing the email does not grant access.

**Existing database:** Bootstrap intentionally fails if the database already contains employees. Do not wipe an existing MySQL volume or change passwords with direct SQL. Use an authorized account migration/password reset procedure instead.

**Operational security:** Before real deployment, require MFA/SSO, signed configuration management, incident monitoring, independent security review and production database protection. No login has been created in your running MySQL server by producing this ZIP.
