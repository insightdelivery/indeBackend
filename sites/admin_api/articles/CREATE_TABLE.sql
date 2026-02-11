-- ============================================
-- Article 테이블 생성
-- ============================================
CREATE TABLE IF NOT EXISTS `article` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '아티클 ID',
    `title` VARCHAR(500) NOT NULL COMMENT '제목',
    `subtitle` VARCHAR(500) NULL DEFAULT NULL COMMENT '부제목',
    `content` MEDIUMTEXT NOT NULL COMMENT '본문 내용',
    `thumbnail` VARCHAR(500) NULL DEFAULT NULL COMMENT '썸네일 URL',
    `category` VARCHAR(50) NOT NULL COMMENT '카테고리 (sysCodeSid)',
    `author` VARCHAR(100) NOT NULL COMMENT '작성자',
    `authorAffiliation` VARCHAR(200) NULL DEFAULT NULL COMMENT '작성자 소속',
    `visibility` VARCHAR(50) NOT NULL COMMENT '공개 범위 (sysCodeSid)',
    `status` VARCHAR(50) NOT NULL DEFAULT 'draft' COMMENT '발행 상태 (sysCodeSid)',
    `isEditorPick` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '에디터 추천 (0: 아니오, 1: 예)',
    `viewCount` INT NOT NULL DEFAULT 0 COMMENT '조회수',
    `rating` FLOAT NULL DEFAULT NULL COMMENT '평점',
    `commentCount` INT NOT NULL DEFAULT 0 COMMENT '댓글 수',
    `highlightCount` INT NOT NULL DEFAULT 0 COMMENT '하이라이트 수',
    `questionCount` INT NOT NULL DEFAULT 0 COMMENT '질문 수',
    `tags` JSON NULL DEFAULT NULL COMMENT '태그 목록',
    `questions` JSON NULL DEFAULT NULL COMMENT '질문 목록',
    `previewLength` INT NULL DEFAULT 50 COMMENT '미리보기 길이',
    `scheduledAt` DATETIME NULL DEFAULT NULL COMMENT '예약 발행 일시',
    `deletedAt` DATETIME NULL DEFAULT NULL COMMENT '삭제 일시',
    `deletedBy` VARCHAR(100) NULL DEFAULT NULL COMMENT '삭제자',
    `createdAt` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성 일시',
    `updatedAt` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정 일시',
    
    PRIMARY KEY (`id`),
    KEY `idx_article_category` (`category`),
    KEY `idx_article_status` (`status`),
    KEY `idx_article_visibility` (`visibility`),
    KEY `idx_article_created` (`createdAt`),
    KEY `idx_article_deleted` (`deletedAt`),
    KEY `idx_article_author` (`author`)
    
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci 
  COMMENT='아티클 관리 테이블';

