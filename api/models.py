"""
관리자 회원 모델
AdminMemberShip: 관리자 페이지 회원 정보
"""
from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from core.utils import generate_seq_code


def generate_admin_member_sid():
    """
    관리자 회원 SID 생성
    generate_seq_code 함수를 사용하여 시퀀스 코드 생성
    """
    try:
        return generate_seq_code('adminMemberShip')
    except Exception as e:
        # 시퀀스 정보가 없으면 기본값 반환 (임시)
        from datetime import datetime
        import hashlib
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        hash_part = hashlib.md5(f"adminMemberShip{timestamp}".encode()).hexdigest()[:8].upper()
        return f"ADM{timestamp}{hash_part}"


class AdminMemberShip(models.Model):
    """
    관리자 회원 모델
    관리자 페이지 전용 회원 정보를 저장
    """
    # 기본 정보
    memberShipSid = models.CharField(primary_key=True, max_length=15, default=generate_admin_member_sid, editable=False, verbose_name='회원 SID')
    memberShipId = models.CharField(max_length=50, unique=True, verbose_name='회원 ID')
    memberShipPassword = models.CharField(max_length=255, verbose_name='비밀번호')
    memberShipName = models.CharField(max_length=100, verbose_name='이름')
    memberShipEmail = models.EmailField(unique=True, verbose_name='이메일')
    memberShipPhone = models.CharField(max_length=20, blank=True, null=True, verbose_name='전화번호')
    
    # 권한 및 레벨 (§18.3 Super Admin: memberShipLevel == 1)
    memberShipLevel = models.IntegerField(default=2, verbose_name='회원 레벨')
    admin_role = models.CharField(
        max_length=20,
        blank=True,
        default='editor',
        verbose_name='관리자 역할',
        help_text='director | editor — 초기 user_permissions 템플릿용',
    )
    is_admin = models.BooleanField(default=False, verbose_name='관리자 여부')
    is_active = models.BooleanField(default=True, verbose_name='활성화')
    
    # 추가 정보
    last_login = models.DateTimeField(blank=True, null=True, verbose_name='마지막 로그인')
    login_count = models.IntegerField(default=0, verbose_name='로그인 횟수')
    token_issued_at = models.DateTimeField(blank=True, null=True, verbose_name='마지막 토큰 발급 시간')
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        db_table = 'adminMemberShip'
        verbose_name = '관리자 회원'
        verbose_name_plural = '관리자 회원'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['memberShipId']),
            models.Index(fields=['memberShipEmail']),
            models.Index(fields=['is_active', 'is_admin']),
        ]
    
    def __str__(self):
        return f"{self.memberShipName} ({self.memberShipId})"
    
    def set_password(self, raw_password):
        """비밀번호 설정 (해시화)"""
        self.memberShipPassword = make_password(raw_password)
        self.save(update_fields=['memberShipPassword'])
    
    def check_password(self, raw_password):
        """비밀번호 확인"""
        return check_password(raw_password, self.memberShipPassword)
    
    def is_staff(self):
        """스태프 여부 (관리자 또는 레벨이 높은 경우)"""
        return self.is_admin or self.memberShipLevel >= 5
    
    @property
    def is_authenticated(self):
        """인증 여부 (DRF IsAuthenticated permission에서 사용)"""
        return True
    
    @property
    def is_anonymous(self):
        """익명 사용자 여부"""
        return False


class UserPermission(models.Model):
    """
    관리자 메뉴 권한 (adminUserPermissionsPlan.md §4)
    판단은 이 테이블만 사용한다.
    """

    user = models.ForeignKey(
        AdminMemberShip,
        on_delete=models.CASCADE,
        related_name='menu_permissions',
        db_column='user_id',
    )
    menu_code = models.CharField(max_length=20)
    can_read = models.BooleanField(default=True)
    can_write = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        db_table = 'user_permissions'
        verbose_name = '관리자 메뉴 권한'
        verbose_name_plural = '관리자 메뉴 권한'
        constraints = [
            models.UniqueConstraint(fields=['user', 'menu_code'], name='uniq_user_menu_code'),
        ]
        indexes = [
            models.Index(fields=['user', 'menu_code'], name='user_perm_user_menu_idx'),
        ]

    def __str__(self):
        return f'{self.user_id} {self.menu_code}'
