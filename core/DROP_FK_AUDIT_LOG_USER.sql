-- ============================================
-- audit_log 테이블의 user_id 외래키 제약조건 제거
-- ============================================
-- user_id는 Account.id (UUID)와 AdminMemberShip.memberShipSid (CHAR(15)) 모두 저장해야 하므로
-- 외래키 제약조건을 제거해야 합니다.
-- ============================================

-- 1. 외래키 제약조건 제거 (제약조건 이름이 다를 수 있으므로 확인 후 실행)
-- 먼저 현재 외래키 제약조건 확인:
-- SELECT CONSTRAINT_NAME 
-- FROM information_schema.KEY_COLUMN_USAGE 
-- WHERE TABLE_SCHEMA = 'inde' 
--   AND TABLE_NAME = 'audit_log' 
--   AND COLUMN_NAME = 'user_id' 
--   AND REFERENCED_TABLE_NAME IS NOT NULL;

-- 외래키 제약조건 제거 (제약조건 이름이 'fk_audit_log_user'인 경우)
ALTER TABLE `audit_log` 
DROP FOREIGN KEY `fk_audit_log_user`;

-- 만약 위 명령이 실패하면, 실제 제약조건 이름을 확인하고 아래 명령을 사용하세요:
-- ALTER TABLE `audit_log` 
-- DROP FOREIGN KEY `실제_제약조건_이름`;

-- ============================================
-- 확인
-- ============================================
-- SHOW CREATE TABLE audit_log;



