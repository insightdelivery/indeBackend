-- publicMemberShip 테이블에 is_staff 컬럼 추가 (공지/FAQ/문의 관리자 권한용)
-- 실행: mysql -u root -p inde < ADD_IS_STAFF_TO_PUBLIC_MEMBERSHIP.sql

ALTER TABLE `publicMemberShip`
  ADD COLUMN `is_staff` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '관리자 여부';
