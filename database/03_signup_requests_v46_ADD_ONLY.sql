-- Run ONLY after backing up sass_hrm and repairing the existing schema. Never resets employees.
-- v4.6: Public applications are PENDING; only authenticated HR admins can approve.
-- Passwords exist only as salted hashes; after review the request hash is erased.
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
