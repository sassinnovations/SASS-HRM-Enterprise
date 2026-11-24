-- SASS HRM v4.5.0: additive MySQL 8.4 security activity schema.
-- IMPORTANT: Back up your database before execution. Inspect your current
-- DB first with CHECK_FULL_MYSQL_SCHEMA.bat and repair the older missing tables.
-- This file DOES NOT fix the 16 existing missing v4.4 tables or work_email.
-- Run only after verifying the selected connection/database is sass_hrm.
-- No account passwords, JWTs, IP addresses, or browser data are stored here.
CREATE TABLE IF NOT EXISTS account_login_events (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 created_at VARCHAR(64) NOT NULL,
 FOREIGN KEY(employee_id) REFERENCES employees(id),
 INDEX idx_login_events_employee_date(employee_id,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
