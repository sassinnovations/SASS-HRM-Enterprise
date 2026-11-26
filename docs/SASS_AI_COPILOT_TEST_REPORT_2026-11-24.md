# AI Copilot v2 — Feature Control, Database and Security Verification

**24 November 2026. Source-level staging release only; not a live SASS HRM deployment.**

### Source coverage

- 73 registered feature paths in `docs/FEATURE_SCREEN_DATABASE_CONTRACTS.csv`.
- 73 permission-aware feature guides and role-filtered navigation paths.
- 9 allowlisted, confirmed actions across 5 owning modules: leave, Request Desk, attendance, calendar and work arrangements.
- Published policies and HR-admin-published articles indexed in in-memory lexical retrieval per request, with retrieved source citations; optional external chat completion disabled by default.
- 268 expected MySQL table definitions, including previously introduced `ai_knowledge_articles` and `ai_action_proposals`; **no new schema migration added in v2**.
- Source reports represent backend declarations, not live MySQL read/write transactions.

### Tests executed and passed

| Test | Result |
|---|---|
| `server/ai_copilot_test.py` | PASS — 73 scoped guides, nine actions, published-only RAG, cross-user calendar and work-mode ID rejection, attendance, pending/cancel, one-time/expiry, stale calendar delete prevention, owner lookup isolation, admin-only AI health |
| `server/full_mysql_schema_test.py` | PASS — 268 source table definitions, 2,213 source column definitions |
| `server/mysql_feature_schema_integrity_test.py` | PASS — schema parity and deliberately failing drift-fixture simulations; this test prints a simulated FAIL before final PASS |
| `server/feature_screen_integrations_test.py` | PASS — 73 representative route and table mapping checks, isolated database simulations |
| `server/employee_directory_code_edit_test.py` | PASS — SASS0047 and employee HRIS edit regressions |
| `server/consolidated_catalog_crud_test.py` | PASS — previous protected CRUD for office/catalog and task templates |
| `server/culture_suite_test.py` | PASS — culture and HR service workflows |
| `server/route_audit_test.py` | PASS — 308 GET audit calls over 154 GET routes, with expected authorization denials |
| `server/database_workflow_integration_test.py` | PASS — representative ATS and database reports |
| Backend Python compile + React TypeScript source parse | PASS — no source syntax diagnostics |

### Not verified

- `npm run build` attempted but blocked by missing npm type-definition dependencies in the local sandbox (`react`, `react-dom`, `prop-types`, `estree`); full TS typechecking and Vite compilation remain necessary.
- No live production or staging MySQL connection, external LLM call, browser end-to-end run, Docker deployment, security penetration test or 73-feature CRUD acceptance test.
- No embeddings/vector search, autonomous general agent, automatic PDF/Word/ATS file indexing, unrestricted database access or automatic payroll/recruitment decision-making.
- 131 historical schema-foundation tables are not asserted to have complete business workflows.

### Security controls

- Every automated write is explicitly allowlisted and reuses its owning HRM handler.
- Server-generated review preview, per-account binding, expiry, one-time confirmation, audit logs and replay protection.
- Own-only personal calendar records guarded on prepare AND confirm; server snapshot comparison avoids silently applying stale calendar edit/deletion.
- Work mode decisions remain with authorized managers/HR; assistant can only request/cancel own pending workflow.
- Role restrictions enforced on guide, action catalog, prepare and confirm; developer grant is separate.
- Optional LLM receives only published document excerpts and questions with basic PII screening, not private employee DB records. **PII filtering is best-effort and not a comprehensive DLP system.**

**Summary:** Source-level implementation and isolated regression tests pass. This does not certify all 73 feature workflows or live MySQL integrations.
