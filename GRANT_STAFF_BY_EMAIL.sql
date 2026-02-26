-- ============================================
-- 공지/FAQ/문의 관리자 권한 부여 (is_staff=1)
-- ============================================
-- 사용법: 아래 이메일을 실제 관리자 이메일로 바꾼 뒤 실행
-- mysql -u inde -p inde -e "UPDATE publicMemberShip SET is_staff = 1 WHERE email = 'admin@example.com';"
-- 또는 MySQL 클라이언트에서:
-- USE inde;
-- UPDATE publicMemberShip SET is_staff = 1 WHERE email = '관리자이메일@example.com';
-- ============================================

-- 예: 특정 이메일 한 명만 관리자로 설정
-- UPDATE publicMemberShip SET is_staff = 1 WHERE email = 'indemgz@gmail.com';

-- 예: member_sid로 지정 (이메일 대신 SID로 설정할 때)
-- UPDATE publicMemberShip SET is_staff = 1 WHERE member_sid = 1;

SELECT '아래 UPDATE 문에서 이메일을 수정한 뒤 실행하세요.' AS message;
-- UPDATE publicMemberShip SET is_staff = 1 WHERE email = '여기에_관리자_이메일@example.com';
