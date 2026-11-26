-- 20: Recruitment JD library; safe, add-only and no data seeded.
-- JD deletion is an authenticated API operation, never a database migration side effect.
CREATE TABLE IF NOT EXISTS jd_import_batches (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  filename VARCHAR(191) NOT NULL,
  content_sha256 CHAR(64) NOT NULL,
  rows_received INT NOT NULL,
  rows_imported INT NOT NULL,
  rows_skipped INT NOT NULL,
  imported_by BIGINT NOT NULL,
  imported_at VARCHAR(191) NOT NULL,
  FOREIGN KEY (imported_by) REFERENCES employees(id),
  INDEX idx_jd_import_date (imported_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recruitment_job_descriptions (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(191) NOT NULL,
  description LONGTEXT NOT NULL,
  department VARCHAR(191) NOT NULL DEFAULT '',
  location VARCHAR(191) NOT NULL DEFAULT '',
  employment_type VARCHAR(32) NOT NULL DEFAULT 'Full-time',
  required_skills TEXT NOT NULL,
  preferred_skills TEXT NOT NULL,
  min_experience DOUBLE NOT NULL DEFAULT 0,
  education VARCHAR(191) NOT NULL DEFAULT '',
  status VARCHAR(20) NOT NULL DEFAULT 'Open',
  job_opening_id BIGINT NULL,
  import_batch_id BIGINT NULL,
  dedup_key CHAR(64) NOT NULL,
  created_by BIGINT NOT NULL,
  updated_by BIGINT NOT NULL,
  created_at VARCHAR(191) NOT NULL,
  updated_at VARCHAR(191) NOT NULL,
  UNIQUE KEY uq_job_description_content (dedup_key),
  FOREIGN KEY (job_opening_id) REFERENCES jobs(id) ON DELETE SET NULL,
  FOREIGN KEY (import_batch_id) REFERENCES jd_import_batches(id) ON DELETE SET NULL,
  FOREIGN KEY (created_by) REFERENCES employees(id),
  FOREIGN KEY (updated_by) REFERENCES employees(id),
  INDEX idx_jd_status (status),
  INDEX idx_jd_title (title),
  INDEX idx_jd_batch (import_batch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
