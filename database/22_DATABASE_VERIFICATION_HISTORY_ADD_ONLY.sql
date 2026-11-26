-- SASS HRM — SASS INNOVATIONS ENTERPRISE | migration 22 | database verification history
-- Safe add-only operational schema for persisted administrative connectivity checks.
CREATE TABLE IF NOT EXISTS database_verification_runs (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  run_status VARCHAR(24) NOT NULL,
  expected_tables INT NOT NULL DEFAULT 0,
  present_tables INT NOT NULL DEFAULT 0,
  missing_tables INT NOT NULL DEFAULT 0,
  missing_columns INT NOT NULL DEFAULT 0,
  missing_indexes INT NOT NULL DEFAULT 0,
  missing_foreign_keys INT NOT NULL DEFAULT 0,
  access_failures INT NOT NULL DEFAULT 0,
  requested_by BIGINT NOT NULL,
  checked_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (requested_by) REFERENCES employees(id),
  INDEX idx_database_checks_time (checked_at),
  INDEX idx_database_checks_status (run_status,checked_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS database_verification_findings (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  run_id BIGINT NOT NULL,
  finding_type VARCHAR(40) NOT NULL,
  object_name VARCHAR(191) NOT NULL,
  checked_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (run_id) REFERENCES database_verification_runs(id),
  INDEX idx_database_findings_run (run_id,finding_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS database_module_checks (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  run_id BIGINT NOT NULL,
  module_name VARCHAR(120) NOT NULL,
  required_count INT NOT NULL DEFAULT 0,
  present_count INT NOT NULL DEFAULT 0,
  missing_names VARCHAR(2048) NOT NULL DEFAULT '',
  FOREIGN KEY (run_id) REFERENCES database_verification_runs(id),
  UNIQUE KEY uq_database_module_run (run_id,module_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
