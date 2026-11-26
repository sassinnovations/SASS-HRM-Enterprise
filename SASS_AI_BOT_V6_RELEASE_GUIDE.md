# SASS HRM Enterprise — Floating AI Bot v6

Date: 25 November 2026
Release type: additive application update (no database schema migration)

## Overview

The existing floating AI assistant has been improved **in place**, without adding a duplicate bot or a left-sidebar entry.

### New functionality

1. **Natural-language guided actions.** The chat recognizes 16 allowlisted actions, such as requesting leave, filing an expense claim, creating a service ticket, checking in/out, editing personal calendar events, submitting attendance corrections, managing own notifications/preferences, and updating HR tasks. Managers/HR Administrators may receive task-assignment suggestions within their existing permissions. Natural-language requests are matched by server-owned rules, not arbitrary model-generated tool calls.
2. **Explicit review and confirmation.** Chat returns an action shortcut only; it does not call a database write. User opens Assisted actions, fills the form, receives a preview from the existing backend, and explicitly confirms. Existing ownership, scope, validation, expiration, audit and stale-record rules remain active. Negated instructions and conceptual queries are excluded from action-intent routing.
3. **RAG result diversity.** Retrieval caps a single policy or knowledge article at two selected excerpts so several relevant sources can appear. Role and audience restrictions still apply before ranking. GenAI provider privacy restrictions remain unchanged.
4. **Export chat transcript.** A local browser text export with a privacy confirmation. No transcript upload, database storage, or telemetry was added. The file may contain sensitive information and should be protected.
5. **Retry failed chat input.** If the request fails, the previously submitted question is restored in the field with a retry control. Existing friendly HTTP 500/503 messages are retained.
6. **Floating window unchanged.** The bottom-right launcher, movable/resizable dialog, minimization, feature navigation and conversation continuity are retained.

## Files changed

- `server/ai_copilot.py` — action-intent recognition, query routing, diverse RAG results and exposed capabilities.
- `web/src/SassAICopilot.tsx` — action result label, local transcript export, retry and safer clear-chat confirmation.
- `web/src/sass-ai-copilot.css` — responsive chat and error controls.
- `server/ai_copilot_v6_test.py` — new isolated regression tests.
- `CHECK_AI_ASSISTANT_V6.bat` — Windows isolated regression launcher.

## Security and production considerations

- The assistant **does not** directly execute every operation across all 73 feature screens. Direct AI change operations remain limited to the existing 16 permission-checked actions.
- Company-specific facts must be sourced from authorized policy/knowledge/data, and general GenAI requests require a configured provider.
- Never paste passwords, payroll secrets or private employee records into the general GenAI chat.
- Data can be personal in a downloaded transcript: the export confirmation warns the user.
- This release does not change or clear production MySQL data, accounts, or the existing 270-table schema.
- Browser behavior, production MySQL and external LLM provider calls still need staging verification.

## Install and validate

1. Back up the deployed project and the production database.
2. Install this project's source in a **staging** environment using the existing README and environment variables; do not copy `.env` secrets from another user.
3. Install frontend dependencies with `cd web && npm ci`, then `npm run build`.
4. Run backend tests with `cd server && python ai_copilot_v6_test.py`. For compatibility, run `ai_copilot_v5_test.py`, `ai_assistant_v4_test.py` and `ai_copilot_test.py`.
5. Start the backend and verify `/api/live`, `/api/health`, `/api/ready` and authenticated `/api/ai/copilot/capabilities`.
6. Sign in as an Employee and separately as HR Administrator. Ask: “submit my leave request”, “create a support ticket”, and “what is check-in?”. Verify a review action is offered only for the first two; no record changes from chat alone.
7. Open the right-side floating bot, inspect mobile/desktop layout, test retry after an intentionally disconnected API, and confirm local transcript export.
8. Confirm in staging that all intended actions still require review and confirmation and that no employee can access admin-only workflows or another employee's records.
9. Only deploy to production after a successful build, staging end-to-end checks and normal change approval.

## Verification completed in the project workspace

- v6 isolated action-intent, role, no-side-effect and RAG diversity tests passed.
- v5 general conversation/provider privacy tests passed.
- v4 scoped knowledge/company-fact privacy tests passed.
- v3 73-feature navigation, owner-scoped actions and confirmation tests passed.
- 45 TypeScript/TSX files passed a parser-only syntax check (this is **not** a full type check or production build).
- Full frontend build and live deployment not performed.
