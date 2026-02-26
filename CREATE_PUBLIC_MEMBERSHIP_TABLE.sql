-- ============================================
-- publicMemberShip 테이블만 생성
-- ============================================
-- 실행: mysql -u root -p inde < CREATE_PUBLIC_MEMBERSHIP_TABLE.sql
-- 또는: mysql -u root -p → USE inde; → source /path/to/CREATE_PUBLIC_MEMBERSHIP_TABLE.sql;
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

SELECT 'publicMemberShip 테이블 생성 완료.' AS message;
