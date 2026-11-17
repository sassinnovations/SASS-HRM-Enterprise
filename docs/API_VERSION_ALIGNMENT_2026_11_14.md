# SASS HRM – API version warning fix (14 November 2026)

## Root cause
The previous Developer Console (`web/src/App.tsx`) hardcoded API v4.6.0,
while `web/package.json` and `server/main.py` both identify the bundled release as v4.8.0.
The resulting warning was a false mismatch between source versions; it did not
establish any MySQL corruption or an API failure.

## Changes
- Developer Console now imports the frontend release version from `web/package.json`.
- The developer warning appears only if the status endpoint reports a different version.
- The warning explains safe rebuild/deployment rather than implying that MySQL must be reset.
- Added `CHECK_API_VERSION_ALIGNMENT.bat` and `scripts/verify-api-version-alignment.py`.
- No payroll, employee, candidate, settings, schema, or stored data was changed.

## Safe Docker update on Windows
**Back up your MySQL database before deployments** and keep any production change window.
From the extracted `SASS_HRM_Enterprise` directory, with Docker Desktop running:

```powershell
docker compose -f docker-compose.full.yml ps
docker compose -f docker-compose.full.yml up -d --build --no-deps web
docker compose -f docker-compose.full.yml ps
```

This rebuilds only the web container, keeping the MySQL container and its named volume intact.
For a complete-stack upgrade from this same project (if required), use
`docker compose -f docker-compose.full.yml up -d --build` with verified backup and env.
**Never** run `docker compose down -v`, `docker volume rm`, or MySQL reinitialization
to solve this version-label problem.

After the rebuild, hard-refresh the browser (Ctrl+Shift+R), open Developer Console,
and confirm that the status API and frontend show v4.8.0. Check the proxy:

```powershell
Invoke-RestMethod http://127.0.0.1:5173/api/health
```

You can also run `CHECK_API_VERSION_ALIGNMENT.bat` and `VERIFY_DOCKER_FULL.bat`.

## Limitations
This package was statically checked in the authoring environment. It was not
deployed to your local Docker engine or your public server; no live browser build,
SQL transaction, or browser acceptance test has been claimed.
