"""
공개 API 시리얼라이저
"""
from rest_framework import serializers
from sites.public_api.models import PublicMemberShip


class RegisterSerializer(serializers.Serializer):
    """회원 가입 요청 (일반 가입)"""
    email = serializers.EmailField(required=True, help_text='이메일 주소')
    password = serializers.CharField(required=True, write_only=True, min_length=8, help_text='비밀번호 (최소 8자)')
    password_confirm = serializers.CharField(required=True, write_only=True, help_text='비밀번호 확인')
    name = serializers.CharField(required=True, max_length=100, help_text='이름')
    nickname = serializers.CharField(required=True, max_length=100, help_text='닉네임')
    phone = serializers.CharField(required=True, max_length=20, help_text='휴대폰 번호')
    position = serializers.CharField(required=False, allow_blank=True, max_length=100, help_text='직분')
    birth_year = serializers.IntegerField(required=False, allow_null=True, min_value=1900, max_value=2100)
    birth_month = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=12)
    birth_day = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=31)
    region = serializers.CharField(required=False, allow_blank=True, max_length=100, help_text='지역(국내)')
    is_overseas = serializers.BooleanField(required=False, default=False, help_text='해외 거주 여부')
    newsletter_agree = serializers.BooleanField(required=False, default=False)

    def validate(self, data):
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({'password_confirm': '비밀번호가 일치하지 않습니다.'})
        return data

    def validate_email(self, value):
        if PublicMemberShip.objects.filter(email=value).exists():
            raise serializers.ValidationError('이미 사용 중인 이메일입니다.')
        return value


class LoginSerializer(serializers.Serializer):
    """로그인 요청"""
    email = serializers.EmailField(required=True, help_text='이메일 주소')
    password = serializers.CharField(required=True, write_only=True, help_text='비밀번호')
