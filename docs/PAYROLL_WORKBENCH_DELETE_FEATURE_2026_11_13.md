# Payroll Processing Workbench — Safe Delete Update (13 November 2026)

## What changed

**Payroll Workbench → Salary structures:** a **Delete** button is available beside each configured salary package. Admins must supply a reason (8–300 characters) and type `DELETE` to confirm. If the employee has any saved monthly adjustments, those must be removed first. Existing payroll snapshots and the employee's HR profile are *never* deleted by this action.

**Payroll Workbench → Monthly adjustments:** a **Delete** button appears beside adjustments for the selected month. The button is unavailable when there is any payroll run for that period, because deleting that adjustment would not change an already-created snapshot. To delete the adjustment, first delete the draft/reviewed pay run for that period; published runs cannot be deleted.

**Payroll Workbench → Create monthly payroll snapshot:** each **Draft** or **Reviewed** pay run now has **Inspect run** and **Delete** actions. Deleting such a run removes the run and the run's simulated payslip snapshot rows in the same database transaction. It leaves salary structures and monthly adjustments unchanged, allowing HR to revise data and generate a new draft. **Published** pay runs have no Delete button, and the API rejects deletion requests with HTTP 409.

Only logged-in HR administrators can use these APIs (`require_hr`). Each completed deletion is recorded in `audit_events` with the acting administrator, reference and reason. The API also rejects missing/incorrect confirmation, short/blank reasons, and non-existent records.

## The reviewed November 2026 run shown in your screenshot

When you deploy the update, sign in as the HR administrator, open `/compensation/payroll-workbench`, scroll to **3 · Create monthly payroll snapshot**, and find the **2026-11 / Reviewed** row. Click **Delete**, enter an 8+ character deletion reason, and type `DELETE` at the second confirmation. After deletion, the month can have a new draft. Use **Inspect run** first and export any reconciliation records you need. **Nothing will be deleted automatically** by the upgrade.

## Safe upgrade from an existing installation

1. **Back up the live MySQL database** using your proven backup/restore process (the project has `BACKUP_MYSQL.bat`). Verify the backup.
2. **Preserve** your existing `server/.env`, root `.env`, Docker MySQL volumes, encryption keys and service credentials. This ZIP intentionally contains no live credentials. **Never run** `docker compose down -v` or wipe/reset a live database.
3. Replace application source with this updated release, preserving local config and data. Rebuild/restart the backend and frontend using your existing deployment process. `START_DOCKER_FULL.bat` is available for a compatible local Windows Docker installation; a live production deployment requires your normal release process.
4. For isolated regression tests, run `CHECK_PAYROLL_DELETION.bat`. For live MySQL checks, run `CHECK_COMPENSATION_MYSQL.bat`. Test the buttons in a staging environment with non-production employee/payroll records and confirm both the 200 result and error messages.
5. Verify normal viewing/export of older **Published** runs and that newly deleted draft/reviewed months are available to regenerate; verify the admin audit trail.

## Implementation details

New JSON-body `DELETE` endpoints:

- `/api/payroll-v2/salary-packages/{employee_id}`
- `/api/payroll-v2/adjustments/{employee_id}/{month}`
- `/api/payroll-v2/runs/{run_id}`

Required JSON body: `{ "confirm": "DELETE", "reason": "Explain why this record must be removed" }`.

No destructive schema migration is required, and no new MySQL tables are created. MySQL run deletion locks the run row during the transaction so a concurrent review/publication cannot bypass the Published protection. MySQL pay-item foreign keys are respected by explicitly deleting only the unpublished run's children before the run record.

## Verification notes

Passing locally: `server/payroll_delete_test.py`, `server/payroll_esi_review_test.py`, `server/compensation_ops_test.py`, `server/compensation_settings_v32_test.py`, `server/route_audit_test.py`, `server/mysql_sql_compat_test.py`, `server/full_mysql_schema_test.py`, `scripts/check-page-routing.py`, TSX syntactic transpilation, and Python compilation.

Not verified here: live MySQL deletion against your production data, Docker deployment, and a full React production build (npm dependencies were not available offline). **This update does not change your deployed website until you install and deploy it.** This workbench remains a simulation; it does not carry out wage transfers, tax filings, or statutory compliance certification.
