-- Personal default draft view; independent of submitted history preferences.
CREATE TABLE IF NOT EXISTS self_service_draft_views (
  employee_id BIGINT NOT NULL PRIMARY KEY,
  module_filter VARCHAR(32) NOT NULL,
  draft_view VARCHAR(16) NOT NULL CHECK(draft_view IN ('all','drafting','ready','pinned')),
  sort_order VARCHAR(16) NOT NULL CHECK(sort_order IN ('newest','oldest','title')),
  FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Employee-owned default calendar layout and agenda range.
CREATE TABLE IF NOT EXISTS employee_calendar_agenda_preferences (
 employee_id BIGINT NOT NULL PRIMARY KEY,
 preferred_view VARCHAR(12) NOT NULL DEFAULT 'month',
 agenda_days INTEGER NOT NULL DEFAULT 14,
 CONSTRAINT fk_calendar_agenda_preferences_employee FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
