-- ============================================
-- video 테이블 생성 스크립트
-- 비디오/세미나 콘텐츠 관리 테이블
-- ============================================
-- 실행 방법:
-- mysql -u root -p inde < CREATE_TABLE.sql
-- 또는
-- mysql -u root -p
-- USE inde;
-- source /path/to/CREATE_TABLE.sql;
-- ============================================

-- 데이터베이스 선택 (필요시)
-- USE inde;

-- ============================================
-- video 테이블 (비디오/세미나 콘텐츠)
-- ============================================
CREATE TABLE IF NOT EXISTS `video` (
    -- 기본 정보
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '비디오 ID',
    `contentType` VARCHAR(20) NOT NULL COMMENT '콘텐츠 타입 (video: 비디오, seminar: 세미나)',
    `category` VARCHAR(50) NOT NULL COMMENT '카테고리 (sysCodeSid)',
    
    -- 제목 및 설명
    `title` VARCHAR(500) NOT NULL COMMENT '제목',
    `subtitle` VARCHAR(500) NULL DEFAULT NULL COMMENT '부제목',
    `body` TEXT NULL DEFAULT NULL COMMENT '본문 설명',
    
    -- 미디어
    `videoStreamId` VARCHAR(100) NULL DEFAULT NULL COMMENT 'Cloudflare Stream 비디오 ID',
    `videoUrl` VARCHAR(1000) NULL DEFAULT NULL COMMENT '영상 URL (YouTube/Vimeo URL, 레거시 지원)',
    `thumbnail` VARCHAR(500) NULL DEFAULT NULL COMMENT '썸네일 URL',
    
    -- 인물 정보
    `speaker` VARCHAR(200) NULL DEFAULT NULL COMMENT '출연자/강사',
    `speakerAffiliation` VARCHAR(200) NULL DEFAULT NULL COMMENT '출연자 소속',
    `editor` VARCHAR(100) NULL DEFAULT NULL COMMENT '에디터',
    `director` VARCHAR(100) NULL DEFAULT NULL COMMENT '디렉터',
    
    -- 공개 설정
    `visibility` VARCHAR(50) NOT NULL COMMENT '공개 범위 (sysCodeSid)',
    `status` VARCHAR(50) NOT NULL DEFAULT 'private' COMMENT '상태 (public: 공개, private: 비공개, scheduled: 예약, deleted: 삭제대기)',
    
    -- 배지 및 기능
    `isNewBadge` TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'NEW 배지 표시 (0: 비표시, 1: 표시)',
    `isMaterialBadge` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '자료 배지 표시 (0: 비표시, 1: 표시)',
    `allowRating` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '별점 허용 (0: 비허용, 1: 허용)',
    `allowComment` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '댓글 허용 (0: 비허용, 1: 허용)',
    
    -- 통계 정보
    `viewCount` INT NOT NULL DEFAULT 0 COMMENT '조회수',
    `rating` DECIMAL(3, 2) NULL DEFAULT NULL COMMENT '평점 (0.00 ~ 5.00)',
    `commentCount` INT NOT NULL DEFAULT 0 COMMENT '댓글 수',
    
    -- 추가 정보 (JSON)
    `tags` JSON NULL DEFAULT NULL COMMENT '태그 목록 (JSON 배열)',
    `questions` JSON NULL DEFAULT NULL COMMENT '적용 질문 (Q1, Q2) (JSON 배열)',
    `attachments` JSON NULL DEFAULT NULL COMMENT '첨부파일 목록 (강의 자료) (JSON 배열)',
    
    -- 예약 발행
    `scheduledAt` DATETIME NULL DEFAULT NULL COMMENT '예약 발행 일시',
    
    -- 삭제 정보 (소프트 삭제)
    `deletedAt` DATETIME NULL DEFAULT NULL COMMENT '삭제 일시',
    `deletedBy` VARCHAR(100) NULL DEFAULT NULL COMMENT '삭제자',
    
    -- 타임스탬프
    `createdAt` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성 일시',
    `updatedAt` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정 일시',
    
    PRIMARY KEY (`id`),
    KEY `idx_video_content_type` (`contentType`),
    KEY `idx_video_category` (`category`),
    KEY `idx_video_status` (`status`),
    KEY `idx_video_visibility` (`visibility`),
    KEY `idx_video_created` (`createdAt`),
    KEY `idx_video_deleted` (`deletedAt`),
    KEY `idx_video_speaker` (`speaker`),
    KEY `idx_video_editor` (`editor`)
    
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci 
  COMMENT='비디오/세미나 콘텐츠 관리 테이블';

-- ============================================
-- 완료 메시지
-- ============================================
SELECT 'video 테이블 생성이 완료되었습니다!' AS message;
SHOW CREATE TABLE `video`;

