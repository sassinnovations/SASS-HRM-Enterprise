# Company Setup & HRIS Import — update

This release integrates the existing administrator-only, database-backed CSV/XLSX HRIS importer into **People Management → Company Setup & HRIS Import**. The older fixed-column CSV-only importer has been replaced on that page, avoiding two competing import workflows. The same importer remains available in HR Data Quality Center.

## Settings and workflow

- Configure duplicate handling (reject/skip), date format, worksheet, default role/work mode, trimming, blank-row skipping, maximum rows and column mapping.
- Download a template, choose CSV/XLSX, inspect columns, preview errors and confirm the import. Backend validation and role permissions remain enforced.
- View import history. Imported accounts are inactive and existing employees are not overwritten.
- Access organization settings, account provisioning, data-quality reviews and audit history from the setup page.
- After import, refresh workspace employee data.

## Deployment

1. Back up MySQL and the deployed application.
2. Apply the updated frontend source and rebuild (`cd web && npm ci && npm run build`).
3. Deploy the new frontend, retaining the existing backend and MySQL database.
4. Verify with an administrator using a **small, non-production test workbook**: inspect, preview, commit, verify directory and history; verify a non-admin cannot access import APIs.
5. Run `python CHECK_COMPANY_HRIS_SETUP.py` and `python scripts/check-feature-pages.py`.

No new MySQL migration is needed **if** the existing HR Data Quality import migration (`database/17_HR_DATA_QUALITY_IMPORT_ADD_ONLY.sql`) was already applied. Otherwise apply that migration safely after backup. Do not reset MySQL volumes. No candidate data is preloaded.

## Limitations

Static TypeScript syntax and navigation checks passed. Existing importer backend tests and schema checks passed. Full Vite production build, live MySQL execution and real browser import were **not** verified in this environment. This release does not change live HR data or deploy to your website.
