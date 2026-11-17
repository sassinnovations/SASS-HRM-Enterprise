# SASS HRM Enterprise — Independent Build and Live-Stack Verification

**Date:** 16 November 2026  
**Baseline:** `SASS_HRM_Enterprise_Payroll_Workbench_Complete_2026-11-16.zip`  
**Verdict:** Offline code and regression checks pass. **Full frontend build, actual MySQL queries in the running deployment, and logged-in browser workflows are not yet verified.**

## What was executed

- The release ZIP passed a CRC integrity check, and its 373 packaged entries were extracted safely for inspection.
- **21 of 21 existing focused regression and source-navigation checks passed** in this environment: payroll review and deletion, ESI, compensation settings, tax calculator, candidate library, hiring, biometric attendance, profile/account security, MySQL schema structure, schema migrations, 73-route navigation, refresh integration and zero candidate preload. One initially selected test name (`profile_management_test.py`) does not exist in this release; the actual profile suites (`profile_v29_test.py` and `profile_photo_v44_test.py`) were run and passed. That initial test-runner typo is excluded from the results.
- Globally installed TypeScript compiler parser checked **35 TypeScript/TSX** source files: **zero syntax errors**.
- PostCSS parsed **27 CSS** source files: **zero syntax errors**.
- A real `npm ci --no-audit --no-fund --fetch-retries=0 --fetch-timeout=10000` was attempted. It **failed during dependency download**, with `getaddrinfo EAI_AGAIN` for `registry.npmjs.org` and npm's `Exit handler never called` error. npm did not install React, Vite or other locked packages; therefore `npm run build` could **not** run. This is **not** a successful production build.
- Docker, `mysqld`, and MySQL client binaries are not available in this environment. There is no access to the user's local `127.0.0.1` stack or authorized browser session. **Real MySQL and browser checks were not performed.**

## Verification-script improvements in the accompanying ZIP

1. `scripts/verify-four-live-areas.ps1` and `scripts/verify-docker-full.ps1` now load the expected version from `web/package.json` rather than hardcoding a prior API version.
2. `scripts/check-live-mysql.ps1` correctly states that an `/api/health` response only confirms **configured engine selection**. The actual MySQL connection/schema proof is provided by the separate `scripts/verify-docker-full.ps1` invoking `server/deployment_probe.py` inside the API container.
3. The authenticated four-area checker now performs a **read-only payroll preflight** request for supported payroll months, validating the new workbench endpoint.
4. `VERIFY_BUILD_AND_LIVE_STACK.bat` runs the real frontend build checker, full Docker/MySQL schema probe, and four-area live checks in order. It stops on the first failure and **never resets MySQL volumes**.
5. `scripts/verify-browser-readonly.py` adds an **optional genuine Chromium UI smoke test**, requiring Python Playwright and an authorized test account. It signs in, navigates to five HRM screens, clicks the read-only payroll readiness button, and records JS/HTTP 5xx failures. It does not edit, delete or publish HR/payroll data and does not save login credentials.

## How to complete verification on Windows

Before running anything, **back up your MySQL database**, project environment files and deployment. Do **not** delete or reset MySQL/Docker volumes. Keep the stack running.

1. Extract the updated ZIP and open a Command Prompt in the `SASS_HRM_Enterprise` directory.
2. Run `VERIFY_BUILD_AND_LIVE_STACK.bat` (requires Node/npm, a functioning npm registry connection, Docker Desktop, and the configured running SASS HRM full stack). If it fails at the first step, share `FRONTEND_BUILD_VERIFICATION_LOG.txt` and fix the reported npm/TypeScript/Vite error before proceeding.
3. If the combined checker passes, optionally install the Chromium test dependency with `python -m pip install playwright` and `python -m playwright install chromium`.
4. Run `python scripts/verify-browser-readonly.py`. Use an authorized **test** account, not a payroll production administrator if avoidable. Credentials are prompted securely; no traces or screenshots are saved.
5. Inspect the output. Passing these targeted smoke checks does not constitute complete coverage of all 73 pages or certify payroll legislation/statutory filings.

**Scope:** The ZIP is an updated *verification package* only; it does not claim that your live HRM was modified or that MySQL data was imported. The app code and existing candidate/hiring/payroll features are unchanged. Live verification must run on a machine that can reach the real HRM stack.
