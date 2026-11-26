# SASS HRM Enterprise — Official Work Details Editing (Employee, HR Sub-Admin, HR Administrator)

## Location

Go to **My profile & settings → My details → Official work details**. An **Edit official details** button is available to Employees, HR Sub-Admins, and HR Administrators.

## Role behavior

| Account tier | Edit form | Saving behavior | Approval required |
| --- | --- | --- | --- |
| Employee | Yes | Submits proposed details to HR without altering the active employee record | Yes — HR Administrator |
| HR Sub-Admin (stored role `manager`, tier `hr_subadmin`) | Yes | Submits proposed details to HR without altering the active employee record | Yes — HR Administrator |
| HR Administrator (`admin`) | Yes | Directly updates their own existing official record using the existing protected Account Administration handler | No |

Employees and HR Sub-Admins can propose changes to employee code, official name, work email, department, designation, office, work mode, and joining date. A reason (6+ characters) is required. Their current work details **remain unchanged until approval**. Roles, passwords, sign-in email, database IDs, and permissions **cannot** be changed by this form.

## HR approval workflow

1. Employee or HR Sub-Admin opens **Edit official details**, proposes an update, enters a reason, and clicks **Submit for HR approval**.
2. HR Administrator opens **People Management → Profile management → Official work-detail approval requests**.
3. Administrator reviews proposed fields and the reason, then **Approves** or **Rejects**. Rejections require a review note.
4. Approval updates the existing employee record within a single database transaction and generates audit entries. Rejections leave the record untouched. Employee request history shows the decision.
5. If the original employee details changed after submission, approval is blocked to prevent overwriting a newer authoritative record. HR can reject the stale request and ask for a new one.

Changes to work email revoke previous login sessions. The employee must log in again as appropriate. The original employee ID, account role, password, payroll data and historical records remain intact.

## Database changes

A single additive table, `official_work_detail_requests`, holds the proposed-field JSON, original snapshot for stale-change detection, reason, status, reviewing administrator, review note and timestamps. The canonical MySQL source schema now declares **270 tables / 2,226 columns**. Existing table definitions are unchanged. Installer copies and table inventory were synchronized.

For a **fresh installation**, use the updated bundled installation scripts as documented in the main project.

For an **existing production MySQL installation**, after a verified backup, apply only the additive file:

`database/25_official_work_details_all_roles_ADD_ONLY.sql`

Run this migration against the intended SASS HRM database **before** deploying the upgraded backend. Do not reset database volumes, delete existing employees or reinitialize payroll records.

## Verification

From the `server` directory run:

- `python official_work_details_all_roles_test.py`
- `python official_work_details_edit_test.py`
- `python profile_v29_test.py`
- `python accounts_v25_test.py`
- `python full_mysql_schema_test.py`
- `python mysql_feature_schema_integrity_test.py`
- `python mysql_connection_audit_test.py`

The new integration test uses **a disposable SQLite database** and checks all three roles, request approval/rejection, ownership, unauthorized access, audit history, unchanged records before approval, and stale-change conflict protection. It does **not** test production MySQL or a deployed frontend.

Run `npm ci` and `npm run build` inside `web` after installing dependencies, and test each of the three roles against a staging MySQL copy before production deployment. A local TypeScript/TSX parse passed, but the complete frontend build could not be verified in this environment because project npm dependencies were not installed.

## Backend APIs added

- `GET /api/profile/me/official-change-requests`
- `POST /api/profile/me/official-change-requests`
- `GET /api/profile/admin/official-change-requests` — Administrator only
- `POST /api/profile/admin/official-change-requests/{request_id}/decision` — Administrator only

The direct administrator edit continues using `PATCH /api/admin/accounts/{employee_id}/profile`, with its validations centralized for reuse by the approval flow.

**Deployment status:** Only the downloadable source package was updated. No change was made to the live website or production MySQL.
