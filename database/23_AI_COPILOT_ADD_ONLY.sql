-- v5.5 AI Copilot, safe additive schema for existing MySQL installations.
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
