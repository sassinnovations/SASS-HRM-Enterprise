# SASS HRM Enterprise — AI Bot All-Feature Connection Upgrade

Release: 24 November 2026. Base: `SASS_HRM_ENTERPRISE_RIGHT_SIDE_AI_BOT_NON_OVERLAPPING_2026-11-24.zip`.

## Verified in this package

- All **73 registered feature pages** are available as AI guides and launcher controls to accounts that have permission. The AI stays in its non-overlapping right dock, and the real feature runs in the main SASS HRM workspace.
- The bot now **tracks the currently open feature**. It loads that feature's role-scoped guide and approved RAG articles; users can ask about the current screen, open the controls/guide, or navigate to related settings without losing their conversation.
- The bot supports **deterministic chat commands** like `open Employee HRIS` and `open Recruitment ATS`. Its links open existing feature pages. No LLM output is executed as an HTTP request or SQL operation.
- The new **Check feature connections** button calls authenticated `GET /api/ai/copilot/integrations`: probes registered GET paths and whether each feature's key MySQL/SQLite tables can be accessed via `SELECT 1 ... LIMIT 0`. No employee records are read. Results are limited to features permitted to the requesting user. **It does not test CRUD or prove that MySQL is deployed.**
- Per-feature guides display source-declared API methods, and a create/edit/delete plan warns when the source inventory lacks a matching method. Source method presence is **not** proof of a supported or authorized operation.
- **16 explicitly approved actions** with existing review-and-confirm flow. Added (1) **mark my own notification read** and (2) **update my own preferences**. Both reuse the original HRM module handlers and honor stale-state and ownership checks.
- Existing GenAI provider integration remains optional; existing lexical RAG searches feature guidance, approved policies and published audience-scoped knowledge articles. It does not automatically ingest confidential HR rows or privately held content into the LLM provider.
- Existing **269-table schema**, existing AI Knowledge Studio, 73-feature catalog, leave, attendance, service requests, task workflows, right-side dock and 14 earlier actions are preserved. **No new tables or migration are necessary.**

## Three coverage levels (do not confuse them)

| Level | What is established | Verified? |
|---|---|---|
| 73 registered features | Role-scoped AI navigation/guidance and method inventory | Yes, from source and isolated API tests |
| 73 API/table contracts | Representative route exists, mapped table accessible in isolated SQLite | 73/73 for administrator with developer grant, 54/54 for tested employee account |
| Direct AI database modifications | 16 allowlisted reviewed actions across supported personal/manager workflows | Passed selected isolated integration tests |
| Every feature's CRUD | All add/edit/delete/settings actions actually work through AI | **No** — feature controls are navigated through their normal HRM screens |
| Live environment | Production MySQL, hosted API, actual GenAI provider | **Not tested** |

## Usage

1. Open SASS HRM and click the AI icon on the **right edge**. The main page remains visible and usable.
2. Navigate to Employee HRIS, Recruitment ATS, leave or any other feature you can access. The bot automatically displays that feature's guide and settings shortcut.
3. Use **All features** to search all the modules you are authorized to use. Click **Check feature connections** to see read-only route/table status for your account.
4. Ask *"How do I use this page?"*, *"Open Employee HRIS"* or *"How do I edit the employee code?"*; follow the appropriate authorized page and normal edit dialog.
5. For eligible personal actions, choose **Assisted actions**, review the preview, and then press **Confirm**. Confirmation is one-time, expiring and tied to the authenticated employee.
6. HR admins can curate RAG knowledge under Knowledge Studio with feature and audience scopes. Only publish reviewed content suitable for its audience.

## Security boundaries

- Chat cannot issue arbitrary network requests, SQL, raw CRUD or changes to any feature selected by the model.
- Hiring/rejection, payroll posting, approvals, salary changes, employee deletion and bulk access remain subject to their original modules and human authorization.
- API access and SQL operations use existing roles and data-ownership checks, including employee-scoped queries and authenticated AI endpoints. The status scan discloses no record data.
- **No administrator, manager, or employee should treat navigation guidance as approval to bypass a permission check.**

## Test notes

- `python server/ai_copilot_test.py`: PASS — 73 feature guidance/contract probes, role scopes, context RAG, command navigation, 16 actions, notification ownership, preference stale-state, existing AI regressions.
- `python scripts/check-ai-right-dock.py`: PASS — 15 dock/layout source checks, no left AI entry, dock is not a fixed overlay.
- `python server/organization_settings_v26_test.py`, `python server/official_work_details_edit_test.py`, `python server/consolidated_catalog_crud_test.py`, `python server/mysql_feature_schema_integrity_test.py`, `python server/mysql_connection_audit_test.py`, `python server/database_workflow_integration_test.py`: PASS in their designed isolated/mocked modes.
- Frontend **TypeScript/TSX syntax parsing** passes with global TypeScript compiler. `npm run build` fails because required React, Lucide and React type packages are not present in the local dependency environment. Complete build remains unverified.
- **Production MySQL connectivity, provider API, browser E2E testing, and all 73 module CRUD flows have not been verified.**

## Deployment

Back up the database and test the release in staging with separate admin, manager and two unrelated employee accounts. Install the frontend packages with a working registry/cache (`cd web && npm ci`), run `npm run build`, launch the backend against a staging MySQL database, and use the bot's read-only connection scan. Run sample create/edit/delete operations only on disposable staging records, check authorization and audit logs, and verify responsive split layout. Deploy both frontend and backend together. Keep JWT secrets and any AI provider key outside the project ZIP.

See `docs/AI_BOT_73_FEATURE_CONNECTION_MATRIX.csv` for all per-feature capabilities and declared methods.
