-- Add-only product catalog and project register. Equipment is unchanged.
CREATE TABLE IF NOT EXISTS hrm_work_catalog (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    kind VARCHAR(12) NOT NULL,
    code VARCHAR(48) NOT NULL,
    name VARCHAR(160) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(24) NOT NULL,
    category VARCHAR(80) NOT NULL,
    owner_id BIGINT NULL,
    start_date VARCHAR(10) NULL,
    end_date VARCHAR(10) NULL,
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    archived_at VARCHAR(40) NULL,
    UNIQUE KEY ux_hrm_work_catalog_kind_code (kind,code),
    INDEX idx_hrm_work_catalog_visible (kind,archived_at,id),
    CONSTRAINT fk_hrm_work_catalog_owner FOREIGN KEY (owner_id) REFERENCES employees(id) ON DELETE SET NULL,
    CONSTRAINT ck_hrm_work_catalog_kind CHECK (kind IN ('products','projects'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS hrm_work_catalog_settings (
    kind VARCHAR(12) NOT NULL PRIMARY KEY,
    default_status VARCHAR(24) NOT NULL,
    categories_json TEXT NOT NULL,
    CONSTRAINT ck_hrm_work_catalog_settings_kind CHECK (kind IN ('products','projects'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
