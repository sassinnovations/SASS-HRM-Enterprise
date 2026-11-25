# SASS HRM Enterprise — SASS AI Copilot v5 functional upgrade

**Release:** 25 November 2026  
**Base:** `SASS_HRM_ENTERPRISE_HTTP_500_DIAGNOSTIC_UPDATE_2026-11-25.zip`  
**Scope:** Floating AI chatbot functionality only; no database migration.

## Function improvements delivered

1. **Context-aware general chat** — The chat includes up to three prior *general GenAI question-and-answer pairs* so that natural follow-ups such as “Give me another example” can use earlier context. Context is ephemeral: the browser sends it with the next question, and the API does not store it in MySQL.
2. **Private and company-specific boundaries** — Previous company-policy answers, personal HRM records, and restricted RAG results are excluded from the general-chat history sent to a configured external model. The backend independently checks recent turns for sensitive content and excludes the entire context if any turn is disallowed. Current company questions still require approved sources.
3. **Feature-aware suggestions** — New permission-filtered `GET /api/ai/copilot/suggestions?feature_key=<key>` returns relevant help and action-guide prompts for the active HRM feature; admin-only features return `404` to unauthorized users.
4. **Faster RAG retrieval** — Lexical search precomputes document frequencies instead of recalculating them for every candidate chunk. Alias expansion now matches whole terms/phrases to avoid accidental feature matches.
5. **Better request recovery** — A failed chat request restores the user's question to the input instead of silently losing it. API HTTP 500 and HTTP 503 failures display actionable, sanitized troubleshooting advice. No backend secrets are included.
6. **Interface quality** — Added Copy Answer, auto-scroll to the most recent message, clearer GenAI-provider status, contextual suggested questions, and a reduced-motion-friendly copy control. The existing movable, resizable floating robot and window remain unchanged.
7. **Configuration visibility** — `GET /api/ai/copilot/capabilities` now reports `provider_status` (`ready`, `missing-key`, or `disabled`) and `recent_general_context`, without exposing credentials. "Ready" means configured, **not** a successful live provider call.

## Existing features preserved

- Role-aware navigation and guided workflows for the registered HRM screens.
- Existing 16 confirmed, allowlisted assisted actions, still subject to existing HRM permissions and manual confirmation.
- RAG over published policies, approved knowledge and feature guides; published article scope/audience restrictions.
- Owner-scoped personal record lookups, administrator knowledge studio and database diagnostics.
- The non-modal, draggable/resizable right-side floating bot, with conversation state preserved while minimized.
- The HTTP 500 diagnostic improvement with `/api/live`, `/api/health`, `/api/ready`, and its read-only troubleshooting script.

## Setup and verification

1. **Back up** the deployed source and MySQL database. Do not reset, truncate, or delete tables.
2. Extract the ZIP in staging. Configure `.env` for the backend (use `.env.example` as reference). The optional general GenAI function needs `AI_COPILOT_GENERATION=1`, a server-side `AI_API_KEY`, `AI_BASE_URL`, and `AI_MODEL`. Never expose the key as `VITE_...`, in frontend code, or in public logs.
3. In the project root on Windows, run `CHECK_AI_ASSISTANT_V5.bat`. On macOS/Linux run `python server/ai_copilot_v5_test.py`, `python server/ai_assistant_v4_test.py`, and `python scripts/check-ai-right-dock.py`.
4. With network access, run `cd web && npm ci && npm run build`. The environment used to package this ZIP did not have the complete frontend npm dependencies, so this build remains to be verified.
5. Test in staging with Employee, HR Sub-Admin, and HR Administrator accounts. Open features, check new suggestions, ask a general question and follow up, ask a company policy question with and without approved evidence, and verify a confirmed action requires deliberate review.
6. Check `/api/live`, `/api/health` and `/api/ready` on the deployed backend. These are separate from actual external AI provider connectivity. For unresolved HTTP 500 errors, review the backend stack trace for the failing request.

## Test evidence and limitations

- `server/ai_copilot_v5_test.py`: isolated API test passed for limited general follow-up context, sensitive-context suppression, permission-filtered suggestions, request validation and RAG ranking.
- `server/ai_assistant_v4_test.py` and `server/ai_copilot_test.py`: selected prior GenAI/RAG/privacy/16-action and 73-feature-contract tests passed.
- `server/http_500_health_test.py`, `server/official_work_details_all_roles_test.py`, `server/module_excel_center_test.py`: selected regressions passed.
- `scripts/check-ai-right-dock.py`: 22 source checks passed. `scripts/check-empty-candidate-bundle.py`: no seed candidate records/job roles reintroduced.
- TypeScript transpile-based **syntax parsing** passed for modified frontend files, but it is not a complete `tsc` type check or real browser test.
- The 1,200-document lexical ranking performance check passed in an isolated local run. It is not a production performance guarantee.
- **Not verified:** live external AI provider request, production MySQL, full frontend build, end-to-end browser UX, all feature CRUD, or deployment to the hosted domain.

## Important boundaries

The copilot can guide users across registered HRM features, but it does **not** autonomously execute all possible create/edit/delete actions. Payroll changes, approvals, hiring decisions, admin account changes, and deleting employee data remain in their authorized workflows. An external GenAI provider is optional; without it the bot provides source-grounded HRM guidance and limited offline explanations, not arbitrary open-ended GenAI answers.
