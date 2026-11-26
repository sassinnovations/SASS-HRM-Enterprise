# SASS AI: conversational HR assistant

Open the floating **AI** button at the lower right of SASS HRM.

- Ask “What is my leave balance?”, “Show my pending work”, “What is my latest service request status?”, or “Show my timesheets.” These are role- or ownership-checked HRM workflows.
- Follow with **Check again**, **Open the source**, or **What next?** (or equivalent supported wording). The server identifies the last eligible source and checks current access and publication state again. It uses fresh records and published evidence instead of guessing. Links open the relevant HRM module without closing chat.
- HR administrators can ask “Show products” or “Show projects” for live register totals, or “Open product catalog” / “Open project register” to jump to the module.
- Start a new chat to clear the working context. The conversation is not stored in the database. A signed source pointer expires after 30 minutes and is scoped to the signed-in account, role and session version.
- Assisted changes use existing review and explicit confirmation. The assistant cannot perform arbitrary changes, approve payroll or hiring, or browse the internet.

## Enable optional general AI and drafting

Local HR answers and supported follow-ups work without a model key. An administrator can enable the existing optional model integration for general questions and drafting. Only do this after approving the provider and reviewing data-handling requirements. In the backend's existing environment configuration, set `AI_COPILOT_GENERATION=1`, provide `AI_API_KEY` securely, and choose an approved `AI_BASE_URL` and `AI_MODEL`. Restart the backend. Never put the key in frontend/VITE settings, source, or chat. The assistant shows provider configuration state.

Private employee lookups, admin register summaries and these context follow-ups stay in SASS HRM. For allowed general conversations and eligible RAG generation, the configured provider may receive prompts, eligible recent general messages, and approved all-staff excerpts. Automated screening is not a guarantee; do not enter confidential details in general chat. This upgrade does not enable the provider or send data externally.

## Update

If you already installed **Connected Overview, Products and Projects**, back up your project and merge the package into that configured folder. Keep existing root/server .env files and database. Restart frontend and backend; don't rerun setup. No additional schema is needed beyond the two existing catalog tables from that release. If coming from an older release, see PRODUCTS_PROJECTS_RELEASE_NOTES.md for the existing additive migration.

Tests use disposable SQLite data and a mocked model connection where needed. Live MySQL and your provider account were not contacted.
