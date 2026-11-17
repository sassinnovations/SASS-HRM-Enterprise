-- OPTIONAL manual upgrade for EXISTING SASS HRM MySQL databases. BACKUP FIRST.
-- The updated application also applies this column automatically on first startup.
-- Run only if information_schema.columns shows content_sha256 is absent.
ALTER TABLE candidate_import_batches ADD COLUMN content_sha256 CHAR(64) NULL;
-- Existing candidate records and uploaded Excel archives are NOT deleted by this migration.
