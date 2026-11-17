# Operational MySQL extension — 173 tables

The SASS HRM schema expands from 153 to 173 tables by appending 20 review/approval data structures.
See `database/README.md` for installation and rollback guidance. The authoritative schema has
1,343 columns, 147 named indexes, and 252 foreign-key relationships. The 20-table patch adds
184 columns, 40 named indexes, and 59 FK relationships.

The new tables are *not wired into application screens or API handlers*. They are reserved for
future implementations of employee transfer/authorization reviews; attendance roster and leave
reconciliations; payroll change/review controls; recruiting/references; and learning/compliance
and asset returns. HR and recruitment permissions must be enforced server-side if APIs are added.

## Safeguards

- Existing HRM records, candidate data and payroll snapshots remain untouched by this release.
- New installations preload **zero candidates**.
- Never store raw biometrics, secrets, or bank account credentials in these structures.
- The versioned migration contains 20 `CREATE TABLE IF NOT EXISTS` statements; no updates/deletes.
- A live test of MySQL queries and browser interactions was not possible in this environment.

## Upgrade sequence

1. Back up the production MySQL database, confirm restore, and inspect the chosen schema name.
2. If the live database contains the previous 153 tables, run only the `13_...ADD_ONLY.sql` patch.
3. Run the read-only audit `CHECK_OPERATIONAL_MYSQL_EXTENSION.bat /LIVE`.
4. Do not reset volumes. Defer all new screens/automations until they have API permissions and testing.
