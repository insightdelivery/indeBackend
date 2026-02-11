#!/usr/bin/env python3
"""
adminMemberShip 테이블에 token_issued_at 컬럼 추가 스크립트
"""
import os
import sys
import django

# Django 설정
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.db import connection

def add_token_issued_at_column():
    """token_issued_at 컬럼 추가"""
    with connection.cursor() as cursor:
        try:
            # 컬럼이 이미 존재하는지 확인
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'adminMemberShip'
                  AND COLUMN_NAME = 'token_issued_at'
            """)
            exists = cursor.fetchone()[0] > 0
            
            if exists:
                print("✓ token_issued_at 컬럼이 이미 존재합니다.")
                return
            
            # 컬럼 추가
            cursor.execute("""
                ALTER TABLE `adminMemberShip` 
                ADD COLUMN `token_issued_at` DATETIME NULL DEFAULT NULL 
                COMMENT '마지막 토큰 발급 시간 (로그아웃 후 토큰 무효화 추적용)' 
                AFTER `login_count`
            """)
            print("✓ token_issued_at 컬럼이 성공적으로 추가되었습니다.")
            
        except Exception as e:
            print(f"✗ 오류 발생: {str(e)}")
            sys.exit(1)

if __name__ == '__main__':
    add_token_issued_at_column()



