# SASS HRM Enterprise — Feature-to-Database Connection Audit

**Audit date:** 24 November 2026

**Scope:** Uploaded `SASS_HRM_ENTERPRISE_FEATURE_AUDIT_CONSOLIDATED_CRUD_2026-11-24.zip` source, local offline schema validation, and isolated backend tests. No production MySQL connection or hosted website test was available.

## Verdict

- **Partially connected; cannot certify all features.** MySQL is the default required production engine (`server/main.py`). Frontend screens call `/api` routes; FastAPI imports register 413 distinct method/path pairs, with no duplicate method/path registration.
- **266 MySQL table definitions** were verified by the offline schema integrity checker, with **2,196 declared columns, 324 named indexes, and 500 declared foreign-key relationships**. This checks local SQL files, not objects installed on the live server.
- **136 tables** have detectable direct SQL references in production backend Python. This is static source evidence only and does not imply all reads/writes, permissions or user workflows are correct.
- **131 tables** are still classified by the project inventory as database foundations requiring review; **130** have no detected backend SQL reference. The exception `asset_maintenance_requests` has implemented GET/POST/PATCH API use but remains conservatively classified as foundation in the original inventory.
- **73 feature URLs** are registered in the frontend source. The audit did not run a browser/UI test for each URL.
- **Live MySQL connection, table grants, migrations, and production persistence were not verified**: the uploaded source has no configured `server/.env`, and no running MySQL/Docker instance or production credentials were available.

## Schema-domain coverage (static source evidence)

| Domain | DDL tables | Classified foundations | Tables with detected backend SQL refs |
|---|---:|---:|---:|
| Assets, files & documents | 13 | 6 | 8 |
| Employee self-service & notifications | 6 | 0 | 6 |
| HR tasks, service desk & helpdesk | 11 | 0 | 11 |
| Identity, security & profiles | 41 | 27 | 14 |
| Organization, settings & administration | 37 | 19 | 18 |
| Payroll, benefits, tax & expenses | 40 | 26 | 14 |
| People performance & learning | 22 | 2 | 20 |
| Policies, employee voices & culture | 12 | 0 | 12 |
| Talent, hiring & interviews | 47 | 26 | 21 |
| Time, attendance, scheduling & leave | 37 | 25 | 12 |
| **Total** | **266** | **131** | **136** |

## Source traces for representative features

| Frontend feature | API or backend source | MySQL tables referenced | Verification performed |
|---|---|---|---|
| Employee HRIS and code editing | `GET/POST /api/employees`, `PATCH /api/employees/{employee_id}` in `main.py` / account modules | `employees`, `audit_events` and linked records by employee ID | Isolated employee-code editing, duplicate validation, role restrictions, audit passed |
| Organization settings and offices | `organization_settings_v26.py`: `/api/admin/organization/settings`, `/api/admin/organization/offices` | `organization_preferences`, `organization_offices`, `employees` | Isolated settings and office CRUD passed |
| Shift and schedule management | `compensation_ops.py` and `feature_consolidation_crud_test.py` | Shift/schedule tables and employee/leave validation | Isolated edit/delete and restrictions passed |
| Candidate database and JD/ATS | `candidate_library.py`, `job_descriptions.py`, `recruitment_match_history.py` | `candidate_profiles`, `recruitment_job_descriptions`, `jd_import_batches`, `recruitment_match_runs`, `recruitment_match_results`, `recruitment_match_review_notes`, `candidate_shortlist_decisions` | Isolated candidate import, JD CRUD and persisted match reviews passed |
| Expenses and assets | `expense_management.py`, `asset_management.py` | Claim/expense tables, `assets`, `asset_profiles`, `asset_maintenance_requests` | Isolated expense and asset workflow tests passed |
| Compensation and hiring | `compensation_ops.py`, `hiring_pipeline.py` | Compensation, leave, hiring-stage tables | Selected backend regression tests passed; payroll publication was not tested |
| Database diagnostics | `mysql_connection_audit.py`, `database_verification.py`; Developer Console in `App.tsx` | MySQL `INFORMATION_SCHEMA` and 3 verification history tables | Offline/simulated schema and SQLite audit tests passed; live status not available |

## Verified test execution

The following tests passed in this working environment (synthetic SQLite fixtures or mocked MySQL metadata, **not** real production MySQL):

- `database_workflow_integration_test.py`
- `employee_directory_code_edit_test.py`
- `feature_consolidation_crud_test.py`
- `organization_settings_v26_test.py`
- `candidate_library_test.py`
- `job_descriptions_test.py`
- `expense_management_test.py`
- `asset_management_test.py`
- `compensation_ops_test.py`
- `culture_suite_test.py`
- `employee_services_v20_test.py`
- `hiring_pipeline_test.py`
- `mysql_connection_audit_test.py`
- `mysql_feature_schema_integrity_test.py`
- `mysql_schema_status_test.py`

The source command `python database_feature_coverage.py --check` initially failed because the checked-in inventory was stale by one referencing module (`enterprise.py` newly references `recruitment_job_descriptions`). This release **regenerated only** `database/FEATURE_TABLE_COVERAGE.csv`. It made **no** code, credential, table-definition, migration, or live-record changes.

## Items requiring follow-up

1. **Live MySQL:** Confirm the host credentials, database name, tables, 2,196 columns, named indexes, foreign keys and SELECT grants on the actual deployed MySQL instance.
2. **Workflow gap:** Review the 131 foundation-category tables and build missing API/UI actions where business workflows require them. A table existing is not proof that a feature is connected.
3. **Permissions and writes:** For each sensitive feature, test create/update/delete or appropriate archive/offboarding workflows with an approved staging account; inspect persistent rows and audit events after refreshing/signing in again.
4. **Deployment:** Build React/Vite and verify all 73 frontend pages, 413 API routes, and authorized browser interactions. Neither a full frontend build nor live browser testing was run in this audit.
5. **Safety:** Back up live data and apply only reviewed additive migrations; do not run fresh-install SQL or reset Docker/MySQL volumes on an existing installation.

## Safe live verification commands (run by your deployment administrator)

With a configured MySQL backend environment on your own server, run from `server/`:

```bash
python mysql_feature_schema_integrity.py --file-only
python check_all_mysql_connections.py --probe-tables
```

Or on Windows with your configured Docker stack: `CHECK_ALL_DATABASE_CONNECTIONS.bat`. It runs a read-only metadata/table-access checker. An administrator can also use **Developer Console → Verify all database tables** on the deployed site. These checks do not establish that all business workflows are correct.

## Included detailed indexes

- `docs/DATABASE_FEATURE_CONNECTION_CHECKLIST_2026-11-24.csv`: all 73 pages; states exactly what was and was not tested.
- `docs/DATABASE_SCHEMA_FOUNDATIONS_REQUIRING_WORKFLOW_REVIEW_2026-11-24.csv`: the 131 foundation-category tables, domains and detected references.
- `database/FEATURE_TABLE_COVERAGE.csv`: regenerated, in-sync static table coverage.
