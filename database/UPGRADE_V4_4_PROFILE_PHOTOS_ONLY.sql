-- SASS HRM v4.4.0: additive profile photo storage for existing MySQL 8.4 databases.
-- BACK UP FIRST. Run against the existing SASS HRM database; no data deletions.
-- Uses current database (do not change MYSQL_DATABASE without checking the target).
CREATE TABLE IF NOT EXISTS profile_photos (
 employee_id BIGINT NOT NULL PRIMARY KEY,
 mime_type VARCHAR(32) NOT NULL,
 photo_bytes MEDIUMBLOB NOT NULL,
 updated_at VARCHAR(48) NOT NULL,
 CONSTRAINT fk_profile_photo_employee FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
