# Database upgrade inventory — original Saritha (105 tables) to merged (241 tables)

Static source comparison confirms that **all 105 original MySQL `CREATE TABLE`
definitions are preserved exactly** after normalized whitespace, and **136
additional tables** were added without deleting any original table.
The merged schema contains **241 tables, 1,986 columns, 274 named indexes
and 442 foreign-key relationships**.

Each new table occurs in at least one of these 16 add-only migration scripts:

  1. `03_signup_requests_v46_ADD_ONLY.sql` — 1 new tables
  2. `04_signup_settings_v47_ADD_ONLY.sql` — 1 new tables
  3. `05_candidate_library_v48_ADD_ONLY.sql` — 3 new tables
  4. `07_HIRING_PIPELINE_ADD_ONLY.sql` — 3 new tables
  5. `08_payroll_workbench_controls_ADD_ONLY.sql` — 1 new tables
  6. `09_MISSING_MODULE_TABLES_ADD_ONLY.sql` — 5 new tables
  7. `10_ADVANCED_HR_MODULES_ADD_ONLY.sql` — 15 new tables
  8. `11_HIRING_STAGE_SETTINGS_ADD_ONLY.sql` — 1 new tables
  9. `12_ADDITIONAL_WORKFLOW_TABLES_ADD_ONLY.sql` — 20 new tables
 10. `13_ADDITIONAL_OPERATIONAL_TABLES_ADD_ONLY.sql` — 20 new tables
 11. `14_REVIEW_AND_PLANNING_TABLES_ADD_ONLY.sql` — 20 new tables
 12. `15_ADDITIONAL_CONTROL_TABLES_ADD_ONLY.sql` — 20 new tables
 13. `16_ASSET_MANAGEMENT_PROFILES_INSPECTIONS_ADD_ONLY.sql` — 2 new tables
 14. `17_HR_DATA_QUALITY_IMPORT_ADD_ONLY.sql` — 2 new tables
 15. `18_ADDITIONAL_OPERATIONAL_EVIDENCE_ADD_ONLY.sql` — 20 new tables
 16. `19_EXPENSES_CLAIMS_SETTINGS_ADD_ONLY.sql` — 4 new tables

The full list and script coverage are in `database/SARITHA_136_NEW_TABLE_MIGRATION_COVERAGE.csv`.
The original definition fingerprints are in `database/SARITHA_BASELINE_105_TABLE_HASHES.csv`.

**Important:** These are migration inventory files and proposed dependency-ordered
upgrade steps, **not a tested one-command migration for an existing database**.
The uploaded ZIP is a source snapshot, not a live MySQL schema dump; deployed
databases may differ. Back up and restore-test a clone, inspect live `information_schema`,
and review all ALTER/INDEX statements and any v4.3 account-identity changes before
applying scripts to staging. `05_candidate_library_v48_ADD_ONLY.sql` and
`17_HR_DATA_QUALITY_IMPORT_ADD_ONLY.sql` include standalone indexes that
require existence checks if rerun. `07_candidate_excel_removal_v50_UPGRADE.sql`
and historical v4.3 schema upgrades must be assessed independently.

Do not run `02_FRESH_INSTALL_ALL_IN_ONE.sql` on an occupied database.
Do not reset Docker volumes or add seeded employee/candidate/claim records.
