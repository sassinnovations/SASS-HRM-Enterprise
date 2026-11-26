-- AI control center v3. Safe additive migration; older unscoped articles retain All visibility.
-- Review existing articles and assign a restricted audience before publishing sensitive guidance.
CREATE TABLE IF NOT EXISTS ai_knowledge_scopes (
  article_id BIGINT NOT NULL PRIMARY KEY,
  feature_key VARCHAR(80) NOT NULL DEFAULT '',
  audience VARCHAR(16) NOT NULL DEFAULT 'All',
  INDEX idx_ai_scope_feature (feature_key,audience),
  FOREIGN KEY (article_id) REFERENCES ai_knowledge_articles(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

