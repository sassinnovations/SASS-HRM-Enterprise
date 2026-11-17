-- SASS HRM: configurable hiring stage requirements and permissions.
-- BACK UP BEFORE UPGRADING. Select the existing database deliberately.
-- Additive, no candidate deletion or sample rows.

CREATE TABLE IF NOT EXISTS hiring_stage_settings (
 stage VARCHAR(32) NOT NULL PRIMARY KEY,
 checklist_json LONGTEXT NOT NULL, instructions LONGTEXT NOT NULL,
 sla_days INT NOT NULL DEFAULT 7, reviewer_role VARCHAR(16) NOT NULL DEFAULT 'manager',
 note_min_chars INT NOT NULL DEFAULT 8, updated_by BIGINT NULL,
 updated_at VARCHAR(64) NOT NULL DEFAULT '',
 FOREIGN KEY (updated_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

