
-- Per-account display preferences for the Team leave & coverage planner.
CREATE TABLE IF NOT EXISTS leave_coverage_personal_preferences (
 employee_id BIGINT NOT NULL PRIMARY KEY,
 default_department VARCHAR(191),
 show_holidays TINYINT NOT NULL DEFAULT 1,
 plan_status VARCHAR(16) NOT NULL DEFAULT 'All',
 my_assignments_only TINYINT NOT NULL DEFAULT 0,
 FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Private draft stage and pin metadata; existing drafts keep their default stage.
CREATE TABLE IF NOT EXISTS self_service_draft_organization (
  draft_id BIGINT NOT NULL PRIMARY KEY,
  stage VARCHAR(16) NOT NULL CHECK(stage IN ('drafting','ready')),
  pinned TINYINT NOT NULL CHECK(pinned IN (0,1)),
  updated_at VARCHAR(48) NOT NULL,
  FOREIGN KEY(draft_id) REFERENCES self_service_drafts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Owner-only initial filters, order and page size for the notification inbox.
CREATE TABLE IF NOT EXISTS employee_inbox_display_defaults (
 employee_id BIGINT NOT NULL PRIMARY KEY,
 notification_order VARCHAR(8) NOT NULL DEFAULT 'newest',
 notification_page_size INT NOT NULL DEFAULT 25,
 reminder_view VARCHAR(12) NOT NULL DEFAULT 'open',
 FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Account-owned event categories. Deleting a category removes only assignments.
CREATE TABLE IF NOT EXISTS employee_calendar_categories (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 employee_id BIGINT NOT NULL,
 name VARCHAR(48) NOT NULL,
 name_key VARCHAR(160) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
 color VARCHAR(12) NOT NULL DEFAULT 'blue',
 UNIQUE KEY uq_employee_calendar_category_name(employee_id,name_key),
 CONSTRAINT fk_calendar_category_employee FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS personal_calendar_event_categories (
 event_id BIGINT NOT NULL PRIMARY KEY,
 category_id BIGINT NOT NULL,
 INDEX idx_calendar_category_events(category_id),
 CONSTRAINT fk_calendar_tag_event FOREIGN KEY(event_id) REFERENCES personal_calendar_events(id) ON DELETE CASCADE,
 CONSTRAINT fk_calendar_tag_category FOREIGN KEY(category_id) REFERENCES employee_calendar_categories(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Personal Security checklist settings; no device, credential, or audit data.
CREATE TABLE IF NOT EXISTS employee_security_checklist_settings (
 employee_id BIGINT NOT NULL PRIMARY KEY,
 status_filter VARCHAR(12) NOT NULL DEFAULT 'all',
 sort_order VARCHAR(12) NOT NULL DEFAULT 'due',
 default_due VARCHAR(12) NOT NULL DEFAULT 'none',
 FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
