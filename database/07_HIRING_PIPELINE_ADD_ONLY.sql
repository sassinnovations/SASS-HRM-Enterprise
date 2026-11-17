-- Additive hiring pipeline tables for an existing SASS HRM database.
-- Back up first; do not DROP tables or reset MySQL volumes.
-- Select the correct database before executing.

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
CREATE TABLE IF NOT EXISTS hiring_job_requirements (
 job_id BIGINT NOT NULL PRIMARY KEY, required_skills LONGTEXT NOT NULL,
 education VARCHAR(500) NOT NULL, min_experience_years BIGINT NOT NULL DEFAULT 0,
 criteria LONGTEXT NOT NULL, updated_by BIGINT NOT NULL, updated_at VARCHAR(191) NOT NULL,
 FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
