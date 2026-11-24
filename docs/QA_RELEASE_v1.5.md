# Release 1.5 verification record

Local checks performed in the packaging environment (October 14, 2026):

| Validation | Result | Limits |
|---|---|---|
| Isolated clean install and administrator bootstrap | PASS | SQLite test-only; not live MySQL |
| Existing merged feature, developer and authorization tests | PASS | Does not cover every browser click |
| Culture + request desk end-to-end FastAPI tests | PASS | Synthetic test-only records, no actual SASS personnel |
| Employee Voice / Discipline privacy and state changes | PASS | No anonymous or independent investigator model |
| Employee Career and Request Desk AI read-scoping | PASS | Read-only assistant; no automated decisions |
| 132 role-scoped GET checks across 66 endpoints | PASS | Any expected HTTP 403 counts as authorized denial |
| All 40 original demo screens + Developer console | PASS static | Presence in source, not screenshot parity |
| Four new module pages and paths | PASS static | Presence in source, not complete browser testing |
| TypeScript/TSX parsing of five source files | PASS | Does not constitute `tsc` type checking / Vite build |
| CSS parsing of four stylesheets | PASS | Does not prove Chrome/mobile rendering |
| Eight additive MySQL CREATE TABLE statements | PASS static | Requires live MySQL 8.4 integration test |
| npm dependency installation and Vite build | BLOCKED | npm registry DNS `EAI_AGAIN` |
| Browser E2E / UX | NOT TESTED | Run in user's environment |
| Docker/MySQL 8.4 integration | NOT TESTED | No local Docker/MySQL daemon |
| Legal review / deployment security | NOT TESTED | Required before live personnel data |

**Run locally on Windows:** `SETUP_SASS_HRM.bat` (fresh install only), `START_MYSQL.bat`, `CREATE_ADMIN.bat` (fresh empty DB only), `START_HERE.bat`, `CHECK_MYSQL.bat`, `VERIFY_EVERYTHING.bat`.

For upgrading an existing organization, **do not** run first-admin bootstrap or regenerate and overwrite deployed secrets. Back up the database and use your authorized environment configuration. Check new table creation and manager/employee permissions before enabling staff access.
