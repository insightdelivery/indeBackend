"""
관리자 회원 API 시리얼라이저
"""
from rest_framework import serializers
from api.models import AdminMemberShip


class AdminRegisterSerializer(serializers.Serializer):
    """관리자 회원 가입 요청 시리얼라이저"""
    memberShipId = serializers.CharField(required=True, max_length=50, help_text='회원 ID')
    password = serializers.CharField(required=True, write_only=True, min_length=8, help_text='비밀번호 (최소 8자)')
    password_confirm = serializers.CharField(required=True, write_only=True, help_text='비밀번호 확인')
    memberShipName = serializers.CharField(required=True, max_length=100, help_text='이름')
    memberShipEmail = serializers.EmailField(required=True, help_text='이메일 주소')
    memberShipPhone = serializers.CharField(required=False, allow_blank=True, max_length=20, help_text='전화번호')
    memberShipLevel = serializers.IntegerField(required=False, default=1, help_text='회원 레벨 (기본값: 1)')
    is_admin = serializers.BooleanField(required=False, default=False, help_text='관리자 여부')
    
    def validate(self, data):
        """비밀번호 일치 확인"""
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': '비밀번호가 일치하지 않습니다.'
            })
        return data
    
    def validate_memberShipId(self, value):
        """회원 ID 중복 확인"""
        if AdminMemberShip.objects.filter(memberShipId=value).exists():
            raise serializers.ValidationError('이미 사용 중인 회원 ID입니다.')
        return value
    
    def validate_memberShipEmail(self, value):
        """이메일 중복 확인"""
        if AdminMemberShip.objects.filter(memberShipEmail=value).exists():
            raise serializers.ValidationError('이미 사용 중인 이메일입니다.')
        return value


class AdminLoginSerializer(serializers.Serializer):
    """관리자 로그인 요청 시리얼라이저"""
    memberShipId = serializers.CharField(required=True, help_text='회원 ID')
    password = serializers.CharField(required=True, write_only=True, help_text='비밀번호')


class AdminUpdateSerializer(serializers.Serializer):
    """관리자 회원 수정 요청 시리얼라이저"""
    memberShipName = serializers.CharField(required=False, max_length=100, help_text='이름')
    memberShipEmail = serializers.EmailField(required=False, help_text='이메일 주소')
    memberShipPhone = serializers.CharField(required=False, allow_blank=True, max_length=20, help_text='전화번호')
    memberShipLevel = serializers.IntegerField(required=False, help_text='회원 레벨')
    is_admin = serializers.BooleanField(required=False, help_text='관리자 여부')
    is_active = serializers.BooleanField(required=False, help_text='활성화 여부')
    password = serializers.CharField(required=False, write_only=True, min_length=8, allow_blank=True, help_text='비밀번호 (변경 시에만 입력)')
    password_confirm = serializers.CharField(required=False, write_only=True, allow_blank=True, help_text='비밀번호 확인')
    
    def validate(self, data):
        """비밀번호 일치 확인"""
        password = data.get('password')
        password_confirm = data.get('password_confirm')
        
        if password or password_confirm:
            if password != password_confirm:
                raise serializers.ValidationError({
                    'password_confirm': '비밀번호가 일치하지 않습니다.'
                })
        return data
    
    def validate_memberShipEmail(self, value):
        """이메일 중복 확인 (자기 자신 제외)"""
        # 수정 시에는 인스턴스가 필요하므로 뷰에서 처리
        return value

