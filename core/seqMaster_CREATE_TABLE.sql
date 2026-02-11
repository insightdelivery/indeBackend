-- ============================================
-- seqMaster 테이블 생성 스크립트
-- ============================================
-- 데이터베이스: MariaDB / MySQL
-- 테이블명: seqMaster
-- 설명: 시퀀스 코드 생성을 관리하는 마스터 테이블
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
    'ADM',              -- 접두사
    'adminMemberShip',  -- 테이블명
    20,                 -- 전체 자리수 (예: ADM20260122B0001 = 20자)
    0,                  -- 초기 시퀀스 값
    NULL,               -- 년도 4자리 (NULL이면 사용 안함)
    NULL,               -- 년도 2자리 (NULL이면 사용 안함)
    'B',                -- 밀레니엄 코드 (B=2000년대)
    NULL,               -- 월 (NULL이면 사용 안함)
    NULL                -- 일 (NULL이면 사용 안함)
) ON DUPLICATE KEY UPDATE `seq_tablename` = `seq_tablename`;

-- ============================================
-- 시퀀스 설정 예시
-- ============================================
-- 
-- 예시 1: ADM20260122B0001 형식
-- seq_top: 'ADM'
-- seq_yyyy: '2026' (사용)
-- seq_mm: '01' (사용)
-- seq_dd: '22' (사용)
-- seq_yyc: 'B' (사용)
-- seq_seatcount: 20
-- 결과: ADM20260122B0001
--
-- 예시 2: ADM260122B0001 형식
-- seq_top: 'ADM'
-- seq_yy: '26' (사용)
-- seq_mm: '01' (사용)
-- seq_dd: '22' (사용)
-- seq_yyc: 'B' (사용)
-- seq_seatcount: 15
-- 결과: ADM260122B0001
--
-- 예시 3: ADM2026B0001 형식
-- seq_top: 'ADM'
-- seq_yyyy: '2026' (사용)
-- seq_yyc: 'B' (사용)
-- seq_seatcount: 12
-- 결과: ADM2026B0001
--
-- ============================================
-- 테이블 구조 확인
-- ============================================
-- DESCRIBE seqMaster;
-- SELECT * FROM seqMaster WHERE seq_tablename = 'adminMemberShip';



