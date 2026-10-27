# SASS HRM Enterprise v2.9.0 — Profile Settings and HR Profile Management

## What was added

- **My profile** sidebar page and avatar shortcut: professional headline, preferred display name, professional biography, optional work telephone, IANA timezone, language preference metadata, selectable initial-avatar color, directory visibility. Settings persist in MySQL, scoped to the signed-in account.
- **Staff directory:** lists only active employees whose professional profiles have not been hidden. Optional professional contact details are visible only when the employee enables directory visibility. Personal contact addresses, emergency contacts, pay, passwords, JWTs, and HR notes are never included.
- **Identity correction workflow:** employees can request a correction to their official employee name. HR administrators approve/reject with audit logging; no self-approval. The request does not change an email address or account role and cannot replace account provisioning.
- **Profile management (HR only):** directory-visibility/completeness overview, search, pending correction reviews, and direct links to official HRIS record editing, account administration, and organization settings.
- **Existing personal settings preserved:** password changes, account session revocation, display density and date formatting, private emergency contacts, administrator permissions and existing employee modules remain unchanged.
- Professional profile values are not passport verification, legal identity validation, employee consent/legal compliance proof, or automatic localizations. Language is stored preference metadata; the complete interface remains English.

## Database & privacy

Additive tables: `professional_profiles` and `profile_change_requests`; index `idx_profile_changes_owner`. No existing tables are dropped or overwritten. Existing MySQL schema auto-application runs on backend startup; back up your current MySQL data before upgrading. HR may see professional profile completeness and correction requests, but does not gain access to private contact profiles through these new endpoints.

Paths:
- `GET /api/profile/me`, `PUT /api/profile/me`
- `GET /api/profile/directory`
- `GET /api/profile/me/requests`, `POST /api/profile/me/requests`
- `GET /api/profile/admin/overview`, `GET /api/profile/admin/requests`, `POST /api/profile/admin/requests/{id}/decision`

All endpoints require a valid Bearer JWT. Administrator routes require HR administrator role. Changes to official names are audited, reviewed as single-use decisions, and transactions roll back if a database operation fails.

## Running safely on Windows 11

### Upgrading a working deployment
1. Back up the existing MySQL Docker volume using your current `BACKUP_MYSQL.bat`, and verify the backup before upgrading.
2. Keep private `.env` and `server/.env` outside the release ZIP; securely restore to the correct locations in the updated project. Never publish credentials or reuse defaults.
3. Start Docker Desktop. Run `START_DOCKER_FULL.bat` from the extracted `SASS_HRM_Enterprise` folder. Do not run a fresh-install setup or `docker compose down -v` on an existing database.
4. Run `VERIFY_DOCKER_FULL.bat`, then confirm `http://localhost:8000/api/health` reports `2.9.0` and MySQL.
5. Open `http://localhost:5173`, sign in with your existing admin account, and open **My profile** or **Profile management**.

### Fresh empty installation only
Run `SETUP_SASS_HRM.bat`, `START_MYSQL.bat`, `CREATE_ADMIN.bat`, and `START_DOCKER_FULL.bat` in the order specified by the project setup instructions. Securely choose new credentials; no default administrator login is included.

### Troubleshooting a restarting API
MySQL being healthy does not mean the backend is healthy. From project root run:

```powershell
docker compose -f docker-compose.full.yml ps -a
docker compose -f docker-compose.full.yml logs --tail 100 api
```

Inspect backend logs before attempting schema or password changes. Do not delete persistent volumes or post secrets in chat.

## Testing

Run `CHECK_PROFILE_MANAGEMENT.bat` for isolated SQLite security/persistence checks. Run `VERIFY_EVERYTHING.bat` for the existing regressions and full build on the deployment machine. No production Docker engine or working MySQL deployment was available in the code audit environment; full live integration, performance, browser and accessibility checks must be run on Windows.
