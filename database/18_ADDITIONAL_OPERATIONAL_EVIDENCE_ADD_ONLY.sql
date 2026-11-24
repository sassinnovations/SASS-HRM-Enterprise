-- SASS HRM: Additive operational evidence tables (release 18).
-- Existing verified schema: 217 tables. Upgrade only after a backup and restore rehearsal.
-- This is a schema-only extension: no new APIs, HR actions, automatic decisions, or seeded records.
-- No raw biometric templates, scanned medical documents, employee addresses or payment credentials.
-- Do NOT use the fresh-install schema as an upgrade and do NOT reset MySQL volumes.

-- Employee lifecycle and verification (4)
CREATE TABLE IF NOT EXISTS employee_contact_change_reviews (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  field_code VARCHAR(64) NOT NULL,
  change_request_reference VARCHAR(191) NOT NULL,
  review_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  requested_by BIGINT NOT NULL,
  reviewed_by BIGINT NULL,
  reviewed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (requested_by) REFERENCES employees(id),
  FOREIGN KEY (reviewed_by) REFERENCES employees(id),
  INDEX idx_contact_change_employee (employee_id,created_at),
  INDEX idx_contact_change_status (review_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_employment_letter_register (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  letter_type VARCHAR(80) NOT NULL,
  secure_document_reference VARCHAR(191) NOT NULL,
  issue_status VARCHAR(24) NOT NULL DEFAULT 'Draft',
  requested_by BIGINT NOT NULL,
  issued_by BIGINT NULL,
  issued_on DATE NULL,
  expires_on DATE NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (requested_by) REFERENCES employees(id),
  FOREIGN KEY (issued_by) REFERENCES employees(id),
  INDEX idx_employment_letter_employee (employee_id,created_at),
  INDEX idx_employment_letter_status (issue_status,expires_on)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_exit_clearance_signoffs (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  clearance_type VARCHAR(80) NOT NULL,
  clearance_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  assigned_to BIGINT NOT NULL,
  completed_by BIGINT NULL,
  completed_at DATETIME(6) NULL,
  evidence_reference VARCHAR(191) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (assigned_to) REFERENCES employees(id),
  FOREIGN KEY (completed_by) REFERENCES employees(id),
  INDEX idx_exit_signoff_employee (employee_id,clearance_status),
  INDEX idx_exit_signoff_assignee (assigned_to,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_hr_case_consents (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  case_category VARCHAR(80) NOT NULL,
  consent_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  policy_version VARCHAR(40) NOT NULL,
  evidence_reference VARCHAR(191) NULL,
  recorded_by BIGINT NOT NULL,
  recorded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (recorded_by) REFERENCES employees(id),
  INDEX idx_hr_consent_employee (employee_id,case_category),
  INDEX idx_hr_consent_status (consent_status,recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Attendance, devices and leave review (4)
CREATE TABLE IF NOT EXISTS attendance_manual_punch_approvals (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  attendance_id BIGINT NULL,
  work_day DATE NOT NULL,
  punch_type VARCHAR(16) NOT NULL,
  requested_time DATETIME(6) NOT NULL,
  reason_reference VARCHAR(191) NOT NULL,
  approval_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  requested_by BIGINT NOT NULL,
  reviewed_by BIGINT NULL,
  reviewed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (attendance_id) REFERENCES attendance(id),
  FOREIGN KEY (requested_by) REFERENCES employees(id),
  FOREIGN KEY (reviewed_by) REFERENCES employees(id),
  INDEX idx_manual_approval_employee (employee_id,work_day),
  INDEX idx_manual_approval_status (approval_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_device_clock_drift_logs (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  device_id BIGINT NOT NULL,
  observed_at DATETIME(6) NOT NULL,
  drift_seconds INT NOT NULL,
  threshold_seconds INT NOT NULL DEFAULT 60,
  investigation_status VARCHAR(24) NOT NULL DEFAULT 'Open',
  reviewed_by BIGINT NULL,
  reviewed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (device_id) REFERENCES attendance_device_registry(id),
  FOREIGN KEY (reviewed_by) REFERENCES employees(id),
  CHECK (threshold_seconds >= 0),
  INDEX idx_clock_drift_device (device_id,observed_at),
  INDEX idx_clock_drift_status (investigation_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS leave_supporting_document_reviews (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  leave_request_id BIGINT NOT NULL,
  document_type VARCHAR(80) NOT NULL,
  secure_document_reference VARCHAR(191) NOT NULL,
  verification_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  reviewed_by BIGINT NULL,
  reviewed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (leave_request_id) REFERENCES leave_requests(id),
  FOREIGN KEY (reviewed_by) REFERENCES employees(id),
  INDEX idx_leave_doc_request (leave_request_id,created_at),
  INDEX idx_leave_doc_status (verification_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS timesheet_approval_batches (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  department VARCHAR(191) NOT NULL,
  batch_status VARCHAR(24) NOT NULL DEFAULT 'Draft',
  entry_count INT NOT NULL DEFAULT 0,
  created_by BIGINT NOT NULL,
  reviewed_by BIGINT NULL,
  reviewed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (created_by) REFERENCES employees(id),
  FOREIGN KEY (reviewed_by) REFERENCES employees(id),
  CHECK (period_end >= period_start),
  CHECK (entry_count >= 0),
  INDEX idx_timesheet_batch_period (period_start,period_end),
  INDEX idx_timesheet_batch_status (batch_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Payroll and statutory eligibility review (4)
CREATE TABLE IF NOT EXISTS payroll_esi_eligibility_reviews (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  contribution_period VARCHAR(24) NOT NULL,
  gross_wages DECIMAL(14,2) NOT NULL,
  review_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  assessment_reference VARCHAR(191) NULL,
  decision VARCHAR(32) NULL,
  reviewed_by BIGINT NULL,
  reviewed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (reviewed_by) REFERENCES employees(id),
  CHECK (gross_wages >= 0),
  INDEX idx_esi_review_employee (employee_id,contribution_period),
  INDEX idx_esi_review_status (review_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payroll_pf_eligibility_reviews (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  effective_on DATE NOT NULL,
  review_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  eligibility_basis_reference VARCHAR(191) NULL,
  decision VARCHAR(32) NULL,
  reviewed_by BIGINT NULL,
  reviewed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (reviewed_by) REFERENCES employees(id),
  INDEX idx_pf_review_employee (employee_id,effective_on),
  INDEX idx_pf_review_status (review_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payroll_offcycle_run_requests (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  requested_for DATE NOT NULL,
  reason_code VARCHAR(64) NOT NULL,
  gross_adjustment DECIMAL(14,2) NOT NULL DEFAULT 0,
  request_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  requested_by BIGINT NOT NULL,
  approved_by BIGINT NULL,
  approved_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (requested_by) REFERENCES employees(id),
  FOREIGN KEY (approved_by) REFERENCES employees(id),
  INDEX idx_offcycle_employee (employee_id,requested_for),
  INDEX idx_offcycle_status (request_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payroll_payment_exception_cases (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  run_id BIGINT NOT NULL,
  employee_id BIGINT NOT NULL,
  exception_code VARCHAR(64) NOT NULL,
  case_status VARCHAR(24) NOT NULL DEFAULT 'Open',
  incident_reference VARCHAR(191) NOT NULL,
  assigned_to BIGINT NULL,
  resolved_by BIGINT NULL,
  resolved_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (run_id) REFERENCES pay_runs_v2(id),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (assigned_to) REFERENCES employees(id),
  FOREIGN KEY (resolved_by) REFERENCES employees(id),
  INDEX idx_payment_exception_run (run_id,case_status),
  INDEX idx_payment_exception_assignee (assigned_to,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Structured recruiting assessments (4)
CREATE TABLE IF NOT EXISTS recruitment_job_skill_requirements (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  job_id BIGINT NOT NULL,
  skill_name VARCHAR(120) NOT NULL,
  minimum_years DECIMAL(5,2) NOT NULL DEFAULT 0,
  is_required TINYINT NOT NULL DEFAULT 1,
  requirement_status VARCHAR(24) NOT NULL DEFAULT 'Active',
  updated_by BIGINT NOT NULL,
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (job_id) REFERENCES jobs(id),
  FOREIGN KEY (updated_by) REFERENCES employees(id),
  CHECK (minimum_years >= 0),
  UNIQUE KEY uq_recruit_job_skill (job_id,skill_name),
  INDEX idx_recruit_skill_status (requirement_status,updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recruitment_interview_scorecards (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  candidate_id BIGINT NOT NULL,
  job_id BIGINT NOT NULL,
  evaluator_id BIGINT NOT NULL,
  competency_code VARCHAR(80) NOT NULL,
  score DECIMAL(5,2) NULL,
  recommendation VARCHAR(24) NOT NULL DEFAULT 'Pending',
  evidence_reference VARCHAR(191) NULL,
  reviewed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (candidate_id) REFERENCES candidates(id),
  FOREIGN KEY (job_id) REFERENCES jobs(id),
  FOREIGN KEY (evaluator_id) REFERENCES employees(id),
  CHECK (score IS NULL OR (score >= 0 AND score <= 100)),
  INDEX idx_interview_scorecard_candidate (candidate_id,job_id),
  INDEX idx_interview_scorecard_evaluator (evaluator_id,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recruitment_offer_acceptance_events (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  candidate_id BIGINT NOT NULL,
  job_id BIGINT NOT NULL,
  event_type VARCHAR(32) NOT NULL,
  secure_offer_reference VARCHAR(191) NULL,
  recorded_by BIGINT NOT NULL,
  recorded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (candidate_id) REFERENCES candidates(id),
  FOREIGN KEY (job_id) REFERENCES jobs(id),
  FOREIGN KEY (recorded_by) REFERENCES employees(id),
  INDEX idx_offer_acceptance_candidate (candidate_id,recorded_at),
  INDEX idx_offer_acceptance_job (job_id,event_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recruitment_candidate_talent_tags (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  candidate_id BIGINT NOT NULL,
  tag_name VARCHAR(80) NOT NULL,
  tag_source VARCHAR(32) NOT NULL DEFAULT 'Manual',
  tagged_by BIGINT NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (candidate_id) REFERENCES candidates(id),
  FOREIGN KEY (tagged_by) REFERENCES employees(id),
  UNIQUE KEY uq_recruit_candidate_tag (candidate_id,tag_name),
  INDEX idx_recruit_tag_search (tag_name,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Assets and import quality controls (4)
CREATE TABLE IF NOT EXISTS asset_custody_acknowledgements (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  asset_id BIGINT NOT NULL,
  employee_id BIGINT NOT NULL,
  acknowledgement_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  acknowledgement_reference VARCHAR(191) NULL,
  issued_by BIGINT NOT NULL,
  acknowledged_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (asset_id) REFERENCES assets(id),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (issued_by) REFERENCES employees(id),
  INDEX idx_custody_asset (asset_id,created_at),
  INDEX idx_custody_employee (employee_id,acknowledgement_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS asset_disposal_approvals (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  asset_id BIGINT NOT NULL,
  disposal_reason_code VARCHAR(80) NOT NULL,
  request_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  requested_by BIGINT NOT NULL,
  approved_by BIGINT NULL,
  approved_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (asset_id) REFERENCES assets(id),
  FOREIGN KEY (requested_by) REFERENCES employees(id),
  FOREIGN KEY (approved_by) REFERENCES employees(id),
  INDEX idx_asset_disposal_asset (asset_id,created_at),
  INDEX idx_asset_disposal_status (request_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS hr_data_quality_import_row_issues (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  import_id BIGINT NOT NULL,
  source_row_number INT NOT NULL,
  source_column_key VARCHAR(80) NOT NULL,
  issue_code VARCHAR(64) NOT NULL,
  severity VARCHAR(24) NOT NULL DEFAULT 'Error',
  issue_status VARCHAR(24) NOT NULL DEFAULT 'Open',
  reviewed_by BIGINT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (import_id) REFERENCES hr_data_quality_import_history(id),
  FOREIGN KEY (reviewed_by) REFERENCES employees(id),
  CHECK (source_row_number > 0),
  INDEX idx_import_issue_import (import_id,source_row_number),
  INDEX idx_import_issue_status (issue_status,severity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS hr_data_quality_import_approval_reviews (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  import_id BIGINT NOT NULL,
  decision VARCHAR(24) NOT NULL DEFAULT 'Pending',
  review_reference VARCHAR(191) NULL,
  requested_by BIGINT NOT NULL,
  reviewed_by BIGINT NULL,
  reviewed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (import_id) REFERENCES hr_data_quality_import_history(id),
  FOREIGN KEY (requested_by) REFERENCES employees(id),
  FOREIGN KEY (reviewed_by) REFERENCES employees(id),
  INDEX idx_import_approval_import (import_id,created_at),
  INDEX idx_import_approval_decision (decision,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
