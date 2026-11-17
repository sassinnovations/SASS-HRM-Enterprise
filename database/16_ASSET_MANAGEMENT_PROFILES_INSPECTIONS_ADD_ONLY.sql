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
