"""
공개 API용 시스템 코드 읽기 전용 뷰.
홈페이지(www)에서 회원가입/프로필 등에 사용하는 syscode를 8001에서 조회할 수 있도록 함.
"""
from collections import defaultdict

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from core.models import SysCodeManager

BULK_PARENT_IDS_MAX = 50


def _item_to_dict(item):
    """SysCodeManager 행을 by_parent와 동일한 필드로 변환."""
    return {
        'sysCodeSid': item.sysCodeSid,
        'sysCodeName': item.sysCodeName,
        'sysCodeVal': item.sysCodeVal or item.sysCodeSid,
        'sysCodeSort': item.sysCodeSort or 0,
        'sysCodeUse': item.sysCodeUse or 'Y',
    }


class SysCodeByParentView(APIView):
    """부모 코드 기준 하위 시스템 코드 조회 (읽기 전용, 인증 불필요)"""
    permission_classes = [AllowAny]

    def get(self, request):
        parent_id = request.query_params.get('parent_id') or '*'
        queryset = SysCodeManager.objects.filter(sysCodeParentsSid=parent_id).order_by('sysCodeSort', 'sysCodeSid')
        data = [_item_to_dict(item) for item in queryset]
        return Response(data)


class SysCodeListByParentsSidView(APIView):
    """
    GET /systemmanage/syscode
    - ?sysCodeSid= — 해당 sid **본인 1행**만 (직계 자식 아님). 사용 Y만, 없으면 [].
    - ?sysCodeParentsSid= — 관리자 list 쿼리명과 동일(단일 부모의 직계 자식).
    parent 미지정·빈 값이면 빈 배열 (루트 전체 노출 방지).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        single_sid = (request.query_params.get('sysCodeSid') or '').strip()
        if single_sid:
            item = SysCodeManager.objects.filter(sysCodeSid=single_sid, sysCodeUse='Y').first()
            return Response([_item_to_dict(item)] if item else [])

        parent_id = (request.query_params.get('sysCodeParentsSid') or '').strip()
        if not parent_id:
            return Response([])
        queryset = SysCodeManager.objects.filter(sysCodeParentsSid=parent_id).order_by(
            'sysCodeSort', 'sysCodeSid'
        )
        data = [_item_to_dict(item) for item in queryset]
        return Response(data)


class SysCodeBulkByParentsView(APIView):
    """
    여러 부모 코드에 대한 직계 자식을 한 번에 조회 (API 1회).
    쿼리: parent_ids=SYS26209B002,SYS26127B017,... (쉼표 구분, 최대 50개)
    응답: { "SYS26209B002": [...], "SYS26127B017": [...], ... } (자식 없으면 [])
    """
    permission_classes = [AllowAny]

    def get(self, request):
        raw = request.query_params.get('parent_ids') or ''
        parent_ids = [s.strip() for s in raw.split(',') if s.strip()][:BULK_PARENT_IDS_MAX]
        if not parent_ids:
            return Response({})

        queryset = SysCodeManager.objects.filter(
            sysCodeParentsSid__in=parent_ids,
            sysCodeUse='Y',
        ).order_by('sysCodeSort', 'sysCodeSid')

        grouped = defaultdict(list)
        for item in queryset:
            grouped[item.sysCodeParentsSid].append(_item_to_dict(item))

        result = {pid: grouped.get(pid, []) for pid in parent_ids}
        return Response(result)
