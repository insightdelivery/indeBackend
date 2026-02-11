"""
공통 모델 정의
- Account: 확장된 사용자 모델 (UUID, 전화번호, 생년월일, 이메일 인증 등)
- AuditLog: 사용자 활동 자동 로깅
"""
import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class AccountManager(BaseUserManager):
    """Account 모델용 커스텀 매니저"""
    
    def create_user(self, email, password=None, **extra_fields):
        """일반 사용자 생성"""
        if not email:
            raise ValueError('이메일은 필수입니다.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """슈퍼유저 생성"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('슈퍼유저는 is_staff=True여야 합니다.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('슈퍼유저는 is_superuser=True여야 합니다.')
        
        return self.create_user(email, password, **extra_fields)


class Account(AbstractBaseUser, PermissionsMixin):
    """
    확장된 사용자 모델
    - UUID 기반 식별자 (CHAR(36) 형식)
    - 전화번호, 생년월일, 이메일 인증 등 지원
    """
    id = models.CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()), editable=False, verbose_name='UUID')
    email = models.EmailField(unique=True, verbose_name='이메일')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='전화번호')
    birth_date = models.DateField(blank=True, null=True, verbose_name='생년월일')
    name = models.CharField(max_length=100, blank=True, verbose_name='이름')
    
    is_active = models.BooleanField(default=True, verbose_name='활성화')
    is_staff = models.BooleanField(default=False, verbose_name='스태프')
    is_superuser = models.BooleanField(default=False, verbose_name='슈퍼유저')
    
    email_verified = models.BooleanField(default=False, verbose_name='이메일 인증')
    email_verified_at = models.DateTimeField(blank=True, null=True, verbose_name='이메일 인증일시')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    objects = AccountManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        db_table = 'account'
        verbose_name = '계정'
        verbose_name_plural = '계정'
    
    def __str__(self):
        return self.email


class AuditLog(models.Model):
    """
    사용자 활동 자동 로깅
    - 로그인, 로그아웃, CRUD 작업 등 기록
    """
    ACTION_CHOICES = [
        ('login', '로그인'),
        ('logout', '로그아웃'),
        ('create', '생성'),
        ('read', '조회'),
        ('update', '수정'),
        ('delete', '삭제'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    user_id = models.CharField(max_length=50, null=True, blank=True, verbose_name='사용자 ID', help_text='Account.id(UUID 36자) 또는 AdminMemberShip.memberShipSid(15자) 또는 IndeUser.id')
    site_slug = models.CharField(max_length=50, blank=True, verbose_name='사이트')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='액션')
    resource = models.CharField(max_length=100, blank=True, verbose_name='리소스')
    resource_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='리소스 ID')
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name='IP 주소')
    user_agent = models.TextField(blank=True, verbose_name='User Agent')
    details = models.JSONField(blank=True, null=True, verbose_name='상세 정보')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    
    class Meta:
        db_table = 'audit_log'
        verbose_name = '감사 로그'
        verbose_name_plural = '감사 로그'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id', 'created_at'], name='idx_audit_user_created'),
            models.Index(fields=['site_slug', 'action', 'created_at'], name='idx_audit_site_action'),
        ]
    
    def __str__(self):
        user_info = self.user_id if self.user_id else "Unknown"
        return f"{user_info} - {self.action} - {self.resource}"


class SeqMaster(models.Model):
    """
    시퀀스 마스터 테이블
    각 테이블별 시퀀스 코드 생성을 관리
    """
    seqSid = models.BigAutoField(primary_key=True, verbose_name='시퀀스 SID')
    seq_top = models.CharField(max_length=3, default='', verbose_name='시퀀스 접두사')
    seq_tablename = models.CharField(max_length=60, default='', verbose_name='테이블명')
    seq_seatcount = models.IntegerField(null=True, blank=True, verbose_name='시퀀스 자리수')
    seq_value = models.IntegerField(null=True, blank=True, verbose_name='시퀀스 값')
    seq_yyyy = models.CharField(max_length=4, null=True, blank=True, verbose_name='년도 (4자리)')
    seq_yyc = models.CharField(max_length=2, null=True, blank=True, verbose_name='밀레니엄 코드')
    seq_yy = models.CharField(max_length=2, null=True, blank=True, verbose_name='년도 (2자리)')
    seq_mm = models.CharField(max_length=2, null=True, blank=True, verbose_name='월')
    seq_dd = models.CharField(max_length=2, null=True, blank=True, verbose_name='일')
    
    class Meta:
        db_table = 'seqMaster'
        verbose_name = '시퀀스 마스터'
        verbose_name_plural = '시퀀스 마스터'
        indexes = [
            models.Index(fields=['seq_tablename']),
        ]
    
    def __str__(self):
        return f"{self.seq_tablename} - {self.seq_value}"


class SysCodeManager(models.Model):
    """시스템 코드 관리 모델 - sysCodeManager 테이블과 매핑"""
    sid = models.AutoField(primary_key=True)
    parentsSid = models.IntegerField()
    sysCodeSid = models.CharField(max_length=12, default='')
    sysCodeParentsSid = models.CharField(max_length=12, default='')
    sysCodeName = models.CharField(max_length=255, default='')
    sysCodeValName = models.CharField(max_length=255, null=True, blank=True)
    sysCodeVal = models.CharField(max_length=255, null=True, blank=True)
    sysCodeVal1Name = models.CharField(max_length=255, null=True, blank=True)
    sysCodeVal1 = models.CharField(max_length=255, null=True, blank=True)
    sysCodeVal2Name = models.CharField(max_length=255, null=True, blank=True)
    sysCodeVal2 = models.CharField(max_length=255, null=True, blank=True)
    sysCodeVal3Name = models.CharField(max_length=255, null=True, blank=True)
    sysCodeVal3 = models.CharField(max_length=255, null=True, blank=True)
    sysCodeVal4Name = models.CharField(max_length=255, null=True, blank=True)
    sysCodeVal4 = models.CharField(max_length=255, null=True, blank=True)
    sysCodeUse = models.CharField(
        max_length=1,
        choices=[('Y', '사용'), ('N', '미사용')],
        default='Y'
    )
    sysCodeSort = models.IntegerField(null=True, blank=True)
    sysCodeRegUserName = models.CharField(max_length=30, null=True, blank=True)
    sysCodeRegDateTime = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False  # 기존 테이블 사용
        db_table = 'sysCodeManager'
        verbose_name = '시스템 코드 관리'
        verbose_name_plural = '시스템 코드 관리'

    def __str__(self):
        return f"{self.sysCodeSid} - {self.sysCodeName}"


