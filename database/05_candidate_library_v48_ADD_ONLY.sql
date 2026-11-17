-- Additive candidate search migration (existing HRM database; backup first).
-- Use once manually in MySQL Workbench, or let backend install automatically.
-- Additive migration: preserves existing ATS candidate IDs.
-- The original uploaded workbook is archived as checksummed BLOB chunks, ensuring
-- every auxiliary sheet, hyperlink, formula and exception survives the import.
CREATE TABLE IF NOT EXISTS candidate_import_batches (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 sha256 CHAR(64) NOT NULL UNIQUE,
 filename VARCHAR(255) NOT NULL,
 sheet_name VARCHAR(100) NOT NULL,
 rows_expected BIGINT NOT NULL,
 rows_imported BIGINT NOT NULL,
 file_size_bytes BIGINT NOT NULL,
 archive_chunks INT NOT NULL,
 content_sha256 CHAR(64) NULL,
 created_by BIGINT NULL,
 created_at VARCHAR(64) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS candidate_import_chunks (
 batch_id BIGINT NOT NULL,
 part_number INT NOT NULL,
 data MEDIUMBLOB NOT NULL,
 PRIMARY KEY(batch_id,part_number),
 FOREIGN KEY(batch_id) REFERENCES candidate_import_batches(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS candidate_profiles (
 candidate_id BIGINT NOT NULL PRIMARY KEY,
 import_batch_id BIGINT NULL,
 source_sheet VARCHAR(191) NULL,
 source_row BIGINT NULL,
 source_order BIGINT NULL,
 email TEXT NULL, phone TEXT NULL,
 location TEXT NULL, preferred_locations LONGTEXT NULL,
 education LONGTEXT NULL, degree TEXT NULL, university LONGTEXT NULL,
 postgraduate TEXT NULL, doctorate TEXT NULL,
 experience_years DOUBLE NULL, experience_raw VARCHAR(191) NULL,
 company TEXT NULL, designation TEXT NULL,
 salary_raw VARCHAR(191) NULL, salary_lpa DOUBLE NULL,
 notice TEXT NULL, resume_headline LONGTEXT NULL,
 skills_manual TEXT NOT NULL, screening_answers LONGTEXT NULL,
 raw_fields LONGTEXT NOT NULL,
 created_at VARCHAR(64) NOT NULL, updated_at VARCHAR(64) NOT NULL,
 FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
 FOREIGN KEY(import_batch_id) REFERENCES candidate_import_batches(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_candidate_profiles_import_order ON candidate_profiles(import_batch_id,source_order);
CREATE INDEX idx_candidate_profiles_experience ON candidate_profiles(experience_years);
CREATE INDEX idx_candidates_job_title ON candidates(job_title);
