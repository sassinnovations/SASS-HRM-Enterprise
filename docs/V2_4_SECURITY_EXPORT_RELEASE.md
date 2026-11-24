# SASS HRM Enterprise v2.4.0 — Security and CSV exports

## Preserved
All existing HRM menus, screens, database tables, identities, and workflows are unchanged. No migration or sample records are required. The old v2.3.0 ZIP remains separate from this deliverable.

## Fixes
1. Removed previously bundled `.env` and `server/.env` credentials. Only `.env.example` templates ship. This **does not rotate** credentials used by an existing MySQL database. If the old ZIP was shared, rotate affected credentials using an approved, coordinated deployment process and invalidate compromised JWT secrets. For a fresh install, run `SETUP_SASS_HRM.bat`, then follow README. Existing deployments must preserve their old configuration files outside the ZIP and back up the database before upgrading; never use the fresh-install setup over an existing installation.
2. Removed Windows-specific `web/node_modules` and stale build outputs. Docker frontend now installs reproducibly using the committed `package-lock.json` via `npm ci` and excludes dependency caches from the Docker context. CI and first-time Windows setup also use `npm ci`.
3. Added the missing `REPAIR_FRONTEND.bat` which regenerates machine-specific dependencies and verifies frontend build; it does not touch backend, database, or source files.

## New features
- **My attendance CSV** in Time & attendance: authenticated personal-only export for the previous 365 days, with optional API query dates `start` and `end` (YYYY-MM-DD, <=366-day range).
- **Audit trail CSV** in Audit trail: HR administrator-only export of the most recent 500 events (optional `limit` 1-1000). Export events are logged.
- All CSV files include spreadsheet-formula injection guards, no-store response headers, and stable column headings; both endpoints use existing authorization rules and schema.

## Verification
Run `VERIFY_EVERYTHING.bat` on Windows; or `python server/exports_v24_test.py` from the `server` folder with dependencies installed, and `npm ci && npm run build` from `web`. A complete MySQL/Docker/browser rollout check still requires those services locally.

## Security limitation
No external production security certification, SMTP delivery check, regulatory payroll compliance, or production SSO/MFA is implied. Do not publish personnel or payroll data without a formal review.
