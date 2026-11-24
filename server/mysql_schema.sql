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

-- HR data quality center: reviewed CSV/XLSX HRIS imports, mapping preferences and audit metadata.
-- No workbook bytes or row-level personal information are stored here.
CREATE TABLE IF NOT EXISTS hr_data_quality_import_settings (
  id BIGINT NOT NULL PRIMARY KEY,
  mapping_json LONGTEXT NOT NULL,
  duplicate_mode VARCHAR(12) NOT NULL DEFAULT 'reject',
  date_format VARCHAR(12) NOT NULL DEFAULT 'YYYY-MM-DD',
  sheet_name VARCHAR(100) NOT NULL DEFAULT '',
  default_role VARCHAR(20) NOT NULL DEFAULT 'employee',
  default_work_mode VARCHAR(20) NOT NULL DEFAULT 'On-site',
  trim_values TINYINT NOT NULL DEFAULT 1,
  skip_blank_rows TINYINT NOT NULL DEFAULT 1,
  max_rows BIGINT NOT NULL DEFAULT 1000,
  updated_by BIGINT NOT NULL,
  updated_at VARCHAR(64) NOT NULL,
  CONSTRAINT fk_hr_dq_import_settings_author FOREIGN KEY (updated_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS hr_data_quality_import_history (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  filename VARCHAR(180) NOT NULL,
  content_sha256 CHAR(64) NOT NULL,
  source_rows BIGINT NOT NULL,
  created_rows BIGINT NOT NULL,
  duplicate_rows BIGINT NOT NULL,
  actor_id BIGINT NOT NULL,
  created_at VARCHAR(64) NOT NULL,
  CONSTRAINT fk_hr_dq_import_history_actor FOREIGN KEY (actor_id) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX idx_dq_import_history_actor ON hr_data_quality_import_history(actor_id);

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

-- v4.5 successful sign-in history (no credentials or device tracking).
CREATE TABLE IF NOT EXISTS account_login_events (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL, created_at VARCHAR(64) NOT NULL,
 FOREIGN KEY(employee_id) REFERENCES employees(id),
 INDEX idx_login_events_employee_date(employee_id,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- v4.6: Public applications are PENDING; only authenticated HR admins can approve.
-- Passwords exist only as salted hashes; after review the request hash is erased.
CREATE TABLE IF NOT EXISTS account_signup_requests (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(191) NOT NULL,
  email VARCHAR(191) NOT NULL,
  work_email VARCHAR(191) NOT NULL,
  requested_role VARCHAR(32) NOT NULL,
  designation VARCHAR(191) NOT NULL,
  department VARCHAR(191) NOT NULL,
  location VARCHAR(191) NOT NULL,
  work_mode VARCHAR(32) NOT NULL,
  password_hash VARCHAR(191) NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'Pending',
  created_at VARCHAR(64) NOT NULL,
  reviewed_at VARCHAR(64),
  reviewed_by BIGINT,
  review_note VARCHAR(300),
  employee_id BIGINT,
  CONSTRAINT fk_signup_reviewer FOREIGN KEY(reviewed_by) REFERENCES employees(id),
  CONSTRAINT fk_signup_employee FOREIGN KEY(employee_id) REFERENCES employees(id),
  INDEX idx_signup_status (status,created_at),
  INDEX idx_signup_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- v4.7 administrator-controlled public registration policy. Does not alter existing accounts.
CREATE TABLE IF NOT EXISTS account_signup_settings (
  id BIGINT NOT NULL PRIMARY KEY,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  allow_employee TINYINT(1) NOT NULL DEFAULT 1,
  allow_hr_subadmin TINYINT(1) NOT NULL DEFAULT 1,
  allow_admin TINYINT(1) NOT NULL DEFAULT 1,
  allowed_email_domain VARCHAR(191) NOT NULL DEFAULT '',
  updated_by BIGINT,
  updated_at VARCHAR(64) NOT NULL DEFAULT '',
  CONSTRAINT fk_signup_settings_updated_by FOREIGN KEY(updated_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Candidate Search Library v4.8: additive, preserves existing ATS candidate IDs.
-- The original uploaded workbook is archived as checksummed BLOB chunks, ensuring
-- every auxiliary sheet, hyperlink, formula and exception survives the import.
CREATE TABLE IF NOT EXISTS candidate_import_batches (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 sha256 CHAR(64) NOT NULL UNIQUE,
 filename VARCHAR(255) NOT NULL,
 sheet_name VARCHAR(100) NOT NULL,
 rows_expected BIGINT NOT NULL,
 rows_imported BIGINT NOT NULL,
 file_size_bytes BIGINT NOT NULL,
 archive_chunks INT NOT NULL,
 content_sha256 CHAR(64) NULL,
 created_by BIGINT NULL,
 created_at VARCHAR(64) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS candidate_import_chunks (
 batch_id BIGINT NOT NULL,
 part_number INT NOT NULL,
 data MEDIUMBLOB NOT NULL,
 PRIMARY KEY(batch_id,part_number),
 FOREIGN KEY(batch_id) REFERENCES candidate_import_batches(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS candidate_profiles (
 candidate_id BIGINT NOT NULL PRIMARY KEY,
 import_batch_id BIGINT NULL,
 source_sheet VARCHAR(191) NULL,
 source_row BIGINT NULL,
 source_order BIGINT NULL,
 email TEXT NULL, phone TEXT NULL,
 location TEXT NULL, preferred_locations LONGTEXT NULL,
 education LONGTEXT NULL, degree TEXT NULL, university LONGTEXT NULL,
 postgraduate TEXT NULL, doctorate TEXT NULL,
 experience_years DOUBLE NULL, experience_raw VARCHAR(191) NULL,
 company TEXT NULL, designation TEXT NULL,
 salary_raw VARCHAR(191) NULL, salary_lpa DOUBLE NULL,
 notice TEXT NULL, resume_headline LONGTEXT NULL,
 skills_manual TEXT NOT NULL, screening_answers LONGTEXT NULL,
 raw_fields LONGTEXT NOT NULL,
 created_at VARCHAR(64) NOT NULL, updated_at VARCHAR(64) NOT NULL,
 FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
 FOREIGN KEY(import_batch_id) REFERENCES candidate_import_batches(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_candidate_profiles_import_order ON candidate_profiles(import_batch_id,source_order);
CREATE INDEX idx_candidate_profiles_experience ON candidate_profiles(experience_years);
CREATE INDEX idx_candidates_job_title ON candidates(job_title);

-- Hiring pipeline (additive; existing candidate/job records remain unchanged).
CREATE TABLE IF NOT EXISTS hiring_stage_reviews (
 candidate_id BIGINT NOT NULL, stage VARCHAR(191) NOT NULL, completed_json LONGTEXT NOT NULL,
 note LONGTEXT NOT NULL, details_json LONGTEXT NOT NULL, updated_by BIGINT NOT NULL, updated_at VARCHAR(191) NOT NULL,
 PRIMARY KEY(candidate_id,stage), FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS hiring_stage_events (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, candidate_id BIGINT NOT NULL,
 from_stage VARCHAR(191) NOT NULL, to_stage VARCHAR(191) NOT NULL, reason VARCHAR(1000) NOT NULL,
 actor_id BIGINT NOT NULL, created_at VARCHAR(191) NOT NULL,
 FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS hiring_stage_settings (
 stage VARCHAR(32) NOT NULL PRIMARY KEY,
 checklist_json LONGTEXT NOT NULL, instructions LONGTEXT NOT NULL,
 sla_days INT NOT NULL DEFAULT 7, reviewer_role VARCHAR(16) NOT NULL DEFAULT 'manager',
 note_min_chars INT NOT NULL DEFAULT 8, updated_by BIGINT NULL,
 updated_at VARCHAR(64) NOT NULL DEFAULT '',
 FOREIGN KEY (updated_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS hiring_job_requirements (
 job_id BIGINT NOT NULL PRIMARY KEY, required_skills LONGTEXT NOT NULL,
 education VARCHAR(500) NOT NULL, min_experience_years BIGINT NOT NULL DEFAULT 0,
 criteria LONGTEXT NOT NULL, updated_by BIGINT NOT NULL, updated_at VARCHAR(191) NOT NULL,
 FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- v5.2 privacy-conscious attendance capture (no fingerprint or iris templates are stored).
CREATE TABLE IF NOT EXISTS attendance_capture_events (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  work_day VARCHAR(10) NOT NULL,
  event_type VARCHAR(32) NOT NULL,
  method VARCHAR(32) NOT NULL,
  occurred_at VARCHAR(64) NOT NULL,
  recorded_by BIGINT NULL,
  device_id VARCHAR(64) NOT NULL DEFAULT '',
  note VARCHAR(500) NOT NULL DEFAULT '',
  INDEX idx_attendance_capture_employee(employee_id,work_day),
  FOREIGN KEY(employee_id) REFERENCES employees(id),
  FOREIGN KEY(recorded_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_photo_evidence (
  event_id BIGINT NOT NULL PRIMARY KEY,
  ciphertext LONGBLOB NOT NULL,
  created_at VARCHAR(64) NOT NULL,
  expires_at VARCHAR(64) NOT NULL,
  FOREIGN KEY(event_id) REFERENCES attendance_capture_events(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_device_nonces (
  device_id VARCHAR(64) NOT NULL,
  nonce VARCHAR(128) NOT NULL,
  used_at VARCHAR(64) NOT NULL,
  PRIMARY KEY(device_id,nonce)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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

-- Optional foundations: workforce planning, attendance review, payroll review, recruiting and compliance.

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

-- SASS HRM: Asset Management enrichment. Run after existing schema 213 (and a verified backup).
-- Add-only; no assets, candidates, employee data, or MySQL volumes are deleted.
CREATE TABLE IF NOT EXISTS asset_profiles (
  asset_id BIGINT NOT NULL PRIMARY KEY,
  category VARCHAR(80) NOT NULL,
  description TEXT NOT NULL,
  manufacturer VARCHAR(120) NOT NULL DEFAULT '',
  model VARCHAR(120) NOT NULL DEFAULT '',
  asset_tag VARCHAR(80) NULL,
  condition_label VARCHAR(30) NOT NULL,
  storage_location VARCHAR(191) NOT NULL,
  purchase_date DATE NULL,
  purchase_amount DECIMAL(12,2) NULL,
  warranty_expiry DATE NULL,
  supplier_name VARCHAR(150) NOT NULL DEFAULT '',
  invoice_number VARCHAR(120) NOT NULL DEFAULT '',
  accessories TEXT NOT NULL,
  internal_notes TEXT NOT NULL,
  updated_by BIGINT NOT NULL,
  updated_at VARCHAR(40) NOT NULL,
  FOREIGN KEY (asset_id) REFERENCES assets(id),
  FOREIGN KEY (updated_by) REFERENCES employees(id),
  UNIQUE KEY uq_asset_profiles_tag (asset_tag),
  INDEX idx_asset_profiles_category (category,condition_label)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS asset_inspections (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  asset_id BIGINT NOT NULL,
  inspector_id BIGINT NOT NULL,
  inspected_on DATE NOT NULL,
  condition_label VARCHAR(30) NOT NULL,
  working_ok TINYINT(1) NOT NULL,
  accessories_ok TINYINT(1) NOT NULL,
  security_ok TINYINT(1) NOT NULL,
  note VARCHAR(1000) NOT NULL DEFAULT '',
  created_at VARCHAR(40) NOT NULL,
  FOREIGN KEY (asset_id) REFERENCES assets(id),
  FOREIGN KEY (inspector_id) REFERENCES employees(id),
  INDEX idx_asset_inspections_asset (asset_id,inspected_on)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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

-- 20: Recruitment JD library; safe, add-only and no data seeded.
-- JD deletion is an authenticated API operation, never a database migration side effect.
CREATE TABLE IF NOT EXISTS jd_import_batches (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  filename VARCHAR(191) NOT NULL,
  content_sha256 CHAR(64) NOT NULL,
  rows_received INT NOT NULL,
  rows_imported INT NOT NULL,
  rows_skipped INT NOT NULL,
  imported_by BIGINT NOT NULL,
  imported_at VARCHAR(191) NOT NULL,
  FOREIGN KEY (imported_by) REFERENCES employees(id),
  INDEX idx_jd_import_date (imported_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recruitment_job_descriptions (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(191) NOT NULL,
  description LONGTEXT NOT NULL,
  department VARCHAR(191) NOT NULL DEFAULT '',
  location VARCHAR(191) NOT NULL DEFAULT '',
  employment_type VARCHAR(32) NOT NULL DEFAULT 'Full-time',
  required_skills TEXT NOT NULL,
  preferred_skills TEXT NOT NULL,
  min_experience DOUBLE NOT NULL DEFAULT 0,
  education VARCHAR(191) NOT NULL DEFAULT '',
  status VARCHAR(20) NOT NULL DEFAULT 'Open',
  job_opening_id BIGINT NULL,
  import_batch_id BIGINT NULL,
  dedup_key CHAR(64) NOT NULL,
  created_by BIGINT NOT NULL,
  updated_by BIGINT NOT NULL,
  created_at VARCHAR(191) NOT NULL,
  updated_at VARCHAR(191) NOT NULL,
  UNIQUE KEY uq_job_description_content (dedup_key),
  FOREIGN KEY (job_opening_id) REFERENCES jobs(id) ON DELETE SET NULL,
  FOREIGN KEY (import_batch_id) REFERENCES jd_import_batches(id) ON DELETE SET NULL,
  FOREIGN KEY (created_by) REFERENCES employees(id),
  FOREIGN KEY (updated_by) REFERENCES employees(id),
  INDEX idx_jd_status (status),
  INDEX idx_jd_title (title),
  INDEX idx_jd_batch (import_batch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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

-- SASS HRM — SASS INNOVATIONS ENTERPRISE | migration 22 | database verification history
-- Safe add-only operational schema for persisted administrative connectivity checks.
CREATE TABLE IF NOT EXISTS database_verification_runs (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  run_status VARCHAR(24) NOT NULL,
  expected_tables INT NOT NULL DEFAULT 0,
  present_tables INT NOT NULL DEFAULT 0,
  missing_tables INT NOT NULL DEFAULT 0,
  missing_columns INT NOT NULL DEFAULT 0,
  missing_indexes INT NOT NULL DEFAULT 0,
  missing_foreign_keys INT NOT NULL DEFAULT 0,
  access_failures INT NOT NULL DEFAULT 0,
  requested_by BIGINT NOT NULL,
  checked_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (requested_by) REFERENCES employees(id),
  INDEX idx_database_checks_time (checked_at),
  INDEX idx_database_checks_status (run_status,checked_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS database_verification_findings (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  run_id BIGINT NOT NULL,
  finding_type VARCHAR(40) NOT NULL,
  object_name VARCHAR(191) NOT NULL,
  checked_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY (run_id) REFERENCES database_verification_runs(id),
  INDEX idx_database_findings_run (run_id,finding_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS database_module_checks (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  run_id BIGINT NOT NULL,
  module_name VARCHAR(120) NOT NULL,
  required_count INT NOT NULL DEFAULT 0,
  present_count INT NOT NULL DEFAULT 0,
  missing_names VARCHAR(2048) NOT NULL DEFAULT '',
  FOREIGN KEY (run_id) REFERENCES database_verification_runs(id),
  UNIQUE KEY uq_database_module_run (run_id,module_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- v5.5 AI copilot. Article publication is admin-managed; proposals are short-lived and user-bound.
CREATE TABLE IF NOT EXISTS ai_knowledge_articles (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(190) NOT NULL, category VARCHAR(100) NOT NULL,
  content LONGTEXT NOT NULL, status VARCHAR(24) NOT NULL DEFAULT 'Draft',
  created_by BIGINT NOT NULL, created_at VARCHAR(40) NOT NULL, updated_at VARCHAR(40) NOT NULL,
  INDEX idx_ai_knowledge_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ai_knowledge_scopes (
  article_id BIGINT NOT NULL PRIMARY KEY,
  feature_key VARCHAR(80) NOT NULL DEFAULT '',
  audience VARCHAR(16) NOT NULL DEFAULT 'All',
  INDEX idx_ai_scope_feature (feature_key,audience),
  FOREIGN KEY (article_id) REFERENCES ai_knowledge_articles(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ai_action_proposals (
  id VARCHAR(48) NOT NULL PRIMARY KEY, actor_id BIGINT NOT NULL,
  operation VARCHAR(80) NOT NULL, args_json LONGTEXT NOT NULL,
  preview LONGTEXT NOT NULL, state VARCHAR(24) NOT NULL DEFAULT 'Pending',
  created_at VARCHAR(40) NOT NULL, expires_at VARCHAR(40) NOT NULL,
  result_json LONGTEXT NOT NULL,
  INDEX idx_ai_action_owner (actor_id,state),
  FOREIGN KEY (actor_id) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Additive schema: official work detail change approval requests (all three account types).
-- Apply once to an existing production MySQL schema before deploying the new backend.
CREATE TABLE IF NOT EXISTS official_work_detail_requests (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 payload_json TEXT NOT NULL,
 baseline_json TEXT NOT NULL,
 change_reason VARCHAR(450) NOT NULL,
 status VARCHAR(20) NOT NULL DEFAULT 'Pending',
 requested_at VARCHAR(48) NOT NULL,
 reviewed_by BIGINT NULL,
 reviewed_at VARCHAR(48) NULL,
 review_note VARCHAR(450) NOT NULL DEFAULT '',
 INDEX idx_official_detail_requests_employee (employee_id,status),
 INDEX idx_official_detail_requests_status (status,requested_at),
 CONSTRAINT fk_official_change_employee FOREIGN KEY (employee_id) REFERENCES employees(id),
 CONSTRAINT fk_official_change_reviewer FOREIGN KEY (reviewed_by) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
