-- 19: Expenses & Claims settings, detailed claim register, activity and reimbursement records.
-- Add-only / no seeded claims, no records deleted, no bank operations.
CREATE TABLE IF NOT EXISTS expense_policy_settings (
  id BIGINT NOT NULL PRIMARY KEY,
  settings_json LONGTEXT NOT NULL,
  updated_at VARCHAR(191) NOT NULL,
  updated_by BIGINT NULL,
  FOREIGN KEY (updated_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS expense_claim_details (
  expense_id BIGINT NOT NULL PRIMARY KEY,
  expense_date VARCHAR(10) NOT NULL,
  merchant VARCHAR(150) NOT NULL DEFAULT '',
  business_purpose VARCHAR(1000) NOT NULL DEFAULT '',
  cost_center VARCHAR(80) NOT NULL DEFAULT '',
  receipt_reference VARCHAR(240) NOT NULL DEFAULT '',
  updated_at VARCHAR(191) NOT NULL,
  FOREIGN KEY (expense_id) REFERENCES expenses(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS expense_claim_events (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  expense_id BIGINT NOT NULL,
  actor_id BIGINT NOT NULL,
  event_type VARCHAR(40) NOT NULL,
  event_note VARCHAR(500) NOT NULL DEFAULT '',
  created_at VARCHAR(191) NOT NULL,
  FOREIGN KEY (expense_id) REFERENCES expenses(id),
  FOREIGN KEY (actor_id) REFERENCES employees(id),
  INDEX idx_expense_claim_events_expense (expense_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS expense_reimbursement_records (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  expense_id BIGINT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'Scheduled',
  external_payment_reference VARCHAR(120) NOT NULL DEFAULT '',
  notes VARCHAR(500) NOT NULL DEFAULT '',
  updated_by BIGINT NOT NULL,
  updated_at VARCHAR(191) NOT NULL,
  UNIQUE KEY uq_expense_reimbursement_claim (expense_id),
  FOREIGN KEY (expense_id) REFERENCES expenses(id),
  FOREIGN KEY (updated_by) REFERENCES employees(id),
  INDEX idx_expense_reimbursement_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
