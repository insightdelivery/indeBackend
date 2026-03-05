-- public_api 0007: publicMemberShip 탈퇴(Soft Delete) 필드 추가
-- Django migrate 없이 MySQL에서 수동 적용할 때 사용.
-- 컬럼이 이미 있으면 해당 ALTER는 스킵하고 다음만 실행하면 됨.
-- 모두 적용 후 3) 실행.

-- 1) 컬럼 추가 (컬럼별로 실행, 이미 있으면 에러 시 해당 줄만 스킵)
ALTER TABLE publicMemberShip ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' COMMENT '회원 상태';
ALTER TABLE publicMemberShip ADD COLUMN withdraw_reason TEXT NULL COMMENT '탈퇴 사유';
ALTER TABLE publicMemberShip ADD COLUMN withdraw_detail_reason TEXT NULL COMMENT '탈퇴 상세 사유';
ALTER TABLE publicMemberShip ADD COLUMN withdraw_requested_at DATETIME NULL COMMENT '탈퇴 요청일시';
ALTER TABLE publicMemberShip ADD COLUMN withdraw_completed_at DATETIME NULL COMMENT '탈퇴 완료일시';
ALTER TABLE publicMemberShip ADD COLUMN withdraw_ip VARCHAR(45) NULL COMMENT '탈퇴 요청 IP';
ALTER TABLE publicMemberShip ADD COLUMN withdraw_user_agent TEXT NULL COMMENT '탈퇴 요청 User-Agent';

-- 2) status 인덱스 (이미 있으면 에러 시 스킵)
CREATE INDEX publicMemberShip_status_idx ON publicMemberShip (status);

-- 3) 마이그레이션 기록 (Django가 적용된 것으로 인식하도록)
INSERT INTO django_migrations (app, name, applied) VALUES ('public_api', '0007_publicmembership_withdraw_fields', NOW());
