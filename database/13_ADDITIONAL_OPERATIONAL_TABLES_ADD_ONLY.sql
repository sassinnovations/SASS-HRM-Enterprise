-- SASS HRM Enterprise | additional operational review tables | MySQL 8.4
-- Existing database upgrade ONLY after verified backup and correct database selection.
-- Additive, no data mutations or sensitive raw biometrics/payment credentials.
-- No API endpoints, UI access, payments, approvals or automated actions are enabled here.

CREATE TABLE IF NOT EXISTS employee_license_renewals (
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 license_type VARCHAR(100) NOT NULL,
 renewal_due DATE NOT NULL,
 verification_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
 evidence_reference VARCHAR(191) NULL,
 reviewer_id BIGINT NULL,
 reviewed_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (reviewer_id) REFERENCES employees(id),
 INDEX idx_license_employee_due (employee_id,renewal_due),
 INDEX idx_license_review_status (verification_status,renewal_due)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_work_authorization_reviews (
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 jurisdiction_code VARCHAR(12) NOT NULL,
 authorization_category VARCHAR(100) NOT NULL,
 valid_until DATE NULL,
 review_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
 verified_by BIGINT NULL,
 verified_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (verified_by) REFERENCES employees(id),
 INDEX idx_work_authorization_employee (employee_id,valid_until),
 INDEX idx_work_authorization_review (review_status,valid_until)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_manager_assignments (
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 manager_id BIGINT NOT NULL,
 effective_from DATE NOT NULL,
 effective_to DATE NULL,
 reason VARCHAR(500) NOT NULL DEFAULT '',
 recorded_by BIGINT NOT NULL,
 recorded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 CHECK (manager_id <> employee_id),
 CHECK (effective_to IS NULL OR effective_to >= effective_from),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (manager_id) REFERENCES employees(id),
 FOREIGN KEY (recorded_by) REFERENCES employees(id),
 INDEX idx_manager_assignment_employee_dates (employee_id,effective_from,effective_to),
 INDEX idx_manager_assignment_manager (manager_id,effective_from)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_transfer_requests (
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 from_department_id BIGINT NOT NULL,
 to_department_id BIGINT NOT NULL,
 proposed_date DATE NOT NULL,
 justification VARCHAR(1000) NOT NULL,
 status VARCHAR(24) NOT NULL DEFAULT 'Pending',
 requested_by BIGINT NOT NULL,
 decided_by BIGINT NULL,
 decided_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 CHECK (from_department_id <> to_department_id),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (from_department_id) REFERENCES departments(id),
 FOREIGN KEY (to_department_id) REFERENCES departments(id),
 FOREIGN KEY (requested_by) REFERENCES employees(id),
 FOREIGN KEY (decided_by) REFERENCES employees(id),
 INDEX idx_transfer_employee_date (employee_id,proposed_date),
 INDEX idx_transfer_status (status,proposed_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_roster_publications (
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 shift_id BIGINT NOT NULL,
 roster_day DATE NOT NULL,
 location_code VARCHAR(100) NOT NULL DEFAULT '',
 publication_status VARCHAR(24) NOT NULL DEFAULT 'Draft',
 prepared_by BIGINT NOT NULL,
 approved_by BIGINT NULL,
 approved_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (shift_id) REFERENCES shifts(id),
 FOREIGN KEY (prepared_by) REFERENCES employees(id),
 FOREIGN KEY (approved_by) REFERENCES employees(id),
 INDEX idx_roster_day_status (roster_day,publication_status),
 INDEX idx_roster_shift_day (shift_id,roster_day)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_remote_work_reviews (
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 work_day DATE NOT NULL,
 work_location VARCHAR(191) NOT NULL DEFAULT 'Remote',
 reason VARCHAR(1000) NOT NULL DEFAULT '',
 review_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
 reviewer_id BIGINT NULL,
 reviewed_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (reviewer_id) REFERENCES employees(id),
 INDEX idx_remote_work_employee_day (employee_id,work_day),
 INDEX idx_remote_work_review (review_status,work_day)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS leave_blackout_periods (
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 department_id BIGINT NULL,
 starts_on DATE NOT NULL,
 ends_on DATE NOT NULL,
 reason VARCHAR(500) NOT NULL,
 review_status VARCHAR(24) NOT NULL DEFAULT 'Draft',
 requested_by BIGINT NOT NULL,
 approved_by BIGINT NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 CHECK (ends_on >= starts_on),
 FOREIGN KEY (department_id) REFERENCES departments(id),
 FOREIGN KEY (requested_by) REFERENCES employees(id),
 FOREIGN KEY (approved_by) REFERENCES employees(id),
 INDEX idx_leave_blackout_dates (starts_on,ends_on),
 INDEX idx_leave_blackout_department (department_id,review_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS leave_balance_reconciliations (
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 leave_category VARCHAR(64) NOT NULL,
 reconciliation_on DATE NOT NULL,
 previously_reported_days DECIMAL(8,2) NOT NULL,
 corrected_days DECIMAL(8,2) NOT NULL,
 explanation VARCHAR(1000) NOT NULL,
 status VARCHAR(24) NOT NULL DEFAULT 'Pending',
 reviewed_by BIGINT NULL,
 reviewed_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (reviewed_by) REFERENCES employees(id),
 INDEX idx_leave_reconcile_employee (employee_id,reconciliation_on),
 INDEX idx_leave_reconcile_status (status,reconciliation_on)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payroll_input_change_requests (
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 run_id BIGINT NOT NULL,
 employee_id BIGINT NOT NULL,
 change_category VARCHAR(64) NOT NULL,
 reason VARCHAR(1000) NOT NULL,
 status VARCHAR(24) NOT NULL DEFAULT 'Pending',
 requested_by BIGINT NOT NULL,
 reviewed_by BIGINT NULL,
 reviewed_at DATETIME(6) NULL,
 requested_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (run_id) REFERENCES pay_runs_v2(id),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (requested_by) REFERENCES employees(id),
 FOREIGN KEY (reviewed_by) REFERENCES employees(id),
 INDEX idx_payroll_input_run (run_id,status),
 INDEX idx_payroll_input_employee (employee_id,requested_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payroll_deduction_review_cases (
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 run_id BIGINT NOT NULL,
 employee_id BIGINT NOT NULL,
 deduction_category VARCHAR(64) NOT NULL,
 concern VARCHAR(1000) NOT NULL,
 review_status VARCHAR(24) NOT NULL DEFAULT 'Open',
 reviewer_id BIGINT NULL,
 reviewed_at DATETIME(6) NULL,
 opened_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (run_id) REFERENCES pay_runs_v2(id),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (reviewer_id) REFERENCES employees(id),
 INDEX idx_deduction_review_run (run_id,review_status),
 INDEX idx_deduction_review_employee (employee_id,opened_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payroll_cost_center_allocations (
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 cost_center_code VARCHAR(64) NOT NULL,
 allocation_percent DECIMAL(5,2) NOT NULL,
 effective_from DATE NOT NULL,
 effective_to DATE NULL,
 approved_by BIGINT NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 CHECK (allocation_percent > 0 AND allocation_percent <= 100),
 CHECK (effective_to IS NULL OR effective_to >= effective_from),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (approved_by) REFERENCES employees(id),
 INDEX idx_cost_center_employee (employee_id,effective_from,effective_to),
 INDEX idx_cost_center_code (cost_center_code,effective_from)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payroll_tax_document_checks (
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 tax_year VARCHAR(12) NOT NULL,
 document_category VARCHAR(80) NOT NULL,
 evidence_reference VARCHAR(191) NULL,
 review_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
 reviewer_id BIGINT NULL,
 reviewed_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (reviewer_id) REFERENCES employees(id),
 INDEX idx_tax_doc_employee_year (employee_id,tax_year),
 INDEX idx_tax_doc_review (review_status,tax_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recruitment_requisition_requests (
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 job_id BIGINT NULL,
 requested_title VARCHAR(191) NOT NULL,
 openings_requested INT NOT NULL DEFAULT 1,
 business_justification VARCHAR(1200) NOT NULL,
 approval_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
 requested_by BIGINT NOT NULL,
 approved_by BIGINT NULL,
 approved_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 CHECK (openings_requested > 0),
 FOREIGN KEY (job_id) REFERENCES jobs(id),
 FOREIGN KEY (requested_by) REFERENCES employees(id),
 FOREIGN KEY (approved_by) REFERENCES employees(id),
 INDEX idx_requisition_approval (approval_status,created_at),
 INDEX idx_requisition_job (job_id,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS candidate_stage_sla_cases (
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 candidate_id BIGINT NOT NULL,
 job_id BIGINT NULL,
 stage VARCHAR(24) NOT NULL,
 due_at DATETIME(6) NOT NULL,
 case_status VARCHAR(24) NOT NULL DEFAULT 'Open',
 owner_id BIGINT NULL,
 closed_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (candidate_id) REFERENCES candidates(id),
 FOREIGN KEY (job_id) REFERENCES jobs(id),
 FOREIGN KEY (owner_id) REFERENCES employees(id),
 INDEX idx_stage_sla_due (case_status,due_at),
 INDEX idx_stage_sla_candidate (candidate_id,stage)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS candidate_reference_check_reviews (
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 candidate_id BIGINT NOT NULL,
 job_id BIGINT NULL,
 review_method VARCHAR(50) NOT NULL,
 review_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
 review_summary VARCHAR(1200) NOT NULL DEFAULT '',
 reviewer_id BIGINT NULL,
 completed_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (candidate_id) REFERENCES candidates(id),
 FOREIGN KEY (job_id) REFERENCES jobs(id),
 FOREIGN KEY (reviewer_id) REFERENCES employees(id),
 INDEX idx_reference_check_candidate (candidate_id,review_status),
 INDEX idx_reference_check_status (review_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS candidate_offer_document_reviews (
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 candidate_id BIGINT NOT NULL,
 job_id BIGINT NULL,
 secure_document_reference VARCHAR(191) NOT NULL,
 review_status VARCHAR(24) NOT NULL DEFAULT 'Draft',
 reviewer_id BIGINT NULL,
 reviewed_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (candidate_id) REFERENCES candidates(id),
 FOREIGN KEY (job_id) REFERENCES jobs(id),
 FOREIGN KEY (reviewer_id) REFERENCES employees(id),
 INDEX idx_offer_doc_candidate (candidate_id,review_status),
 INDEX idx_offer_doc_job (job_id,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS training_certificate_renewals (
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 course_id BIGINT NULL,
 certificate_category VARCHAR(100) NOT NULL,
 renewal_due DATE NOT NULL,
 verification_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
 verified_by BIGINT NULL,
 verified_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (course_id) REFERENCES courses(id),
 FOREIGN KEY (verified_by) REFERENCES employees(id),
 INDEX idx_training_certificate_due (renewal_due,verification_status),
 INDEX idx_training_certificate_employee (employee_id,course_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_training_compliance_cases (
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 course_id BIGINT NOT NULL,
 due_on DATE NOT NULL,
 compliance_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
 assigned_by BIGINT NOT NULL,
 reviewer_id BIGINT NULL,
 reviewed_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (course_id) REFERENCES courses(id),
 FOREIGN KEY (assigned_by) REFERENCES employees(id),
 FOREIGN KEY (reviewer_id) REFERENCES employees(id),
 INDEX idx_training_case_employee (employee_id,due_on),
 INDEX idx_training_case_status (compliance_status,due_on)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS asset_return_confirmations (
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 asset_id BIGINT NOT NULL,
 employee_id BIGINT NOT NULL,
 offboarding_id BIGINT NULL,
 return_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
 returned_on DATE NULL,
 confirmed_by BIGINT NULL,
 confirmation_note VARCHAR(1000) NOT NULL DEFAULT '',
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (asset_id) REFERENCES assets(id),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (offboarding_id) REFERENCES offboarding(id),
 FOREIGN KEY (confirmed_by) REFERENCES employees(id),
 INDEX idx_asset_return_employee (employee_id,return_status),
 INDEX idx_asset_return_asset (asset_id,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS compliance_control_attestations (
id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 policy_id BIGINT NULL,
 control_code VARCHAR(80) NOT NULL,
 review_period VARCHAR(24) NOT NULL,
 responsible_employee_id BIGINT NOT NULL,
 attestation_status VARCHAR(24) NOT NULL DEFAULT 'Pending',
 attested_at DATETIME(6) NULL,
 reviewed_by BIGINT NULL,
 reviewed_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (policy_id) REFERENCES policies(id),
 FOREIGN KEY (responsible_employee_id) REFERENCES employees(id),
 FOREIGN KEY (reviewed_by) REFERENCES employees(id),
 INDEX idx_control_attestation_period (control_code,review_period),
 INDEX idx_control_attestation_status (attestation_status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
