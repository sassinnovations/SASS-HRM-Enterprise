# SASS HRM Enterprise — Full Frontend Build Verification

## Scope

Source archive: `SASS_HRM_Enterprise_Uploaded_App_CSS_Merged_2026-11-13.zip`.

## What was tested in the isolated environment

- Parsed all 58 frontend TS/TSX/CSS source files using the globally installed TypeScript parser and PostCSS: **PASS**, zero parsing diagnostics.
- Ran `python scripts/check-page-routing.py`: **PASS**, 73 application routes, address-bar/navigation and refresh integration checks.
- Ran `python scripts/check-single-refresh.py`: **PASS**, single refresh control and module listeners.
- Attempted `npm ci --no-audit --no-fund`: **BLOCKED** before package installation. The npm debug log records `getaddrinfo EAI_AGAIN`/DNS resolution failures when fetching dependency tarballs from `registry.npmjs.org`. npm ended with `Exit handler never called`.
- `npm run build`: **NOT RUN**, because locked React, Vite, TypeScript and Lucide dependencies were not installed.
- Live authenticated application browser workflows: **NOT TESTED**; no running backend/database or application login session was available.

These checks do not establish that the frontend production build passes. They also do not establish functionality of payroll, candidate imports, uploads, or live MySQL.

## Run the full build on Windows

1. Back up your existing project before changing your deployment.
2. Extract the updated release ZIP. Open the `SASS_HRM_Enterprise` folder.
3. Double-click `VERIFY_FRONTEND_BUILD.bat`, or run it from Command Prompt.
4. Read `FRONTEND_BUILD_VERIFICATION_LOG.txt` in the same folder. The script returns failure if `npm ci` or `npm run build` fails, or Vite output is missing.
5. After the script passes, open Command Prompt in `web` and run `npm run preview -- --host 127.0.0.1`. Start the backend and MySQL separately if you need authenticated live operations.
6. In Chrome, verify login, menu navigation, sticky sidebar + scrolling, Candidate Search, Excel upload/delete, payroll adjustment/run delete, employee forms, and refresh. Observe Developer Tools Console and Network tabs for errors.

**Security and privacy:** Test delete actions with throwaway records; do not delete production payroll runs or candidate imports merely to validate buttons. Browser tests require a configured backend and appropriate authorized test account.

## How to report errors

Send the last 50 lines of `FRONTEND_BUILD_VERIFICATION_LOG.txt` if the script fails, or screenshots of the browser Console/Network errors if the build passes but a screen malfunctions. Do not share passwords, access tokens, or personal records in logs.
