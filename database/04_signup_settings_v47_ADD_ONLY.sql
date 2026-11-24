-- Existing installations: back up first; this only adds the registration policy table.
-- Disable/enable roles in People Management > Account Provisioning.
-- v4.7 administrator-controlled public registration policy. Does not alter existing accounts.
CREATE TABLE IF NOT EXISTS account_signup_settings (
  id BIGINT NOT NULL PRIMARY KEY,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  allow_employee TINYINT(1) NOT NULL DEFAULT 1,
  allow_hr_subadmin TINYINT(1) NOT NULL DEFAULT 1,
  allow_admin TINYINT(1) NOT NULL DEFAULT 1,
  allowed_email_domain VARCHAR(191) NOT NULL DEFAULT '',
  updated_by BIGINT,
  updated_at VARCHAR(64) NOT NULL DEFAULT '',
  CONSTRAINT fk_signup_settings_updated_by FOREIGN KEY(updated_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
