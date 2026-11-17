-- SASS HRM Enterprise | 20 advanced HR workflow tables | MySQL 8.4
-- EXISTING DATABASE UPGRADE (AFTER VERIFIED BACKUP): SELECT THE CORRECT DATABASE FIRST.
-- Additive only: CREATE TABLE IF NOT EXISTS. No candidate preloads, updates or deletes.
-- No raw fingerprint/iris data, bank account details, secrets, or uploaded file bytes.

-- Employee qualifications and HR review metadata; documents remain in the secure document service.
CREATE TABLE IF NOT EXISTS employee_education_records (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 education_level VARCHAR(100) NOT NULL,
 qualification VARCHAR(191) NOT NULL,
 institution VARCHAR(191) NOT NULL,
 completion_year SMALLINT NULL,
 verification_status VARCHAR(24) NOT NULL DEFAULT 'Unverified',
 verified_by BIGINT NULL,
 verified_at DATETIME(6) NULL,
 recorded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (verified_by) REFERENCES employees(id),
 INDEX idx_education_employee_level (employee_id,education_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_probation_reviews (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 review_due DATE NOT NULL,
 status VARCHAR(24) NOT NULL DEFAULT 'Scheduled',
 outcome VARCHAR(32) NOT NULL DEFAULT 'Undecided',
 review_note VARCHAR(1000) NOT NULL DEFAULT '',
 reviewer_id BIGINT NULL,
 reviewed_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (reviewer_id) REFERENCES employees(id),
 INDEX idx_probation_due_status (review_due,status),
 INDEX idx_probation_employee (employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_position_assignments (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 job_title VARCHAR(191) NOT NULL,
 department_name VARCHAR(191) NOT NULL,
 office_name VARCHAR(191) NOT NULL,
 effective_from DATE NOT NULL,
 effective_to DATE NULL,
 change_reason VARCHAR(500) NOT NULL DEFAULT '',
 recorded_by BIGINT NOT NULL,
 recorded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (recorded_by) REFERENCES employees(id),
 INDEX idx_position_employee_dates (employee_id,effective_from,effective_to)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_exit_interviews (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 offboarding_id BIGINT NOT NULL,
 employee_id BIGINT NOT NULL,
 interviewer_id BIGINT NULL,
 interview_date DATE NULL,
 feedback_summary VARCHAR(2000) NOT NULL DEFAULT '',
 follow_up_required TINYINT(1) NOT NULL DEFAULT 0,
 status VARCHAR(24) NOT NULL DEFAULT 'Scheduled',
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (offboarding_id) REFERENCES offboarding(id),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (interviewer_id) REFERENCES employees(id),
 INDEX idx_exit_interviews_employee (employee_id,interview_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Attendance adjustments remain reviewable; these tables do not post punches or recalculate pay.
CREATE TABLE IF NOT EXISTS attendance_overtime_requests (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 work_day DATE NOT NULL,
 minutes_requested INT NOT NULL CHECK (minutes_requested > 0 AND minutes_requested <= 1440),
 reason VARCHAR(1000) NOT NULL,
 status VARCHAR(24) NOT NULL DEFAULT 'Pending',
 requested_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 reviewed_by BIGINT NULL,
 reviewed_at DATETIME(6) NULL,
 review_note VARCHAR(500) NOT NULL DEFAULT '',
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (reviewed_by) REFERENCES employees(id),
 INDEX idx_overtime_employee_date (employee_id,work_day),
 INDEX idx_overtime_status (status,requested_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_shift_change_requests (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 current_shift_id BIGINT NOT NULL,
 requested_shift_id BIGINT NOT NULL,
 effective_on DATE NOT NULL,
 reason VARCHAR(1000) NOT NULL,
 status VARCHAR(24) NOT NULL DEFAULT 'Pending',
 reviewer_id BIGINT NULL,
 reviewed_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (current_shift_id) REFERENCES shifts(id),
 FOREIGN KEY (requested_shift_id) REFERENCES shifts(id),
 FOREIGN KEY (reviewer_id) REFERENCES employees(id),
 INDEX idx_shift_changes_employee_date (employee_id,effective_on)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_exception_reviews (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 attendance_id BIGINT NOT NULL,
 case_type VARCHAR(64) NOT NULL,
 status VARCHAR(24) NOT NULL DEFAULT 'Open',
 review_note VARCHAR(1000) NOT NULL DEFAULT '',
 reviewer_id BIGINT NULL,
 resolved_at DATETIME(6) NULL,
 opened_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (attendance_id) REFERENCES attendance(id),
 FOREIGN KEY (reviewer_id) REFERENCES employees(id),
 INDEX idx_attendance_exceptions_status (status,opened_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS leave_carryforward_events (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 leave_type VARCHAR(64) NOT NULL,
 source_year SMALLINT NOT NULL,
 destination_year SMALLINT NOT NULL,
 days_carried DECIMAL(7,2) NOT NULL CHECK (days_carried >= 0),
 decision VARCHAR(24) NOT NULL DEFAULT 'Pending',
 decided_by BIGINT NULL,
 decided_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (decided_by) REFERENCES employees(id),
 INDEX idx_leave_carryforward_employee_year (employee_id,destination_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Payroll component catalogue and verification data; not an automated payment processor.
CREATE TABLE IF NOT EXISTS payroll_component_catalog (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 component_code VARCHAR(64) NOT NULL UNIQUE,
 display_name VARCHAR(191) NOT NULL,
 component_kind VARCHAR(32) NOT NULL,
 taxable TINYINT(1) NOT NULL DEFAULT 0,
 active TINYINT(1) NOT NULL DEFAULT 1,
 created_by BIGINT NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (created_by) REFERENCES employees(id),
 INDEX idx_payroll_components_kind (component_kind,active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payroll_employee_components (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 component_id BIGINT NOT NULL,
 amount DECIMAL(14,2) NOT NULL CHECK (amount >= 0),
 currency CHAR(3) NOT NULL DEFAULT 'INR',
 effective_from DATE NOT NULL,
 effective_to DATE NULL,
 recorded_by BIGINT NOT NULL,
 recorded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 UNIQUE KEY ux_payroll_component_assignment (employee_id,component_id,effective_from),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (component_id) REFERENCES payroll_component_catalog(id),
 FOREIGN KEY (recorded_by) REFERENCES employees(id),
 INDEX idx_payroll_component_effective (effective_from,effective_to)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payroll_reconciliation_issues (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 run_id BIGINT NOT NULL,
 employee_id BIGINT NULL,
 issue_code VARCHAR(64) NOT NULL,
 severity VARCHAR(24) NOT NULL DEFAULT 'Medium',
 status VARCHAR(24) NOT NULL DEFAULT 'Open',
 difference_amount DECIMAL(14,2) NOT NULL DEFAULT 0,
 currency CHAR(3) NOT NULL DEFAULT 'INR',
 explanation VARCHAR(1000) NOT NULL DEFAULT '',
 opened_by BIGINT NOT NULL,
 resolved_by BIGINT NULL,
 resolved_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (run_id) REFERENCES pay_runs_v2(id),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (opened_by) REFERENCES employees(id),
 FOREIGN KEY (resolved_by) REFERENCES employees(id),
 INDEX idx_reconciliation_run_status (run_id,status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payroll_approval_signoffs (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 run_id BIGINT NOT NULL,
 approval_stage VARCHAR(32) NOT NULL,
 approver_id BIGINT NOT NULL,
 decision VARCHAR(24) NOT NULL,
 decision_note VARCHAR(1000) NOT NULL DEFAULT '',
 signed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 UNIQUE KEY ux_payroll_signoff (run_id,approval_stage,approver_id),
 FOREIGN KEY (run_id) REFERENCES pay_runs_v2(id),
 FOREIGN KEY (approver_id) REFERENCES employees(id),
 INDEX idx_signoff_run_decision (run_id,decision)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Candidate data remains empty until manually imported; these contain no seeded applicants.
CREATE TABLE IF NOT EXISTS candidate_assessment_results (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 candidate_id BIGINT NOT NULL,
 job_id BIGINT NULL,
 assessment_type VARCHAR(100) NOT NULL,
 score_percent DECIMAL(5,2) NULL CHECK (score_percent BETWEEN 0 AND 100),
 result_status VARCHAR(32) NOT NULL DEFAULT 'Pending',
 evaluation_note VARCHAR(1000) NOT NULL DEFAULT '',
 evaluated_by BIGINT NULL,
 evaluated_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
 FOREIGN KEY (job_id) REFERENCES jobs(id),
 FOREIGN KEY (evaluated_by) REFERENCES employees(id),
 INDEX idx_candidate_assessment (candidate_id,result_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS candidate_interview_feedback (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 interview_id BIGINT NOT NULL,
 reviewer_id BIGINT NOT NULL,
 rating TINYINT NULL CHECK (rating BETWEEN 1 AND 5),
 recommendation VARCHAR(32) NOT NULL DEFAULT 'Pending',
 feedback VARCHAR(2000) NOT NULL DEFAULT '',
 submitted_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 UNIQUE KEY ux_interview_feedback_author (interview_id,reviewer_id),
 FOREIGN KEY (interview_id) REFERENCES interviews(id),
 FOREIGN KEY (reviewer_id) REFERENCES employees(id),
 INDEX idx_interview_feedback_recommendation (recommendation)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS candidate_offer_approvals (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 candidate_id BIGINT NOT NULL,
 job_id BIGINT NOT NULL,
 approval_level VARCHAR(32) NOT NULL DEFAULT 'HR',
 decision VARCHAR(24) NOT NULL DEFAULT 'Pending',
 requested_by BIGINT NOT NULL,
 approver_id BIGINT NULL,
 decision_note VARCHAR(1000) NOT NULL DEFAULT '',
 decided_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (candidate_id) REFERENCES candidates(id),
 FOREIGN KEY (job_id) REFERENCES jobs(id),
 FOREIGN KEY (requested_by) REFERENCES employees(id),
 FOREIGN KEY (approver_id) REFERENCES employees(id),
 INDEX idx_offer_approval_candidate (candidate_id,decision)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS candidate_duplicate_review_cases (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 candidate_id BIGINT NOT NULL,
 possible_duplicate_id BIGINT NOT NULL,
 match_reason VARCHAR(191) NOT NULL,
 status VARCHAR(24) NOT NULL DEFAULT 'Open',
 reviewed_by BIGINT NULL,
 reviewed_at DATETIME(6) NULL,
 opened_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 CHECK (candidate_id <> possible_duplicate_id),
 FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
 FOREIGN KEY (possible_duplicate_id) REFERENCES candidates(id) ON DELETE CASCADE,
 FOREIGN KEY (reviewed_by) REFERENCES employees(id),
 UNIQUE KEY ux_candidate_duplicate_pair (candidate_id,possible_duplicate_id),
 INDEX idx_candidate_duplicate_status (status,opened_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Privacy reviews and integration delivery metadata; no payloads, tokens or personal exports stored.
CREATE TABLE IF NOT EXISTS data_access_review_cases (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 resource_type VARCHAR(64) NOT NULL,
 purpose VARCHAR(500) NOT NULL,
 requester_id BIGINT NOT NULL,
 reviewer_id BIGINT NULL,
 status VARCHAR(24) NOT NULL DEFAULT 'Pending',
 decision_note VARCHAR(1000) NOT NULL DEFAULT '',
 reviewed_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (requester_id) REFERENCES employees(id),
 FOREIGN KEY (reviewer_id) REFERENCES employees(id),
 INDEX idx_access_review_status (status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS integration_webhook_receipts (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 integration_key VARCHAR(100) NOT NULL,
 delivery_id VARCHAR(191) NOT NULL,
 event_type VARCHAR(100) NOT NULL,
 payload_sha256 CHAR(64) NOT NULL,
 signature_verified TINYINT(1) NOT NULL DEFAULT 0,
 status VARCHAR(24) NOT NULL DEFAULT 'Received',
 received_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 processed_at DATETIME(6) NULL,
 UNIQUE KEY ux_webhook_delivery (integration_key,delivery_id),
 INDEX idx_webhook_status (status,received_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS retention_hold_requests (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 resource_type VARCHAR(64) NOT NULL,
 resource_id BIGINT NOT NULL,
 reason VARCHAR(1000) NOT NULL,
 status VARCHAR(24) NOT NULL DEFAULT 'Pending',
 requested_by BIGINT NOT NULL,
 reviewed_by BIGINT NULL,
 reviewed_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (requested_by) REFERENCES employees(id),
 FOREIGN KEY (reviewed_by) REFERENCES employees(id),
 INDEX idx_retention_hold_resource (resource_type,resource_id,status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_data_export_requests (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 requested_by BIGINT NOT NULL,
 reviewed_by BIGINT NULL,
 export_scope VARCHAR(100) NOT NULL,
 status VARCHAR(24) NOT NULL DEFAULT 'Pending',
 purpose VARCHAR(500) NOT NULL DEFAULT '',
 secure_export_reference VARCHAR(191) NULL,
 expires_at DATETIME(6) NULL,
 reviewed_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (requested_by) REFERENCES employees(id),
 FOREIGN KEY (reviewed_by) REFERENCES employees(id),
 INDEX idx_export_requests_employee (employee_id,status,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
