# Saritha merge — deployment and database upgrade guide

## What this ZIP contains

The latest 241-table HRM source code has been merged into the originally uploaded
`SASS-HRM-Enterprise-Saritha.zip` project structure. The original Railway/Vercel
configuration was kept. This package contains **source code and SQL only**; it does
not contain existing MySQL data, active credentials or deployed services.

## Existing Saritha site: protect and migrate data first

1. **Back up the actual production database** and verify restoration separately.
   Keep its MySQL service/volume and all secret environment variables. Do not
   run `SETUP_SASS_HRM.bat` against a populated database.
2. Determine the existing database's table/column inventory first. The uploaded
   source declares substantially fewer tables than the merged release. This is
   **not** a simple 237 → 241 migration, so *migration 19 alone is insufficient*.
3. In a **staging clone**, assess missing prerequisites and execute the appropriate
   additive scripts in `database/` in dependency order, reviewing each change.
   Scripts 03–19 cover new capabilities, but earlier baseline changes and any
   custom schema drift must be reconciled from a live schema diff. `CREATE TABLE
   IF NOT EXISTS` does not repair the shape of a mismatched existing table.
4. Do not import `database/02_FRESH_INSTALL_ALL_IN_ONE.sql` into an existing
   database. It is only intended for an **empty, new** MySQL database.
5. Deploy the corresponding updated FastAPI backend and Vite frontend together.
   Run `python scripts/verify-saritha-merge.py` and the regression checks.
6. Run `CHECK_ALL_DATABASE_CONNECTIONS.bat` or `server/check_all_mysql_connections.py`
   against staging/live MySQL to check all required tables and permissions.
   Check API `/api/ready`; test login, roles, claims, imports and assets in a browser.

## Railway backend

- Keep `Procfile`, `railpack.json`, `railway.toml` and root `requirements.txt`.
- Start command: `python -m uvicorn main:app --app-dir server --host 0.0.0.0 --port $PORT`.
- Health path: `/api/ready` (requires DB connectivity and core tables).
- Set `DB_ENGINE=mysql`, a unique `JWT_SECRET` with at least 40 characters,
  `APP_ENV=production`, `PUBLIC_APP_URL=https://<your-vercel-domain>`, and
  `CORS_ORIGINS=https://<your-vercel-domain>`. Replace the placeholder with your real URL.
- Provide MySQL credentials via either `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`,
  `MYSQL_PASSWORD`, `MYSQL_DATABASE` **or** Railway's `MYSQLHOST`, `MYSQLPORT`,
  `MYSQLUSER`, `MYSQLPASSWORD`, `MYSQLDATABASE` variables. Explicit MYSQL_* wins.
- Do **not** set `MYSQL_HOST=127.0.0.1` on Railway; that would override `MYSQLHOST`.
- A live database migration is a distinct authorized production operation; this ZIP
  does not connect to Railway or modify its service.

## Vercel frontend

- Deploy the `web/` subdirectory. Build: `npm ci && npm run build`; output: `dist`.
- Set `VITE_API_URL` to the **HTTPS Railway API origin without a trailing `/api`**.
  Rebuild/redeploy the frontend after changing `VITE_API_URL`.
- Keep `web/vercel.json` to support client-side navigation refreshes.

## Local Docker / Windows

- Follow the project setup instructions for an empty installation or use an
  existing database after explicit schema migration. Local Docker MySQL uses port
  3307 by default; Railway's database typically uses the values provided there.
- Preserve credentials outside ZIP and never reset the existing Docker MySQL volume.
- Run `CHECK_EXPENSES_CLAIMS.bat /LIVE` and the module-specific verification scripts
  after configuring the actual MySQL connection.

## Known limits

Offline schema and selected integration tests do not verify a real production
MySQL migration, frontend browser interactions, payroll statutory compliance,
automated payments or any external provider. Several of the 241 tables are
schema-only foundations. HRIS import creates inactive employees; expense receipts
are references rather than uploaded receipt attachments.
