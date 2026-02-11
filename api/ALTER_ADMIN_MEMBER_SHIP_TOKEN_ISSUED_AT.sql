-- ============================================
-- adminMemberShip 테이블에 token_issued_at 컬럼 추가
-- ============================================
-- 로그아웃 후 토큰 무효화를 추적하기 위한 필드
-- ============================================

-- token_issued_at 컬럼 추가
ALTER TABLE `adminMemberShip` 
ADD COLUMN `token_issued_at` DATETIME NULL DEFAULT NULL COMMENT '마지막 토큰 발급 시간 (로그아웃 후 토큰 무효화 추적용)' 
AFTER `login_count`;

-- ============================================
-- 확인
-- ============================================
-- DESCRIBE adminMemberShip;
-- SHOW CREATE TABLE adminMemberShip;



