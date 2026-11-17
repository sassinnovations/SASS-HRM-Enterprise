# Verify the four live SASS HRM areas on Windows

This guide supports SASS HRM backend version `4.8.0` and the existing `http://localhost:5173` frontend.

## What was changed

- The Docker startup and verification scripts no longer require ClamAV to have a Docker HEALTHCHECK label; instead, the real clamd service must respond to a protocol PING. This avoids a false startup failure while preserving malware scanning.
- The running-backend MySQL probe now verifies **every table declared in the shipped 113-table schema**, not just a 14-table subset. It reports employee, candidate and candidate-import-batch counts without revealing personal data.
- `VERIFY_FOUR_LIVE_AREAS.bat` is a new diagnostic for MySQL-backed API connectivity, frontend HTTP delivery, authenticated employee/payroll/administration endpoints, vault readiness, candidate search and an optional real upload/download/delete of **one temporary text file**.
- Corrected an outdated backend-version message in the MySQL check.

## How to run

1. **Back up** your existing MySQL database and `.env` configurations before applying any project update. Never reset an existing database as a troubleshooting step.
2. Copy the corrected project source into a separate folder; carry over your existing configuration by following the normal update instructions. Do not overwrite a populated MySQL data volume.
3. Start Docker Desktop, then run `START_DOCKER_FULL.bat`. It builds and launches MySQL, FastAPI, ClamAV and nginx/React. The first build needs internet access for pip/npm dependencies and the first ClamAV update may need time to initialize.
4. Run `VERIFY_DOCKER_FULL.bat` to verify container health, ClamAV PING, MySQL-backed API, nginx proxy and all 113 required MySQL tables.
5. Run **`VERIFY_FOUR_LIVE_AREAS.bat`**. It does read-only HTTP checks first. If the API is correctly backed by MySQL, it optionally prompts for your HRM login credentials. The script uses credentials in memory and does **not** write them to a report. Leave the email prompt blank to skip authenticated tests.
6. To verify file storage fully, answer **Y** to the prompt for the *temporary vault upload*. This sends a uniquely marked short `.txt` file to your account, retrieves it and deletes it. It does not upload your candidate spreadsheet or alter payroll/employee records. If removal fails, the script prints the test file ID so you can delete it in the vault.
7. Open `http://localhost:5173` and manually test the employee screen, compensation settings, payroll workbench, candidate search, and upload screen (including filter changes, save controls, refresh, table pagination, and validation messages).

## How to read the results

- **FAIL: API health/MySQL**: check that the backend uses `DB_ENGINE=mysql`, matches the current release, has correct credentials, and that the MySQL container is healthy. The API is at `http://localhost:8000/api/health`; the proxied API is `http://localhost:5173/api/health`.
- **FAIL: ClamAV vault readiness**: check `vault-av` container logs, malware signature downloads, `VAULT_FERNET_KEY` and `VAULT_AV_HOST`. Do **not** disable scanning or encryption to bypass the check.
- **FAIL: 113-table schema**: inspect the missing names in the probe report; take a backup before applying the approved additive migration. Never use destructive database reset scripts.
- **Candidate count = 0**: the candidate Excel import has not been performed on that live server. The bundled workbook and data seed do not install themselves. Import by **one** documented method only.
- **FAIL: frontend routes or JS**: rebuild web dependencies and the Docker web image, then retest. A successful HTTP response does not prove React event handlers or page buttons work.
- **FAIL: authentication or permission**: use an actual active HRM account; HR-only checks are attempted only when the account has the admin role.

## Scope and limitations

The standalone offline tests pass, but **this package has not connected to your Windows localhost or MySQL**, and the frontend production build could not be performed in the supplied execution environment because npm packages were unavailable. The four-area script checks read-only live functionality and optionally a temporary vault file. It **does not** change real salary data, run payroll, test statutory filing or bank transfers, or automate real browser clicks. For production, perform separate test-account end-to-end browser checks, a reviewed payroll dry-run, backup/restore tests and access-control verification.

Do not upload application logs containing JWT tokens, passwords or personal candidate data into a public repository; redact them before sharing diagnostic failures.
