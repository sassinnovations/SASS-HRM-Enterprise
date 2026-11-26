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
