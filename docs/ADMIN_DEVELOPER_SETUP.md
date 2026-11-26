# First SASS HRM administrator and developer diagnostics

## Full Docker stack: first account only

1. Start Docker Desktop and the configured project with `START_DOCKER_FULL.bat`. Use `SETUP_SASS_HRM.bat` **only for a new, unconfigured installation**. For upgrades, retain your existing `.env` files and MySQL volume.
2. Check that `http://localhost:8000/api/ready` is ready. Run `CREATE_ADMIN.bat` from the same project folder, if approved by your Windows security policy.
3. Confirm the displayed target database. Enter the intended work email, display name, employee code and office location. Choose a **new unique password** at the hidden prompt (12 or more characters with letters and digits). No password is supplied by the app.
4. Open `http://localhost:5173` and sign in with the newly created HR administrator account.

The batch uses the existing API container, checks MySQL, and refuses to run against a database that already contains employees. It does not grant developer diagnostics and does not install Windows Python or reset configuration. For a split local development setup, see the administrator CLI `server/create_admin.py --help` in the configured backend Python environment, and use it only via an approved procedure on a new, empty MySQL database.

**If Windows still blocks the batch:** Leave the protection enabled and follow your organization’s approved review or distribution process. A new ZIP does not make a batch trusted. Do not reset a populated database to get past the first-admin safeguard. Use the existing administrator or an authorized recovery path instead.

## Developer diagnostics

Developer diagnostics is a separate permission, enforced by the backend. The launcher does not enable it by default. The separate CLI grant is intended only where expressly authorized. This app does not provision a shared password or a second login for diagnostics.
