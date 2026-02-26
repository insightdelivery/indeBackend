"""
Public API 모델
- PublicMemberShip: 공개 사이트 회원 (일반/소셜 가입, DB 테이블 publicMemberShip)
- IndeUser: 웹사이트 회원
- SocialAccount: SNS 연동 계정
"""
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.contrib.auth.hashers import make_password, check_password
from django.core.validators import MinValueValidator, MaxValueValidator
from core.utils import generate_seq_code


def generate_public_member_sid():
    """
    레거시 호환용 스텁. 0003 마이그레이션 로드 시 참조되므로 모듈에 유지.
    실제 PK는 PublicMemberShip.member_sid = AutoField (0004) 사용.
    """
    return 'PBM00000000000001'


class PublicMemberShip(models.Model):
    """
    공개 사이트 회원 (테이블: publicMemberShip)
    - 일반 회원가입: email + password, joined_via='LOCAL'
    - 소셜 로그인: 추후 연동 시 password=null, joined_via='KAKAO'|'NAVER'|'GOOGLE'
    """
    JOINED_VIA_CHOICES = [
        ('LOCAL', '로컬 가입'),
        ('KAKAO', '카카오'),
        ('NAVER', '네이버'),
        ('GOOGLE', '구글'),
    ]
    REGION_TYPE_CHOICES = [
        ('DOMESTIC', '국내'),
        ('FOREIGN', '해외'),
    ]

    member_sid = models.AutoField(primary_key=True, verbose_name='회원 SID')  # 1부터 자동 증가
    email = models.EmailField(unique=True, verbose_name='이메일')
    password = models.CharField(max_length=255, null=True, blank=True, verbose_name='비밀번호')  # 소셜만 가입 시 null
    name = models.CharField(max_length=100, verbose_name='이름')
    nickname = models.CharField(max_length=100, verbose_name='닉네임')
    phone = models.CharField(max_length=20, verbose_name='휴대폰 번호')

    position = models.CharField(max_length=100, null=True, blank=True, verbose_name='직분')
    birth_year = models.IntegerField(
        null=True, blank=True, verbose_name='출생년도',
        validators=[MinValueValidator(1900), MaxValueValidator(2100)]
    )
    birth_month = models.IntegerField(
        null=True, blank=True, verbose_name='출생월',
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    birth_day = models.IntegerField(
        null=True, blank=True, verbose_name='출생일',
        validators=[MinValueValidator(1), MaxValueValidator(31)]
    )
    region_type = models.CharField(
        max_length=10, choices=REGION_TYPE_CHOICES, null=True, blank=True, verbose_name='지역 타입'
    )
    region_domestic = models.CharField(max_length=100, null=True, blank=True, verbose_name='국내 지역')
    region_foreign = models.CharField(max_length=100, null=True, blank=True, verbose_name='해외 지역')

    joined_via = models.CharField(
        max_length=10, choices=JOINED_VIA_CHOICES, default='LOCAL', verbose_name='가입 경로'
    )
    sns_provider_uid = models.CharField(
        max_length=255, null=True, blank=True, verbose_name='SNS 제공자 고유 회원 코드',
        help_text='KAKAO/NAVER/GOOGLE 가입 시 해당 제공자의 회원 고유 ID'
    )
    newsletter_agree = models.BooleanField(default=False, verbose_name='뉴스레터 수신 동의')
    profile_completed = models.BooleanField(default=True, verbose_name='프로필 완료 여부')  # 일반 가입 시 필수 입력으로 완료
    email_verified = models.BooleanField(default=False, verbose_name='이메일 인증 여부')  # 인증 메일 클릭 후 True
    is_staff = models.BooleanField(default=False, verbose_name='관리자 여부')  # 공지/FAQ/문의 답변 등 관리 권한
    is_active = models.BooleanField(default=True, verbose_name='활성화')
    last_login = models.DateTimeField(null=True, blank=True, verbose_name='마지막 로그인')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')

    class Meta:
        db_table = 'publicMemberShip'
        verbose_name = '공개 회원'
        verbose_name_plural = '공개 회원'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['joined_via']),
            models.Index(fields=['is_active']),
            models.Index(fields=['sns_provider_uid']),
        ]

    def __str__(self):
        return f"{self.email} ({self.member_sid})"

    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        if self.pk:
            self.save(update_fields=['password'])

    def check_password(self, raw_password):
        if not self.password:
            return False
        return check_password(raw_password, self.password)


def generate_inde_user_id():
    """
    IndeUser ID 생성
    generate_seq_code 함수를 사용하여 시퀀스 코드 생성
    """
    try:
        return generate_seq_code('indeUser')
    except Exception as e:
        # 시퀀스 정보가 없으면 기본값 반환 (임시)
        from datetime import datetime
        import hashlib
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        hash_part = hashlib.md5(f"indeUser{timestamp}".encode()).hexdigest()[:8].upper()
        return f"USR{timestamp}{hash_part}"


