-- SASS HRM Enterprise | ADD-ONLY MODULE TABLES | November 2026
-- Apply only to the correct existing HRM MySQL database, after a verified backup.
-- Select the database with USE `your_database_name` before executing this file.
-- These CREATE TABLE IF NOT EXISTS commands do not delete or update existing rows.
-- Existing table definitions/columns are NOT modified; run the complete read-only audit.
-- If existing tables have incompatible columns, do not reset volumes: review an ALTER migration.
-- No candidate records, payroll rows or employee records are included.

-- account_login_events
CREATE TABLE IF NOT EXISTS account_login_events (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL, created_at VARCHAR(64) NOT NULL,
 FOREIGN KEY(employee_id) REFERENCES employees(id),
 INDEX idx_login_events_employee_date(employee_id,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- account_signup_requests
CREATE TABLE IF NOT EXISTS account_signup_requests (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(191) NOT NULL,
  email VARCHAR(191) NOT NULL,
  work_email VARCHAR(191) NOT NULL,
  requested_role VARCHAR(32) NOT NULL,
  designation VARCHAR(191) NOT NULL,
  department VARCHAR(191) NOT NULL,
  location VARCHAR(191) NOT NULL,
  work_mode VARCHAR(32) NOT NULL,
  password_hash VARCHAR(191) NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'Pending',
  created_at VARCHAR(64) NOT NULL,
  reviewed_at VARCHAR(64),
  reviewed_by BIGINT,
  review_note VARCHAR(300),
  employee_id BIGINT,
  CONSTRAINT fk_signup_reviewer FOREIGN KEY(reviewed_by) REFERENCES employees(id),
  CONSTRAINT fk_signup_employee FOREIGN KEY(employee_id) REFERENCES employees(id),
  INDEX idx_signup_status (status,created_at),
  INDEX idx_signup_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- attendance_capture_events
CREATE TABLE IF NOT EXISTS attendance_capture_events (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  work_day VARCHAR(10) NOT NULL,
  event_type VARCHAR(32) NOT NULL,
  method VARCHAR(32) NOT NULL,
  occurred_at VARCHAR(64) NOT NULL,
  recorded_by BIGINT NULL,
  device_id VARCHAR(64) NOT NULL DEFAULT '',
  note VARCHAR(500) NOT NULL DEFAULT '',
  INDEX idx_attendance_capture_employee(employee_id,work_day),
  FOREIGN KEY(employee_id) REFERENCES employees(id),
  FOREIGN KEY(recorded_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- attendance_photo_evidence
CREATE TABLE IF NOT EXISTS attendance_photo_evidence (
  event_id BIGINT NOT NULL PRIMARY KEY,
  ciphertext LONGBLOB NOT NULL,
  created_at VARCHAR(64) NOT NULL,
  expires_at VARCHAR(64) NOT NULL,
  FOREIGN KEY(event_id) REFERENCES attendance_capture_events(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- attendance_device_nonces
CREATE TABLE IF NOT EXISTS attendance_device_nonces (
  device_id VARCHAR(64) NOT NULL,
  nonce VARCHAR(128) NOT NULL,
  used_at VARCHAR(64) NOT NULL,
  PRIMARY KEY(device_id,nonce)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

