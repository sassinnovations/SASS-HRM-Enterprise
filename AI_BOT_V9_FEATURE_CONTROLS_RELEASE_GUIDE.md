# SASS HRM Enterprise — AI Bot v9: Expanded Confirmed Feature Controls

Release date: 2026-11-25. Source base: AI Bot v8 floating-window project.

## Coverage at a glance

- **73 registered HRM feature screens**: all retain role-filtered navigation, current-page guidance, feature workflow planning, and source-only API/table diagnostics.
- **31 allowlisted confirmed AI operations** across existing modules (16 retained from v8, 15 newly connected in v9).
- **3 admin-managed catalogs newly actionable**: Office Locations, Request Desk Categories, HR Task Templates. Each now offers Create/Edit, and module-specific Activate/Deactivate or Archive/Restore and protected Delete.
- **270 existing MySQL table definitions** retained; no additive schema migration required in this release.
- **Self-only action history**: `/api/ai/copilot/actions/history` returns at most 25 entries for the signed-in account, with operation, state, and date only. It does not expose parameters, personnel records or another user's history.
- The floating robot icon and non-modal, draggable/resizable chat window are preserved, as are GenAI, approved RAG, specialist modes, bulk draft knowledge imports, and the previous self-service workflows.

## What is genuinely executable via AI?

All 31 operations are in a **server-owned allowlist**, visible only when the authenticated user can access the relevant feature and, for the new admin catalog operations, has the `admin` role. Changes follow Prepare → Preview → Confirm, require a live session, record the actor and audit event, and dispatch through the **existing HRM handler**.

The 15 new actions:

| Feature | Added AI actions | Rules |
|---|---|---|
| Organization Settings — Offices | Create, Edit, Deactivate, Activate, Delete | Unique office code/name; valid timezone; linked location records block unsafe rename/deactivation/deletion; deletion reason required |
| Request Desk — Categories | Create, Edit, Archive, Restore, Delete | Duplicate validation; only archived and unreferenced categories can be deleted |
| HR task templates | Create, Edit, Archive, Restore, Delete | Duplicate validation; existing assigned tasks remain unchanged; only archived templates without assignments can be deleted |

Each existing record is fingerprinted during preview and checked again on confirmation. If a record changes after preview, confirmation returns HTTP 409 and requires a fresh review. No deletion can be triggered by chat text alone. Archive and restore remain reversible; a permitted deletion may not be.

## Remaining restrictions

This **does not implement autonomous CRUD on all 73 modules**. Most modules still provide safe planning and links to their existing UI. Critical changes (payroll processing/salary, hiring decisions, approvals, employee deletion, audit retention, security settings) remain in their original permission-protected screens. The bot never issues arbitrary SQL or HTTP operations at the request of a user or LLM. `GET` and `DELETE` entries in the route catalog do not guarantee user permission or working CRUD.

The v9 backend feature-link matrix is at `docs/AI_BOT_V9_FEATURE_CONTROL_MATRIX.csv`. It lists every one of the 73 feature routes, settings connections and genuinely executable actions.

## How to use in the UI

1. Open SASS HRM and click the floating AI robot icon at bottom right.
2. In **All features**, search for a feature and select **Guide** or open the authorized HRM screen.
3. In **Workflow center**, ask for an operation such as `Edit Employee HRIS`, `Settings for Payroll workbench`, or `Add office`.
4. In **Assisted actions**, select an available option. HR Administrators additionally see office, Request Desk category and task-template editing controls. For existing records, choose the record; for deletion, enter a reason.
5. Read the generated preview before pressing **Confirm action**. To see your own last 25 proposals, click **My recent AI actions**.
6. The page stays accessible while the floating window is open; the window can be moved or minimized.

## Install and verify

1. Back up the production source and MySQL database. Unpack this ZIP to a staging environment, not directly over the live application.
2. Configure the existing JWT and database environment as described in the project README. GenAI requires `AI_COPILOT_GENERATION=1` and a server-only `AI_API_KEY`; RAG works with approved knowledge when the external provider is disabled.
3. Run `CHECK_AI_ASSISTANT_V9.bat` (Windows) or `./CHECK_AI_ASSISTANT_V9.sh` (Linux/macOS). All v9 tests use temporary SQLite, not production MySQL.
4. Install frontend dependencies and run `npm run build` from `web`. A successful parser-only test is **not** a replacement for the complete build.
5. Verify admin vs employee actions, stale confirmations, linked-record delete guards, RAG publication/retrieval, floating chat layout and API `/api/live`, `/api/health`, `/api/ready` on staging.
6. Exercise add/edit/delete with disposable records in a staging **MySQL** database; then deploy only after backups and role checks pass.

## Verification completed for this release

- PASS: new isolated SQLite integration test for 31 allowed operations, role restrictions, duplicate confirmation rejection, office/category/template CRUD and action history.
- PASS: source-level planning test for all 73 registered feature screens, with separate developer grant.
- PASS: earlier v4/v5/v6/v7 GenAI/RAG, confirmation and knowledge-security regression checks (selected tests).
- PASS: parser-only check for 45 TS/TSX source files and Python syntax checks.
- NOT VERIFIED: `npm run build`, real-browser interactions, real external GenAI calls, live production MySQL connectivity, or full end-to-end CRUD across all HRM modules.

This is a downloadable source-code update. It does not change or delete production database records and is not a live deployment.
