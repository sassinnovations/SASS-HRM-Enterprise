# SASS HRM Enterprise v2.1 — original demo design + shared workflow improvements

## What changed

This release is built on **v2.0.1**. It keeps the original SASS white, pale-lavender and indigo/violet style tokens and the same solution-area navigation. It does **not** add demo employees, sample policies, demo salaries, default passwords, or demo payroll entries.

### Shared improvements across the original demo screens

1. **Original demo screen parity:** all 40 original menu destinations, Developer Console, and real-organization modules remain represented. The existing design-parity validator checks the palette and linked screens; it does not prove browser appearance.
2. **Data tables:** shared HR tables now have sortable column headers, a record counter, selectable 10/25/50 rows per page, pagination, and a contextual no-search-match message. Sorting/paging only acts on rows authorized by the server. This is **not** a bulk download or new access to other employees' HR details.
3. **Forms:** the shared modal has a dialog role, initial keyboard focus, Escape-to-close, explicit required/number and date-range checks, and inline validation feedback. Backend validation remains authoritative.
4. **Data resilience:** an API source error no longer erases previously loaded data from other successful sources. A visible banner still reports failed sources, and the top bar has a workspace refresh button. Cached records may be stale after a failed refresh and must not be treated as verified current data.
5. **Date handling:** date-only input defaults use `YYYY-MM-DD` based on the local calendar, avoiding browsers returning locale-specific dates or a UTC day offset.
6. **Unified styling:** reusable controls use the existing SASS design tokens `#FFFFFF`, `#F7F9FD`, `#EEF0FF`, `#5A5FE9` across desktop and narrow screens. Tables remain scrollable on small screens.

### Verification tooling

- `scripts/verify-v21-ui.py`: static checks for shared table/filter/form/date/data-reliability changes and design tokens. Included in `VERIFY_EVERYTHING.bat` and GitHub Actions.
- `CHECK_ALL_SCREENS.bat`: optional **read-only** Playwright navigation audit for each module visible to the signed-in role, including the React error boundary, JavaScript errors, and data-source banners. It requires an actual running backend using **MySQL**, an accessible frontend, and local `SASS_E2E_EMAIL` / `SASS_E2E_PASSWORD` environment variables. It never saves credentials or creates employee records.
- Existing server-side suites and source-level checks remain enabled.

## Safe Windows test sequence

1. Back up the organization's **MySQL** data and safely keep the existing `.env` secrets outside the ZIP. Do not run `CREATE_ADMIN.bat` on a database that already has an administrator.
2. Extract v2.1 to a new folder. Do not overwrite the original project or the MySQL volume.
3. Start MySQL and the backend/frontend, then check `http://localhost:8000/api/health` has `"database":"mysql"`.
4. Run `VERIFY_EVERYTHING.bat`. This validates static design, backend suites, and attempts the frontend production build.
5. For a separate **read-only navigation audit**, install Playwright and Chromium (if needed): `pip install playwright`, `python -m playwright install chromium`. Set `SASS_E2E_EMAIL` and `SASS_E2E_PASSWORD` in your local terminal only, then run `CHECK_ALL_SCREENS.bat`. The script will check pages visible to that account; to cover each role, rerun with authorized accounts for those roles.
6. Test saving and editing records on a private staging MySQL database before handling real personal information. Check additional browser resolutions (desktop/tablet/mobile) and the full permission matrix manually or via further automated tests.

## Verification in the packaging workspace

- Existing design-parity and design-regression tests passed for the v2.1 version.
- All ten backend test scripts passed on isolated SQLite test databases; the Employee Services suite was run separately after the combined run hit a time limit. The route audit includes 158 role-scoped API responses across 79 GET routes.
- All TS/TSX files parsed successfully using the locally installed TypeScript parser; all CSS files parsed successfully.
- The UI change verifier and Python compilation of the browser audit passed.

**Not verified here:** A complete `npm run build` (required frontend packages unavailable offline), a real MySQL 8.4 server, full login/click flows on Chrome and mobile, SMTP delivery, independent security certification, statutory payroll/tax compliance. Do not infer production readiness from static checks and isolated tests.

## Known limitations carried forward

Real payroll publishing requires finance/legal validation; tax calculators are indicative. Employee case records (grievance, discipline) require sensitive-data security governance. The document vault must have encryption, active malware scanning, retention rules, and security testing before being enabled for real employee files. SSO/MFA, deployment monitoring, audit retention, backups and independent penetration testing remain separate production hardening work.
