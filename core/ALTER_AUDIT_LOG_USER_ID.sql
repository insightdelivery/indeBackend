-- ============================================
-- audit_log 테이블의 user_id 컬럼 수정
-- ============================================
-- 기존 user_id 컬럼을 VARCHAR(36)으로 변경하여
-- Account.id (UUID, 36자)와 AdminMemberShip.memberShipSid (CHAR(15)) 모두 저장 가능하게 함
-- ============================================

-- 기존 user_id 컬럼이 ForeignKey로 되어 있다면 제약조건 제거
-- 먼저 외래키 제약조건 이름 확인:
-- SELECT CONSTRAINT_NAME 
-- FROM information_schema.KEY_COLUMN_USAGE 
-- WHERE TABLE_SCHEMA = DATABASE()
--   AND TABLE_NAME = 'audit_log' 
--   AND COLUMN_NAME = 'user_id' 
--   AND REFERENCED_TABLE_NAME IS NOT NULL;

-- 외래키 제약조건 제거 (제약조건 이름이 'fk_audit_log_user'인 경우)
ALTER TABLE `audit_log` 
DROP FOREIGN KEY `fk_audit_log_user`;

-- user_id 컬럼 타입 변경 (CHAR(36) -> CHAR(15))
ALTER TABLE `audit_log` 
MODIFY COLUMN `user_id` CHAR(15) NULL DEFAULT NULL COMMENT '사용자 ID (Account.id 또는 AdminMemberShip.memberShipSid)';

-- 인덱스 재생성
ALTER TABLE `audit_log` 
DROP INDEX IF EXISTS `idx_user_created`;

ALTER TABLE `audit_log` 
ADD INDEX `idx_user_id_created` (`user_id`, `created_at`);

-- ============================================
-- 확인
-- ============================================
-- DESCRIBE audit_log;
-- SHOW CREATE TABLE audit_log;

