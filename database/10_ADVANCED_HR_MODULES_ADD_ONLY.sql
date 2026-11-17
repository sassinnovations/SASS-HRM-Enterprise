-- SASS HRM Enterprise / ADDITIVE UPGRADE: 15 advanced HR data tables
-- Select your existing MySQL database in the client before running; this SQL does NOT select a database.
-- Take and test a backup. CREATE TABLE IF NOT EXISTS never deletes old records.
-- Existing tables with conflicting definitions are NOT repaired by this script.

-- SASS HRM / advanced HR data expansion (15 tables, additive only).
-- Intended as schema foundations for future HR workflows; creation alone does not
-- activate screens, integrations, bank transfers, compliance filings, or retention jobs.
-- No candidate, biometric template, bank account, employee or payroll rows are inserted.

-- Employee safety contact records (access must be restricted before exposing via APIs).
CREATE TABLE IF NOT EXISTS employee_emergency_contacts (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 contact_name VARCHAR(191) NOT NULL,
 relationship VARCHAR(100) NOT NULL,
 phone VARCHAR(40) NOT NULL,
 email VARCHAR(191) NULL,
 is_primary TINYINT(1) NOT NULL DEFAULT 0,
 active TINYINT(1) NOT NULL DEFAULT 1,
 created_by BIGINT NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (created_by) REFERENCES employees(id),
 INDEX idx_emergency_employee_active (employee_id,active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Credentials/qualification metadata only; no certificate file blobs.
CREATE TABLE IF NOT EXISTS employee_certifications (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 certificate_name VARCHAR(191) NOT NULL,
 issuer VARCHAR(191) NOT NULL,
 credential_reference VARCHAR(191) NULL,
 issued_on DATE NULL,
 expires_on DATE NULL,
 status VARCHAR(24) NOT NULL DEFAULT 'Active',
 notes VARCHAR(1000) NOT NULL DEFAULT '',
 created_by BIGINT NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (created_by) REFERENCES employees(id),
 INDEX idx_cert_employee_expiry (employee_id,expires_on)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Append-only intended history of role/department/designation changes.
CREATE TABLE IF NOT EXISTS employee_job_history (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 effective_on DATE NOT NULL,
 previous_role VARCHAR(32) NOT NULL,
 new_role VARCHAR(32) NOT NULL,
 previous_department VARCHAR(191) NOT NULL,
 new_department VARCHAR(191) NOT NULL,
 previous_designation VARCHAR(191) NOT NULL,
 new_designation VARCHAR(191) NOT NULL,
 reason VARCHAR(500) NOT NULL,
 changed_by BIGINT NOT NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (changed_by) REFERENCES employees(id),
 INDEX idx_job_history_employee_date (employee_id,effective_on)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Contract version tracking with references, not document content.
CREATE TABLE IF NOT EXISTS employment_contract_versions (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 version_number INT NOT NULL,
 contract_type VARCHAR(64) NOT NULL,
 effective_from DATE NOT NULL,
 effective_until DATE NULL,
 summary VARCHAR(1000) NOT NULL DEFAULT '',
 status VARCHAR(24) NOT NULL DEFAULT 'Draft',
 recorded_by BIGINT NOT NULL,
 recorded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 UNIQUE KEY ux_contract_employee_version (employee_id,version_number),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (recorded_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Device registry has only device identifiers/metadata, never raw biometric data or signing secrets.
CREATE TABLE IF NOT EXISTS attendance_device_registry (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 device_code VARCHAR(64) NOT NULL UNIQUE,
 device_type VARCHAR(24) NOT NULL,
 display_name VARCHAR(191) NOT NULL,
 location VARCHAR(191) NOT NULL,
 status VARCHAR(24) NOT NULL DEFAULT 'Inactive',
 vendor VARCHAR(191) NOT NULL DEFAULT '',
 registered_by BIGINT NULL,
 registered_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 last_seen_at DATETIME(6) NULL,
 key_reference VARCHAR(191) NOT NULL DEFAULT '',
 FOREIGN KEY (registered_by) REFERENCES employees(id),
 INDEX idx_attendance_devices_location (location,status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Non-reversible external subject tokens; never store fingerprint/iris templates.
CREATE TABLE IF NOT EXISTS attendance_device_employee_links (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 device_id BIGINT NOT NULL,
 employee_id BIGINT NOT NULL,
 external_subject_token VARCHAR(191) NOT NULL,
 linked_by BIGINT NOT NULL,
 linked_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 active TINYINT(1) NOT NULL DEFAULT 1,
 revoked_at DATETIME(6) NULL,
 UNIQUE KEY ux_device_subject (device_id,external_subject_token),
 UNIQUE KEY ux_device_employee (device_id,employee_id),
 FOREIGN KEY (device_id) REFERENCES attendance_device_registry(id),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (linked_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Positive/negative leave accrual history; policies and entitlement computation are separate.
CREATE TABLE IF NOT EXISTS leave_accrual_ledger (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 leave_type VARCHAR(64) NOT NULL,
 period_start DATE NOT NULL,
 period_end DATE NOT NULL,
 delta_days DECIMAL(8,2) NOT NULL,
 reason VARCHAR(500) NOT NULL,
 reference_kind VARCHAR(40) NOT NULL DEFAULT 'Manual',
 reference_id BIGINT NULL,
 recorded_by BIGINT NOT NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (recorded_by) REFERENCES employees(id),
 INDEX idx_leave_ledger_employee_period (employee_id,period_start,period_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Payroll payment tracking is reference-only: no account numbers, transfers, or gateways.
CREATE TABLE IF NOT EXISTS payroll_disbursement_batches (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 run_id BIGINT NOT NULL,
 batch_reference VARCHAR(100) NOT NULL UNIQUE,
 method VARCHAR(32) NOT NULL DEFAULT 'External',
 status VARCHAR(32) NOT NULL DEFAULT 'Draft',
 requested_by BIGINT NOT NULL,
 requested_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 approved_by BIGINT NULL,
 approved_at DATETIME(6) NULL,
 total_amount DECIMAL(16,2) NOT NULL DEFAULT 0,
 currency CHAR(3) NOT NULL DEFAULT 'INR',
 FOREIGN KEY (run_id) REFERENCES pay_runs_v2(id),
 FOREIGN KEY (requested_by) REFERENCES employees(id),
 FOREIGN KEY (approved_by) REFERENCES employees(id),
 INDEX idx_disbursement_run_status (run_id,status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payroll_disbursement_items (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 batch_id BIGINT NOT NULL,
 employee_id BIGINT NOT NULL,
 amount DECIMAL(14,2) NOT NULL,
 currency CHAR(3) NOT NULL DEFAULT 'INR',
 payment_reference VARCHAR(191) NOT NULL DEFAULT '',
 status VARCHAR(24) NOT NULL DEFAULT 'Pending',
 confirmed_at DATETIME(6) NULL,
 note VARCHAR(500) NOT NULL DEFAULT '',
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 UNIQUE KEY ux_disbursement_batch_employee (batch_id,employee_id),
 FOREIGN KEY (batch_id) REFERENCES payroll_disbursement_batches(id),
 FOREIGN KEY (employee_id) REFERENCES employees(id),
 INDEX idx_disbursement_item_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Review/filing tracker only; statutory filings and calculations are NOT automated.
CREATE TABLE IF NOT EXISTS payroll_statutory_obligations (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 run_id BIGINT NOT NULL,
 period VARCHAR(7) NOT NULL,
 country CHAR(2) NOT NULL,
 obligation_type VARCHAR(64) NOT NULL,
 amount DECIMAL(16,2) NOT NULL DEFAULT 0,
 currency CHAR(3) NOT NULL,
 status VARCHAR(32) NOT NULL DEFAULT 'Needs Review',
 external_reference VARCHAR(191) NOT NULL DEFAULT '',
 reviewed_by BIGINT NULL,
 reviewed_at DATETIME(6) NULL,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (run_id) REFERENCES pay_runs_v2(id),
 FOREIGN KEY (reviewed_by) REFERENCES employees(id),
 INDEX idx_statutory_run_period (run_id,period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Candidate consent decisions are scoped to individual candidate IDs.
CREATE TABLE IF NOT EXISTS candidate_consent_events (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 candidate_id BIGINT NOT NULL,
 consent_type VARCHAR(64) NOT NULL,
 decision VARCHAR(32) NOT NULL,
 policy_version VARCHAR(50) NOT NULL DEFAULT '',
 source VARCHAR(50) NOT NULL,
 recorded_by BIGINT NULL,
 recorded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 expires_at DATETIME(6) NULL,
 FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
 FOREIGN KEY (recorded_by) REFERENCES employees(id),
 INDEX idx_consent_candidate_date (candidate_id,recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recruitment_job_approvals (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 job_id BIGINT NOT NULL,
 requested_by BIGINT NOT NULL,
 requested_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 approver_id BIGINT NULL,
 decision VARCHAR(32) NOT NULL DEFAULT 'Pending',
 decision_note VARCHAR(1000) NOT NULL DEFAULT '',
 decided_at DATETIME(6) NULL,
 approval_stage VARCHAR(64) NOT NULL DEFAULT 'Opening',
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (job_id) REFERENCES jobs(id),
 FOREIGN KEY (requested_by) REFERENCES employees(id),
 FOREIGN KEY (approver_id) REFERENCES employees(id),
 INDEX idx_job_approvals_stage (job_id,approval_stage)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Synchronization telemetry; avoid credentials and sensitive payload storage.
CREATE TABLE IF NOT EXISTS integration_sync_runs (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 integration_key VARCHAR(100) NOT NULL,
 direction VARCHAR(24) NOT NULL,
 entity_type VARCHAR(64) NOT NULL,
 started_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 finished_at DATETIME(6) NULL,
 status VARCHAR(32) NOT NULL DEFAULT 'Running',
 processed_count BIGINT NOT NULL DEFAULT 0,
 error_count BIGINT NOT NULL DEFAULT 0,
 triggered_by BIGINT NULL,
 FOREIGN KEY (triggered_by) REFERENCES employees(id),
 INDEX idx_sync_integration_date (integration_key,started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS integration_sync_errors (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 run_id BIGINT NOT NULL,
 source_reference_hash CHAR(64) NOT NULL,
 error_code VARCHAR(64) NOT NULL,
 error_summary VARCHAR(500) NOT NULL,
 occurred_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 retryable TINYINT(1) NOT NULL DEFAULT 0,
 FOREIGN KEY (run_id) REFERENCES integration_sync_runs(id) ON DELETE CASCADE,
 INDEX idx_sync_errors_run (run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Human-reviewed retention policy configuration only, with no automatic deletions.
CREATE TABLE IF NOT EXISTS data_retention_rules (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 resource_type VARCHAR(64) NOT NULL UNIQUE,
 retention_days INT NOT NULL,
 enabled TINYINT(1) NOT NULL DEFAULT 0,
 legal_hold TINYINT(1) NOT NULL DEFAULT 0,
 reviewed_by BIGINT NULL,
 updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 description VARCHAR(500) NOT NULL DEFAULT '',
 FOREIGN KEY (reviewed_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

