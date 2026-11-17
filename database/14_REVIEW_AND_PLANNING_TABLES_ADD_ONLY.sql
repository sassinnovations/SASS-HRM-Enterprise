-- SASS HRM Enterprise | 20 additional operational workflow tables (173 -> 193)
-- APPLY ONLY TO AN EXISTING 173-TABLE INSTANCE AFTER A VERIFIED DATABASE BACKUP.
-- ADDITIVE DDL ONLY. No candidate seeds, role grants, employee data or payroll modifications.
-- MySQL 8.4+; uses the configured database selected by your MySQL client.
-- These tables are database foundations: UI/API and processing are not enabled.

CREATE TABLE IF NOT EXISTS employee_personnel_actions (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  action_kind VARCHAR(64) NOT NULL,
  effective_on DATE NOT NULL,
  justification VARCHAR(1000) NOT NULL,
  review_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  requested_by BIGINT NOT NULL,
  reviewed_by BIGINT NULL,
  reviewed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (requested_by) REFERENCES employees(id),
  FOREIGN KEY (reviewed_by) REFERENCES employees(id),
  INDEX idx_personnel_action_employee (employee_id,effective_on),
  INDEX idx_personnel_action_status (review_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_delegation_assignments (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  delegator_id BIGINT NOT NULL,
  delegate_id BIGINT NOT NULL,
  permission_scope VARCHAR(80) NOT NULL,
  valid_from DATE NOT NULL,
  valid_to DATE NOT NULL,
  assignment_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  approved_by BIGINT NULL,
  approved_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (delegator_id) REFERENCES employees(id),
  FOREIGN KEY (delegate_id) REFERENCES employees(id),
  FOREIGN KEY (approved_by) REFERENCES employees(id),
  CHECK (delegator_id <> delegate_id),
  CHECK (valid_to >= valid_from),
  INDEX idx_delegation_actor (delegator_id,valid_from,valid_to),
  INDEX idx_delegation_delegate (delegate_id,assignment_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS workforce_headcount_plans (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  department_id BIGINT NOT NULL,
  planning_period VARCHAR(24) NOT NULL,
  approved_positions INT NOT NULL DEFAULT 0,
  planned_positions INT NOT NULL DEFAULT 0,
  justification VARCHAR(1000) NOT NULL DEFAULT '',
  review_status VARCHAR(24) NOT NULL DEFAULT 'Draft',
  prepared_by BIGINT NOT NULL,
  approved_by BIGINT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (department_id) REFERENCES departments(id),
  FOREIGN KEY (prepared_by) REFERENCES employees(id),
  FOREIGN KEY (approved_by) REFERENCES employees(id),
  CHECK (approved_positions >= 0),
  CHECK (planned_positions >= 0),
  INDEX idx_headcount_department (department_id,planning_period),
  INDEX idx_headcount_review (review_status,planning_period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_internal_mobility_applications (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  job_id BIGINT NOT NULL,
  application_status VARCHAR(24) NOT NULL DEFAULT 'Submitted',
  motivation VARCHAR(1000) NOT NULL DEFAULT '',
  reviewed_by BIGINT NULL,
  reviewed_at DATETIME(6) NULL,
  submitted_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (job_id) REFERENCES jobs(id),
  FOREIGN KEY (reviewed_by) REFERENCES employees(id),
  INDEX idx_mobility_employee (employee_id,submitted_at),
  INDEX idx_mobility_job (job_id,application_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_missing_punch_cases (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  attendance_id BIGINT NULL,
  work_day DATE NOT NULL,
  missing_event VARCHAR(12) NOT NULL,
  case_status VARCHAR(24) NOT NULL DEFAULT 'Open',
  explanation VARCHAR(1000) NOT NULL DEFAULT '',
  opened_by BIGINT NOT NULL,
  resolved_by BIGINT NULL,
  resolved_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (attendance_id) REFERENCES attendance(id),
  FOREIGN KEY (opened_by) REFERENCES employees(id),
  FOREIGN KEY (resolved_by) REFERENCES employees(id),
  CHECK (missing_event IN ('CheckIn','CheckOut')),
  INDEX idx_missing_punch_employee (employee_id,work_day),
  INDEX idx_missing_punch_status (case_status,work_day)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_break_logs (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  attendance_id BIGINT NULL,
  break_start DATETIME(6) NOT NULL,
  break_end DATETIME(6) NULL,
  break_category VARCHAR(30) NOT NULL DEFAULT 'Rest',
  entry_source VARCHAR(30) NOT NULL DEFAULT 'Manual',
  recorded_by BIGINT NOT NULL,
  review_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (attendance_id) REFERENCES attendance(id),
  FOREIGN KEY (recorded_by) REFERENCES employees(id),
  CHECK (break_end IS NULL OR break_end >= break_start),
  INDEX idx_attendance_break_employee (employee_id,break_start),
  INDEX idx_attendance_break_parent (attendance_id,break_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_shift_swap_requests (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  requester_id BIGINT NOT NULL,
  counterparty_id BIGINT NOT NULL,
  source_assignment_id BIGINT NOT NULL,
  requested_day DATE NOT NULL,
  reason VARCHAR(1000) NOT NULL DEFAULT '',
  decision_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  approved_by BIGINT NULL,
  decided_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (requester_id) REFERENCES employees(id),
  FOREIGN KEY (counterparty_id) REFERENCES employees(id),
  FOREIGN KEY (source_assignment_id) REFERENCES shift_assignments(id),
  FOREIGN KEY (approved_by) REFERENCES employees(id),
  CHECK (requester_id <> counterparty_id),
  INDEX idx_shift_swap_requester (requester_id,requested_day),
  INDEX idx_shift_swap_status (decision_status,requested_day)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS leave_encashment_requests (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  leave_category VARCHAR(64) NOT NULL,
  days_requested DECIMAL(7,2) NOT NULL,
  calculation_period VARCHAR(24) NOT NULL,
  request_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  requested_by BIGINT NOT NULL,
  reviewed_by BIGINT NULL,
  reviewed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (requested_by) REFERENCES employees(id),
  FOREIGN KEY (reviewed_by) REFERENCES employees(id),
  CHECK (days_requested > 0),
  INDEX idx_encashment_employee (employee_id,calculation_period),
  INDEX idx_encashment_status (request_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payroll_variance_review_cases (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  run_id BIGINT NOT NULL,
  employee_id BIGINT NOT NULL,
  prior_net_pay DECIMAL(14,2) NOT NULL,
  current_net_pay DECIMAL(14,2) NOT NULL,
  variance_reason VARCHAR(1000) NOT NULL DEFAULT '',
  review_status VARCHAR(24) NOT NULL DEFAULT 'Open',
  reviewed_by BIGINT NULL,
  reviewed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (run_id) REFERENCES pay_runs_v2(id),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (reviewed_by) REFERENCES employees(id),
  INDEX idx_pay_variance_run (run_id,review_status),
  INDEX idx_pay_variance_employee (employee_id,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payroll_funding_approval_requests (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  run_id BIGINT NOT NULL,
  currency_code CHAR(3) NOT NULL,
  requested_amount DECIMAL(16,2) NOT NULL,
  approval_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  funding_reference VARCHAR(120) NULL,
  requested_by BIGINT NOT NULL,
  approved_by BIGINT NULL,
  approved_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (run_id) REFERENCES pay_runs_v2(id),
  FOREIGN KEY (requested_by) REFERENCES employees(id),
  FOREIGN KEY (approved_by) REFERENCES employees(id),
  CHECK (requested_amount >= 0),
  INDEX idx_funding_run (run_id,approval_status),
  INDEX idx_funding_status (approval_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payroll_tax_residency_declarations (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  tax_year VARCHAR(24) NOT NULL,
  jurisdiction_code VARCHAR(12) NOT NULL,
  residency_category VARCHAR(60) NOT NULL,
  declaration_status VARCHAR(24) NOT NULL DEFAULT 'Submitted',
  declared_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  reviewed_by BIGINT NULL,
  reviewed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (reviewed_by) REFERENCES employees(id),
  INDEX idx_tax_residency_employee (employee_id,tax_year),
  INDEX idx_tax_residency_status (declaration_status,tax_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payroll_recovery_schedules (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  recovery_category VARCHAR(64) NOT NULL,
  total_amount DECIMAL(14,2) NOT NULL,
  installment_count INT NOT NULL,
  start_period CHAR(7) NOT NULL,
  review_status VARCHAR(24) NOT NULL DEFAULT 'Draft',
  approved_by BIGINT NULL,
  approved_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (approved_by) REFERENCES employees(id),
  CHECK (total_amount > 0),
  CHECK (installment_count > 0),
  INDEX idx_recovery_employee (employee_id,start_period),
  INDEX idx_recovery_status (review_status,start_period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS candidate_application_source_records (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  candidate_id BIGINT NOT NULL,
  job_id BIGINT NULL,
  source_channel VARCHAR(64) NOT NULL,
  campaign_code VARCHAR(100) NULL,
  referrer_employee_id BIGINT NULL,
  verification_status VARCHAR(24) NOT NULL DEFAULT 'Unverified',
  recorded_by BIGINT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (candidate_id) REFERENCES candidates(id),
  FOREIGN KEY (job_id) REFERENCES jobs(id),
  FOREIGN KEY (referrer_employee_id) REFERENCES employees(id),
  FOREIGN KEY (recorded_by) REFERENCES employees(id),
  INDEX idx_application_source_candidate (candidate_id,created_at),
  INDEX idx_application_source_job (job_id,source_channel)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recruitment_interview_panel_members (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  interview_id BIGINT NOT NULL,
  reviewer_id BIGINT NOT NULL,
  panel_role VARCHAR(64) NOT NULL,
  invitation_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  response_at DATETIME(6) NULL,
  assigned_by BIGINT NOT NULL,
  assigned_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (interview_id) REFERENCES interviews(id),
  FOREIGN KEY (reviewer_id) REFERENCES employees(id),
  FOREIGN KEY (assigned_by) REFERENCES employees(id),
  INDEX idx_interview_panel_interview (interview_id,invitation_status),
  INDEX idx_interview_panel_reviewer (reviewer_id,assigned_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recruitment_offer_approval_steps (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  candidate_id BIGINT NOT NULL,
  job_id BIGINT NULL,
  approval_sequence INT NOT NULL,
  approver_id BIGINT NULL,
  approval_role VARCHAR(64) NOT NULL,
  approval_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  review_note VARCHAR(1000) NOT NULL DEFAULT '',
  decided_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (candidate_id) REFERENCES candidates(id),
  FOREIGN KEY (job_id) REFERENCES jobs(id),
  FOREIGN KEY (approver_id) REFERENCES employees(id),
  CHECK (approval_sequence > 0),
  INDEX idx_offer_step_candidate (candidate_id,approval_sequence),
  INDEX idx_offer_step_status (approval_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recruitment_candidate_contact_queue (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  candidate_id BIGINT NOT NULL,
  job_id BIGINT NULL,
  communication_type VARCHAR(64) NOT NULL,
  template_reference VARCHAR(100) NOT NULL,
  delivery_status VARCHAR(24) NOT NULL DEFAULT 'Draft',
  scheduled_at DATETIME(6) NULL,
  created_by BIGINT NOT NULL,
  processed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (candidate_id) REFERENCES candidates(id),
  FOREIGN KEY (job_id) REFERENCES jobs(id),
  FOREIGN KEY (created_by) REFERENCES employees(id),
  INDEX idx_candidate_contact_status (delivery_status,scheduled_at),
  INDEX idx_candidate_contact_candidate (candidate_id,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_policy_version_acceptances (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  policy_id BIGINT NOT NULL,
  policy_revision BIGINT NOT NULL,
  acknowledged_at DATETIME(6) NOT NULL,
  acknowledgement_source VARCHAR(40) NOT NULL DEFAULT 'Employee',
  recorded_by BIGINT NULL,
  evidence_reference VARCHAR(191) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (policy_id) REFERENCES policies(id),
  FOREIGN KEY (recorded_by) REFERENCES employees(id),
  CHECK (policy_revision > 0),
  UNIQUE KEY uq_policy_version_acceptance (employee_id,policy_id,policy_revision),
  INDEX idx_policy_version_policy (policy_id,policy_revision)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_skill_gap_reviews (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  skill_id BIGINT NOT NULL,
  required_level VARCHAR(30) NOT NULL,
  current_level VARCHAR(30) NOT NULL,
  development_priority VARCHAR(24) NOT NULL DEFAULT 'Normal',
  assessment_status VARCHAR(24) NOT NULL DEFAULT 'Draft',
  assessed_by BIGINT NOT NULL,
  assessed_on DATE NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (skill_id) REFERENCES skill_catalog(id),
  FOREIGN KEY (assessed_by) REFERENCES employees(id),
  INDEX idx_skill_gap_employee (employee_id,assessed_on),
  INDEX idx_skill_gap_priority (development_priority,assessment_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS hr_ticket_escalation_records (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  ticket_id BIGINT NOT NULL,
  escalated_by BIGINT NOT NULL,
  assigned_to BIGINT NULL,
  escalation_level INT NOT NULL DEFAULT 1,
  due_at DATETIME(6) NULL,
  reason VARCHAR(1000) NOT NULL,
  resolution_status VARCHAR(24) NOT NULL DEFAULT 'Open',
  resolved_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (ticket_id) REFERENCES tickets(id),
  FOREIGN KEY (escalated_by) REFERENCES employees(id),
  FOREIGN KEY (assigned_to) REFERENCES employees(id),
  CHECK (escalation_level > 0),
  INDEX idx_ticket_escalation_ticket (ticket_id,created_at),
  INDEX idx_ticket_escalation_owner (assigned_to,resolution_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS integration_connector_health_results (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  connector_code VARCHAR(100) NOT NULL,
  checked_at DATETIME(6) NOT NULL,
  result_status VARCHAR(24) NOT NULL,
  failure_code VARCHAR(80) NULL,
  response_time_ms INT NULL,
  recorded_by BIGINT NULL,
  review_status VARCHAR(24) NOT NULL DEFAULT 'Open',
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (recorded_by) REFERENCES employees(id),
  CHECK (response_time_ms IS NULL OR response_time_ms >= 0),
  INDEX idx_connector_health_time (connector_code,checked_at),
  INDEX idx_connector_health_status (result_status,checked_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
