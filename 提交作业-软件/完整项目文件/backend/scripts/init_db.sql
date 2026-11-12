-- 本地开发数据库初始化（方案 A：每人一台本地 MySQL）
--
-- 使用前：
--   1. 把下面的 CHANGE_ME_APP_PASSWORD 全部替换成你自己的密码。
--      建议用 `openssl rand -hex 16` 生成，只含 0-9a-f，避免 URL 转义问题。
--   2. 用 root 执行本文件（只需执行一次）：
--      Git Bash:
--        mysql -u root -p --default-character-set=utf8mb4 < scripts/init_db.sql
--      PowerShell:
--        Get-Content .\scripts\init_db.sql -Raw | mysql -u root -p --default-character-set=utf8mb4
--
-- 注意：不要把替换后的密码提交到 Git；应用连接串写在 backend/.env，该文件已被忽略。

SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS smart_study_room
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 同时创建 localhost 与 127.0.0.1，避免 MySQL 主机名匹配差异导致登录失败
CREATE USER IF NOT EXISTS 'study_app'@'localhost'
  IDENTIFIED BY 'CHANGE_ME_APP_PASSWORD';
CREATE USER IF NOT EXISTS 'study_app'@'127.0.0.1'
  IDENTIFIED BY 'CHANGE_ME_APP_PASSWORD';

ALTER USER 'study_app'@'localhost'
  IDENTIFIED BY 'CHANGE_ME_APP_PASSWORD';
ALTER USER 'study_app'@'127.0.0.1'
  IDENTIFIED BY 'CHANGE_ME_APP_PASSWORD';

GRANT ALL PRIVILEGES ON smart_study_room.* TO 'study_app'@'localhost';
GRANT ALL PRIVILEGES ON smart_study_room.* TO 'study_app'@'127.0.0.1';
FLUSH PRIVILEGES;
