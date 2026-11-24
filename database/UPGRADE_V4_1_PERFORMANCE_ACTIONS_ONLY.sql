-- SASS HRM v4.1.0 additive migration: back up MySQL before applying.
-- On a populated MySQL database, select the existing HRM database in Workbench.
-- CREATE TABLE IF NOT EXISTS does not remove or alter existing employee records.
-- v4.1 follow-up actions for human-led employee performance and appraisals.
CREATE TABLE IF NOT EXISTS performance_followup_actions (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL, title VARCHAR(160) NOT NULL, notes TEXT NOT NULL,
 category VARCHAR(32) NOT NULL, due_on VARCHAR(10) NOT NULL,
 status VARCHAR(16) NOT NULL DEFAULT 'Open', created_by BIGINT NOT NULL,
 created_at VARCHAR(64) NOT NULL, completed_at VARCHAR(64) NULL, updated_at VARCHAR(64) NOT NULL,
 FOREIGN KEY(employee_id) REFERENCES employees(id), FOREIGN KEY(created_by) REFERENCES employees(id),
 INDEX idx_perf_followup_owner(employee_id), INDEX idx_perf_followup_due(due_on)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
