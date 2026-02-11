-- ============================================
-- audit_log 테이블에 admin_member_id 컬럼 추가
-- ============================================
-- 기존 테이블에 컬럼을 추가하는 ALTER 문
-- ============================================

-- admin_member_id 컬럼 추가
ALTER TABLE `audit_log` 
ADD COLUMN `admin_member_id` CHAR(15) NULL DEFAULT NULL COMMENT '관리자 회원 ID (adminMemberShip.memberShipSid 참조)' 
AFTER `user_id`;

-- 인덱스 추가
ALTER TABLE `audit_log` 
ADD INDEX `idx_admin_member_created` (`admin_member_id`, `created_at`);

-- 외래키 제약조건 추가
ALTER TABLE `audit_log` 
ADD CONSTRAINT `fk_audit_log_admin_member` 
    FOREIGN KEY (`admin_member_id`) 
    REFERENCES `adminMemberShip` (`memberShipSid`) 
    ON DELETE SET NULL 
    ON UPDATE CASCADE;

-- ============================================
-- 확인
-- ============================================
-- DESCRIBE audit_log;
-- SHOW CREATE TABLE audit_log;



