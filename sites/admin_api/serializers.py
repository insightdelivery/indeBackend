"""
관리자 API 시리얼라이저
"""
from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    """로그인 요청 시리얼라이저"""
    email = serializers.EmailField(required=True, help_text='이메일 주소')
    password = serializers.CharField(required=True, write_only=True, help_text='비밀번호')


class RefreshTokenSerializer(serializers.Serializer):
    """토큰 갱신 요청 시리얼라이저"""
    refresh_token = serializers.CharField(required=True, help_text='Refresh Token')
