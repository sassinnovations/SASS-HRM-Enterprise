-- SASS HRM v4.4.0 / Fresh installation ONLY; DO NOT apply on existing production database.
-- MySQL 8.4. No employee, credential or demonstration data are included.
CREATE DATABASE IF NOT EXISTS `sass_hrm` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `sass_hrm`;

-- SASS HRM Enterprise / MySQL 8.4 -- full application schema
-- Initial SASS HRM Enterprise MySQL application schema.
-- No real employee data is included in this file.
-- This schema intentionally contains no employee, payroll, benefit or policy records.
-- All IDs and role-sensitive records are server-managed.

CREATE TABLE IF NOT EXISTS schema_migrations (
  version INT NOT NULL PRIMARY KEY,
  description VARCHAR(255) NOT NULL,
  applied_at VARCHAR(64) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employees (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, code VARCHAR(191) UNIQUE NOT NULL, name VARCHAR(191) NOT NULL,
            email VARCHAR(191) UNIQUE NOT NULL, work_email VARCHAR(191), role VARCHAR(191) NOT NULL CHECK(role IN ('admin','manager','employee')),
            designation VARCHAR(191) NOT NULL, department VARCHAR(191) NOT NULL, location VARCHAR(191) NOT NULL,
            work_mode VARCHAR(191) NOT NULL DEFAULT 'Hybrid', join_date VARCHAR(191) NOT NULL, manager_id BIGINT,
            password_hash VARCHAR(191) NOT NULL, avatar_color VARCHAR(191) NOT NULL DEFAULT '#3C6DF0',
            FOREIGN KEY(manager_id) REFERENCES employees(id),
  session_version BIGINT NOT NULL DEFAULT 0,
  account_active BIGINT NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Additive v3.3 account tiers: HR Sub-Admin is a scoped manager, never a full admin.
CREATE TABLE IF NOT EXISTS account_access_tiers (
  employee_id BIGINT NOT NULL PRIMARY KEY,
  tier VARCHAR(32) NOT NULL,
  CONSTRAINT fk_access_tier_employee FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Separately granted, authenticated developer diagnostics access. No shared passwords.
CREATE TABLE IF NOT EXISTS developer_grants (
  employee_id BIGINT NOT NULL PRIMARY KEY,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  granted_at VARCHAR(64) NOT NULL,
  CONSTRAINT fk_dev_grant_employee FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS leave_requests (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, employee_id BIGINT NOT NULL, start_date VARCHAR(191) NOT NULL,
            end_date VARCHAR(191) NOT NULL, leave_type VARCHAR(191) NOT NULL, reason VARCHAR(2048) NOT NULL,
            days BIGINT NOT NULL, status VARCHAR(191) NOT NULL DEFAULT 'Pending', decided_by BIGINT,
            created_at VARCHAR(191) NOT NULL, FOREIGN KEY(employee_id) REFERENCES employees(id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, employee_id BIGINT NOT NULL, day VARCHAR(191) NOT NULL,
            check_in VARCHAR(191), check_out VARCHAR(191), status VARCHAR(191) NOT NULL,
            UNIQUE(employee_id, day), FOREIGN KEY(employee_id) REFERENCES employees(id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS candidates (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, name VARCHAR(191) NOT NULL, job_title VARCHAR(191) NOT NULL,
            stage VARCHAR(191) NOT NULL, source VARCHAR(191) NOT NULL, applied_at VARCHAR(191) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payslips (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, employee_id BIGINT NOT NULL, month VARCHAR(191) NOT NULL,
            gross DOUBLE NOT NULL, deductions DOUBLE NOT NULL, currency VARCHAR(191) NOT NULL DEFAULT 'INR',
            UNIQUE(employee_id,month), FOREIGN KEY(employee_id) REFERENCES employees(id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS policies (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, title VARCHAR(191) NOT NULL, category VARCHAR(191) NOT NULL,
            content LONGTEXT NOT NULL, last_updated VARCHAR(191) NOT NULL,
  revision BIGINT NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS audit_events (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, actor_id BIGINT, action VARCHAR(191) NOT NULL,
            target VARCHAR(191) NOT NULL, details LONGTEXT, created_at VARCHAR(191) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS departments (id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,name VARCHAR(191) UNIQUE NOT NULL,head_id BIGINT,location VARCHAR(191) NOT NULL DEFAULT 'Hyderabad') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS shifts (id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,name VARCHAR(191) NOT NULL,start_time VARCHAR(191) NOT NULL,end_time VARCHAR(191) NOT NULL,location VARCHAR(191) NOT NULL DEFAULT 'Office') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS shift_assignments (id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,employee_id BIGINT NOT NULL,shift_id BIGINT NOT NULL,work_day VARCHAR(191) NOT NULL,UNIQUE(employee_id,work_day)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS holidays (id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,name VARCHAR(191) NOT NULL,day VARCHAR(191) UNIQUE NOT NULL,location VARCHAR(191) NOT NULL DEFAULT 'All') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS announcements (id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,title VARCHAR(191) NOT NULL,body LONGTEXT NOT NULL,created_at VARCHAR(191) NOT NULL,author_id BIGINT NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS jobs (id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,title VARCHAR(191) NOT NULL,department VARCHAR(191) NOT NULL,location VARCHAR(191) NOT NULL,employment_type VARCHAR(191) NOT NULL,openings BIGINT NOT NULL DEFAULT 1,status VARCHAR(191) NOT NULL DEFAULT 'Open',created_at VARCHAR(191) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS onboarding (id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,employee_id BIGINT NOT NULL,title VARCHAR(191) NOT NULL,due_date VARCHAR(191) NOT NULL,status VARCHAR(191) NOT NULL DEFAULT 'Pending',FOREIGN KEY(employee_id) REFERENCES employees(id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS goals (id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,employee_id BIGINT NOT NULL,title VARCHAR(191) NOT NULL,description VARCHAR(2048) NOT NULL DEFAULT '',due_date VARCHAR(191) NOT NULL,progress BIGINT NOT NULL DEFAULT 0,status VARCHAR(191) NOT NULL DEFAULT 'In Progress',FOREIGN KEY(employee_id) REFERENCES employees(id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS reviews (id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,employee_id BIGINT NOT NULL,reviewer_id BIGINT NOT NULL,cycle VARCHAR(191) NOT NULL,rating BIGINT NOT NULL,feedback VARCHAR(2048) NOT NULL,created_at VARCHAR(191) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS courses (id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,title VARCHAR(191) NOT NULL,category VARCHAR(191) NOT NULL,duration_hours BIGINT NOT NULL,description VARCHAR(2048) NOT NULL DEFAULT '') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS enrollments (id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,employee_id BIGINT NOT NULL,course_id BIGINT NOT NULL,status VARCHAR(191) NOT NULL DEFAULT 'Enrolled',enrolled_at VARCHAR(191) NOT NULL,UNIQUE(employee_id,course_id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tickets (id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,employee_id BIGINT NOT NULL,subject VARCHAR(191) NOT NULL,category VARCHAR(191) NOT NULL,description VARCHAR(2048) NOT NULL,status VARCHAR(191) NOT NULL DEFAULT 'Open',priority VARCHAR(191) NOT NULL DEFAULT 'Normal',created_at VARCHAR(191) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS assets (id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,employee_id BIGINT NOT NULL,asset_name VARCHAR(191) NOT NULL,serial_number VARCHAR(191) NOT NULL UNIQUE,status VARCHAR(191) NOT NULL DEFAULT 'Assigned',assigned_at VARCHAR(191) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS documents (id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,employee_id BIGINT NOT NULL,title VARCHAR(191) NOT NULL,document_type VARCHAR(191) NOT NULL,status VARCHAR(191) NOT NULL DEFAULT 'Pending',created_at VARCHAR(191) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS offboarding (id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,employee_id BIGINT NOT NULL,last_working_day VARCHAR(191) NOT NULL,reason VARCHAR(2048) NOT NULL,status VARCHAR(191) NOT NULL DEFAULT 'Requested',created_at VARCHAR(191) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS expenses (id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,employee_id BIGINT NOT NULL,title VARCHAR(191) NOT NULL,amount DOUBLE NOT NULL,currency VARCHAR(191) NOT NULL DEFAULT 'INR',category VARCHAR(191) NOT NULL,status VARCHAR(191) NOT NULL DEFAULT 'Pending',created_at VARCHAR(191) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS notifications (id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,employee_id BIGINT NOT NULL,title VARCHAR(191) NOT NULL,body LONGTEXT NOT NULL,is_read BIGINT NOT NULL DEFAULT 0,created_at VARCHAR(191) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS benefit_plans (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, name VARCHAR(191) NOT NULL UNIQUE, category VARCHAR(191) NOT NULL,
            description VARCHAR(2048) NOT NULL, active BIGINT NOT NULL DEFAULT 1) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS benefit_enrollments (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, employee_id BIGINT NOT NULL, plan_id BIGINT NOT NULL,
            status VARCHAR(191) NOT NULL DEFAULT 'Active', enrolled_at VARCHAR(191) NOT NULL,
            UNIQUE(employee_id,plan_id), FOREIGN KEY(employee_id) REFERENCES employees(id),
            FOREIGN KEY(plan_id) REFERENCES benefit_plans(id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recognitions (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, sender_id BIGINT NOT NULL, recipient_id BIGINT NOT NULL,
            value VARCHAR(191) NOT NULL, message VARCHAR(2048) NOT NULL, created_at VARCHAR(191) NOT NULL,
            FOREIGN KEY(sender_id) REFERENCES employees(id), FOREIGN KEY(recipient_id) REFERENCES employees(id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS surveys (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, title VARCHAR(191) NOT NULL, question VARCHAR(2048) NOT NULL,
            choices VARCHAR(2048) NOT NULL, status VARCHAR(191) NOT NULL DEFAULT 'Open', created_at VARCHAR(191) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS survey_responses (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, survey_id BIGINT NOT NULL, employee_id BIGINT NOT NULL,
            answer_index BIGINT NOT NULL, created_at VARCHAR(191) NOT NULL,
            UNIQUE(survey_id,employee_id), FOREIGN KEY(survey_id) REFERENCES surveys(id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS interviews (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, candidate_id BIGINT NOT NULL, interviewer_id BIGINT NOT NULL,
            scheduled_at VARCHAR(191) NOT NULL, duration_minutes BIGINT NOT NULL,
            mode VARCHAR(191) NOT NULL, status VARCHAR(191) NOT NULL DEFAULT 'Scheduled',
            notes VARCHAR(2048) NOT NULL DEFAULT '', created_at VARCHAR(191) NOT NULL,
            FOREIGN KEY(candidate_id) REFERENCES candidates(id),
            FOREIGN KEY(interviewer_id) REFERENCES employees(id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS hr_tasks (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, title VARCHAR(191) NOT NULL, assignee_id BIGINT NOT NULL,
            created_by BIGINT NOT NULL, due_date VARCHAR(191) NOT NULL,
            priority VARCHAR(191) NOT NULL DEFAULT 'Normal',status VARCHAR(191) NOT NULL DEFAULT 'Open',
            created_at VARCHAR(191) NOT NULL, FOREIGN KEY(assignee_id) REFERENCES employees(id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS timesheet_entries (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, employee_id BIGINT NOT NULL, work_day VARCHAR(191) NOT NULL,
            project VARCHAR(191) NOT NULL, hours DOUBLE NOT NULL, notes VARCHAR(2048) NOT NULL DEFAULT '',
            status VARCHAR(191) NOT NULL DEFAULT 'Draft', decided_by BIGINT, created_at VARCHAR(191) NOT NULL,
            FOREIGN KEY(employee_id) REFERENCES employees(id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS account_invites (
          id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, employee_id BIGINT NOT NULL,
          token_hash VARCHAR(191) NOT NULL UNIQUE, expires_at VARCHAR(191) NOT NULL,
          used_at VARCHAR(191), created_by BIGINT NOT NULL, created_at VARCHAR(191) NOT NULL,
          FOREIGN KEY(employee_id) REFERENCES employees(id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS login_attempts (
          email_fingerprint VARCHAR(191) PRIMARY KEY, failures BIGINT NOT NULL DEFAULT 0,
          window_start VARCHAR(191) NOT NULL, locked_until VARCHAR(191)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS leave_entitlements (
          leave_type VARCHAR(191) PRIMARY KEY, days BIGINT NOT NULL CHECK(days BETWEEN 0 AND 365),
          updated_at VARCHAR(191) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ticket_messages (
          id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, ticket_id BIGINT NOT NULL, author_id BIGINT NOT NULL,
          message VARCHAR(2048) NOT NULL, created_at VARCHAR(191) NOT NULL,
          FOREIGN KEY(ticket_id) REFERENCES tickets(id),
          FOREIGN KEY(author_id) REFERENCES employees(id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS skill_catalog (
          id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, name VARCHAR(191) NOT NULL UNIQUE, category VARCHAR(191) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_skills (
          id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, employee_id BIGINT NOT NULL, skill_id BIGINT NOT NULL,
          level VARCHAR(191) NOT NULL CHECK(level IN ('Beginner','Intermediate','Advanced')),
          updated_at VARCHAR(191) NOT NULL, UNIQUE(employee_id,skill_id),
          FOREIGN KEY(employee_id) REFERENCES employees(id),
          FOREIGN KEY(skill_id) REFERENCES skill_catalog(id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS private_profiles (
            employee_id BIGINT PRIMARY KEY,
            contact_phone VARCHAR(191) NOT NULL DEFAULT '',
            emergency_contact_name VARCHAR(191) NOT NULL DEFAULT '',
            emergency_contact_phone VARCHAR(191) NOT NULL DEFAULT '',
            mailing_address VARCHAR(2048) NOT NULL DEFAULT '',
            updated_at VARCHAR(191) NOT NULL,
  FOREIGN KEY (employee_id) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS work_mode_requests (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            employee_id BIGINT NOT NULL,
            requested_mode VARCHAR(191) NOT NULL CHECK(requested_mode IN ('Remote','Hybrid','On-site')),
            reason VARCHAR(2048) NOT NULL,
            effective_date VARCHAR(191) NOT NULL,
            status VARCHAR(191) NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','Approved','Rejected','Cancelled')),
            decided_by BIGINT,
            decided_at VARCHAR(191),
            activated_at VARCHAR(191),
            created_at VARCHAR(191) NOT NULL,
  FOREIGN KEY (employee_id) REFERENCES employees(id)
,
  FOREIGN KEY (decided_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS policy_acknowledgements (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            policy_id BIGINT NOT NULL,
            employee_id BIGINT NOT NULL,
            revision BIGINT NOT NULL,
            acknowledged_at VARCHAR(191) NOT NULL,
            UNIQUE(policy_id,employee_id,revision),
  FOREIGN KEY (policy_id) REFERENCES policies(id)
,
  FOREIGN KEY (employee_id) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS salary_packages (
          employee_id BIGINT PRIMARY KEY,
          country VARCHAR(191) NOT NULL DEFAULT 'IN' CHECK(country IN ('IN')),
          currency VARCHAR(191) NOT NULL DEFAULT 'INR', basic DOUBLE NOT NULL CHECK(basic>=0),
          hra DOUBLE NOT NULL CHECK(hra>=0), allowance DOUBLE NOT NULL CHECK(allowance>=0),
          pf_enabled BIGINT NOT NULL DEFAULT 0, esi_enabled BIGINT NOT NULL DEFAULT 0,
          pf_cap DOUBLE NOT NULL DEFAULT 15000, professional_tax DOUBLE NOT NULL DEFAULT 0,
          other_deductions DOUBLE NOT NULL DEFAULT 0, tax_regime VARCHAR(191) NOT NULL DEFAULT 'new',
          tds_mode VARCHAR(191) NOT NULL DEFAULT 'estimate', monthly_tds DOUBLE NOT NULL DEFAULT 0,
          updated_by BIGINT NOT NULL, updated_at VARCHAR(191) NOT NULL,
  FOREIGN KEY (employee_id) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pay_adjustments_v2 (
          id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, employee_id BIGINT NOT NULL,
          month VARCHAR(191) NOT NULL, bonus DOUBLE NOT NULL DEFAULT 0 CHECK(bonus>=0),
          reimbursements DOUBLE NOT NULL DEFAULT 0 CHECK(reimbursements>=0),
          extra_deductions DOUBLE NOT NULL DEFAULT 0 CHECK(extra_deductions>=0),
          days_worked BIGINT NOT NULL DEFAULT 30 CHECK(days_worked>=0),
          payable_days BIGINT NOT NULL DEFAULT 30 CHECK(payable_days>0),
          tds_override DOUBLE CHECK(tds_override IS NULL OR tds_override>=0),
          notes VARCHAR(2048) NOT NULL DEFAULT '', updated_at VARCHAR(191) NOT NULL,
          UNIQUE(employee_id,month),
  FOREIGN KEY (employee_id) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pay_runs_v2 (
          id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, month VARCHAR(191) NOT NULL UNIQUE, country VARCHAR(191) NOT NULL DEFAULT 'IN',
          status VARCHAR(191) NOT NULL DEFAULT 'Draft' CHECK(status IN ('Draft','Reviewed','Published')),
          created_by BIGINT NOT NULL, reviewed_by BIGINT, published_by BIGINT,
          created_at VARCHAR(191) NOT NULL, reviewed_at VARCHAR(191), published_at VARCHAR(191),
          ruleset_version VARCHAR(191) NOT NULL DEFAULT 'INDIA-2026-27-reference') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pay_items_v2 (
          id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, run_id BIGINT NOT NULL,
          employee_id BIGINT NOT NULL,
          data_json LONGTEXT NOT NULL, UNIQUE(run_id,employee_id),
  FOREIGN KEY (run_id) REFERENCES pay_runs_v2(id)
,
  FOREIGN KEY (employee_id) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_corrections (
          id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
          employee_id BIGINT NOT NULL,
          work_day VARCHAR(191) NOT NULL,
          proposed_in VARCHAR(191) NOT NULL,
          proposed_out VARCHAR(191) NOT NULL,
          reason VARCHAR(2048) NOT NULL,
          status VARCHAR(191) NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','Approved','Rejected','Cancelled')),
          created_at VARCHAR(191) NOT NULL, decided_by BIGINT,
          decided_at VARCHAR(191), decision_note VARCHAR(191) NOT NULL DEFAULT '',
  pending_marker TINYINT GENERATED ALWAYS AS (CASE WHEN status='Pending' THEN 1 ELSE NULL END) STORED,
  UNIQUE KEY uq_corrections_one_pending(employee_id,work_day,pending_marker)
,
  FOREIGN KEY (employee_id) REFERENCES employees(id)
,
  FOREIGN KEY (decided_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS document_vault (
          id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
          employee_id BIGINT NOT NULL,
          uploaded_by BIGINT NOT NULL,
          filename VARCHAR(191) NOT NULL, mime_type VARCHAR(191) NOT NULL,
          category VARCHAR(191) NOT NULL, byte_count BIGINT NOT NULL,
          sha256 VARCHAR(191) NOT NULL, contents LONGBLOB NOT NULL,
          created_at VARCHAR(191) NOT NULL,
  FOREIGN KEY (employee_id) REFERENCES employees(id)
,
  FOREIGN KEY (uploaded_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_tickets_employee ON tickets(employee_id);
CREATE INDEX idx_goals_employee ON goals(employee_id);
CREATE INDEX idx_onboarding_employee ON onboarding(employee_id);
CREATE INDEX idx_expenses_employee ON expenses(employee_id);
CREATE INDEX idx_notifications_employee ON notifications(employee_id);
CREATE INDEX idx_benefit_emp ON benefit_enrollments(employee_id);
CREATE INDEX idx_recipient_recognition ON recognitions(recipient_id);
CREATE INDEX idx_timesheet_emp_date ON timesheet_entries(employee_id,work_day);
CREATE INDEX idx_task_assignee ON hr_tasks(assignee_id);
CREATE INDEX idx_invite_employee ON account_invites(employee_id);
CREATE INDEX idx_ticket_messages ON ticket_messages(ticket_id,id);
CREATE INDEX idx_work_mode_employee_status ON work_mode_requests(employee_id,status);
CREATE INDEX idx_policy_ack_employee ON policy_acknowledgements(employee_id,policy_id);
CREATE INDEX idx_v2_employee ON pay_items_v2(employee_id,run_id);
CREATE INDEX idx_corrections_employee ON attendance_corrections(employee_id,status);
CREATE INDEX idx_document_vault_employee ON document_vault(employee_id,id);

-- SASS HRM 1.5: culture, career development and HR request desk
-- Additive tables. Existing organization data remains untouched.
CREATE TABLE IF NOT EXISTS career_plans (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  target_role VARCHAR(120) NOT NULL,
  aspiration TEXT NOT NULL,
  target_date VARCHAR(20) NOT NULL,
  progress INT NOT NULL DEFAULT 0,
  status VARCHAR(24) NOT NULL DEFAULT 'Planned',
  manager_note TEXT NOT NULL,
  created_by BIGINT NOT NULL,
  created_at VARCHAR(48) NOT NULL,
  updated_at VARCHAR(48) NOT NULL,
  INDEX idx_career_employee(employee_id),
  FOREIGN KEY(employee_id) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS career_milestones (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  plan_id BIGINT NOT NULL,
  title VARCHAR(180) NOT NULL,
  due_date VARCHAR(20) NOT NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  INDEX idx_milestone_plan(plan_id),
  FOREIGN KEY(plan_id) REFERENCES career_plans(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_voice_cases (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  reporter_id BIGINT NOT NULL,
  category VARCHAR(64) NOT NULL,
  title VARCHAR(160) NOT NULL,
  description TEXT NOT NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'Submitted',
  resolution_note TEXT NOT NULL,
  created_at VARCHAR(48) NOT NULL,
  updated_at VARCHAR(48) NOT NULL,
  INDEX idx_voice_reporter(reporter_id),
  FOREIGN KEY(reporter_id) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS employee_voice_messages (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  case_id BIGINT NOT NULL,
  author_id BIGINT NOT NULL,
  message TEXT NOT NULL,
  created_at VARCHAR(48) NOT NULL,
  INDEX idx_voice_thread(case_id),
  FOREIGN KEY(case_id) REFERENCES employee_voice_cases(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS discipline_cases (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  created_by BIGINT NOT NULL,
  category VARCHAR(64) NOT NULL,
  summary TEXT NOT NULL,
  incident_date VARCHAR(20) NOT NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'Draft',
  outcome TEXT NOT NULL,
  employee_response TEXT NOT NULL,
  created_at VARCHAR(48) NOT NULL,
  updated_at VARCHAR(48) NOT NULL,
  INDEX idx_discipline_employee(employee_id),
  FOREIGN KEY(employee_id) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS service_categories (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  description VARCHAR(700) NOT NULL,
  active TINYINT NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS service_requests (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  category_id BIGINT NOT NULL,
  subject VARCHAR(180) NOT NULL,
  details TEXT NOT NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'Open',
  hr_response TEXT NOT NULL,
  created_at VARCHAR(48) NOT NULL,
  updated_at VARCHAR(48) NOT NULL,
  INDEX idx_requests_employee(employee_id),
  FOREIGN KEY(employee_id) REFERENCES employees(id),
  FOREIGN KEY(category_id) REFERENCES service_categories(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS discipline_case_responses (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  case_id BIGINT NOT NULL,
  employee_id BIGINT NOT NULL,
  message TEXT NOT NULL,
  created_at VARCHAR(48) NOT NULL,
  INDEX idx_discipline_responses(case_id),
  FOREIGN KEY(case_id) REFERENCES discipline_cases(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- v1.6: organization profile (one row, explicitly configured by HR; no demo seeds)
CREATE TABLE IF NOT EXISTS organization_profile (
  id BIGINT NOT NULL PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  legal_name VARCHAR(180) NOT NULL,
  country VARCHAR(80) NOT NULL,
  timezone VARCHAR(80) NOT NULL,
  contact_email VARCHAR(180) NOT NULL,
  website VARCHAR(250) NOT NULL DEFAULT '',
  updated_at VARCHAR(48) NOT NULL,
  updated_by BIGINT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Talent workflow additions (additive: existing employee and HR records remain intact)
CREATE TABLE IF NOT EXISTS candidate_activity (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, candidate_id BIGINT NOT NULL,
  author_id BIGINT NOT NULL, note TEXT NOT NULL, created_at VARCHAR(48) NOT NULL,
  INDEX idx_candidate_activity(candidate_id),
  FOREIGN KEY(candidate_id) REFERENCES candidates(id), FOREIGN KEY(author_id) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS onboarding_templates (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, title VARCHAR(160) NOT NULL UNIQUE,
  offset_days INT NOT NULL DEFAULT 0, active TINYINT NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS ticket_assignments (
  ticket_id BIGINT NOT NULL PRIMARY KEY, assignee_id BIGINT NOT NULL,
  due_date VARCHAR(20) NOT NULL, updated_at VARCHAR(48) NOT NULL,
  FOREIGN KEY(ticket_id) REFERENCES tickets(id),FOREIGN KEY(assignee_id) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS offboarding_clearance (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, offboarding_id BIGINT NOT NULL,
  title VARCHAR(140) NOT NULL, status VARCHAR(24) NOT NULL DEFAULT 'Pending',
  completed_by BIGINT, completed_at VARCHAR(48), UNIQUE KEY uq_clearance_title(offboarding_id,title),
  FOREIGN KEY(offboarding_id) REFERENCES offboarding(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS task_comments (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, task_id BIGINT NOT NULL,
  author_id BIGINT NOT NULL, message TEXT NOT NULL, created_at VARCHAR(48) NOT NULL,
  INDEX idx_task_comments(task_id), FOREIGN KEY(task_id) REFERENCES hr_tasks(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS service_messages (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, request_id BIGINT NOT NULL,
  author_id BIGINT NOT NULL, message TEXT NOT NULL, created_at VARCHAR(48) NOT NULL,
  INDEX idx_service_messages(request_id), FOREIGN KEY(request_id) REFERENCES service_requests(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- v1.8 additive compensation review history (no changes to existing employee data)
CREATE TABLE IF NOT EXISTS expense_review_events (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 expense_id BIGINT NOT NULL,reviewer_id BIGINT NOT NULL,
 decision VARCHAR(32) NOT NULL, reason VARCHAR(500) NOT NULL,
 reviewed_at VARCHAR(191) NOT NULL,
 FOREIGN KEY(expense_id) REFERENCES expenses(id),FOREIGN KEY(reviewer_id) REFERENCES employees(id),
 INDEX idx_expense_review_events_expense(expense_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS benefit_verification_events (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 enrollment_id BIGINT NOT NULL,reviewer_id BIGINT NOT NULL,
 decision VARCHAR(40) NOT NULL, notes VARCHAR(500) NOT NULL,
 reviewed_at VARCHAR(191) NOT NULL,
 FOREIGN KEY(enrollment_id) REFERENCES benefit_enrollments(id),FOREIGN KEY(reviewer_id) REFERENCES employees(id),
 INDEX idx_benefit_verification_enrollment(enrollment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- v1.9 additive Culture Operations schema (no demo records)
CREATE TABLE IF NOT EXISTS goal_progress_history (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, goal_id BIGINT NOT NULL,
  actor_id BIGINT NOT NULL, old_progress INTEGER NOT NULL, new_progress INTEGER NOT NULL,
  note TEXT NOT NULL, created_at VARCHAR(64) NOT NULL,
  INDEX idx_goal_history_goal(goal_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS training_verifications (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, enrollment_id BIGINT NOT NULL UNIQUE,
  employee_id BIGINT NOT NULL, evidence_note TEXT NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'Pending', reviewer_id BIGINT NULL,
  review_note TEXT NOT NULL, submitted_at VARCHAR(64) NOT NULL, reviewed_at VARCHAR(64) NULL,
  INDEX idx_training_verifications_employee(employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS training_verification_events (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, verification_id BIGINT NOT NULL,
  actor_id BIGINT NOT NULL, event_type VARCHAR(32) NOT NULL, note TEXT NOT NULL,
  created_at VARCHAR(64) NOT NULL, INDEX idx_training_verification_events(verification_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS recognition_reactions (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, recognition_id BIGINT NOT NULL,
  employee_id BIGINT NOT NULL, created_at VARCHAR(64) NOT NULL,
  UNIQUE KEY uq_recognition_reactor (recognition_id,employee_id),
  INDEX idx_recognition_reactions_recognition (recognition_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS culture_case_status_history (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,case_kind VARCHAR(32) NOT NULL,
 case_id BIGINT NOT NULL,actor_id BIGINT NOT NULL,
 old_status VARCHAR(64) NOT NULL,new_status VARCHAR(64) NOT NULL,
 created_at VARCHAR(64) NOT NULL,
 INDEX idx_culture_case_events (case_kind,case_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- v2.0 Employee Services; additive only, preserves existing files and employees
CREATE TABLE IF NOT EXISTS asset_lifecycle_events (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  asset_id BIGINT NOT NULL, actor_id BIGINT NOT NULL, event_type VARCHAR(40) NOT NULL,
  from_employee_id BIGINT, to_employee_id BIGINT, note VARCHAR(350) NOT NULL DEFAULT '',
  created_at VARCHAR(48) NOT NULL,
  INDEX idx_asset_lifecycle_asset(asset_id),
  FOREIGN KEY(asset_id) REFERENCES assets(id), FOREIGN KEY(actor_id) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS document_review_events (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  document_id BIGINT NOT NULL, reviewer_id BIGINT NOT NULL, decision VARCHAR(30) NOT NULL,
  note VARCHAR(500) NOT NULL DEFAULT '', expires_on VARCHAR(12), reviewed_at VARCHAR(48) NOT NULL,
  INDEX idx_document_review_doc(document_id),
  FOREIGN KEY(document_id) REFERENCES documents(id), FOREIGN KEY(reviewer_id) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS employee_preferences (
  employee_id BIGINT NOT NULL PRIMARY KEY,
  date_format VARCHAR(30) NOT NULL DEFAULT 'DD MMM YYYY',
  density VARCHAR(25) NOT NULL DEFAULT 'Comfortable', reduce_motion TINYINT NOT NULL DEFAULT 0,
  updated_at VARCHAR(48) NOT NULL,
  FOREIGN KEY(employee_id) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- v2.5: additive password recovery tokens; keep existing MySQL records and roles intact.
CREATE TABLE IF NOT EXISTS password_reset_tokens (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 token_hash VARCHAR(64) NOT NULL UNIQUE,
 expires_at VARCHAR(64) NOT NULL,
 used_at VARCHAR(64),
 created_at VARCHAR(64) NOT NULL,
 INDEX idx_reset_employee(employee_id),
 CONSTRAINT fk_reset_employee FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- v2.6: additive organization settings and managed office locations
CREATE TABLE IF NOT EXISTS organization_preferences (
 id BIGINT NOT NULL PRIMARY KEY,
 currency VARCHAR(3) NOT NULL, date_format VARCHAR(12) NOT NULL,
 week_start VARCHAR(12) NOT NULL, fiscal_year_start_month INT NOT NULL,
 hours_per_day INT NOT NULL, updated_at VARCHAR(48) NOT NULL,
 updated_by BIGINT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS organization_offices (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 code VARCHAR(24) NOT NULL UNIQUE,
 name VARCHAR(120) NOT NULL UNIQUE,
 city VARCHAR(90) NOT NULL, country VARCHAR(80) NOT NULL,
 address VARCHAR(500) NOT NULL DEFAULT '', timezone VARCHAR(80) NOT NULL,
 is_active TINYINT NOT NULL DEFAULT 1,
 updated_at VARCHAR(48) NOT NULL, updated_by BIGINT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- v2.7: private employee calendar events; strictly employee-owned by API
CREATE TABLE IF NOT EXISTS personal_calendar_events (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 day VARCHAR(10) NOT NULL,
 start_time VARCHAR(5) NOT NULL DEFAULT '',
 title VARCHAR(120) NOT NULL,
 notes VARCHAR(1000) NOT NULL DEFAULT '',
 created_at VARCHAR(48) NOT NULL,
 updated_at VARCHAR(48) NOT NULL,
 INDEX idx_calendar_owner_day(employee_id,day),
 CONSTRAINT fk_calendar_employee FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- v2.9: professional profiles and official identity corrections (additive)
CREATE TABLE IF NOT EXISTS professional_profiles (
 employee_id BIGINT NOT NULL PRIMARY KEY,
 preferred_name VARCHAR(80) NOT NULL DEFAULT '',
 headline VARCHAR(140) NOT NULL DEFAULT '',
 biography VARCHAR(750) NOT NULL DEFAULT '',
 work_phone VARCHAR(32) NOT NULL DEFAULT '',
 timezone VARCHAR(80) NOT NULL DEFAULT 'Asia/Kolkata',
 language VARCHAR(5) NOT NULL DEFAULT 'en',
 directory_visible TINYINT NOT NULL DEFAULT 1,
 avatar_color VARCHAR(7) NOT NULL DEFAULT '#3C6DF0',
 updated_at VARCHAR(48) NOT NULL DEFAULT '',
 CONSTRAINT fk_professional_employee FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
-- v4.4: authenticated profile portraits (binary image, no credentials or base64 in logs)
CREATE TABLE IF NOT EXISTS profile_photos (
 employee_id BIGINT NOT NULL PRIMARY KEY,
 mime_type VARCHAR(32) NOT NULL,
 photo_bytes MEDIUMBLOB NOT NULL,
 updated_at VARCHAR(48) NOT NULL,
 CONSTRAINT fk_profile_photo_employee FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS profile_change_requests (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 field_name VARCHAR(32) NOT NULL,
 requested_value VARCHAR(100) NOT NULL,
 reason VARCHAR(450) NOT NULL,
 status VARCHAR(20) NOT NULL DEFAULT 'Pending',
 requested_at VARCHAR(48) NOT NULL,
 reviewed_by BIGINT NULL,
 reviewed_at VARCHAR(48) NULL,
 review_note VARCHAR(450) NOT NULL DEFAULT '',
 INDEX idx_profile_changes_owner(employee_id,status),
 CONSTRAINT fk_profile_change_employee FOREIGN KEY(employee_id) REFERENCES employees(id),
 CONSTRAINT fk_profile_reviewer FOREIGN KEY(reviewed_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- v3.0: organization workflow controls, employee inbox preferences and archived alerts
CREATE TABLE IF NOT EXISTS workspace_workflow_settings (
 id BIGINT NOT NULL PRIMARY KEY,
 helpdesk_target_days INT NOT NULL DEFAULT 3,
 task_warning_days INT NOT NULL DEFAULT 2,
 onboarding_warning_days INT NOT NULL DEFAULT 3,
 organization_notice VARCHAR(280) NOT NULL DEFAULT '',
 updated_at VARCHAR(48) NOT NULL DEFAULT '',
 updated_by BIGINT NULL,
 FOREIGN KEY(updated_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS employee_inbox_preferences (
 employee_id BIGINT NOT NULL PRIMARY KEY,
 unread_only TINYINT NOT NULL DEFAULT 0,
 compact_view TINYINT NOT NULL DEFAULT 0,
 FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS archived_notifications (
 notification_id BIGINT NOT NULL PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 archived_at VARCHAR(48) NOT NULL,
 FOREIGN KEY(notification_id) REFERENCES notifications(id) ON DELETE CASCADE,
 FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- v3.1: private employee shortcuts (all activity data references existing tables)
CREATE TABLE IF NOT EXISTS employee_workspace_shortcuts (
 employee_id BIGINT NOT NULL PRIMARY KEY,
 pages_json TEXT NOT NULL,
 updated_at VARCHAR(48) NOT NULL,
 CONSTRAINT fk_workspace_shortcuts_employee FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- v3.2 compensation workflow configuration. This table was absent from the v3.3
-- MySQL schema even though the backend reads and writes it. Additive only.
CREATE TABLE IF NOT EXISTS compensation_workflow_settings (
  id BIGINT NOT NULL PRIMARY KEY,
  settings_json LONGTEXT NOT NULL,
  updated_at VARCHAR(64) NOT NULL,
  updated_by BIGINT,
  CONSTRAINT fk_compensation_settings_editor FOREIGN KEY (updated_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- v3.4: admin-only talent and employee service review guidance (advisory).
CREATE TABLE IF NOT EXISTS talent_service_settings (
  id BIGINT NOT NULL PRIMARY KEY,
  settings_json LONGTEXT NOT NULL,
  updated_at VARCHAR(64) NOT NULL,
  updated_by BIGINT,
  CONSTRAINT fk_talent_settings_editor FOREIGN KEY(updated_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- v3.5: manual, deduplicated workflow in-app notifications (no background sends).
CREATE TABLE IF NOT EXISTS workflow_reminder_dispatches (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 kind VARCHAR(24) NOT NULL, record_id BIGINT NOT NULL,
 employee_id BIGINT NOT NULL, dispatch_day VARCHAR(10) NOT NULL,
 dispatched_by BIGINT NOT NULL, created_at VARCHAR(48) NOT NULL,
 UNIQUE KEY uniq_workflow_reminder_day(kind,record_id,employee_id,dispatch_day),
 FOREIGN KEY(employee_id) REFERENCES employees(id),
 FOREIGN KEY(dispatched_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- v3.6: approved leave coverage thresholds (advisory only).
CREATE TABLE IF NOT EXISTS leave_coverage_settings (
 id BIGINT NOT NULL PRIMARY KEY,
 warning_threshold INT NOT NULL DEFAULT 2,
 updated_at VARCHAR(48) NOT NULL,
 updated_by BIGINT,
 FOREIGN KEY(updated_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- v3.6: reusable HR task templates and safe assignment provenance.
CREATE TABLE IF NOT EXISTS hr_task_templates (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 title VARCHAR(160) NOT NULL UNIQUE,
 guidance TEXT NOT NULL,
 priority VARCHAR(16) NOT NULL DEFAULT 'Normal',
 due_offset_days INT NOT NULL DEFAULT 3,
 active TINYINT NOT NULL DEFAULT 1,
 created_by BIGINT NOT NULL,
 created_at VARCHAR(48) NOT NULL,
 FOREIGN KEY(created_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS hr_task_template_assignments (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 template_id BIGINT NOT NULL,
 task_id BIGINT NOT NULL UNIQUE,
 employee_id BIGINT NOT NULL,
 start_date VARCHAR(10) NOT NULL,
 assigned_by BIGINT NOT NULL,
 assigned_at VARCHAR(48) NOT NULL,
 UNIQUE KEY uniq_task_template_employee_start(template_id,employee_id,start_date),
 FOREIGN KEY(template_id) REFERENCES hr_task_templates(id),
 FOREIGN KEY(task_id) REFERENCES hr_tasks(id),
 FOREIGN KEY(employee_id) REFERENCES employees(id),
 FOREIGN KEY(assigned_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- v3.7: per-user saved search terms (no search results or passwords stored).
CREATE TABLE IF NOT EXISTS employee_saved_searches (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL, query_text VARCHAR(80) NOT NULL,
 category VARCHAR(32) NOT NULL, created_at VARCHAR(64) NOT NULL,
 UNIQUE KEY uq_saved_search (employee_id,query_text,category),
 FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- v3.8 HR data quality: configurable scan thresholds and audited, human-owned review queue.
CREATE TABLE IF NOT EXISTS hr_data_quality_policies (
  id BIGINT PRIMARY KEY,
  task_grace_days BIGINT NOT NULL DEFAULT 0,
  onboarding_grace_days BIGINT NOT NULL DEFAULT 0,
  leave_review_days BIGINT NOT NULL DEFAULT 7,
  helpdesk_review_days BIGINT NOT NULL DEFAULT 14,
  updated_by BIGINT,
  updated_at VARCHAR(64) NOT NULL DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS hr_data_quality_reviews (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  issue_key VARCHAR(191) NOT NULL UNIQUE,
  review_status VARCHAR(32) NOT NULL DEFAULT 'Open',
  assigned_to BIGINT,
  review_note VARCHAR(600) NOT NULL DEFAULT '',
  updated_by BIGINT NOT NULL,
  updated_at VARCHAR(64) NOT NULL,
  CONSTRAINT fk_quality_review_assignee FOREIGN KEY (assigned_to) REFERENCES employees(id),
  CONSTRAINT fk_quality_review_author FOREIGN KEY (updated_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX idx_hr_quality_status ON hr_data_quality_reviews(review_status);

-- v3.9 employee performance review cycles, self appraisal, human manager review, 1:1 conversations.
CREATE TABLE IF NOT EXISTS performance_review_cycles (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, name VARCHAR(90) NOT NULL UNIQUE,
 starts_on VARCHAR(10) NOT NULL, ends_on VARCHAR(10) NOT NULL,
 self_due_on VARCHAR(10) NOT NULL, manager_due_on VARCHAR(10) NOT NULL,
 status VARCHAR(20) NOT NULL DEFAULT 'Draft', created_by BIGINT NOT NULL,
 created_at VARCHAR(64) NOT NULL,
 FOREIGN KEY (created_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS performance_appraisals (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, cycle_id BIGINT NOT NULL,
 employee_id BIGINT NOT NULL, self_summary TEXT NOT NULL, self_strengths TEXT NOT NULL,
 self_growth TEXT NOT NULL, self_submitted_at VARCHAR(64) NOT NULL,
 reviewer_id BIGINT NULL, manager_summary TEXT NULL, manager_strengths TEXT NULL,
 manager_growth TEXT NULL, manager_rating INTEGER NULL, manager_submitted_at VARCHAR(64) NULL,
 acknowledged_at VARCHAR(64) NULL, UNIQUE KEY uq_performance_appraisal_cycle_employee (cycle_id,employee_id),
 FOREIGN KEY (cycle_id) REFERENCES performance_review_cycles(id),
 FOREIGN KEY (employee_id) REFERENCES employees(id), FOREIGN KEY (reviewer_id) REFERENCES employees(id),
 INDEX idx_performance_appraisal_employee (employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS performance_checkins (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, employee_id BIGINT NOT NULL,
 facilitator_id BIGINT NOT NULL, meeting_on VARCHAR(10) NOT NULL,
 discussion TEXT NOT NULL, action_items TEXT NOT NULL, created_at VARCHAR(64) NOT NULL,
 FOREIGN KEY (employee_id) REFERENCES employees(id), FOREIGN KEY (facilitator_id) REFERENCES employees(id),
 INDEX idx_performance_checkins_employee (employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- v4.0 human-led development plans, milestones, and direct manager feedback.
CREATE TABLE IF NOT EXISTS performance_development_plans (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL, title VARCHAR(150) NOT NULL, focus_area VARCHAR(64) NOT NULL,
 success_outcome TEXT NOT NULL, support_needed TEXT NOT NULL,
 target_date VARCHAR(10) NOT NULL, status VARCHAR(24) NOT NULL DEFAULT 'Active',
 created_by BIGINT NOT NULL, created_at VARCHAR(64) NOT NULL, updated_at VARCHAR(64) NOT NULL,
 FOREIGN KEY (employee_id) REFERENCES employees(id), FOREIGN KEY (created_by) REFERENCES employees(id),
 INDEX idx_growth_plan_owner(employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS performance_development_milestones (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 plan_id BIGINT NOT NULL, title VARCHAR(180) NOT NULL, due_on VARCHAR(10) NOT NULL,
 completed_at VARCHAR(64) NULL, created_by BIGINT NOT NULL, created_at VARCHAR(64) NOT NULL,
 FOREIGN KEY (plan_id) REFERENCES performance_development_plans(id),
 FOREIGN KEY (created_by) REFERENCES employees(id), INDEX idx_growth_milestone_plan(plan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS performance_feedback_requests (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL, manager_id BIGINT NOT NULL, topic VARCHAR(140) NOT NULL,
 question TEXT NOT NULL, status VARCHAR(24) NOT NULL DEFAULT 'Pending',
 response TEXT NULL, responded_at VARCHAR(64) NULL, acknowledged_at VARCHAR(64) NULL,
 created_at VARCHAR(64) NOT NULL, FOREIGN KEY (employee_id) REFERENCES employees(id),
 FOREIGN KEY (manager_id) REFERENCES employees(id), INDEX idx_growth_feedback_owner(employee_id),
 INDEX idx_growth_feedback_manager(manager_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- v4.1 follow-up actions for human-led employee performance and appraisals.
CREATE TABLE IF NOT EXISTS performance_followup_actions (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL, title VARCHAR(160) NOT NULL, notes TEXT NOT NULL,
 category VARCHAR(32) NOT NULL, due_on VARCHAR(10) NOT NULL,
 status VARCHAR(16) NOT NULL DEFAULT 'Open', created_by BIGINT NOT NULL,
 created_at VARCHAR(64) NOT NULL, completed_at VARCHAR(64) NULL, updated_at VARCHAR(64) NOT NULL,
 FOREIGN KEY(employee_id) REFERENCES employees(id), FOREIGN KEY(created_by) REFERENCES employees(id),
 INDEX idx_perf_followup_owner(employee_id), INDEX idx_perf_followup_due(due_on)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
