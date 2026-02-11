from rest_framework import serializers
from core.models import SysCodeManager

class SysCodeManagerSerializer(serializers.ModelSerializer):
    """SysCodeManager 모델 시리얼라이저 - 전체 데이터용"""
    
    class Meta:
        model = SysCodeManager
        fields = [
            'sid', 'parentsSid', 'sysCodeSid', 'sysCodeParentsSid', 
            'sysCodeName', 'sysCodeValName', 'sysCodeVal', 'sysCodeVal1Name', 
            'sysCodeVal1', 'sysCodeVal2Name', 'sysCodeVal2', 'sysCodeVal3Name', 
            'sysCodeVal3', 'sysCodeVal4Name', 'sysCodeVal4', 'sysCodeUse', 
            'sysCodeSort', 'sysCodeRegUserName', 'sysCodeRegDateTime'
        ]
        read_only_fields = ['sid']

class SysCodeManagerCreateSerializer(serializers.ModelSerializer):
    """SysCodeManager 생성용 시리얼라이저"""
    
    class Meta:
        model = SysCodeManager
        fields = [
            'sysCodeSid', 'sysCodeParentsSid', 'sysCodeName', 
            'sysCodeValName', 'sysCodeVal', 'sysCodeVal1Name', 'sysCodeVal1', 
            'sysCodeVal2Name', 'sysCodeVal2', 'sysCodeVal3Name', 'sysCodeVal3', 
            'sysCodeVal4Name', 'sysCodeVal4', 'sysCodeUse', 'sysCodeSort', 
            'sysCodeRegUserName'
        ]

class SysCodeManagerUpdateSerializer(serializers.ModelSerializer):
    """SysCodeManager 수정용 시리얼라이저"""
    
    class Meta:
        model = SysCodeManager
        fields = [
            'sysCodeParentsSid', 'sysCodeName', 'sysCodeValName', 
            'sysCodeVal', 'sysCodeVal1Name', 'sysCodeVal1', 'sysCodeVal2Name', 
            'sysCodeVal2', 'sysCodeVal3Name', 'sysCodeVal3', 'sysCodeVal4Name', 
            'sysCodeVal4', 'sysCodeUse', 'sysCodeSort', 'sysCodeRegUserName'
        ]

class SysCodeManagerListSerializer(serializers.ModelSerializer):
    """SysCodeManager 목록 조회용 시리얼라이저"""
    
    class Meta:
        model = SysCodeManager
        fields = [
            'sid', 'sysCodeSid', 'sysCodeName', 'sysCodeVal', 'sysCodeUse', 
            'sysCodeSort', 'sysCodeRegUserName', 'sysCodeRegDateTime'
        ]



