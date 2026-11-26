# SASS HRM — HTTP 500 diagnostics and safe health-check release

**Source:** Latest floating AI bot release, 25 November 2026.

## What this fixes

The old `/api/health` endpoint used the normal database wrapper, which could attempt schema installation during a status check, and returned an unhelpful HTTP 500 on database errors. The new `/api/health` connects to MySQL directly, runs only `SELECT 1`, and returns **HTTP 503** with a non-sensitive message if the database is unavailable. The new `/api/live` answers whether the API process is alive without touching the database. The existing `/api/ready` still checks required tables and reports HTTP 503 when a module is unavailable.

This is a *diagnostic improvement*, not a claim that an unknown live HTTP 500 has been resolved. The source of an actual 500 must be identified from the server error log for the failing URL.

## Diagnose a deployed server

1. Open `https://YOUR_BACKEND/api/live`. It should return JSON status `alive`.
2. Open `https://YOUR_BACKEND/api/health`. It should return JSON status `ok`, or 503 if MySQL is unreachable.
3. Open `https://YOUR_BACKEND/api/ready`. It checks important HRM tables (and reports 503 if unavailable).
4. Run `python scripts/diagnose-http-500.py --url https://YOUR_BACKEND` (do not use the frontend host unless it actually runs the backend).
5. In the hosting dashboard, inspect the **backend application logs at the exact time** of the HTTP 500. Find the failing API request path and the exception type. Redact secrets, tokens, passwords, employee data and authorization headers before sharing.
6. Verify the backend has a valid `JWT_SECRET` (40+ characters), `DB_ENGINE=mysql`, and correct MySQL connection variables. `MYSQL_HOST` overrides Railway's `MYSQLHOST`; remove local `MYSQL_HOST=127.0.0.1` and `MYSQL_PORT=3307` overrides when using managed Railway MySQL.
7. Confirm the frontend `VITE_API_URL` is the backend base origin, e.g. `https://your-backend.example` **without `/api`**, and rebuild/redeploy after changing Vite env variables. Check CORS to match the HTTPS frontend origin.

For authorized host operators only, run the read-only command `python scripts/diagnose-http-500.py --database` (or `DIAGNOSE_HTTP_500.bat` on Windows) inside the installed application environment. This opens MySQL directly and checks four key tables with zero-row reads. It does not install schema or modify candidate/employee data.

## Interpret results

- `/api/live` fails: wrong backend URL, unavailable process, or reverse-proxy/startup deployment issue.
- `/api/live` passes but `/api/health` fails: backend is running; troubleshoot MySQL connection.
- `/api/health` passes but `/api/ready` fails: required HRM schema tables may be missing or inaccessible; preserve your database and review additive migrations.
- All three pass but one AI action returns 500: inspect the **specific `/api/ai/copilot/...` endpoint log**, record ID/request time (not private contents), and its underlying database operation/provider configuration.
- All three show HTML: the URL is likely hitting the frontend rewrite, not FastAPI; correct `VITE_API_URL`.
- A page build fails with 500 before HRM opens: inspect hosting/build logs and npm dependencies. This diagnostic does not replace a completed `npm ci && npm run build`.

## Tests

`cd server && SASS_HRM_TESTING=1 DB_ENGINE=sqlite JWT_SECRET=... python http_500_health_test.py` (set environment variables using your own shell): verifies status behavior and error privacy with a test-only SQLite database. This is *not* a live MySQL test.

**Production precautions:** Do not reset MySQL, delete records, expose `.env`, disable authentication, grant global privileges, or change model permissions to work around HTTP 500. Back up before any deployment and test first in staging.
