-- Separate database for integration tests (never test against the dev DB).
CREATE DATABASE IF NOT EXISTS app_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
GRANT ALL PRIVILEGES ON app_test.* TO 'app'@'%';
