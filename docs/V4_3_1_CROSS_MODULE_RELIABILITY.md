# SASS HRM v4.3.1: cross-module reliability upgrade

This is a source-level reliability improvement applied to every frontend module, not a replacement for live functional testing of every HR workflow.

- Frontend modules use one network transport with a 25-second timeout and actionable network errors.
- Authentication failures for requests carrying the currently stored bearer token cause a secure sign-out and an explanation on the login page. Normal permission-denied responses (403) do **not** force logout.
- Network disruptions show an application-wide warning without adding a second refresh button. The notice clears on a successful HTTP response.
- Browser-offline events display connection warnings; online events are only hints and do not certify that MySQL works.
- The workspace sync timestamp updates only if at least one data source loaded successfully. Failed sources remain listed.
- Exports and downloadable files also use the shared timeout and session handling.
- No changes to MySQL tables, accounts, JWT signing, server access controls, employee data, or existing page URLs.

## Safe upgrade

1. Back up your current MySQL database and private `.env` files.
2. Extract the new release to a separate folder. Preserve the existing named Docker volume.
3. Run `CHECK_RELIABILITY_V431.bat`, then `START_DOCKER_FULL.bat` after moving/restoring your environment files.
4. Sign in and test critical save, refresh, session expiry, and API-outage cases. Avoid submitting a form twice if you cannot confirm the first attempt saved.

## Verification limits

Frontend source and isolated regression checks are not substitutes for production Vite build, live Docker/MySQL, end-to-end browser tests or payroll compliance review.

## Page-by-page rollout checklist

`docs/V4_3_1_70_MODULE_CHECKLIST.csv` lists all 70 module URLs and highlights the live actions still to test.
