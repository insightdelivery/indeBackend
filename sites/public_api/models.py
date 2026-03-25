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
        max_length=50, null=True, blank=True, verbose_name='지역 타입'
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

    # 탈퇴(Soft Delete) 관련 - publicUserWithdrawRules.md
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_WITHDRAW_REQUEST = 'WITHDRAW_REQUEST'
    STATUS_WITHDRAWN = 'WITHDRAWN'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, '정상'),
        (STATUS_WITHDRAW_REQUEST, '탈퇴 요청'),
        (STATUS_WITHDRAWN, '탈퇴 완료'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        verbose_name='회원 상태',
        db_index=False,
    )
    withdraw_reason = models.TextField(null=True, blank=True, verbose_name='탈퇴 사유')
    withdraw_detail_reason = models.TextField(null=True, blank=True, verbose_name='탈퇴 상세 사유')
    withdraw_requested_at = models.DateTimeField(null=True, blank=True, verbose_name='탈퇴 요청일시')
    withdraw_completed_at = models.DateTimeField(null=True, blank=True, verbose_name='탈퇴 완료일시')
    withdraw_ip = models.CharField(max_length=45, null=True, blank=True, verbose_name='탈퇴 요청 IP')
    withdraw_user_agent = models.TextField(null=True, blank=True, verbose_name='탈퇴 요청 User-Agent')

    class Meta:
        db_table = 'publicMemberShip'
        verbose_name = '공개 회원'
        verbose_name_plural = '공개 회원'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email'], name='publicMembe_email_380364_idx'),
            models.Index(fields=['phone'], name='publicMembe_phone_6d843f_idx'),
            models.Index(fields=['joined_via'], name='publicMembe_joined__e763a1_idx'),
            models.Index(fields=['is_active'], name='publicMembe_is_acti_a22f15_idx'),
            models.Index(fields=['sns_provider_uid'], name='publicMembe_sns_pro_idx'),
            models.Index(fields=['status'], name='publicMemberShip_status'),
            models.Index(fields=['status'], name='publicMembe_status_idx'),
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


class PublicUserActivityLog(models.Model):
    """
    라이브러리 사용자 활동 로그 (테이블: publicUserActivityLog)
    - userPublicActiviteLog.md: VIEW는 로그인 무관(user_id=0), regDate·viewCount, UNIQUE uniq_view, INSERT ON DUPLICATE KEY UPDATE
    """
    CONTENT_TYPE_CHOICES = [
        ('ARTICLE', '아티클'),
        ('VIDEO', '비디오'),
        ('SEMINAR', '세미나'),
    ]
    ACTIVITY_TYPE_CHOICES = [
        ('VIEW', '조회'),
        ('RATING', '별점'),
        ('BOOKMARK', '북마크'),
    ]

    public_user_activity_log_id = models.BigAutoField(primary_key=True, db_column='publicUserActivityLogId', verbose_name='사용자 활동 로그 PK')
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, db_column='contentType', verbose_name='콘텐츠 타입')
    content_code = models.CharField(max_length=50, db_column='contentCode', verbose_name='콘텐츠 고유 코드')
    user_id = models.BigIntegerField(default=0, db_column='userId', verbose_name='회원 ID (0=비로그인)')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPE_CHOICES, db_column='activityType', verbose_name='사용자 행동 유형')
    rating_value = models.SmallIntegerField(null=True, blank=True, db_column='ratingValue', verbose_name='별점 값 (1~5)')
    view_count = models.IntegerField(default=1, db_column='viewCount', verbose_name='조회 진입 횟수')
    reg_date = models.DateField(db_column='regDate', verbose_name='로그 날짜(년-월-일)')
    ip_address = models.CharField(max_length=45, null=True, blank=True, db_column='ipAddress', verbose_name='접속 IP')
    user_agent = models.CharField(max_length=500, null=True, blank=True, db_column='userAgent', verbose_name='브라우저 정보')
    reg_date_time = models.DateTimeField(auto_now=True, db_column='regDateTime', verbose_name='기록 시간')

    class Meta:
        db_table = 'publicUserActivityLog'
        verbose_name = '공개 사용자 활동 로그'
        verbose_name_plural = '공개 사용자 활동 로그'
        ordering = ['-reg_date_time']
        indexes = [
            models.Index(fields=['content_type', 'content_code'], name='idx_content'),
            models.Index(fields=['user_id'], name='idx_user'),
            models.Index(fields=['activity_type'], name='idx_activity'),
            models.Index(fields=['reg_date'], name='idx_regDate'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['content_type', 'content_code', 'activity_type', 'user_id', 'reg_date'],
                name='uniq_view',
            ),
        ]

    def __str__(self):
        return f"{self.user_id} {self.activity_type} {self.content_type}:{self.content_code}"


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


class PhoneSmsVerification(models.Model):
    """
    회원가입 휴대폰 SMS 인증 (Aligo).
    phoneVerificationAligo.md — 코드는 code_hash로만 저장.
    """
    id = models.BigAutoField(primary_key=True)
    phone = models.CharField(max_length=20, db_index=True, verbose_name='정규화된 휴대폰')
    code_hash = models.CharField(max_length=128, verbose_name='인증번호 해시')
    expires_at = models.DateTimeField(db_index=True, verbose_name='만료 시각')
    verified = models.BooleanField(default=False, verbose_name='인증 완료')
    attempt_count = models.PositiveSmallIntegerField(default=0, verbose_name='검증 시도 횟수')
    last_sent_at = models.DateTimeField(verbose_name='마지막 발송 시각')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'phoneSmsVerification'
        verbose_name = '휴대폰 SMS 인증'
        verbose_name_plural = '휴대폰 SMS 인증'

    def __str__(self):
        return f'{self.phone} verified={self.verified}'

