# SASS HRM — SASS INNOVATIONS ENTERPRISE
## 266-table database upgrade and feature-connection guide

### What was delivered

This is an **additive source-code release**, developed from the latest branded
263-table Saritha/JD million-row import release. It includes 3 new MySQL tables
that have administrator-facing APIs and screens, plus operational recruitment
APIs that use 4 existing previously schema-only tables.

**New tables (migration 22):**
- `database_verification_runs`: HR-admin initiated audit snapshots, totals and run status.
- `database_verification_findings`: missing schema objects and table access failures.
- `database_module_checks`: inventory-based table counts per business domain.

**Previously unused tables now connected to business workflows:**
- `recruitment_match_runs` and `recruitment_match_results`: save up to 100
  point-in-time advisory ATS matches and scanning metadata per requested run.
- `recruitment_match_review_notes`: manager or HR reviewer notes.
- `candidate_shortlist_decisions`: HR-admin decision records; does not move a
  candidate's hiring stage or automatically reject anyone.

The *Recruitment ATS* and *Candidate Search & Database* screens use a shared
`JobDescriptions` component; both now show Save ATS Results, saved runs, human
review, and HR shortlist controls. The *Developer Console* can inspect the
schema, review domain table coverage, and explicitly save an audit snapshot.

### Upgrade procedure for an existing 263-table database

1. **Back up** the production MySQL database and verify the backup can be
   restored. Do not delete Docker volumes, reset the Railway plugin, or run the
   `02_FRESH_INSTALL_ALL_IN_ONE.sql` file against a populated database.
2. Test the release on a **staging copy** of the database, including role
   permissions and complete business workflows.
3. Apply `database/22_DATABASE_VERIFICATION_HISTORY_ADD_ONLY.sql` in MySQL
   after confirming that migrations 1–21 have already been applied. The file
   has exactly three `CREATE TABLE IF NOT EXISTS` statements and no DML,
   `DROP`, `TRUNCATE`, `ALTER` or cascading deletes.
4. Deploy the **backend and frontend together** from the same ZIP to
   Railway/Vercel or your own hosting service. Preserve production secrets,
   `JWT_SECRET`, `MYSQL*` settings and live volumes.
5. Run `CHECK_MYSQL_266_TABLES.bat /LIVE` from Windows with the configured
   MySQL environment. This performs read-only verification. You can also run:

   ```bash
   cd server
   python mysql_feature_schema_integrity.py --file-only
   python check_all_mysql_connections.py --probe-tables
   ```

6. Log in as an HR administrator, open **Developer Console → MySQL database
   connectivity**, select **Verify all database tables** and inspect the
   domain-coverage and missing-object results. **Save verification snapshot**
   only if you intentionally want to persist an audit record.
7. In **Recruitment ATS / Candidate Search**, select a JD, calculate the ATS
   match estimate, choose **Save ATS results to MySQL**, open the saved run,
   and record a human review or HR shortlist decision. Confirm that the
   original candidate stage and candidate list remain unchanged.

### What verification means

The offline validator checks all bundled table/column/index/foreign-key
statements and their agreement across canonical, manual and fresh-install SQL.
The live validator additionally checks the connected database name, table and
column presence, index and foreign-key definitions and optional zero-row table
access. **Neither test alone proves a feature's application workflow works.**

The maintained static inventory still identifies **131 database-foundation
items without completed workflow certification**. Those require separate
business APIs/screens, access-control design and live end-to-end tests. The
static analyzer finds **136 tables directly referenced in backend SQL**; this
is not a certificate of production functionality or full read/write coverage.
The 266-table archive is not an automatically executed live migration.

### Performance, security and operational notes

- Every matching run scans candidates in batches, saves at most 100 scored
  results, and never persists full resumes, emails, passwords, or personal
  candidate profile payloads.
- Only HR admins can save the database verification snapshot and make
  shortlist decisions. HR admins and managers can save/view matching runs and
  record advisory review notes. Employees cannot access these endpoints.
- Historical match snapshots can outlive a deleted JD, with their optional
  `job_description_id` cleared by MySQL `ON DELETE SET NULL`. The candidate
  and associated review history are preserved for audit; handle data retention
  in accordance with your organizational policy.
- Very large JD workbooks use the existing streaming importer. The 1,000,000-
  row logical ceiling is not a guarantee of completion within hosting limits.
- Production MySQL, production Vite build and hosted Railway/Vercel browser
  journeys were **not** available to execute in this environment. Test those
  before production rollout.
