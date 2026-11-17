# SASS HRM — Asset Management requirements and upgrade guide

This release extends **Employee Services → Asset management**. It is additive and
**does not delete, reset, or replace employee, candidate, payroll, or asset data**.

## What is available

- Required on *new comprehensive registration*: active employee, asset name, unique
  serial number, category, detailed **Asset description** (10–1,500 characters),
  condition, and office/storage location.
- Optional fields: brand/manufacturer, model, internal asset tag (unique when entered),
  purchase date, purchase price in INR, warranty expiry, supplier, invoice reference,
  accessories issued, and internal HR/IT notes.
- Search and status filters; export current visible inventory as CSV (formula-safe).
- Edit details with required reason and audit trail; serial number remains immutable.
- HR inspections with functional/accessory/security checks and recorded condition.
- Maintenance requests and HR-only state changes (Open → In Progress → Resolved/Cancelled).
- Existing custody history, transfer, return, reassign and send-for-repair remain available
  below the new register.
- Admin-only purchase amounts, supplier, invoice and internal notes. Employees see
  only equipment assigned to them; HR can see the full inventory.
- Warranty alerts for items expiring within the next 30 days.

This application does not install tracking software, verify delivery signatures,
process purchases, upload receipts, or contact vendors automatically.

## Database changes

New canonical schema: **215 tables**, **1,764 columns**, **230 named indexes**,
**381 foreign-key relationships**. Two new tables:

- `asset_profiles`: required description, classification, condition, location,
  optional purchase/warranty/accessory metadata, edited-by and time.
- `asset_inspections`: inspection checklist and evidence/condition history.

The existing `asset_maintenance_requests` table is now used by the API, and
`asset_lifecycle_events` continues to record assignment and changes. The installation
does not seed any candidates or other application records.

## Safe upgrade of an existing 213-table installation

1. Back up the configured MySQL database with `BACKUP_MYSQL.bat` or your approved backup
   process and **test that the backup can be restored**.
2. Check that `database/15_ADDITIONAL_CONTROL_TABLES_ADD_ONLY.sql` was already applied,
   and the current deployment includes `asset_maintenance_requests`.
3. Apply **only** `database/16_ASSET_MANAGEMENT_PROFILES_INSPECTIONS_ADD_ONLY.sql`
   to the intended existing database using an authorized MySQL administrator.
4. Deploy the updated frontend and backend, install frontend dependencies, and run
   `npm run build` inside `web/` before publishing.
5. Run `CHECK_ASSET_MANAGEMENT.bat` for isolated tests and schema checks.
   Use `CHECK_ALL_DATABASE_CONNECTIONS.bat` for a read-only live schema audit.
6. In Asset Management, inspect older records. Older assignments remain intact and may
   not yet have an `asset_profiles` row; HR can open **Edit** and enter required details.

**Never run the fresh-install SQL over a live HRM database. Never run `docker compose down -v`
or delete/reset MySQL volumes.** MySQL `CREATE TABLE` DDL is not transactional;
reconcile any partial migration before retrying.

## New installation

Use `database/02_FRESH_INSTALL_ALL_IN_ONE.sql` only on a fresh empty database,
then run normal SASS HRM account setup. No candidates or sample assets are preloaded.

## Security and verification limits

The API validates required fields, protects HR edits, scopes employee reads, records
inspection and maintenance actions, and logs privileged changes. All isolated
Asset Management regression tests and schema checks pass.

The frontend source has passed TSX syntax parsing, but the complete `npm run build`
was **not executed successfully** because the required Vite dependencies are absent
in this environment. A running MySQL/Docker stack, live web deployment and full
browser click-through have **not** been verified here.
