-- SASS HRM v4.3.0 - OPT-IN ADDITIVE UPGRADE (existing MySQL 8.4 database).
-- First BACK UP your database.  Keep its Docker volume and .env credentials.
-- Run against your existing, selected SASS HRM schema only.
-- This script never creates users, resets passwords, or deletes records.
-- The API performs this same migration at startup; do not run both concurrently.
-- For MySQL 8.4: add missing column using a metadata-controlled statement.
SET @schema_name = DATABASE();
SET @has_column = (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=@schema_name AND table_name='employees' AND column_name='work_email');
SET @alter_sql = IF(@has_column=0, 'ALTER TABLE employees ADD COLUMN work_email VARCHAR(191) NULL', 'SELECT 1');
PREPARE add_work_email FROM @alter_sql;
EXECUTE add_work_email;
DEALLOCATE PREPARE add_work_email;

-- Existing accounts retain numeric ID, employee code, password hash, role and sessions.
UPDATE employees SET work_email=LOWER(email) WHERE work_email IS NULL OR TRIM(work_email)='';
SET @has_index = (SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema=@schema_name AND table_name='employees' AND index_name='ux_employees_work_email');
SET @index_sql = IF(@has_index=0, 'CREATE UNIQUE INDEX ux_employees_work_email ON employees(work_email)', 'SELECT 1');
PREPARE add_work_email_index FROM @index_sql;
EXECUTE add_work_email_index;
DEALLOCATE PREPARE add_work_email_index;
-- Password hashes remain unchanged. Sign in with work_email or existing email.
