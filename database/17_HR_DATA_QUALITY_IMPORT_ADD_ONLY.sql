-- HR data quality center: reviewed CSV/XLSX HRIS imports, mapping preferences and audit metadata.
-- No workbook bytes or row-level personal information are stored here.
CREATE TABLE IF NOT EXISTS hr_data_quality_import_settings (
  id BIGINT NOT NULL PRIMARY KEY,
  mapping_json LONGTEXT NOT NULL,
  duplicate_mode VARCHAR(12) NOT NULL DEFAULT 'reject',
  date_format VARCHAR(12) NOT NULL DEFAULT 'YYYY-MM-DD',
  sheet_name VARCHAR(100) NOT NULL DEFAULT '',
  default_role VARCHAR(20) NOT NULL DEFAULT 'employee',
  default_work_mode VARCHAR(20) NOT NULL DEFAULT 'On-site',
  trim_values TINYINT NOT NULL DEFAULT 1,
  skip_blank_rows TINYINT NOT NULL DEFAULT 1,
  max_rows BIGINT NOT NULL DEFAULT 1000,
  updated_by BIGINT NOT NULL,
  updated_at VARCHAR(64) NOT NULL,
  CONSTRAINT fk_hr_dq_import_settings_author FOREIGN KEY (updated_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS hr_data_quality_import_history (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  filename VARCHAR(180) NOT NULL,
  content_sha256 CHAR(64) NOT NULL,
  source_rows BIGINT NOT NULL,
  created_rows BIGINT NOT NULL,
  duplicate_rows BIGINT NOT NULL,
  actor_id BIGINT NOT NULL,
  created_at VARCHAR(64) NOT NULL,
  CONSTRAINT fk_hr_dq_import_history_actor FOREIGN KEY (actor_id) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX idx_dq_import_history_actor ON hr_data_quality_import_history(actor_id);

