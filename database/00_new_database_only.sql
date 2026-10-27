-- OPTIONAL: Run ONLY for a new, manually configured MySQL database.
-- This is not needed when using Docker Compose: MYSQL_DATABASE creates it.
-- If you customize MYSQL_DATABASE in .env, adjust the name here to match.
-- Do NOT run DROP DATABASE, and do NOT put passwords in SQL scripts.
CREATE DATABASE IF NOT EXISTS `sass_hrm` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `sass_hrm`;
