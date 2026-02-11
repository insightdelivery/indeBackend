-- ============================================
-- Article 테이블의 content 컬럼을 MEDIUMTEXT로 변경
-- ============================================
-- 현재: TEXT (최대 65,535 bytes, 약 64KB)
-- 변경: MEDIUMTEXT (최대 16,777,215 bytes, 약 16MB)

ALTER TABLE `article` 
MODIFY COLUMN `content` MEDIUMTEXT NOT NULL COMMENT '본문 내용';

