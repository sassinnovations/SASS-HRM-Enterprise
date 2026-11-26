-- SASS HRM — SASS INNOVATIONS ENTERPRISE | migration 21 | 243 -> 263 tables
-- Additive schema-only foundations for recruitment, employee operations, attendance,
-- payroll, expenses, assets, and integration data quality.
-- Do not run the fresh installer against an existing database. Back up MySQL first.
-- No existing table is altered. No records are inserted, updated, or deleted.
-- Deleting a JD clears its nullable references below; no full JD description
-- or candidate resume is duplicated in these schema-only foundations.

-- Recruitment matching / human-review metadata (5).
CREATE TABLE IF NOT EXISTS recruitment_match_runs (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  job_description_id BIGINT NULL,
  scoring_version VARCHAR(48) NOT NULL,
  candidate_count INT NOT NULL DEFAULT 0,
  run_status VARCHAR(24) NOT NULL DEFAULT 'Queued',
  requested_by BIGINT NOT NULL,
  started_at DATETIME(6) NULL,
  completed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (job_description_id) REFERENCES recruitment_job_descriptions(id) ON DELETE SET NULL,
  FOREIGN KEY (requested_by) REFERENCES employees(id),
  CHECK (candidate_count >= 0),
  INDEX idx_match_runs_jd (job_description_id,created_at),
  INDEX idx_match_runs_status (run_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recruitment_match_results (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  run_id BIGINT NOT NULL,
  candidate_id BIGINT NULL,
  match_score DECIMAL(5,2) NOT NULL,
  skill_match_score DECIMAL(5,2) NULL,
  experience_match_score DECIMAL(5,2) NULL,
  evidence_summary VARCHAR(1000) NOT NULL DEFAULT '',
  reviewed_status VARCHAR(24) NOT NULL DEFAULT 'NotReviewed',
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (run_id) REFERENCES recruitment_match_runs(id),
  FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE SET NULL,
  CHECK (match_score >= 0 AND match_score <= 100),
  UNIQUE KEY uq_match_result_run_candidate (run_id,candidate_id),
  INDEX idx_match_result_rank (run_id,match_score),
  INDEX idx_match_result_review (reviewed_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recruitment_match_review_notes (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  match_result_id BIGINT NOT NULL,
  reviewer_id BIGINT NOT NULL,
  review_action VARCHAR(24) NOT NULL DEFAULT 'Comment',
  review_note VARCHAR(1500) NOT NULL DEFAULT '',
  reviewed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (match_result_id) REFERENCES recruitment_match_results(id),
  FOREIGN KEY (reviewer_id) REFERENCES employees(id),
  INDEX idx_match_review_result (match_result_id,reviewed_at),
  INDEX idx_match_review_actor (reviewer_id,reviewed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recruitment_jd_revision_markers (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  job_description_id BIGINT NULL,
  revision_number INT NOT NULL,
  content_sha256 CHAR(64) NOT NULL,
  change_category VARCHAR(64) NOT NULL DEFAULT 'Content',
  changed_by BIGINT NOT NULL,
  recorded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (job_description_id) REFERENCES recruitment_job_descriptions(id) ON DELETE SET NULL,
  FOREIGN KEY (changed_by) REFERENCES employees(id),
  CHECK (revision_number > 0),
  UNIQUE KEY uq_jd_revision_number (job_description_id,revision_number),
  INDEX idx_jd_revision_actor (changed_by,recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recruitment_jd_approval_requests (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  job_description_id BIGINT NULL,
  decision_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  request_reason VARCHAR(500) NOT NULL DEFAULT '',
  requested_by BIGINT NOT NULL,
  reviewer_id BIGINT NULL,
  reviewed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (job_description_id) REFERENCES recruitment_job_descriptions(id) ON DELETE SET NULL,
  FOREIGN KEY (requested_by) REFERENCES employees(id),
  FOREIGN KEY (reviewer_id) REFERENCES employees(id),
  INDEX idx_jd_approval_status (decision_status,created_at),
  INDEX idx_jd_approval_jd (job_description_id,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Candidate applications, shortlisting, and interview changes (3).
CREATE TABLE IF NOT EXISTS candidate_application_links (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  candidate_id BIGINT NULL,
  job_description_id BIGINT NULL,
  application_status VARCHAR(32) NOT NULL DEFAULT 'Applied',
  application_source VARCHAR(80) NOT NULL DEFAULT 'Manual',
  linked_by BIGINT NOT NULL,
  linked_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE SET NULL,
  FOREIGN KEY (job_description_id) REFERENCES recruitment_job_descriptions(id) ON DELETE SET NULL,
  FOREIGN KEY (linked_by) REFERENCES employees(id),
  UNIQUE KEY uq_candidate_jd_link (candidate_id,job_description_id),
  INDEX idx_candidate_app_status (application_status,linked_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS candidate_interview_schedule_changes (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  interview_id BIGINT NULL,
  previous_schedule_at DATETIME(6) NULL,
  new_schedule_at DATETIME(6) NOT NULL,
  reschedule_reason VARCHAR(600) NOT NULL,
  requested_by BIGINT NOT NULL,
  acknowledged_by BIGINT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (interview_id) REFERENCES interviews(id) ON DELETE SET NULL,
  FOREIGN KEY (requested_by) REFERENCES employees(id),
  FOREIGN KEY (acknowledged_by) REFERENCES employees(id),
  INDEX idx_interview_schedule_change (interview_id,created_at),
  INDEX idx_interview_reschedule_time (new_schedule_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS candidate_shortlist_decisions (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  candidate_id BIGINT NULL,
  job_description_id BIGINT NULL,
  decision VARCHAR(24) NOT NULL DEFAULT 'Review',
  rationale VARCHAR(1200) NOT NULL DEFAULT '',
  decided_by BIGINT NOT NULL,
  decided_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE SET NULL,
  FOREIGN KEY (job_description_id) REFERENCES recruitment_job_descriptions(id) ON DELETE SET NULL,
  FOREIGN KEY (decided_by) REFERENCES employees(id),
  INDEX idx_shortlist_candidate (candidate_id,decided_at),
  INDEX idx_shortlist_jd (job_description_id,decision)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Employee onboarding and HR-case review (3).
CREATE TABLE IF NOT EXISTS employee_onboarding_task_assignments (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  onboarding_id BIGINT NULL,
  employee_id BIGINT NOT NULL,
  assigned_to BIGINT NOT NULL,
  task_label VARCHAR(191) NOT NULL,
  due_on DATE NULL,
  completion_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  completed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (onboarding_id) REFERENCES onboarding(id) ON DELETE SET NULL,
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (assigned_to) REFERENCES employees(id),
  INDEX idx_onboarding_assignment (employee_id,completion_status),
  INDEX idx_onboarding_due (due_on,completion_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_employment_verification_requests (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  request_type VARCHAR(64) NOT NULL,
  external_reference VARCHAR(191) NOT NULL DEFAULT '',
  request_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  requested_by BIGINT NOT NULL,
  verified_by BIGINT NULL,
  verified_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (requested_by) REFERENCES employees(id),
  FOREIGN KEY (verified_by) REFERENCES employees(id),
  INDEX idx_employment_verify_employee (employee_id,created_at),
  INDEX idx_employment_verify_status (request_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_policy_exception_requests (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  policy_id BIGINT NULL,
  exception_type VARCHAR(80) NOT NULL,
  justification VARCHAR(1200) NOT NULL,
  decision_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  requested_by BIGINT NOT NULL,
  approved_by BIGINT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (policy_id) REFERENCES policies(id) ON DELETE SET NULL,
  FOREIGN KEY (requested_by) REFERENCES employees(id),
  FOREIGN KEY (approved_by) REFERENCES employees(id),
  INDEX idx_policy_exception_employee (employee_id,decision_status),
  INDEX idx_policy_exception_policy (policy_id,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Time and leave governance (2).
CREATE TABLE IF NOT EXISTS attendance_location_exception_reviews (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  attendance_id BIGINT NULL,
  employee_id BIGINT NOT NULL,
  site_code VARCHAR(80) NOT NULL DEFAULT '',
  exception_reason VARCHAR(600) NOT NULL,
  review_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  requested_by BIGINT NOT NULL,
  reviewed_by BIGINT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (attendance_id) REFERENCES attendance(id) ON DELETE SET NULL,
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (requested_by) REFERENCES employees(id),
  FOREIGN KEY (reviewed_by) REFERENCES employees(id),
  INDEX idx_att_location_employee (employee_id,created_at),
  INDEX idx_att_location_status (review_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS leave_request_approval_steps (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  leave_request_id BIGINT NOT NULL,
  step_number INT NOT NULL,
  reviewer_id BIGINT NOT NULL,
  decision VARCHAR(24) NOT NULL DEFAULT 'Pending',
  decision_reason VARCHAR(700) NOT NULL DEFAULT '',
  decided_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (leave_request_id) REFERENCES leave_requests(id),
  FOREIGN KEY (reviewer_id) REFERENCES employees(id),
  CHECK (step_number > 0),
  UNIQUE KEY uq_leave_approval_step (leave_request_id,step_number),
  INDEX idx_leave_approval_review (reviewer_id,decision)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Payroll preflight and statutory filing evidence (2).
CREATE TABLE IF NOT EXISTS payroll_preflight_validation_results (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  pay_run_id BIGINT NOT NULL,
  rule_code VARCHAR(80) NOT NULL,
  severity VARCHAR(24) NOT NULL DEFAULT 'Warning',
  resolution_status VARCHAR(24) NOT NULL DEFAULT 'Open',
  issue_count INT NOT NULL DEFAULT 0,
  validated_by BIGINT NOT NULL,
  validated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (pay_run_id) REFERENCES pay_runs_v2(id),
  FOREIGN KEY (validated_by) REFERENCES employees(id),
  CHECK (issue_count >= 0),
  INDEX idx_preflight_run (pay_run_id,severity),
  INDEX idx_preflight_status (resolution_status,validated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payroll_statutory_filing_receipts (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  pay_run_id BIGINT NOT NULL,
  filing_category VARCHAR(64) NOT NULL,
  filing_period VARCHAR(24) NOT NULL,
  receipt_reference VARCHAR(191) NOT NULL,
  filed_on DATE NOT NULL,
  recorded_by BIGINT NOT NULL,
  recorded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (pay_run_id) REFERENCES pay_runs_v2(id),
  FOREIGN KEY (recorded_by) REFERENCES employees(id),
  UNIQUE KEY uq_statutory_receipt_ref (filing_category,filing_period,receipt_reference),
  INDEX idx_statutory_payrun (pay_run_id,filed_on)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Expense receipt review (1): references only, no stored receipt bytes.
CREATE TABLE IF NOT EXISTS expense_receipt_verification_cases (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  expense_id BIGINT NOT NULL,
  receipt_reference VARCHAR(191) NOT NULL DEFAULT '',
  verification_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  exception_code VARCHAR(64) NOT NULL DEFAULT '',
  reviewed_by BIGINT NULL,
  verified_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (expense_id) REFERENCES expenses(id),
  FOREIGN KEY (reviewed_by) REFERENCES employees(id),
  INDEX idx_expense_receipt_case (expense_id,created_at),
  INDEX idx_expense_receipt_status (verification_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Asset stocktakes (2).
CREATE TABLE IF NOT EXISTS asset_stocktake_sessions (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  session_label VARCHAR(191) NOT NULL,
  location_code VARCHAR(120) NOT NULL DEFAULT '',
  session_status VARCHAR(24) NOT NULL DEFAULT 'Draft',
  started_by BIGINT NOT NULL,
  confirmed_by BIGINT NULL,
  started_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  closed_at DATETIME(6) NULL,
  FOREIGN KEY (started_by) REFERENCES employees(id),
  FOREIGN KEY (confirmed_by) REFERENCES employees(id),
  INDEX idx_stocktake_status (session_status,started_at),
  INDEX idx_stocktake_location (location_code,started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS asset_stocktake_items (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  session_id BIGINT NOT NULL,
  asset_id BIGINT NOT NULL,
  observed_condition VARCHAR(32) NOT NULL DEFAULT 'Unverified',
  observed_location VARCHAR(120) NOT NULL DEFAULT '',
  variance_reason VARCHAR(500) NOT NULL DEFAULT '',
  counted_by BIGINT NULL,
  counted_at DATETIME(6) NULL,
  FOREIGN KEY (session_id) REFERENCES asset_stocktake_sessions(id),
  FOREIGN KEY (asset_id) REFERENCES assets(id),
  FOREIGN KEY (counted_by) REFERENCES employees(id),
  UNIQUE KEY uq_stocktake_session_asset (session_id,asset_id),
  INDEX idx_stocktake_item_asset (asset_id,counted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Inbound integration import metadata and row-level failures (2).
CREATE TABLE IF NOT EXISTS integration_import_batches (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  connector_name VARCHAR(120) NOT NULL,
  external_batch_reference VARCHAR(191) NOT NULL DEFAULT '',
  payload_sha256 CHAR(64) NOT NULL,
  imported_count INT NOT NULL DEFAULT 0,
  failed_count INT NOT NULL DEFAULT 0,
  batch_status VARCHAR(24) NOT NULL DEFAULT 'Received',
  initiated_by BIGINT NULL,
  received_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (initiated_by) REFERENCES employees(id) ON DELETE SET NULL,
  CHECK (imported_count >= 0 AND failed_count >= 0),
  INDEX idx_integration_batch_source (connector_name,received_at),
  INDEX idx_integration_batch_status (batch_status,received_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS integration_import_row_errors (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  batch_id BIGINT NOT NULL,
  source_row_number BIGINT NOT NULL,
  field_key VARCHAR(120) NOT NULL,
  error_code VARCHAR(80) NOT NULL,
  error_status VARCHAR(24) NOT NULL DEFAULT 'Open',
  resolved_by BIGINT NULL,
  resolved_at DATETIME(6) NULL,
  FOREIGN KEY (batch_id) REFERENCES integration_import_batches(id),
  FOREIGN KEY (resolved_by) REFERENCES employees(id) ON DELETE SET NULL,
  CHECK (source_row_number > 0),
  INDEX idx_integration_error_batch (batch_id,source_row_number),
  INDEX idx_integration_error_status (error_status,error_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
