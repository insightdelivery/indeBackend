-- ============================================
-- audit_log 테이블의 user_id 컬럼 크기 확대
-- ============================================
-- IndeUser.id는 UUID(36자)이므로 user_id 컬럼을 VARCHAR(50)으로 확대
-- 기존: CHAR(15) 또는 VARCHAR(15)
-- 변경: VARCHAR(50) - UUID(36자)와 AdminMemberShip.memberShipSid(15자) 모두 저장 가능
-- ============================================

-- user_id 컬럼 타입 변경
ALTER TABLE `audit_log` 
MODIFY COLUMN `user_id` VARCHAR(50) NULL DEFAULT NULL COMMENT '사용자 ID (Account.id(UUID 36자) 또는 AdminMemberShip.memberShipSid(15자) 또는 IndeUser.id(UUID 36자))';

-- ============================================
-- 확인
-- ============================================
-- DESCRIBE audit_log;
-- SHOW CREATE TABLE audit_log;




