# Saritha merge verification — 17 November 2026

**Tested locally:**

- All **62 backend `*_test.py` scripts** ran to completion and passed using isolated
  SQLite/test doubles. This includes the new production MySQL environment fallback tests.
- Verified canonical 241-table schema and fresh installer parity: 1,986 columns,
  274 named indexes, 442 declared foreign-key relationships.
- Uploaded 105 original table definitions compare unchanged to the merged schema;
  all 136 new table names occur in bundled additive SQL migration scripts.
- Frontend source syntax parsed for **38 TypeScript/TSX files** (zero parsing errors).
- Static frontend routing audit: **73 distinct routes**, with protected route and
  refresh-action checks passed.
- Source code compiled using Python `compileall` without errors.
- Host configuration checks: Railway native MySQL variables plus explicit application
  overrides, root/server dependency parity, Vercel SPA navigation fallback.
- No live employee/candidate/payroll database files or credential `.env` files bundled.

**Not verified:**

- The full `npm ci && npm run build` could not run offline because npm cache lacks
  Vite and other packages (`ENOTCACHED`). TypeScript parsing is not a semantic
  typecheck or a Vite production build.
- No live MySQL instance or Docker engine was available for migration or permissions tests.
- No Railway/Vercel deployment, browser test, real SMTP, banking/payment, or statutory
  HR/payroll compliance verification was performed.
- A successful offline test suite does not prove all 241 database tables have operational
  API/UI coverage; the schema coverage audit identifies **115 schema-only foundations**.

**Before deploying:** Backup/restore-test your real database, review the migration
checklist against live schema metadata, deploy to staging, then test auth, company
HRIS imports, candidate search, assets, attendance, Expenses & Claims, and payroll
under real account roles. Keep private production credentials on your hosting platform.
