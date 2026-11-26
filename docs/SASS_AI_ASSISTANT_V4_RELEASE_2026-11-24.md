# SASS HRM Enterprise — SASS AI Assistant v4

**Release date:** 24 November 2026  
**Based on:** `SASS_HRM_ENTERPRISE_AI_BOT_ALL_73_FEATURES_CONNECTED_2026-11-24.zip`.

## Requested improvements

1. Removed the sentence **“A unified GenAI + RAG assistant for 73 HRM features, secure navigation and confirmed personal workflows.”** from the right-side AI bot header. The new title is **SASS AI Assistant**.
2. Removed the hardcoded no-results reply **“I could not find a matching approved policy or feature guide…”**.
3. Added a **general GenAI fallback** for questions unrelated to a known HRM policy or module, using a separately configured compatible chat-completions provider. The bot can now ask a generative model even when there is no RAG match.
4. Retained policy/feature/knowledge **RAG with sources**, direct owner-only HRM record lookups, permission-filtered feature navigation and confirmation-based actions.
5. Added **six specialist assistant modes**, with descriptions and allowed feature counts: General; People & HR; Recruitment & ATS; Payroll & Attendance; Performance & Learning; IT & Employee Support. These are specializations, **not additional account permissions**.
6. Improved the offline fallback with useful HR/technology explanations and practical next steps; when the model is disabled it does not pretend to answer arbitrary questions.
7. Fixed two existing frontend action-submit gaps: `mark_notification_read` and `update_my_preferences` now pass the corresponding form data to the server rather than `{}`. Existing server ownership/staleness checks still apply.
8. Kept the **right-side, non-overlapping dock** and preserved all 73 source-mapped HRM feature routes.

## How to enable general GenAI

Set the following **backend environment variables** securely in the server or deployment manager (not in frontend JavaScript).

```env
AI_COPILOT_GENERATION=1
AI_API_KEY=YOUR_SERVER_SIDE_PROVIDER_KEY
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4.1-mini
```

A compatible chat-completions provider and a valid key are required. Without them, the app still provides source-based HRM guidance and a limited built-in knowledge fallback. **No API keys are shipped in the ZIP.** Update environment variables and restart the backend. Server-side outbound HTTPS access is required for external model calls. A successful startup does **not** prove that the external provider is reachable; verify with an innocuous test question.

When enabled, **safe user questions and published all-staff RAG excerpts may be transmitted to the configured external AI provider**. Do not enter confidential or personal identifiers. Questions matching sensitive-personal markers are not forwarded. Published manager/admin-only knowledge is retrieved for permitted users in the HRM database but **never sent to external GenAI**. No employee database rows, unapproved drafts, passwords, or action parameters are included in the provider request. Note that automated checks for PII cannot guarantee perfect detection; do not put restricted information in AI prompts. Follow your company’s privacy/legal policies before enabling a third-party provider.

## What the bot actually controls

- **All 73 source-registered features**: permission-scoped navigation, feature help, setting shortcuts, and guided Add / View / Edit / Delete steps through existing feature pages. These are not remote bot execution for every operation.
- **16 existing direct AI action types**: leave, service requests, attendance, personal calendar, work arrangements, expenses, attendance corrections, HR task assignment/status, own notifications and own preferences. These are reviewed and confirmed, delegated to existing handlers, and role/ownership-limited.
- **Restricted workflows**: payroll posting/edits, recruitment or employment decisions, approval outcomes, disciplinary action, bulk employee edits, arbitrary SQL, employee deletion and unapproved data sharing cannot be executed through chat. Use the normal authorized HRM screens and approvals.
- **Specialist agents** only adjust responses and relevant navigation; selecting an agent cannot reveal hidden modules or authorize new actions.

## Test results from isolated environment

- `python server/ai_assistant_v4_test.py`: **PASS** — general GenAI mocked provider with no RAG match, approved policy/RAG citation, specialist roles, authorization, personal-data filtering, restricted knowledge externalization, company-specific no-hallucination, offline response.
- `python server/ai_copilot_test.py`: **PASS** — 73 feature plans, 16 confirmed actions, ownership, confirmation expiration/replay, prior AI workflows.
- `python server/feature_screen_integrations_test.py`: **PASS** — 73 representative feature route/table contracts in test DB.
- `python scripts/check-ai-right-dock.py`: **PASS** — 15 right dock/layout source checks.
- `python server/full_mysql_schema_test.py`: **PASS** — 269 MySQL table definitions and 2,216 declared columns.
- React/TypeScript source syntax parsing: **PASS**, 43 files (not a full build; React/Lucide/Vite packages unavailable here).

**Still unverified:** real provider network calls, live MySQL, full frontend build with installed npm dependencies, live right-dock browser behavior, and end-to-end control of every feature. The ZIP does not deploy to your production website or change production employee records.

## Staging deployment

1. Back up production database and existing release files. Create a **staging copy** first.
2. Install frontend dependencies under `web` with `npm ci` and run `npm run build`. Install Python backend dependencies from `server/requirements.txt`.
3. Use the supplied application database and the existing SQL migrations as needed; no additional AI schema migration is needed for installations already on the 269-table build.
4. Configure GenAI only on the backend if approved. Do not expose API keys via `VITE_*` environment variables or browser code.
5. Run `CHECK_AI_ASSISTANT_V4.bat` on Windows, or the Python scripts individually on other platforms.
6. In staging, log in as an employee and an HR administrator. Test general questions, published policy answers, role-scoped knowledge, right-side dock, navigation, self-service actions and denied permissions.
7. Verify connected production-like MySQL and an external model response with a non-sensitive question before promoting to production.
