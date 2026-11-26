# SASS HRM Enterprise — AI Control Center, Generative AI & RAG (v2)

**Date:** 24 November 2026  
**Delivery:** Updated source project for staging, not a production deployment.  
**Starting point:** Existing SASS AI Copilot source release; old app screens and databases retained.

## What has actually been added

The earlier copilot was only a feature navigator with two confirmed write operations. This release keeps that original AI assistant and extends it; it does not add a duplicate bot.

- **73 inventoried feature guides:** Each permission-eligible feature appears under **AI Assistant → All features** with Open, Guide, linked Settings and any action shortcuts that have an explicit backend adapter. Chat replies also provide review-form shortcuts for matched allowlisted actions, without executing them. The server checks the user's role; developer grant remains separate. Feature-guide results explain which operations are in the bot versus the existing module UI.
- **Nine confirmed operations:** see table below. These call the existing HRM validation and database handlers, not user-supplied URLs, routes, SQL or model-generated function calls.
- **GenAI:** Optional compatible chat-completion model produces answers grounded in approved retrieved excerpts. Disabled unless both a key and `AI_COPILOT_GENERATION=1` are present.
- **RAG:** Existing BM25-like *lexical* ranking over approved policies, HR-admin-published articles and all permission-visible feature descriptions, with citations. This is not vector/embedding RAG and does not automatically index private employee, payroll, applicant, medical or document-vault contents.
- **My Records:** Permission/owner-scoped lookups for leave, attendance, service desk, goals, HR tasks, expenses, assets, training, benefits, personal calendar and other existing employee views. These raw records are not sent to the optional external LLM.
- **Admin Knowledge Studio:** Add/edit/publish/unpublish RAG guidance. Admin AI health summary reports feature coverage, published policies/articles and provider configuration (without exposing secrets).
- **Audit and safety:** Proposal is server-generated, employee-bound, 10-minute timeout, single-use, requires a separate explicit Confirm. Calendar Edit/Delete checks ownership and checks for changes since the preview. Operations continue through existing handlers and their audit logs.

## Exactly which changes the bot can perform

| Approved operation | Target | Effect | Additional restriction |
|---|---|---|---|
| `submit_leave` | Leave management | Create a pending request | Own leave; entitlement/overlap validation in existing API |
| `submit_service_request` | Request Desk | Create a new request | Own request; category must be active |
| `check_in` | Attendance | Check in | Own attendance only; existing company timezone and duplicate check |
| `check_out` | Attendance | Check out | Own attendance only; must have checked in |
| `create_personal_event` | Personal calendar | Add event | Own private event |
| `edit_personal_event` | Personal calendar | Edit event | Own event, server-reviewed record version |
| `delete_personal_event` | Personal calendar | Permanently delete event | Own event, server-reviewed record version, explicit warning |
| `request_work_mode` | Work arrangement | Create pending change | Own request, no automatic approval |
| `cancel_work_mode` | Work arrangement | Cancel pending request | Must be original requester; pending only |

**All other feature edits/deletes remain in the existing screens** with original permissions. No autonomous change to payroll, compensation, employee identities, recruitment decisions, job offers, approval decisions, role/security configuration, production database schema, or another employee's records. The bot is deliberately not an unrestricted organization-wide superuser. Only nine operations have been connected for direct write execution; **73 features have guided navigation and RAG metadata.**

## How to use

1. Log into SASS HRM as an authorized employee and open **AI Assistant**.
2. **Chat**: ask “Where do I edit an employee code?”, “Explain our approved leave policy”, “Show my calendar” or “How do I check in?”. View sources before relying on advice.
3. **All features**: search any of the 73 module names, select **Guide**, then open the feature, its authorized settings, or a related supported action.
4. **Assisted actions**: select an operation, enter the required fields, press **Review action**, read the exact preview, then **Confirm action**. The server validates permissions again on confirmation.
5. **Knowledge studio** (HR admin): publish approved policies or how-to knowledge; unpublish outdated guidance. The right column shows current status and RAG coverage.

## Installation (existing deployment)

1. **Back up production MySQL and application config**, verify ability to restore, and deploy to a staging environment first.
2. Copy the updated `server` and `web` application code together; no new schemas or DB tables are added beyond the two AI tables already introduced in the prior release. For an older production version, review and apply **only** the additive migration `database/23_AI_COPILOT_ADD_ONLY.sql` if missing, after a backup.
3. Use the existing MySQL database environment (`DB_ENGINE=mysql`, `MYSQL_HOST`/`MYSQLPORT` or Railway variables, database user/password, JWT_SECRET, CORS settings). No credentials or employee data are included in this source archive.
4. For optional external generation, configure and enable only after confirming privacy/data-processing requirements:

```dotenv
AI_COPILOT_GENERATION=0
AI_API_KEY=
AI_MODEL=gpt-4.1-mini
AI_BASE_URL=https://api.openai.com/v1
```

External generation sends questions and retrieved *published* content to the configured provider, if enabled; don't type confidential employee information into AI questions. Set `AI_COPILOT_GENERATION=1` only when ready.

5. Run `CHECK_AI_COPILOT.bat` on Windows or `python server/ai_copilot_test.py`, then `python server/feature_screen_integrations_test.py`, and `python server/full_mysql_schema_test.py` in an environment with dependencies installed.
6. Run `npm ci && npm run build` from `web/` and validate in a staging browser. The attempted frontend build in this environment failed from missing npm type-definition packages; syntax-level transpilation passed, but a full typecheck/build is outstanding.
7. Validate live MySQL schema connectivity and authenticated create/edit/delete in staging. This deliverable did **not** reach a live production MySQL server, an external GenAI API, or a deployed frontend.

## Architecture and boundaries

```text
Authenticated user → AI Assistant (React)
  ├── Chat → own-record read-only lookups OR lexical RAG over approved articles,
  │          published policies and permission-visible 73-feature descriptions
  │                 → optional external chat completion (published snippets only)
  ├── All features → role-filtered Guide/Open/Settings for existing screens
  ├── Assisted actions → explicit allowlist of 9 schema-validated operations
  │                 → Prepare (owner-checked, audit) → Review (10 min TTL)
  │                 → Confirm (actor, role, owner, version checks) → existing HRM handler
  └── HR Admin Knowledge Studio → draft / publish / unpublish / AI health
                              ↓
                         Existing MySQL schema
                    266 prior + 2 Copilot = 268 tables
```

**Important:** This release does not confer autonomous CRUD access to every HRM feature or prove live database connectivity for all 73 screens. The earlier audit found 131 schema-foundation tables needing workflow completion. Please do not interpret search/navigation capability as successful complete HRIS workflow execution.

## Included artifacts

- `docs/AI_COPILOT_FEATURE_CONTROL_MATRIX_2026-11-24.csv` — 73-feature capability-by-capability control matrix
- `server/ai_copilot_test.py` — isolated backend role/CRUD/RAG/confirmation tests
- `docs/SASS_AI_COPILOT_GENAI_RAG_INSTALL.md` — this full guide
- `docs/SASS_AI_COPILOT_TEST_REPORT_2026-11-24.md` — execution results and limitations

## Deployment notes

The assistant does not require another embedding/vector database; retrieval is lexical. Knowledge articles are manually approved and stored in existing MySQL. Do not import or index unreviewed HR records or raw payroll/ATS document repositories into an external provider. Every direct action is owner-scoped or permission-checked and must be confirmed by a person.
