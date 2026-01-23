-- ============================================
-- adminMemberShip 테이블 생성 스크립트
-- ============================================
-- 데이터베이스: MariaDB / MySQL
-- 테이블명: adminMemberShip
-- 설명: 관리자 페이지 회원 정보를 저장하는 테이블
-- ============================================

CREATE TABLE IF NOT EXISTS `adminMemberShip` (
    -- 기본 식별자
    `memberShipSid` CHAR(15) NOT NULL COMMENT '회원 고유 식별자 (시퀀스 코드)',
    
    -- 로그인 정보
    `memberShipId` VARCHAR(50) NOT NULL COMMENT '회원 ID (로그인용)',
    `memberShipPassword` VARCHAR(255) NOT NULL COMMENT '비밀번호 (해시화됨)',
    
    -- 개인 정보
    `memberShipName` VARCHAR(100) NOT NULL COMMENT '이름',
    `memberShipEmail` VARCHAR(255) NOT NULL COMMENT '이메일 주소',
    `memberShipPhone` VARCHAR(20) NULL DEFAULT NULL COMMENT '전화번호',
    
    -- 권한 및 레벨
    `memberShipLevel` INT NOT NULL DEFAULT 1 COMMENT '회원 레벨 (1~10)',
    `is_admin` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '관리자 여부 (0: 일반, 1: 관리자)',
    `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '활성화 여부 (0: 비활성, 1: 활성)',
    
    -- 로그인 정보
    `last_login` DATETIME NULL DEFAULT NULL COMMENT '마지막 로그인 시간',
    `login_count` INT NOT NULL DEFAULT 0 COMMENT '로그인 횟수',
    
    -- 타임스탬프
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일시',
    
    -- Primary Key
    PRIMARY KEY (`memberShipSid`),
    
    -- Unique 제약조건
    UNIQUE KEY `uk_memberShipId` (`memberShipId`),
    UNIQUE KEY `uk_memberShipEmail` (`memberShipEmail`),
    
    -- 인덱스
    KEY `idx_is_active_admin` (`is_active`, `is_admin`),
    KEY `idx_created_at` (`created_at`),
    KEY `idx_memberShipLevel` (`memberShipLevel`)
    
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci 
  COMMENT='관리자 페이지 회원 정보 테이블';

-- ============================================
-- 테이블 구조 확인
-- ============================================
-- DESCRIBE adminMemberShip;
-- SHOW CREATE TABLE adminMemberShip;

-- ============================================
-- 샘플 데이터 삽입 (선택사항)
-- ============================================
-- INSERT INTO `adminMemberShip` (
--     `memberShipSid`,
--     `memberShipId`,
--     `memberShipPassword`,
--     `memberShipName`,
--     `memberShipEmail`,
--     `memberShipLevel`,
--     `is_admin`,
--     `is_active`
-- ) VALUES (
--     UUID(),
--     'admin',
--     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqB5q5q5qO',  -- 'admin123' 해시값 (실제로는 Django의 make_password 사용)
--     '관리자',
--     'admin@example.com',
--     10,
--     1,
--     1
-- );

-- ============================================
-- 참고사항
-- ============================================
-- 1. memberShipSid는 시퀀스 코드 형식 (CHAR(15))
-- 2. memberShipPassword는 Django의 make_password()로 해시화된 값 저장
-- 3. is_admin, is_active는 TINYINT(1)로 저장 (0 또는 1)
-- 4. created_at, updated_at은 자동으로 타임스탬프 관리
-- 5. 인덱스는 조회 성능 최적화를 위해 설정됨

