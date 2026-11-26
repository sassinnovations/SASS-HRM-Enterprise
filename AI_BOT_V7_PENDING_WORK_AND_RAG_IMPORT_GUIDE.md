# SASS HRM Enterprise — Floating AI Bot v7

**Release:** 25 November 2026  
**Basis:** Floating AI Bot v6 source package  
**Scope:** Two practical function upgrades; no changes to 16 confirmed action types, feature navigation, or live database schema.

## 1. My pending work — owner-scoped HR snapshot

Employee and HR users can ask the bot **“Show my pending HR requests and tasks”**, **“My pending items”**, or **“What needs my attention?”**. A button appears in Chat → Suggested questions. The server reads counts directly from the authenticated user's six connected HRM workflows:

| Workflow | Counted items |
|---|---|
| Leave Management | Pending leave requests |
| Request Desk | Requests not closed, resolved, cancelled, or rejected |
| HR tasks | Assigned tasks not completed or cancelled |
| Expenses & Claims | Pending expense claims |
| Attendance Corrections | Pending correction requests |
| Work Arrangements | Pending requests |

The response is **read-only** and includes source links back to the relevant HRM screens. Each query uses the employee ID from the verified login session, never an ID supplied by the browser. This is a snapshot, not a universal pending-work inbox and not proof that all other HRM modules have no pending records. The result is **not sent to an external GenAI provider** or added to RAG training material.

**Endpoint:** `GET /api/ai/copilot/my-pending` (authenticated). Chat also handles these queries with `POST /api/ai/copilot/ask`.

## 2. Bulk RAG Knowledge Studio import

The HR Administrator's Knowledge Studio now offers **Download CSV template**, **Choose knowledge CSV**, a **server-validated preview**, and **Confirm import drafts**. This provides a faster way to add guidance relevant to multiple HRM modules.

Required CSV headers (in any order):

```csv
title,category,content,feature_key,audience
```

- `title`: 4–190 characters.
- `category`: 2–100 characters.
- `content`: 20–24,000 characters (CSV quoting supports commas and newlines).
- `feature_key`: optional, or a valid feature key in the 73-feature registry.
- `audience`: `All`, `Manager`, or `Admin`.
- Max **50 articles per batch**, **250 KB file size in browser**, and **180,000 total content characters** on server.
- Restricted feature guidance cannot be imported with an audience of `All`.
- A duplicate `(title, feature_key, audience)` is rejected, both within the upload and against existing knowledge.
- Every imported article is a **Draft**, regardless of CSV contents. Admin must inspect and publish each one individually.
- Preview signatures expire after ten minutes, are tied to the administrator and exact reviewed row values, and are validated again at import time.
- Import runs transactionally: if validation or insertion fails, the batch rolls back rather than partially saving.
- Audit records log import count and actor without logging the article content.

Endpoints (HR Administrator only):

- `POST /api/ai/copilot/knowledge/bulk/preview` — `{ "rows": [...] }`.
- `POST /api/ai/copilot/knowledge/bulk/import` — `{ "rows": [...], "preview_token": "...", "confirm": "IMPORT_DRAFTS" }`.

**Important:** Avoid uploading resumes, financial data, passwords, or confidential employee records into HR knowledge articles. Audience restrictions are retrieval controls, not a substitute for content classification. If a knowledge item needs updates, edit it from Knowledge Studio after import.

## 3. Preserved behavior

- Right-bottom floating robot icon; movable/resizable chat window.
- 73 feature pages for role-scoped navigation/guidance.
- 16 permission-checked action types with explicit prepare → review → confirm.
- General GenAI answers only when `AI_API_KEY` and `AI_COPILOT_GENERATION=1` are configured; approved RAG still uses existing source controls.
- No arbitrary SQL access, no automated payroll changes, approvals, recruitment decisions, or employee deletion.

## 4. Installation and checks

1. Back up the current deployed application and database; apply this update to a **staging** environment first.
2. Extract the project ZIP over a **separate staging copy** of SASS HRM v6. Do not replace your production deployment without testing.
3. Install the existing Python and web dependencies following `README.md` (this release adds no new external dependencies or database tables).
4. Run `CHECK_AI_ASSISTANT_V7.bat` on a Windows development machine, or execute `PYTHONPATH=server python server/ai_copilot_v7_test.py` and `PYTHONPATH=server python server/ai_copilot_v6_test.py`.
5. Sign in as Employee → ask **“What needs my attention?”** → verify counts against the user's own HRM records. Sign in as another user → confirm separate counts.
6. Sign in as HR Administrator → Knowledge Studio → download template → import one or more test articles → confirm they are drafts and invisible to regular employee RAG queries until published.
7. Verify duplicate rows, restricted feature scope, expired preview, and unauthorized import are rejected.
8. Check live backend `/api/live`, `/api/health`, and `/api/ready` after deployment; do not infer live MySQL status from unit tests.
9. Complete a full `npm` frontend build and interactive desktop/mobile browser check in staging; these were not completed in the local tool environment.

## 5. Verification and limitations

**Passed in isolated test environment**

- AI v7: own-record pending counts, authentication, manager/employee isolation, bulk import preview/confirm, altered preview rejection, expiry, duplicate prevention, draft-only publication, and audit logging.
- AI v6, v5, v4, and v3 regression suites.
- HTTP 500/503 health-check regression, Excel Data Center regression, and official-work-details approval regression.
- 73 feature source/API contract test and the MySQL schema integrity simulation (270 tables).
- TypeScript syntax parsing: 45 `.ts`/`.tsx` files; modified AI component compiled with `transpileModule` successfully.
- CSV parser smoke test for quoted commas/newlines and invalid input.

**Not verified:** Full frontend production build, real external LLM response, hosted MySQL connectivity, browser drag/resize behavior, and production deployment. The historical HTTP 500 observed earlier cannot be diagnosed conclusively without the failing live request and server logs.

**Schema:** No new MySQL migrations; existing 270-table schema retained.
