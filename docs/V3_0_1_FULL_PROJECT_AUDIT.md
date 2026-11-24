# SASS HRM Enterprise v3.0.1 — Frontend / Backend Audit Patch

This is a **maintenance and compatibility release** built on v3.0.0. It preserves the existing SASS HRM navigation, employee accounts, payroll, recruitment, workflows, API permissions, and company data structures. No demo records or passwords are included.

## Confirmed corrections

1. **MySQL approval-inbox display:** The attendance-correction row previously used SQLite's `||` string concatenation operator in SQL. Under MySQL's normal SQL mode, `||` means logical OR and produces incorrect data. The endpoint now selects the start/end times and generates the time-range label in Python; both backends return a string such as `09:30–18:30`.
2. **Local-versus-release validation:** The distributable-package validator correctly rejected local `.env`, `node_modules`, and build output, but the same validation also ran against a properly configured developer machine where these local files are expected. `--workspace` mode now checks ignore protections without rejecting local files. Distribution validation without that flag continues to reject bundled credentials or dependencies. The integrated Windows scripts use workspace mode.
3. **Missing checks in aggregate backend suite:** `scripts/test-backend.ps1` now includes organization settings, Talent v2.8.1 edits, v3.0 Action Center/inbox, and new cross-database approval tests, which were absent from the aggregate launcher.
4. **Release/version consistency:** API version, frontend version, lockfile, startup checks, static audits, and browser stale-backend warning all use `3.0.1`.

## Tests completed in the isolated environment

- ZIP checksum/integrity: checked after packaging.
- Python syntax (`compileall`): passed.
- Frontend TypeScript type check (`tsc --noEmit`): passed.
- All **19 isolated backend regression scripts**: passed (temporary SQLite database with synthetic identities; real HR data untouched).
- Static layout, navigation, login, Docker configuration, and release-version checks: passed.
- New MySQL compatibility test verifies that approval labels and access scopes are correct; it also checks the MySQL SQL adapter's placeholder/upsert rewrites and schema statement splitter.

## What these tests do NOT establish

- The full Vite production bundle could not be built in the audit container: the available dependencies did not include Rollup's Linux native optional package, and a fresh network installation was unavailable. TypeScript validation passed. Docker builds a fresh frontend in `node:22-alpine` with `npm ci` when network access is available.
- There was no running Docker engine or MySQL 8.4 database available in this environment. Real MySQL schema application, SMTP, account invitation emails, Docker container health, browser interaction, and actual user data migrations remain to be verified on your Windows machine.
- This is not a complete production security or payroll compliance certification.

## Safe upgrade path for Windows

1. Make a restorable backup of your MySQL volume and save your existing `.env` and `server/.env` configuration **outside** the new ZIP.
2. Extract the ZIP to a *new* directory. Copy the existing two configuration files only into their matching locations; do not share or upload those files.
3. Start Docker Desktop; ensure the Linux engine is running.
4. Run `CHECK_V3_0_1_FIXES.bat` to check source-level compatibility. This does not touch MySQL.
5. Run `START_DOCKER_FULL.bat` to build and launch the existing Docker project; it does **not** remove your persistent MySQL volume.
6. Verify `http://localhost:8000/api/health` returns `version=3.0.1`, `status=ok`, and `database=mysql`; then open `http://localhost:5173` and sign in.
7. Run `VERIFY_DOCKER_FULL.bat` and check the administrator inbox, employee request flows, and attendance-correction approval labels.
8. If the API still restarts, get diagnostics with `docker compose -f docker-compose.full.yml logs --tail 120 api`. **Do not** run `docker compose down -v` or recreate the database on a populated installation.

To run comprehensive tests on a developer machine with Python and Node.js available, use `VERIFY_EVERYTHING.bat`. The strict release-package checks are deliberately separate from the local-workspace tests.
