-- Employee-owned drafts and request history preferences. Additive; no workflow rows altered.
CREATE TABLE IF NOT EXISTS self_service_preferences (
  employee_id BIGINT NOT NULL PRIMARY KEY,
  default_kind VARCHAR(32) NOT NULL,
  default_status VARCHAR(16) NOT NULL,
  page_size INT NOT NULL,
  FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS self_service_drafts (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  kind VARCHAR(32) NOT NULL,
  title VARCHAR(150) NOT NULL,
  notes TEXT NOT NULL,
  created_at VARCHAR(48) NOT NULL,
  updated_at VARCHAR(48) NOT NULL,
  KEY idx_self_service_drafts_owner(employee_id,updated_at,id),
  FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Private calendar preferences and personal inbox reminders.
CREATE TABLE IF NOT EXISTS employee_calendar_preferences (
 employee_id BIGINT NOT NULL PRIMARY KEY,
 week_start VARCHAR(9) NOT NULL DEFAULT 'monday',
 visibility VARCHAR(12) NOT NULL DEFAULT 'all',
 default_start_time VARCHAR(5) NOT NULL DEFAULT '',
 include_private_export TINYINT(1) NOT NULL DEFAULT 0,
 CONSTRAINT fk_calendar_preferences_employee FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_inbox_reminders (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 title VARCHAR(120) NOT NULL,
 body VARCHAR(1200) NOT NULL,
 due_date VARCHAR(10) NULL,
 is_done TINYINT NOT NULL DEFAULT 0,
 created_at VARCHAR(48) NOT NULL,
 updated_at VARCHAR(48) NOT NULL,
 INDEX idx_inbox_reminders_employee(employee_id,id),
 FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Personal account-security display preferences and private review checklist.
CREATE TABLE IF NOT EXISTS employee_security_preferences (
 employee_id BIGINT NOT NULL PRIMARY KEY,
 history_limit INT NOT NULL DEFAULT 30,
 display_timezone VARCHAR(12) NOT NULL DEFAULT 'local',
 FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_security_checklist (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 title VARCHAR(120) NOT NULL,
 due_on VARCHAR(10) NULL,
 completed INT NOT NULL DEFAULT 0,
 updated_at VARCHAR(64) NOT NULL,
 FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE,
 INDEX idx_sec_checklist_employee(employee_id, completed, due_on, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Manual coverage plans are advisory and never write leave requests.
CREATE TABLE IF NOT EXISTS leave_coverage_warning_options (
 id BIGINT NOT NULL PRIMARY KEY,
 weekdays_only TINYINT NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS leave_coverage_manual_plans (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 label VARCHAR(100) NOT NULL,
 primary_employee_id BIGINT NOT NULL,
 backup_employee_id BIGINT NOT NULL,
 starts_on VARCHAR(10) NOT NULL,
 ends_on VARCHAR(10) NOT NULL,
 status VARCHAR(16) NOT NULL,
 notes VARCHAR(500) NOT NULL DEFAULT '',
 revision INT NOT NULL DEFAULT 1,
 deleted_at VARCHAR(48),
 KEY ix_leave_coverage_plans_window (deleted_at,starts_on,ends_on),
 FOREIGN KEY(primary_employee_id) REFERENCES employees(id),
 FOREIGN KEY(backup_employee_id) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
