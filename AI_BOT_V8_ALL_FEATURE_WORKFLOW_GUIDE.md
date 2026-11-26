# SASS HRM Enterprise — AI Bot v8: All-Feature Command & Workflow Center

Release date: 2026-11-25

## Purpose

The AI bot remains a bottom-right floating robot icon with a movable chat window. Version 8 adds **feature-wide command planning** and **cross-module guided workflows** on top of the previous GenAI, RAG, personal record queries, and 16 allowlisted review-and-confirm actions.

The project contains **73 registered feature screens**. They are available for planning and navigation **only when the signed-in account has access**. An HR Administrator ordinarily sees 72; the developer-only screen requires a separate grant. A staff account sees a smaller set, based on permission policy.

## New UI: Workflow Center

Open the floating SASS AI bot → **Workflow center**. Enter commands such as:

- `Edit Employee HRIS`
- `Settings for Payroll workbench`
- `View Recruitment ATS`
- `Delete a candidate` (suggests an existing authorized screen; no deletion is executed)
- `Create HR tasks`

The server identifies one or more permitted features, shows a screen shortcut, the declared source API method inventory, and the exact allowlisted AI actions available. Commands never call an arbitrary API, never run SQL, and never override a feature's own validation or authorization. A source-declared API method is **not** proof that CRUD works end-to-end.

Seven read-only workflow guides cover recruitment/onboarding, employee setup, time/payroll, self-service, performance, offboarding, and administration. Each step links to its HRM feature; restricted steps are omitted. The checkbox progress is local to the bot window, not a change to task, payroll, employee, or other HRM records.

The same command routing is available in **Chat** for explicit queries such as `Edit Employee HRIS` and `Settings for Employee HRIS`. Natural-language requests for already approved personal operations still route to their existing **Assisted actions** forms. All changes require a separate server-generated preview and a user's explicit confirmation.

## New API endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/ai/copilot/commands/preview` | Preview a role-filtered feature operation. Body `{"command":"Edit Employee HRIS", "feature_key":""}`. Returns candidates and no-op plans. |
| GET | `/api/ai/copilot/workflows` | Return role-filtered multi-module workflow guides. Never performs an operation. |

These endpoints use the existing JWT session, role model, feature inventory, action allowlist, and existing protected workflows. No new MySQL tables or migrations are required.

## Existing capabilities retained

- General GenAI conversation when an external provider is configured
- Approved RAG policy and feature knowledge with audience scoping
- Employee-specific personal record queries and pending work summary
- Admin Knowledge Studio and draft-only CSV knowledge imports
- 16 confirmation-protected action types (unchanged in v8)
- Right-bottom floating bot icon and movable/resizable window
- Existing HTTP 500/503 backend diagnostics and `/api/live`, `/api/health`, `/api/ready`

**Not implemented:** full autonomous Add/Edit/Delete/Settings across all 73 screens. The application has workflow-specific rules and sensitive operations that must stay in the main authorized HRM screens (payroll, hiring decisions, salary updates, employee deletion, audit history, etc.).

## Installation

1. Back up the production project and MySQL database before any deployment.
2. Extract the ZIP into a **staging** copy. Do not copy over a running production environment.
3. Install the existing backend and frontend dependencies according to the project README.
4. Keep existing `.env` database/JWT settings and configure a GenAI provider separately if general AI answers are required. Never store provider keys in frontend source.
5. Run `CHECK_AI_ASSISTANT_V8.bat` (Windows) or `python server/ai_copilot_v8_test.py` (from project root) in a test environment. This test uses isolated SQLite only and creates no production records.
6. Build the frontend, open the floating bot, select **Workflow center**, preview commands for employee and administrator accounts, and confirm that restricted modules are hidden.
7. Check `/api/live`, `/api/health`, and `/api/ready` on staging; test key workflows against staging MySQL and verify database backups before production deployment.

## Verification summary

- PASS: v8 isolated backend test across all 73 features when the correct grants are present, including protection of developer-only module.
- PASS: role-scoped workflow recipes, unrecognized command handling, no automatic writes, review-flow preservation.
- PASS: AI v3–v7 regression tests and official work details approval regression test.
- PASS: HTTP 500 health regression and runtime diagnostics tests.
- PASS: source parsing for 45 TypeScript/TSX files.
- NOT VERIFIED: full frontend build (missing local npm dependencies), interactive browser layout, external GenAI responses, or live production MySQL/HTTP 500 root cause.

**Note:** This ZIP is a source-code update, not a live deployment. Existing MySQL data is not modified simply by downloading it.