class IndeUserManager(BaseUserManager):
    """IndeUser 모델용 커스텀 매니저"""
    
    def create_user(self, email, password=None, **extra_fields):
        """일반 사용자 생성"""
        if not email:
            raise ValueError('이메일은 필수입니다.')
        email = self.normalize_email(email)
        # ID가 없으면 자동 생성
        if 'id' not in extra_fields or not extra_fields.get('id'):
            extra_fields['id'] = generate_inde_user_id()
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user


class IndeUser(AbstractBaseUser):
    """
    웹사이트 회원 모델
    이메일을 아이디로 사용
    """
    # 기본 정보
    id = models.CharField(primary_key=True, max_length=15, default=generate_inde_user_id, editable=False, verbose_name='회원 ID')
    email = models.EmailField(unique=True, verbose_name='이메일')
    password = models.CharField(max_length=255, null=True, blank=True, verbose_name='비밀번호')
    name = models.CharField(max_length=100, null=True, blank=True, verbose_name='이름')
    phone = models.CharField(max_length=20, null=True, blank=True, unique=True, verbose_name='전화번호')
    position = models.CharField(max_length=100, null=True, blank=True, verbose_name='교회 직분')
    
    # 생년월일
    birth_year = models.IntegerField(null=True, blank=True, verbose_name='출생년도',
                                     validators=[MinValueValidator(1900), MaxValueValidator(2100)])
    birth_month = models.IntegerField(null=True, blank=True, verbose_name='출생월',
                                      validators=[MinValueValidator(1), MaxValueValidator(12)])
    birth_day = models.IntegerField(null=True, blank=True, verbose_name='출생일',
                                    validators=[MinValueValidator(1), MaxValueValidator(31)])
    
    # 지역 정보
    REGION_TYPE_CHOICES = [
        ('DOMESTIC', '국내'),
        ('FOREIGN', '해외'),
    ]
    region_type = models.CharField(max_length=10, choices=REGION_TYPE_CHOICES, null=True, blank=True, verbose_name='지역 타입')
    region_domestic = models.CharField(max_length=100, null=True, blank=True, verbose_name='국내 지역')
    region_foreign = models.CharField(max_length=100, null=True, blank=True, verbose_name='해외 지역')
    
    # 상태 정보
    profile_completed = models.BooleanField(default=False, verbose_name='프로필 완료 여부')
    
    JOINED_VIA_CHOICES = [
        ('LOCAL', '로컬 가입'),
        ('KAKAO', '카카오'),
        ('NAVER', '네이버'),
        ('GOOGLE', '구글'),
    ]
    joined_via = models.CharField(max_length=10, choices=JOINED_VIA_CHOICES, default='LOCAL', verbose_name='가입 경로')
    
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    last_login = models.DateTimeField(null=True, blank=True, verbose_name='마지막 로그인 시간')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    objects = IndeUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        db_table = 'indeUser'
        verbose_name = '웹사이트 회원'
        verbose_name_plural = '웹사이트 회원'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['joined_via']),
            models.Index(fields=['profile_completed']),
            models.Index(fields=['region_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.email or str(self.id)
    
    def clean(self):
        """지역 입력 규칙 검증"""
        from django.core.exceptions import ValidationError
        
        if self.region_type == 'DOMESTIC':
            if not self.region_domestic:
                raise ValidationError({'region_domestic': '국내 지역을 입력해주세요.'})
            if self.region_foreign:
                self.region_foreign = None
        elif self.region_type == 'FOREIGN':
            if not self.region_foreign:
                raise ValidationError({'region_foreign': '해외 지역을 입력해주세요.'})
            if self.region_domestic:
                self.region_domestic = None
    
    def save(self, *args, **kwargs):
        """저장 전 검증"""
        self.full_clean()
        super().save(*args, **kwargs)


class SocialAccount(models.Model):
    """
    SNS 연동 계정 모델
    """
    PROVIDER_CHOICES = [
        ('kakao', '카카오'),
        ('naver', '네이버'),
        ('google', '구글'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(IndeUser, on_delete=models.CASCADE, related_name='social_accounts', verbose_name='사용자')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, verbose_name='SNS 제공자')
    provider_user_id = models.CharField(max_length=255, verbose_name='SNS 제공자의 사용자 ID')
    email_from_provider = models.EmailField(null=True, blank=True, verbose_name='SNS 제공자로부터 받은 이메일')
    
    connected_at = models.DateTimeField(auto_now_add=True, verbose_name='연동일시')
    last_login_at = models.DateTimeField(null=True, blank=True, verbose_name='마지막 로그인 시간')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        db_table = 'SocialAccount'
        verbose_name = 'SNS 연동 계정'
        verbose_name_plural = 'SNS 연동 계정'
        unique_together = [['provider', 'provider_user_id']]
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['provider']),
            models.Index(fields=['email_from_provider']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.get_provider_display()}"

