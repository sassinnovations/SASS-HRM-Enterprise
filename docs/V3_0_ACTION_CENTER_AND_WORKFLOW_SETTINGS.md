# SASS HRM Enterprise v3.0.0 — Action Center and Workspace Settings

## What is new

- **Action Center:** role-scoped counts of active/overdue HR tasks, pending/overdue onboarding items, and open/high-priority helpdesk tickets. Existing task, onboarding, and helpdesk pages remain the place where users perform workflow actions.
- **Notification Inbox:** own-account list with All, Unread and Archived filters; mark all visible unarchived alerts read; archive/restore individually. Inbox display preferences (start on unread, compact view) persist per employee.
- **HR Workflow Settings:** administrator-only configurable helpdesk response target (1–30 days), task warning window (0–30 days), onboarding warning window (0–30 days) and a short organizational notice. Values are saved to MySQL and settings writes are audited.
- **Navigation:** Action Center and Notification Inbox in Workspace; Workflow Settings under People Management for HR. Settings page links to each new module.
- **Design:** preserves previous SASS purple/white layout and all existing modules.

### What the settings do *not* do

Target days are operational guidance and do not schedule email reminders, automatically approve requests, change payroll, change HR decisions, or promise a formal SLA. The existing JWT login and role checks remain in force. No demo users or default credentials were added.

## Update an existing installation safely (Windows 11)

1. **Back up MySQL** using the old working release's `BACKUP_MYSQL.bat` and confirm the backup exists.
2. Keep the private `.env` and `server/.env` configuration files separately. Never copy these into a public/shared ZIP or Git repository.
3. Extract this release to a new folder. Copy the existing environment files into the matching locations in this new folder (do not run fresh setup again).
4. Start Docker Desktop and open VS Code in the extracted project root.
5. Run `START_DOCKER_FULL.bat`. Compose preserves the existing named MySQL volume: `sass_hrm_real_sass_hrm_mysql_data`.
6. Verify `http://localhost:8000/api/health` reports `status=ok`, `database=mysql` and `version=3.0.0`. Then open `http://localhost:5173` and sign in.
7. Test Notification Inbox using an existing account with alerts; test Workflow Settings with an administrator.

**Never run `docker compose down -v` or delete the MySQL volume during an upgrade.** The v3.0 schema is additive, with three new tables. Existing records are not deleted by these changes.

### If the API container restarts or the website says connection refused

Use:

```powershell
docker compose -f docker-compose.full.yml ps -a
docker compose -f docker-compose.full.yml logs --tail 100 api
docker compose -f docker-compose.full.yml logs --tail 80 mysql
```

The original user's live Docker startup issue could not be reproduced in this offline audit, so these logs are needed to determine its actual cause. Do not paste environment secrets or access tokens.

## Checks performed for this release

- Python compilation succeeded.
- Existing isolated regression tests completed, including account, authentication, calendars, talent, culture, payroll/compensation, exports, organization, profiles and API audit.
- v3.0 isolated API test validates employee ownership, forbidden cross-account archive/restore, bulk mark read, preferences, role permissions, validation, persistence and audit entry.
- TypeScript type-check passed using archived local development dependencies.
- Navigation, theme, and package checks passed.
- Vite production build *could not be completed here* because the archived dependencies were installed for Windows and the Linux Rollup optional package was unavailable. A clean `npm ci` inside the Docker Linux builder is required.
- Live MySQL/Docker startup, SMTP, payroll compliance validation and interactive browser testing remain unverified.
