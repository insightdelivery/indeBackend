-- ============================================
-- 공지/FAQ/1:1 문의 게시판 테이블 생성
-- ============================================
-- 실행: mysql -u inde -p inde < CREATE_BOARD_TABLES.sql
-- 전제: publicMemberShip 테이블이 있어야 함 (inquiry.user_id FK)
-- ============================================

-- 1. notice_notice (공지사항)
CREATE TABLE IF NOT EXISTS `notice_notice` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `title` VARCHAR(255) NOT NULL,
    `content` LONGTEXT NOT NULL,
    `is_pinned` TINYINT(1) NOT NULL DEFAULT 0,
    `view_count` INT NOT NULL DEFAULT 0,
    `created_at` DATETIME(6) NOT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_is_pinned_created` (`is_pinned`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. faq_faq (FAQ)
CREATE TABLE IF NOT EXISTS `faq_faq` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `question` VARCHAR(255) NOT NULL,
    `answer` LONGTEXT NOT NULL,
    `order` INT NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`),
    KEY `idx_order` (`order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. inquiry_inquiry (1:1 문의) — publicMemberShip.member_sid 참조
CREATE TABLE IF NOT EXISTS `inquiry_inquiry` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `title` VARCHAR(255) NOT NULL,
    `content` LONGTEXT NOT NULL,
    `answer` LONGTEXT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'waiting',
    `created_at` DATETIME(6) NOT NULL,
    `user_id` INT NOT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_created_at` (`created_at`),
    CONSTRAINT `fk_inquiry_user` FOREIGN KEY (`user_id`) REFERENCES `publicMemberShip` (`member_sid`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SELECT 'Board tables (notice_notice, faq_faq, inquiry_inquiry) created.' AS message;
