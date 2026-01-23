-- ============================================
-- Inde Backend 데이터베이스 테이블 생성 스크립트
-- ============================================
-- 데이터베이스: MariaDB / MySQL
-- 문자셋: utf8mb4
-- 엔진: InnoDB
-- ============================================

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
-- 4. Django 기본 테이블 (필요한 경우)
-- ============================================

-- django_migrations 테이블 (마이그레이션 이력)
CREATE TABLE IF NOT EXISTS `django_migrations` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `app` VARCHAR(255) NOT NULL,
    `name` VARCHAR(255) NOT NULL,
    `applied` DATETIME(6) NOT NULL,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci;

-- django_content_type 테이블 (컨텐츠 타입)
CREATE TABLE IF NOT EXISTS `django_content_type` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `app_label` VARCHAR(100) NOT NULL,
    `model` VARCHAR(100) NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`, `model`)
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci;

-- django_session 테이블 (세션)
CREATE TABLE IF NOT EXISTS `django_session` (
    `session_key` VARCHAR(40) NOT NULL,
    `session_data` LONGTEXT NOT NULL,
    `expire_date` DATETIME(6) NOT NULL,
    PRIMARY KEY (`session_key`),
    KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci;

-- auth_permission 테이블 (권한)
CREATE TABLE IF NOT EXISTS `auth_permission` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(255) NOT NULL,
    `content_type_id` INT NOT NULL,
    `codename` VARCHAR(100) NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`, `codename`),
    CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` 
        FOREIGN KEY (`content_type_id`) 
        REFERENCES `django_content_type` (`id`) 
        ON DELETE CASCADE
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci;

-- account_user_permissions 테이블 (사용자 권한 연결)
CREATE TABLE IF NOT EXISTS `account_user_permissions` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `account_id` CHAR(36) NOT NULL,
    `permission_id` INT NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `account_user_permissions_account_id_permission_id_xxx` (`account_id`, `permission_id`),
    KEY `account_user_permissions_permission_id_xxx` (`permission_id`),
    CONSTRAINT `account_user_permissions_account_id_xxx_fk` 
        FOREIGN KEY (`account_id`) 
        REFERENCES `account` (`id`) 
        ON DELETE CASCADE,
    CONSTRAINT `account_user_permissions_permission_id_xxx_fk` 
        FOREIGN KEY (`permission_id`) 
        REFERENCES `auth_permission` (`id`) 
        ON DELETE CASCADE
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci;

-- account_user_groups 테이블 (사용자 그룹 연결)
CREATE TABLE IF NOT EXISTS `account_user_groups` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `account_id` CHAR(36) NOT NULL,
    `group_id` INT NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `account_user_groups_account_id_group_id_xxx` (`account_id`, `group_id`),
    KEY `account_user_groups_group_id_xxx` (`group_id`),
    CONSTRAINT `account_user_groups_account_id_xxx_fk` 
        FOREIGN KEY (`account_id`) 
        REFERENCES `account` (`id`) 
        ON DELETE CASCADE,
    CONSTRAINT `account_user_groups_group_id_xxx_fk` 
        FOREIGN KEY (`group_id`) 
        REFERENCES `auth_group` (`id`) 
        ON DELETE CASCADE
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci;

-- auth_group 테이블 (그룹)
CREATE TABLE IF NOT EXISTS `auth_group` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(150) NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci;

-- auth_group_permissions 테이블 (그룹 권한 연결)
CREATE TABLE IF NOT EXISTS `auth_group_permissions` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `group_id` INT NOT NULL,
    `permission_id` INT NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`, `permission_id`),
    KEY `auth_group_permissions_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
    CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` 
        FOREIGN KEY (`group_id`) 
        REFERENCES `auth_group` (`id`) 
        ON DELETE CASCADE,
    CONSTRAINT `auth_group_permissions_permission_id_84c5c92e_fk_auth_perm` 
        FOREIGN KEY (`permission_id`) 
        REFERENCES `auth_permission` (`id`) 
        ON DELETE CASCADE
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 테이블 생성 확인
-- ============================================
-- 다음 명령어로 테이블이 정상적으로 생성되었는지 확인하세요:
-- 
-- SHOW TABLES;
-- DESCRIBE account;
-- DESCRIBE audit_log;
-- DESCRIBE adminMemberShip;
-- 
-- ============================================
-- 참고사항
-- ============================================
-- 1. 모든 테이블은 utf8mb4 문자셋 사용 (이모지 지원)
-- 2. InnoDB 엔진 사용 (트랜잭션 지원)
-- 3. 외래키 제약조건 설정 (데이터 무결성 보장)
-- 4. 인덱스 최적화 (조회 성능 향상)
-- 5. UUID는 CHAR(36) 형식으로 저장
-- 6. 비밀번호는 Django의 make_password()로 해시화하여 저장
-- 
-- ============================================

