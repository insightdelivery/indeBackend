"""
시스템 코드 모델
"""
from django.db import models


class SystemCode(models.Model):
    """
    시스템 코드 모델
    계층적 구조를 가진 시스템 코드 관리
    """
    sysCodeSid = models.CharField(primary_key=True, max_length=15, verbose_name='시스템 코드 SID')
    sysCodeParentsSid = models.CharField(max_length=15, null=True, blank=True, verbose_name='부모 코드 SID')
    sysCodeName = models.CharField(max_length=100, verbose_name='코드 이름')
    
    # 값 필드들
    sysCodeValName = models.CharField(max_length=100, null=True, blank=True, verbose_name='값 이름')
    sysCodeVal = models.CharField(max_length=255, null=True, blank=True, verbose_name='값')
    sysCodeVal1Name = models.CharField(max_length=100, null=True, blank=True, verbose_name='값1 이름')
    sysCodeVal1 = models.CharField(max_length=255, null=True, blank=True, verbose_name='값1')
    sysCodeVal2Name = models.CharField(max_length=100, null=True, blank=True, verbose_name='값2 이름')
    sysCodeVal2 = models.CharField(max_length=255, null=True, blank=True, verbose_name='값2')
    sysCodeVal3Name = models.CharField(max_length=100, null=True, blank=True, verbose_name='값3 이름')
    sysCodeVal3 = models.CharField(max_length=255, null=True, blank=True, verbose_name='값3')
    sysCodeVal4Name = models.CharField(max_length=100, null=True, blank=True, verbose_name='값4 이름')
    sysCodeVal4 = models.CharField(max_length=255, null=True, blank=True, verbose_name='값4')
    
    # 상태 및 정렬
    sysCodeUse = models.CharField(max_length=1, default='Y', verbose_name='사용 여부')
    sysCodeSort = models.IntegerField(null=True, blank=True, verbose_name='정렬 순서')
    
    # 등록 정보
    sysCodeRegUserName = models.CharField(max_length=100, null=True, blank=True, verbose_name='등록자 이름')
    sysCodeRegDateTime = models.DateTimeField(auto_now_add=True, verbose_name='등록 일시')
    
    class Meta:
        db_table = 'sysCode'
        verbose_name = '시스템 코드'
        verbose_name_plural = '시스템 코드'
        ordering = ['sysCodeSort', 'sysCodeName']
        indexes = [
            models.Index(fields=['sysCodeParentsSid']),
            models.Index(fields=['sysCodeUse']),
        ]
    
    def __str__(self):
        return f"{self.sysCodeName} ({self.sysCodeSid})"



