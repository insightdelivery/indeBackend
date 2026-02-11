"""
시스템 코드 시리얼라이저
"""
from rest_framework import serializers
from sites.admin_api.sysCodeManage.models import SystemCode


class SystemCodeSerializer(serializers.ModelSerializer):
    """시스템 코드 시리얼라이저"""
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = SystemCode
        fields = [
            'sysCodeSid',
            'sysCodeParentsSid',
            'sysCodeName',
            'sysCodeValName',
            'sysCodeVal',
            'sysCodeVal1Name',
            'sysCodeVal1',
            'sysCodeVal2Name',
            'sysCodeVal2',
            'sysCodeVal3Name',
            'sysCodeVal3',
            'sysCodeVal4Name',
            'sysCodeVal4',
            'sysCodeUse',
            'sysCodeSort',
            'sysCodeRegUserName',
            'sysCodeRegDateTime',
            'children',
        ]
        read_only_fields = ['sysCodeSid', 'sysCodeRegDateTime']
    
    def get_children(self, obj):
        """자식 코드들을 재귀적으로 가져오기"""
        children = SystemCode.objects.filter(
            sysCodeParentsSid=obj.sysCodeSid,
            sysCodeUse='Y'
        ).order_by('sysCodeSort', 'sysCodeName')
        
        if children.exists():
            serializer = SystemCodeSerializer(children, many=True)
            return serializer.data
        return []


class SystemCodeCreateSerializer(serializers.ModelSerializer):
    """시스템 코드 생성 시리얼라이저"""
    
    class Meta:
        model = SystemCode
        fields = [
            'sysCodeParentsSid',
            'sysCodeName',
            'sysCodeValName',
            'sysCodeVal',
            'sysCodeVal1Name',
            'sysCodeVal1',
            'sysCodeVal2Name',
            'sysCodeVal2',
            'sysCodeVal3Name',
            'sysCodeVal3',
            'sysCodeVal4Name',
            'sysCodeVal4',
            'sysCodeUse',
            'sysCodeSort',
            'sysCodeRegUserName',
        ]
    
    def validate_sysCodeName(self, value):
        """코드 이름 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError('코드 이름은 필수입니다.')
        return value.strip()



