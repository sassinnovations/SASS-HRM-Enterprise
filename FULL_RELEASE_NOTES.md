# SASS HRM Enterprise White and Blue | Full checked release

This package combines the complete Workspace Workflows release, the latest first-admin launcher, and the visual fix for the **Create your account** page.

- All 288 MySQL table definitions, additive migrations, role-scoped workspace controls, Overview, Products and Projects, and the floating AI assistant remain included.
- Company Setup now hides HRIS import until it verifies MySQL and the matching API release.
- The signup form no longer has an inner outline or shadow. The outer panel, account-type cards, fields and approval requirements are unchanged.
- `CREATE_ADMIN.bat` checks the running full Docker stack and MySQL before prompting. It is only for the first administrator on an empty employee table. The password is entered privately and developer diagnostics are not granted by default.

## Update your existing installation

Back up your project and MySQL first. Extract this ZIP separately and merge its files into your configured project while keeping the existing `.env` files and database volume. **Do not rerun setup or reset MySQL.** Restart with the normal launcher for your installation. See `WORKSPACE_WORKFLOWS_RELEASE_NOTES.md` for migration 29 if your previous installation does not yet have it.

Open `http://localhost:8000/api/ready` and run `CHECK_WORKSPACE_MYSQL.bat` for the read-only workspace data check. Open `http://localhost:5173` and refresh the page after rebuilding. If you already have an administrator, skip first-admin creation. If Windows still blocks the batch, leave Smart App Control enabled and follow your approved review process.

The source ZIP contains no production database, live configuration, credentials, or pre-created admin account. OpenAI chat and drafting are optional and still need a correctly configured server-side API key.

## What was checked

The production frontend build, bundled Python regression suite, browser signup and core workspace flows, and real MySQL 8.4 schema deployment on disposable data passed. Windows Smart App Control trust, live company MySQL data, and optional external provider credentials were not tested.
