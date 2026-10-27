# v2.2 Verification — exact scope of checks

This report describes checks run on the source ZIP in the development workspace, not a production certification.

## Fixed
- The previous `docker-compose.mysql.yml` health-check line had invalid YAML quoting. Corrected and confirmed both Compose files parse with PyYAML.
- `START_HERE.bat` now starts the complete Docker stack by default. Previous separate local development launchers are retained as `START_LOCAL_DEV.bat`.
- Added internal Docker networking: frontend nginx → FastAPI → MySQL 8.4. All ports are bound to Windows loopback, and the existing database volume is reused.
- Added configuration consistency check to catch mismatched MySQL passwords, placeholder JWT keys, or attempted production-mode use of the local Docker HTTP configuration.
- Added MySQL schema probe, Docker container health checks, nginx reverse-proxy smoke tests, and binary-safe SQL backup script.
- Existing SASS white/lavender/violet design and 40 reference screens are unchanged.

## Verified in the workspace
- Source-based MySQL/Docker audit: passed (including simulated bad-credential rejection).
- YAML parse: both database-only and full-stack Compose files passed.
- MySQL schema DDL order: all 74 declared tables have their referenced tables defined earlier.
- All ten existing Python backend test scripts passed with **isolated SQLite test databases**, never connecting to real employees.
- Existing role-scoped audit: 158 GET checks across 79 endpoints passed, including permission-denied cases.
- Original demo design and shared v2.1 UI regression checks: passed.
- React/TypeScript source parser: ten application files parsed without syntax errors.
- Python source compilation: passed.
- ZIP archive integrity, excluded secrets, and clean-extraction checks: passed.

## Not verified here
- `docker compose up --build` could not be executed because Docker is not installed in this workspace.
- A live MySQL 8.4 instance, InnoDB mutations, database backup/restore and schema migrations were not run here.
- Full `npm run build` could not complete because npm registry DNS failed with `EAI_AGAIN` and dependencies are not cached.
- No real browser/multiple-role E2E test, SMTP delivery, vault antivirus, production SSO/MFA, penetration test or statutory payroll/legal certification was performed.

## Windows acceptance tests

On Windows, stop prior Vite/Python servers, back up your old database, keep the original secrets and run `START_HERE.bat`. Then run `VERIFY_DOCKER_FULL.bat`, `VERIFY_EVERYTHING.bat`, and the read-only `CHECK_ALL_SCREENS.bat` with locally supplied authorized credentials. Use the live system only after these pass and after the independent security, privacy, retention, payroll and backup/restore reviews that your organization requires. Preserve the MySQL volume; never reset it to fix a login error.
