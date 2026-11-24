-- SASS HRM v4.2 additive migration for EXISTING MySQL 8.4 installations.
-- Back up your database before running. No DROP/DELETE/TRUNCATE operations.
-- Use your existing configured sass_hrm database in MySQL Workbench.
-- v4.2: employee-controlled performance evidence and an append-only goal check-in journal.
CREATE TABLE IF NOT EXISTS performance_evidence (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL, title VARCHAR(160) NOT NULL,
 details TEXT NOT NULL, category VARCHAR(32) NOT NULL,
 occurred_on VARCHAR(10) NOT NULL, visibility VARCHAR(12) NOT NULL DEFAULT 'Private',
 archived INTEGER NOT NULL DEFAULT 0, created_at VARCHAR(64) NOT NULL, updated_at VARCHAR(64) NOT NULL,
 FOREIGN KEY(employee_id) REFERENCES employees(id),
 INDEX idx_perf_evidence_employee(employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS performance_goal_checkins (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 goal_id BIGINT NOT NULL, author_id BIGINT NOT NULL,
 summary TEXT NOT NULL, blockers TEXT NOT NULL, next_step TEXT NOT NULL,
 created_at VARCHAR(64) NOT NULL,
 FOREIGN KEY(goal_id) REFERENCES goals(id), FOREIGN KEY(author_id) REFERENCES employees(id),
 INDEX idx_perf_checkin_goal(goal_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
