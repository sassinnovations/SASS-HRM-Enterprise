-- SASS HRM additive payroll workflow audit events; back up your existing database first.
CREATE TABLE IF NOT EXISTS payroll_run_events_v2 (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  run_id BIGINT NOT NULL,
  action VARCHAR(80) NOT NULL,
  note VARCHAR(1000) NOT NULL DEFAULT '',
  checklist_json LONGTEXT NOT NULL,
  actor_id BIGINT NOT NULL,
  created_at VARCHAR(191) NOT NULL,
  FOREIGN KEY (run_id) REFERENCES pay_runs_v2(id),
  FOREIGN KEY (actor_id) REFERENCES employees(id),
  INDEX idx_payroll_events_run (run_id,id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

