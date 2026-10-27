# SASS HRM Enterprise v2.0 — Employee Services, Account Preferences & AI clarity

## Build scope
This version extends **v1.9**, preserving People Management, Talent Management, Compensation,
Culture, the real-organization bootstrap, existing database records, and SASS's white/violet theme.
No demo accounts, personal credentials, real employee records, or automatic sample data are included.

### Functional additions
- Asset management: HR-only return, repair, restore, transfer and reassign decisions.
  Asset custody changes are stored in `asset_lifecycle_events` and the existing audit trail.
  Employees may view their currently assigned assets and simplified history; prior employee
  identities and internal maintenance comments are withheld from employee views.
- Employee document register: authorized HR can verify, reject, or mark **metadata records**
  expired, with expiry dates and a durable review history. Employees can see their own statuses;
  HR-internal review notes are private. **This does not verify document authenticity or actual files**.
- Approval inbox: a role-restricted employee-services queue summarizing pending document reviews,
  returned equipment and maintenance. The existing leave/expense/attendance approvals remain intact.
- My workspace: account-owned date format, display density and reduced-motion preferences.
  Date formatting changes apply to the shared formatter; specialized forms use their own formats.
- SASS AI: capability indicator distinguishes basic account/policy lookup from separately configured
  optional LLM. Conversation remains read-only and can be cleared in browser. No automatic HR decisions.

### Storage / migration
Three **additive** MySQL tables:
`asset_lifecycle_events`, `document_review_events`, `employee_preferences`.
Schema tracking entry: **version 5**. The backend installs them on startup when MySQL is configured.
New entries are written transactionally using existing database context and server-side role checks.
No DROP statements or demo data were added.

### Test inventory
- `server/employee_services_v20_test.py` — clean synthetic SQLite database, three roles,
  change-of-custody restrictions, maintenance transitions, document privacy and mandatory rejection
  notes, settings isolation, audit entries, AI capabilities.
- The original **nine** backend regression scripts also run from `scripts/test-backend.ps1`.
- `CHECK_EMPLOYEE_SERVICES_MYSQL.bat` validates the MySQL engine, new tables and schema version
  **read-only**. Requires an actual MySQL server; cannot be treated as a successful check until run.
- `VERIFY_EVERYTHING.bat` attempts the complete TypeScript and Vite build with Node dependencies.
- `CHECK_BROWSER_V2.bat` runs a **read-only** Playwright/Chromium smoke test against a running **MySQL** backend using credentials supplied through environment variables. Requires Playwright installed locally. It checks login, five screen loads and relevant new panels. This test was not run on the user’s Windows deployment.

### Restrictions before production use
- **MySQL live transactions, backup restore, complete browser testing and deployment security
  have not been verified in the packaging environment.** Run local checks in Windows.
- Vault upload remains disabled unless both encryption and a live malware scanner are configured.
  The old application intentionally fails closed. Encryption/scanning configuration alone does
  not prove legal compliance or independent security certification.
- Statutory payroll/tax and payment disbursements are not made compliant by this release.
- HR review of a registered document is **metadata only**, not an authenticity check.
- Before processing real confidential HR data: validate least-privilege access, audit retention,
  secrets, TLS, network/firewall policy, disaster recovery, regulatory obligations and privacy notices.
- If optional external AI API is enabled, independently review organizational data-processing terms;
  do not send private case data, credentials or government IDs to AI.

## Upgrade instructions
1. Back up the current database. Stop old frontend/backend processes.
2. Extract v2.0 to a **different folder**; do not overwrite your existing `.env` or database.
3. Reuse the authorized MySQL configuration securely (`server/.env`). Never include it in a ZIP.
4. Start the configured MySQL server, then start FastAPI. Verify Developer Console says **mysql**.
5. Run `CHECK_EMPLOYEE_SERVICES_MYSQL.bat` and `VERIFY_EVERYTHING.bat`.
6. Open the Employee Services pages; confirm HR permissions using a non-production test account.
7. Preserve the old release and database backup until regression and rollback checks succeed.
