-- ============================================
-- Inde Backend 전체 테이블 생성 스크립트
-- ============================================
-- 실행 방법:
-- mysql -u root -p inde < CREATE_ALL_TABLES.sql
-- 또는
-- mysql -u root -p
-- USE inde;
-- source /path/to/CREATE_ALL_TABLES.sql;
-- ============================================

-- 데이터베이스 선택 (필요시)
-- USE inde;

-- ============================================
-- 1. account 테이블 (사용자 계정)
-- ============================================
CREATE TABLE IF NOT EXISTS `account` (
    `id` CHAR(36) NOT NULL COMMENT 'UUID (고유 식별자)',
    `email` VARCHAR(255) NOT NULL COMMENT '이메일 주소',
    `phone` VARCHAR(20) NULL DEFAULT NULL COMMENT '전화번호',
    `birth_date` DATE NULL DEFAULT NULL COMMENT '생년월일',
    `name` VARCHAR(100) NULL DEFAULT '' COMMENT '이름',
    `password` VARCHAR(128) NOT NULL COMMENT '비밀번호 (해시화)',
    `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '활성화 여부',
    `is_staff` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '스태프 여부',
    `is_superuser` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '슈퍼유저 여부',
    `email_verified` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '이메일 인증 여부',
    `email_verified_at` DATETIME NULL DEFAULT NULL COMMENT '이메일 인증일시',
    `last_login` DATETIME NULL DEFAULT NULL COMMENT '마지막 로그인 시간',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일시',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_email` (`email`),
    KEY `idx_is_active` (`is_active`),
    KEY `idx_is_staff` (`is_staff`),
    KEY `idx_created_at` (`created_at`)
    
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci 
  COMMENT='사용자 계정 테이블';

-- ============================================
-- 2. audit_log 테이블 (감사 로그)
-- ============================================
CREATE TABLE IF NOT EXISTS `audit_log` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유 식별자',
    `user_id` CHAR(15) NULL DEFAULT NULL COMMENT '사용자 ID (Account.id 또는 AdminMemberShip.memberShipSid)',
    `site_slug` VARCHAR(50) NULL DEFAULT '' COMMENT '사이트 식별자',
    `action` VARCHAR(20) NOT NULL COMMENT '액션 타입 (login, logout, create, read, update, delete)',
    `resource` VARCHAR(100) NULL DEFAULT '' COMMENT '리소스 타입',
    `resource_id` VARCHAR(100) NULL DEFAULT NULL COMMENT '리소스 ID',
    `ip_address` VARCHAR(45) NULL DEFAULT NULL COMMENT 'IP 주소 (IPv4/IPv6)',
    `user_agent` TEXT NULL COMMENT 'User Agent',
    `details` JSON NULL COMMENT '상세 정보 (JSON)',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
    
    PRIMARY KEY (`id`),
    KEY `idx_user_id_created` (`user_id`, `created_at`),
    KEY `idx_site_action_created` (`site_slug`, `action`, `created_at`),
    KEY `idx_resource` (`resource`, `resource_id`),
    KEY `idx_ip_address` (`ip_address`),
    KEY `idx_created_at` (`created_at`)
    
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci 
  COMMENT='감사 로그 테이블';

-- ============================================
-- 3. adminMemberShip 테이블 (관리자 회원)
-- ============================================
CREATE TABLE IF NOT EXISTS `adminMemberShip` (
    `memberShipSid` CHAR(15) NOT NULL COMMENT '회원 고유 식별자 (시퀀스 코드)',
    `memberShipId` VARCHAR(50) NOT NULL COMMENT '회원 ID (로그인용)',
    `memberShipPassword` VARCHAR(255) NOT NULL COMMENT '비밀번호 (해시화됨)',
    `memberShipName` VARCHAR(100) NOT NULL COMMENT '이름',
    `memberShipEmail` VARCHAR(255) NOT NULL COMMENT '이메일 주소',
    `memberShipPhone` VARCHAR(20) NULL DEFAULT NULL COMMENT '전화번호',
    `memberShipLevel` INT NOT NULL DEFAULT 1 COMMENT '회원 레벨 (1~10)',
    `is_admin` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '관리자 여부 (0: 일반, 1: 관리자)',
    `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '활성화 여부 (0: 비활성, 1: 활성)',
    `last_login` DATETIME NULL DEFAULT NULL COMMENT '마지막 로그인 시간',
    `login_count` INT NOT NULL DEFAULT 0 COMMENT '로그인 횟수',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일시',
    
    PRIMARY KEY (`memberShipSid`),
    UNIQUE KEY `uk_memberShipId` (`memberShipId`),
    UNIQUE KEY `uk_memberShipEmail` (`memberShipEmail`),
    KEY `idx_is_active_admin` (`is_active`, `is_admin`),
    KEY `idx_created_at` (`created_at`),
    KEY `idx_memberShipLevel` (`memberShipLevel`)
    
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci 
  COMMENT='관리자 페이지 회원 정보 테이블';

-- ============================================
-- 4. publicMemberShip 테이블 (공개 사이트 회원)
-- ============================================
-- 일반 회원가입: email + password, joined_via='LOCAL'
-- 소셜 로그인(추후): password=NULL, joined_via='KAKAO'|'NAVER'|'GOOGLE'
-- ============================================
CREATE TABLE IF NOT EXISTS `publicMemberShip` (
    `member_sid` INT NOT NULL AUTO_INCREMENT COMMENT '회원 SID (1부터 자동 증가, PK)',
    `email` VARCHAR(254) NOT NULL COMMENT '이메일 주소',
    `password` VARCHAR(255) NULL DEFAULT NULL COMMENT '비밀번호 (해시, 소셜 전용 가입 시 NULL)',
    `name` VARCHAR(100) NOT NULL COMMENT '이름',
    `nickname` VARCHAR(100) NOT NULL COMMENT '닉네임',
    `phone` VARCHAR(20) NOT NULL COMMENT '휴대폰 번호',
    `position` VARCHAR(100) NULL DEFAULT NULL COMMENT '직분',
    `birth_year` INT NULL DEFAULT NULL COMMENT '출생년도 (1900~2100)',
    `birth_month` INT NULL DEFAULT NULL COMMENT '출생월 (1~12)',
    `birth_day` INT NULL DEFAULT NULL COMMENT '출생일 (1~31)',
    `region_type` VARCHAR(10) NULL DEFAULT NULL COMMENT '지역 타입 (DOMESTIC, FOREIGN)',
    `region_domestic` VARCHAR(100) NULL DEFAULT NULL COMMENT '국내 지역',
    `region_foreign` VARCHAR(100) NULL DEFAULT NULL COMMENT '해외 지역',
    `joined_via` VARCHAR(10) NOT NULL DEFAULT 'LOCAL' COMMENT '가입 경로 (LOCAL, KAKAO, NAVER, GOOGLE)',
    `sns_provider_uid` VARCHAR(255) NULL DEFAULT NULL COMMENT 'SNS 제공자 고유 회원 코드 (KAKAO/NAVER/GOOGLE 가입 시)',
    `newsletter_agree` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '뉴스레터 수신 동의',
    `profile_completed` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '프로필 완료 여부',
    `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '활성화 여부',
    `last_login` DATETIME NULL DEFAULT NULL COMMENT '마지막 로그인',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일시',

    PRIMARY KEY (`member_sid`),
    UNIQUE KEY `uk_email` (`email`),
    KEY `idx_email` (`email`),
    KEY `idx_phone` (`phone`),
    KEY `idx_joined_via` (`joined_via`),
    KEY `idx_is_active` (`is_active`),
    KEY `idx_created_at` (`created_at`),
    KEY `idx_sns_provider_uid` (`sns_provider_uid`)

) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='공개 사이트 회원 (일반/소셜 가입)';

-- ============================================
-- 5. seqMaster 테이블 (시퀀스 마스터)
-- ============================================
CREATE TABLE IF NOT EXISTS `seqMaster` (
    `seqSid` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '시퀀스 SID',
    `seq_top` VARCHAR(3) NOT NULL DEFAULT '' COMMENT '시퀀스 접두사',
    `seq_tablename` VARCHAR(60) NOT NULL DEFAULT '' COMMENT '테이블명',
    `seq_seatcount` INT(10) NULL DEFAULT NULL COMMENT '시퀀스 자리수',
    `seq_value` INT(10) NULL DEFAULT NULL COMMENT '시퀀스 값',
    `seq_yyyy` VARCHAR(4) NULL DEFAULT NULL COMMENT '년도 (4자리)',
    `seq_yyc` VARCHAR(2) NULL DEFAULT NULL COMMENT '밀레니엄 코드',
    `seq_yy` VARCHAR(2) NULL DEFAULT NULL COMMENT '년도 (2자리)',
    `seq_mm` VARCHAR(2) NULL DEFAULT NULL COMMENT '월',
    `seq_dd` VARCHAR(2) NULL DEFAULT NULL COMMENT '일',
    
    PRIMARY KEY (`seqSid`),
    KEY `idx_seq_tablename` (`seq_tablename`)
    
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb3 
  COLLATE=utf8mb3_general_ci 
  COMMENT='시퀀스 마스터 테이블';

-- ============================================
-- adminMemberShip 시퀀스 초기 데이터 삽입
-- ============================================
INSERT INTO `seqMaster` (
    `seq_top`,
    `seq_tablename`,
    `seq_seatcount`,
    `seq_value`,
    `seq_yyyy`,
    `seq_yy`,
    `seq_yyc`,
    `seq_mm`,
    `seq_dd`
) VALUES (
    'ADM',
    'adminMemberShip',
    20,
    0,
    NULL,
    NULL,
    'B',
    NULL,
    NULL
) ON DUPLICATE KEY UPDATE `seq_tablename` = `seq_tablename`;

-- ============================================
-- 완료 메시지
-- ============================================
SELECT '테이블 생성이 완료되었습니다!' AS message;
SELECT '생성된 테이블:' AS info;
SHOW TABLES LIKE '%account%';
SHOW TABLES LIKE '%audit%';
SHOW TABLES LIKE '%adminMember%';
SHOW TABLES LIKE '%publicMember%';
SHOW TABLES LIKE '%seqMaster%';

