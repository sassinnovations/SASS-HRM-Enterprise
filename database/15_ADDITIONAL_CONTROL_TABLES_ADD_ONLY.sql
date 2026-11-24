-- SASS HRM Enterprise | Additive operational controls extension (193 -> 213 tables)
-- Run ONLY after a verified backup and successful installation of migrations through 14.
-- MySQL 8.4+; explicitly select the intended, existing SASS HRM database first.
-- Database foundations ONLY: no new APIs, screens, payment flows or automatic actions.
-- No INSERT/UPDATE/DELETE/DROP/ALTER, candidate preload, raw biometric templates or secrets.

-- Employee lifecycle and HR coordination (4)
CREATE TABLE IF NOT EXISTS employee_work_authorization_documents (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  review_id BIGINT NULL,
  document_category VARCHAR(60) NOT NULL,
  vault_reference VARCHAR(191) NULL,
  expires_on DATE NULL,
  verification_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  checked_by BIGINT NULL,
  checked_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (review_id) REFERENCES employee_work_authorization_reviews(id),
  FOREIGN KEY (checked_by) REFERENCES employees(id),
  INDEX idx_authorization_doc_employee (employee_id,expires_on),
  INDEX idx_authorization_doc_review (verification_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_probation_action_items (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  review_id BIGINT NOT NULL,
  employee_id BIGINT NOT NULL,
  action_title VARCHAR(191) NOT NULL,
  due_on DATE NULL,
  action_status VARCHAR(24) NOT NULL DEFAULT 'Open',
  owner_id BIGINT NOT NULL,
  completed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (review_id) REFERENCES employee_probation_reviews(id),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (owner_id) REFERENCES employees(id),
  INDEX idx_probation_action_review (review_id,action_status),
  INDEX idx_probation_action_due (owner_id,due_on)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_contract_renewal_requests (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  contract_id BIGINT NOT NULL,
  proposed_end DATE NOT NULL,
  renewal_reason VARCHAR(1000) NOT NULL,
  approval_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  requested_by BIGINT NOT NULL,
  approved_by BIGINT NULL,
  decided_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (contract_id) REFERENCES employment_contract_versions(id),
  FOREIGN KEY (requested_by) REFERENCES employees(id),
  FOREIGN KEY (approved_by) REFERENCES employees(id),
  INDEX idx_contract_renewal_employee (employee_id,proposed_end),
  INDEX idx_contract_renewal_status (approval_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_assignment_handover_checklists (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  transfer_request_id BIGINT NULL,
  handover_kind VARCHAR(40) NOT NULL,
  checklist_reference VARCHAR(191) NOT NULL,
  due_on DATE NULL,
  handover_status VARCHAR(24) NOT NULL DEFAULT 'Open',
  assigned_to BIGINT NOT NULL,
  verified_by BIGINT NULL,
  verified_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (transfer_request_id) REFERENCES employee_transfer_requests(id),
  FOREIGN KEY (assigned_to) REFERENCES employees(id),
  FOREIGN KEY (verified_by) REFERENCES employees(id),
  INDEX idx_assignment_handover_employee (employee_id,due_on),
  INDEX idx_assignment_handover_status (handover_status,assigned_to)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Attendance, device uptime and leave evidence (4)
CREATE TABLE IF NOT EXISTS attendance_device_maintenance_cases (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  device_id BIGINT NOT NULL,
  fault_code VARCHAR(80) NOT NULL,
  severity VARCHAR(20) NOT NULL DEFAULT 'Medium',
  case_status VARCHAR(24) NOT NULL DEFAULT 'Open',
  reported_by BIGINT NOT NULL,
  assigned_to BIGINT NULL,
  resolved_at DATETIME(6) NULL,
  resolution_reference VARCHAR(191) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (device_id) REFERENCES attendance_device_registry(id),
  FOREIGN KEY (reported_by) REFERENCES employees(id),
  FOREIGN KEY (assigned_to) REFERENCES employees(id),
  INDEX idx_biometric_maintenance_device (device_id,case_status),
  INDEX idx_biometric_maintenance_severity (severity,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_roster_change_reviews (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  assignment_id BIGINT NOT NULL,
  employee_id BIGINT NOT NULL,
  proposed_shift_id BIGINT NOT NULL,
  effective_day DATE NOT NULL,
  reason VARCHAR(1000) NOT NULL,
  review_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  requested_by BIGINT NOT NULL,
  reviewed_by BIGINT NULL,
  reviewed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (assignment_id) REFERENCES shift_assignments(id),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (proposed_shift_id) REFERENCES shifts(id),
  FOREIGN KEY (requested_by) REFERENCES employees(id),
  FOREIGN KEY (reviewed_by) REFERENCES employees(id),
  INDEX idx_roster_review_employee (employee_id,effective_day),
  INDEX idx_roster_review_pending (review_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS leave_return_to_work_confirmations (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  leave_request_id BIGINT NOT NULL,
  employee_id BIGINT NOT NULL,
  expected_return_on DATE NOT NULL,
  actual_return_on DATE NULL,
  confirmation_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  confirmed_by BIGINT NULL,
  confirmed_at DATETIME(6) NULL,
  followup_reference VARCHAR(191) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (leave_request_id) REFERENCES leave_requests(id),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (confirmed_by) REFERENCES employees(id),
  INDEX idx_return_work_employee (employee_id,expected_return_on),
  INDEX idx_return_work_pending (confirmation_status,expected_return_on)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_exception_approval_steps (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  exception_review_id BIGINT NOT NULL,
  sequence_no INT NOT NULL,
  approver_id BIGINT NOT NULL,
  decision_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  decision_note VARCHAR(1000) NOT NULL DEFAULT '',
  decided_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (exception_review_id) REFERENCES attendance_exception_reviews(id),
  FOREIGN KEY (approver_id) REFERENCES employees(id),
  CHECK (sequence_no > 0),
  UNIQUE KEY uq_attendance_exception_step (exception_review_id,sequence_no),
  INDEX idx_attendance_exception_approver (approver_id,decision_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Payroll safety, tracking and delivery (4); no payments are initiated (4)
CREATE TABLE IF NOT EXISTS payroll_employee_payment_holds (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  run_id BIGINT NOT NULL,
  employee_id BIGINT NOT NULL,
  hold_reason VARCHAR(1000) NOT NULL,
  hold_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  placed_by BIGINT NOT NULL,
  released_by BIGINT NULL,
  released_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (run_id) REFERENCES pay_runs_v2(id),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (placed_by) REFERENCES employees(id),
  FOREIGN KEY (released_by) REFERENCES employees(id),
  INDEX idx_payment_hold_run (run_id,hold_status),
  INDEX idx_payment_hold_employee (employee_id,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payroll_retro_adjustment_requests (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  original_run_id BIGINT NOT NULL,
  target_run_id BIGINT NULL,
  adjustment_amount DECIMAL(15,2) NOT NULL,
  currency CHAR(3) NOT NULL DEFAULT 'INR',
  change_reason VARCHAR(1000) NOT NULL,
  review_status VARCHAR(24) NOT NULL DEFAULT 'Draft',
  requested_by BIGINT NOT NULL,
  approved_by BIGINT NULL,
  decided_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (original_run_id) REFERENCES pay_runs_v2(id),
  FOREIGN KEY (target_run_id) REFERENCES pay_runs_v2(id),
  FOREIGN KEY (requested_by) REFERENCES employees(id),
  FOREIGN KEY (approved_by) REFERENCES employees(id),
  INDEX idx_payroll_retro_employee (employee_id,created_at),
  INDEX idx_payroll_retro_status (review_status,original_run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payroll_payslip_delivery_receipts (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  payslip_id BIGINT NOT NULL,
  employee_id BIGINT NOT NULL,
  delivery_channel VARCHAR(32) NOT NULL,
  delivery_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  sent_at DATETIME(6) NULL,
  acknowledged_at DATETIME(6) NULL,
  delivery_reference VARCHAR(191) NULL,
  recorded_by BIGINT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (payslip_id) REFERENCES payslips(id),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (recorded_by) REFERENCES employees(id),
  INDEX idx_payslip_delivery_employee (employee_id,created_at),
  INDEX idx_payslip_delivery_status (delivery_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payroll_month_end_checkpoints (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  run_id BIGINT NOT NULL,
  checkpoint_kind VARCHAR(80) NOT NULL,
  checkpoint_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  evidence_reference VARCHAR(191) NULL,
  reviewed_by BIGINT NULL,
  reviewed_at DATETIME(6) NULL,
  signed_off_by BIGINT NULL,
  signed_off_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (run_id) REFERENCES pay_runs_v2(id),
  FOREIGN KEY (reviewed_by) REFERENCES employees(id),
  FOREIGN KEY (signed_off_by) REFERENCES employees(id),
  UNIQUE KEY uq_payroll_month_checkpoint (run_id,checkpoint_kind),
  INDEX idx_payroll_checkpoint_pending (checkpoint_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Hiring evidence and review controls (4)
CREATE TABLE IF NOT EXISTS recruitment_screening_templates (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  job_id BIGINT NOT NULL,
  template_name VARCHAR(191) NOT NULL,
  version_no INT NOT NULL DEFAULT 1,
  instruction_reference VARCHAR(191) NULL,
  template_status VARCHAR(24) NOT NULL DEFAULT 'Draft',
  created_by BIGINT NOT NULL,
  approved_by BIGINT NULL,
  approved_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (job_id) REFERENCES jobs(id),
  FOREIGN KEY (created_by) REFERENCES employees(id),
  FOREIGN KEY (approved_by) REFERENCES employees(id),
  CHECK (version_no > 0),
  UNIQUE KEY uq_screen_template_version (job_id,template_name,version_no),
  INDEX idx_screen_template_status (template_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recruitment_screening_responses (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  template_id BIGINT NOT NULL,
  candidate_id BIGINT NOT NULL,
  response_reference VARCHAR(191) NULL,
  evaluation_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  score DECIMAL(7,2) NULL,
  evaluated_by BIGINT NULL,
  evaluated_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (template_id) REFERENCES recruitment_screening_templates(id),
  FOREIGN KEY (candidate_id) REFERENCES candidates(id),
  FOREIGN KEY (evaluated_by) REFERENCES employees(id),
  CHECK (score IS NULL OR (score >= 0 AND score <= 100)),
  INDEX idx_screen_response_candidate (candidate_id,created_at),
  INDEX idx_screen_response_status (evaluation_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recruitment_candidate_document_checks (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  candidate_id BIGINT NOT NULL,
  job_id BIGINT NOT NULL,
  document_kind VARCHAR(80) NOT NULL,
  verification_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  secure_document_reference VARCHAR(191) NULL,
  verified_by BIGINT NULL,
  verified_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (candidate_id) REFERENCES candidates(id),
  FOREIGN KEY (job_id) REFERENCES jobs(id),
  FOREIGN KEY (verified_by) REFERENCES employees(id),
  INDEX idx_candidate_docs_candidate (candidate_id,verification_status),
  INDEX idx_candidate_docs_job (job_id,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recruitment_stage_escalation_cases (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  candidate_id BIGINT NOT NULL,
  job_id BIGINT NOT NULL,
  hiring_stage VARCHAR(30) NOT NULL,
  escalation_level INT NOT NULL DEFAULT 1,
  reason VARCHAR(1000) NOT NULL,
  escalation_status VARCHAR(24) NOT NULL DEFAULT 'Open',
  assigned_to BIGINT NULL,
  closed_by BIGINT NULL,
  closed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (candidate_id) REFERENCES candidates(id),
  FOREIGN KEY (job_id) REFERENCES jobs(id),
  FOREIGN KEY (assigned_to) REFERENCES employees(id),
  FOREIGN KEY (closed_by) REFERENCES employees(id),
  CHECK (escalation_level > 0),
  INDEX idx_hiring_escalation_candidate (candidate_id,hiring_stage),
  INDEX idx_hiring_escalation_status (escalation_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Governance, audits and service traceability (4)
CREATE TABLE IF NOT EXISTS compliance_evidence_register (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  control_code VARCHAR(80) NOT NULL,
  evidence_type VARCHAR(80) NOT NULL,
  evidence_reference VARCHAR(191) NOT NULL,
  review_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  reviewed_by BIGINT NULL,
  reviewed_at DATETIME(6) NULL,
  expires_on DATE NULL,
  created_by BIGINT NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (reviewed_by) REFERENCES employees(id),
  FOREIGN KEY (created_by) REFERENCES employees(id),
  INDEX idx_compliance_evidence_control (control_code,review_status),
  INDEX idx_compliance_evidence_expiry (expires_on,review_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS privacy_data_correction_requests (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  data_category VARCHAR(64) NOT NULL,
  correction_reference VARCHAR(191) NULL,
  request_reason VARCHAR(1000) NOT NULL,
  request_status VARCHAR(24) NOT NULL DEFAULT 'Submitted',
  assigned_to BIGINT NULL,
  resolved_by BIGINT NULL,
  resolved_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (assigned_to) REFERENCES employees(id),
  FOREIGN KEY (resolved_by) REFERENCES employees(id),
  INDEX idx_privacy_correction_employee (employee_id,created_at),
  INDEX idx_privacy_correction_status (request_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS integration_field_mapping_revisions (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  connector_code VARCHAR(100) NOT NULL,
  mapping_version INT NOT NULL,
  mapping_reference VARCHAR(191) NOT NULL,
  validation_status VARCHAR(24) NOT NULL DEFAULT 'Draft',
  approved_by BIGINT NULL,
  approved_at DATETIME(6) NULL,
  created_by BIGINT NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (approved_by) REFERENCES employees(id),
  FOREIGN KEY (created_by) REFERENCES employees(id),
  CHECK (mapping_version > 0),
  UNIQUE KEY uq_integration_mapping_rev (connector_code,mapping_version),
  INDEX idx_integration_mapping_status (validation_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS asset_maintenance_requests (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  asset_id BIGINT NOT NULL,
  employee_id BIGINT NULL,
  maintenance_kind VARCHAR(80) NOT NULL,
  severity VARCHAR(20) NOT NULL DEFAULT 'Medium',
  request_status VARCHAR(24) NOT NULL DEFAULT 'Open',
  reported_by BIGINT NOT NULL,
  assigned_to BIGINT NULL,
  completed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (asset_id) REFERENCES assets(id),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (reported_by) REFERENCES employees(id),
  FOREIGN KEY (assigned_to) REFERENCES employees(id),
  INDEX idx_asset_maintenance_asset (asset_id,created_at),
  INDEX idx_asset_maintenance_status (request_status,severity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
