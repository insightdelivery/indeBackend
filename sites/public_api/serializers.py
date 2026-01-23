"""
공개 API 시리얼라이저
"""
from rest_framework import serializers
from core.models import Account


class RegisterSerializer(serializers.Serializer):
    """회원 가입 요청 시리얼라이저"""
    email = serializers.EmailField(required=True, help_text='이메일 주소')
    password = serializers.CharField(required=True, write_only=True, min_length=8, help_text='비밀번호 (최소 8자)')
    password_confirm = serializers.CharField(required=True, write_only=True, help_text='비밀번호 확인')
    name = serializers.CharField(required=True, max_length=100, help_text='이름')
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20, help_text='전화번호')
    birth_date = serializers.DateField(required=False, allow_null=True, help_text='생년월일 (YYYY-MM-DD)')
    
    def validate(self, data):
        """비밀번호 일치 확인"""
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': '비밀번호가 일치하지 않습니다.'
            })
        return data
    
    def validate_email(self, value):
        """이메일 중복 확인"""
        if Account.objects.filter(email=value).exists():
            raise serializers.ValidationError('이미 사용 중인 이메일입니다.')
        return value


class LoginSerializer(serializers.Serializer):
    """로그인 요청 시리얼라이저"""
    email = serializers.EmailField(required=True, help_text='이메일 주소')
    password = serializers.CharField(required=True, write_only=True, help_text='비밀번호')
