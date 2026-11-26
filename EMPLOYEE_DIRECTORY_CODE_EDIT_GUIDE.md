# SASS HRM — Employee Directory: edit staff codes and official employment details

**Release:** 23 November 2026 | **Company:** SASS INNOVATIONS ENTERPRISE

## Where to edit

Sign in as an **HR administrator**, then open **People Management → Employee HRIS → All employees → Edit** next to the correct employee. The dialog includes the existing employee code and lets you change it to a new unique code, for example `SASS0047`. **Do not use `SASS0047` for a different employee if that code is already assigned.** This release does not automatically set any employee's code and contains no production employee database.

In the Employee HRIS Edit window, administrators can edit:

- Employee code (3–50 letters, digits, periods, underscores or hyphens; must be unique case-insensitively)
- Official name, sign-in email and work email
- Designation, department and office/location
- Work mode (Remote, Hybrid, On-site)
- Joining date and reporting manager, including removing a manager
- Change reason (at least six characters when changing employee code or joining date)

**Save changes** persists the edited fields to the existing `employees` row in a single transaction. The table refreshes to show the new code. The directory's name cell displays the code. Other HRM modules join to the employee's unchanged numeric database ID and continue pointing to the same person. The edit is logged to `audit_events` including the old and new staff codes and the administrator's reason.

An administrator can also edit **Employee code**, **Joining date**, and **Change reason** through **People Management → Account administration → Edit details**. That panel uses the pre-existing, validated account-profile endpoint; the administrative account listing was updated to include joining dates.

## Security and guardrails

- Only an authenticated HR administrator may edit these official details. Managers and employees receive HTTP 403.
- The form/API cannot change an employee's numeric database ID, role, access tier, credentials or password. Account roles and password actions are separate in **Account administration**.
- Invalid code/date/email, conflicting code/email, self-reporting manager or reporting-line cycle is rejected. Database uniqueness constraints also protect against conflicting concurrent edits.
- Changes to sign-in or work email invalidate the edited employee's existing JWT sessions. If you change your own email, sign in again.
- Changing employee code does **not** delete the old employee, clear payroll or attendance records, create an account, or overwrite related database records. Historic exports/snapshots may preserve previously displayed codes.
- Biometric scanners, payroll providers or other **external systems that submit an employee code** may require their staff-code mappings to be updated after the change. Internal HRM records use numeric employee IDs.

## Existing database and deployment

**No new MySQL tables or schema migration are required.** This ZIP is source code; it does not contain or change the records in your live `hrms.sassinnovations.com` database. Before production deployment, back up your MySQL database and publish updated backend and frontend files. Rebuild/deploy the React app, then refresh the page. **Do not recreate the database, run fresh-install schema scripts against an existing database, or reset MySQL volumes.**

The deployment cannot be performed just by downloading this ZIP. An administrator must deploy the updated source to the hosting environment.

## Verification

Run `VERIFY_EMPLOYEE_DIRECTORY_CODE_EDIT.bat` on Windows, or from the project root:

```bash
python server/employee_directory_code_edit_test.py
python server/official_work_details_edit_test.py
python server/route_audit_test.py
```

Tests use temporary **SQLite test-only** databases. These verify roles, code `SASS0047`, uniqueness, joining-date reason, audit history, linked attendance ID, reporting manager edits and session revocation. They do not certify live MySQL connectivity or end-to-end browser behavior. The TypeScript source was syntax checked; full frontend build was not verifiable in the build environment because the required npm packages could not be installed.
