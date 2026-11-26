# SASS HRM Enterprise — SASS AI Control Center v3

Updated: 24 November 2026. Source project: `SASS_HRM_ENTERPRISE_AI_CONTROL_CENTER_GENAI_RAG_2026-11-24.zip`.

## What is implemented

- **Single assistant**, extending the existing SASS AI interface rather than adding another bot.
- **73 role-scoped feature guides** with interactive plans for **View / Create / Edit / Delete / Settings / Help**. These are navigation and instructions; **they do not directly execute CRUD**. After opening a screen, the normal HRM APIs enforce rights and validation.
- **14 explicitly allowlisted write operations** (13 available to eligible employees, plus HR task assignment for managers/HR admins): leave request, service request, attendance check-in/out, personal-calendar create/edit/delete, work-mode request/cancel, expense claim, attendance correction create/cancel, update HR task status, create HR task.
- **Two-stage action workflow**: `POST /api/ai/copilot/actions/prepare` validates and creates an expiring, employee-bound proposal, and a separate authenticated `POST /api/ai/copilot/actions/{id}/confirm` executes the owning module's existing handler. Proposals can be cancelled and are one-time use. Some actions check for stale records.
- **RAG with feature-specific scope and audience**: Published Knowledge Studio articles can be associated with a feature and a visibility tier (All / Manager / Admin), enforced in server retrieval and feature guides; legacy unscoped articles default to All. Approved policy text and the source-owned 73-feature registry are also searched. Evidence appears with source links.
- **Optional GenAI**: the project already uses an OpenAI-compatible chat completions API and returns a retrieved lexical answer when generation is disabled/unavailable. No embeddings, vector database, agentic planner, autonomous job execution, or cross-module arbitrary API access are claimed.
- External provider requests exclude employee-specific record lookups, restricted (Manager/Admin) RAG articles, passwords and common sensitive prompts. Even general published articles and questions can be sent to a provider when enabled: secure a data-processing agreement and train staff not to enter confidential data.

## Action catalog

| Area | Available reviewed actions | Authorization |
|---|---|---|
| Leave | Submit my leave | Authenticated employee, normal HRM validation |
| Request Desk | Submit my service request | Own account, active service category |
| Attendance | Check in / Check out | Own account, ordinary attendance validation |
| Calendar | Create / Edit / Delete personal events | Owner only; stale edited records rejected |
| Work arrangements | Request / Cancel pending work-mode change | Owner only; requests still require HR review |
| Expenses | Submit expense claim | Own account, expense policy/receipt validation |
| Attendance corrections | Submit / Cancel correction | Owner only, time window and status controls |
| HR tasks | Update assigned/created task status | Employee's own or authored task, stale-state guard |
| HR tasks | Create HR task | Manager or HR admin; ordinary reporting-scope validation |

**Not automated:** Payroll posting, payslip modification, candidate hiring/rejection, employee deletion, employee-code changes, department deletions, approval decisions, disciplinary decisions, broad data exports, and unrestricted SQL. These are navigated to the existing HRM feature where permitted.

## Installation and configuration

1. Back up the live MySQL database and take a tested restore point. Do not run release migrations directly against live production first.
2. On an existing v2 MySQL deployment, apply only **`database/24_AI_KNOWLEDGE_SCOPES_ADD_ONLY.sql`**. It creates one new table and does not modify existing employee, payroll, or knowledge rows. On a new install, use `database/02_FRESH_INSTALL_ALL_IN_ONE.sql` (the canonical schema includes the new table). `database/23_AI_COPILOT_ADD_ONLY.sql` also now includes the new table, so applying 23 to a new install is safe/idempotent; do not re-run other migrations without checking history.
3. Deploy the updated backend and frontend together; backend Dockerfile includes `server`, `database` and feature-contract `docs`. Keep MySQL environment configuration and JWT secret in secure deployment secrets, not the ZIP.
4. Optional environment variables in the **backend only**: `AI_COPILOT_GENERATION=1`, `AI_API_KEY=<provider-secret>`, `AI_BASE_URL=https://api.openai.com/v1`, `AI_MODEL=gpt-4.1-mini`. Leave generation off until security and vendor privacy checks are complete. Never put `AI_API_KEY` in `VITE_...` variables.
5. Login as HR admin and open **SASS AI Assistant → Knowledge Studio**. Review existing Published articles: old articles have audience `All`, so assign Admin/Manager scopes if necessary. Publish reviewed, nonconfidential articles per feature; employees will only retrieve authorized content. Admins can see policy/article counts in the health panel.
6. Test in staging with one admin, one manager and two unrelated employee accounts: verify 73 feature plans, scoped knowledge, action prepare/confirm/cancel, record ownership, reports, database table existence, and backups. Verify payroll and recruitment are not mutated through chat. Deploy to production only after a full UI build and real MySQL integration test.

## Relevant APIs

- `GET /api/ai/copilot/features` — role-scoped feature catalog.
- `GET /api/ai/copilot/features/{feature_key}/guide` — grounded per-feature guide and published scoped articles.
- `POST /api/ai/copilot/control/plan` — `{"feature_key":"employees","intent":"edit"}`; returns a navigation plan, **not a saved change**.
- `POST /api/ai/copilot/ask` — lexical RAG, citations, optional grounded GenAI.
- `GET /api/ai/copilot/actions/catalog` — role-scoped executable action types.
- `GET /api/ai/copilot/actions/my-options` — owner-scoped IDs for safe form dropdowns.
- `POST /api/ai/copilot/actions/prepare`; `POST /api/ai/copilot/actions/{proposal_id}/confirm`; `POST /api/ai/copilot/actions/{proposal_id}/cancel`.
- `GET /api/ai/copilot/knowledge`, `POST`, `PUT`, `PATCH` and `DELETE` (unpublish) — HR administrator only.
- `GET /api/ai/copilot/health` — administrator-only configuration/inventory status, **not** live end-to-end MySQL certification.

## Database

- Baseline project had 268 declared tables. New `ai_knowledge_scopes` adds exactly one, giving **269 declared MySQL tables, 2,216 columns, 327 named indexes, and 502 FK relationships**.
- `ai_knowledge_articles` and `ai_action_proposals` are retained; `ai_knowledge_scopes` maps each article to one feature key (or general) and audience. Existing articles without scope rows remain visible as All and must be reviewed by HR.
- The bundled fresh-installer schema, server schema, manual schema, add-only migration and `ALL_MYSQL_TABLES.csv` were synchronized. **These counts describe source definitions, not a successful connection to the live database.**

## Verification boundaries

See the accompanying test report and per-feature CSV. Isolated test environments use SQLite and mocked scenarios, not the deployed MySQL instance. Full `npm run build` was **not** proven because the available npm dependency packages are incomplete. TypeScript TSX syntax parsing passed. An external LLM call was **not** performed, and no production data or hosted website was changed.
