# SASS HRM Enterprise v3.4.0 — Administration Settings Center

## New settings features

**Administration Settings Center:** `/people/admin-settings-center`. HR administrators can navigate to every existing configuration area and see ten non-sensitive setup indicators based on saved records. A setup indicator is not a security, compliance, or integration certification.

**Talent & Employee Services Settings:** `/people/talent-service-settings`. HR administrators can edit **22 validated configuration values** covering six operational areas:

1. Recruitment ATS & interview follow-up guidance
2. Onboarding and joining checklist review targets
3. HR helpdesk, escalation and Request Desk guidance
4. HR tasks and offboarding review targets
5. Employee documents, assets and profile review guidance
6. Policy review and announcement guidance

Values are stored as a validated JSON document in the new **`talent_service_settings`** MySQL table, with the last editor and UTC update time. The backend enforces administrator permissions for reading and editing. Audit events log **changed field names only**, not free text. Managers and employees cannot read or change these admin-only configuration values.

In the existing Talent Tools UI, the onboarding-template creation form uses the saved suggested due offset, and the HR helpdesk triage form initially proposes a due date based on the saved service review target. Users can still change these dates. These controls are guidance, **not** automatic approval, background notifications or statutory compliance rules.

All existing Organization, Compensation, Workspace Workflow, Account Provisioning and Profile Management pages remain present and can be opened from the new hub.

## What remains outside scope

- No background SLA escalations, notifications, candidate screening decisions, payroll decisions, tax determinations, legal policy enforcement or data deletion are added.
- MFA/SSO, SMTP delivery, file encryption and statutory payroll compliance still need operational integrations and specialist review.
- No live MySQL 8.4 execution, Docker startup, production Vite build or interactive browser testing has been completed in this environment. Static checks and isolated SQLite tests do not prove full deployment readiness.

## Safe upgrade (existing installations)

1. Back up the existing MySQL database and **test restoring that backup to another instance**. Preserve the private `.env` and `server/.env` files **outside the extracted ZIP**. Keep the existing Docker volume and do not run first-time setup.
2. Extract v3.4.0 into a new folder. Copy private configuration to the matching locations securely (do not put credentials in Git or shared ZIPs).
3. Run `CHECK_ADMIN_SETTINGS_V34.bat` for source and synthetic-DB checks.
4. Start Docker Desktop and run `CHECK_FULL_MYSQL_SCHEMA.bat` against your configured MySQL instance. The read-only verification should expect **87 tables and 565 declared columns**. If the only missing object is `talent_service_settings`, use the explicit `INSTALL_FULL_MYSQL_SCHEMA.bat` **after verifying a backup**, or apply the reviewed additive DDL from `database/01_application_schema.sql`. The installer does not delete employee records, but MySQL DDL changes may not roll back.
5. Run `CHECK_FULL_MYSQL_SCHEMA.bat` again. Do **not** reset the database if an existing table reports a missing column; develop a reviewed additive column migration.
6. Run `START_DOCKER_FULL.bat`, then verify `http://localhost:8000/api/health` reports v3.4.0 and that `http://localhost:5173/people/admin-settings-center` opens for an admin. Navigate to `/people/talent-service-settings`, save a test setting, reload, and confirm it persisted.
7. Verify permissions using a separate employee account; admin settings APIs and pages must reject ordinary employees and managers. Review the Audit Trail for `admin.talent_settings.updated`.

## Source-only automated checks

```powershell
.\CHECK_ADMIN_SETTINGS_V34.bat
.\VERIFY_EVERYTHING.bat
```

The second command needs network access for `npm ci` on a fresh system and performs the frontend production build. Isolated tests use synthetic temporary SQLite databases, not your HRM production MySQL database.

## Tables and schema

The old release shipped 86 tables, 561 columns. v3.4 adds exactly one new table (4 columns): `talent_service_settings`. The bundled `server/mysql_schema.sql`, `database/01_application_schema.sql`, `database/02_FRESH_INSTALL_ALL_IN_ONE.sql` and table inventory have all been updated together. The full fresh-install SQL **must not** be used as a migration on an existing DB.
