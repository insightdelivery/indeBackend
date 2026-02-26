"""
공개 API용 시스템 코드 읽기 전용 뷰.
홈페이지(www)에서 회원가입/프로필 등에 사용하는 syscode를 8001에서 조회할 수 있도록 함.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from core.models import SysCodeManager


class SysCodeByParentView(APIView):
    """부모 코드 기준 하위 시스템 코드 조회 (읽기 전용, 인증 불필요)"""
    permission_classes = [AllowAny]

    def get(self, request):
        parent_id = request.query_params.get('parent_id') or '*'
        queryset = SysCodeManager.objects.filter(sysCodeParentsSid=parent_id).order_by('sysCodeSort', 'sysCodeSid')
        data = [
            {
                'sysCodeSid': item.sysCodeSid,
                'sysCodeName': item.sysCodeName,
                'sysCodeVal': item.sysCodeVal or item.sysCodeSid,
                'sysCodeSort': item.sysCodeSort or 0,
                'sysCodeUse': item.sysCodeUse or 'Y',
            }
            for item in queryset
        ]
        return Response(data)
