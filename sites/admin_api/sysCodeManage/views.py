"""
시스템 코드 API 뷰
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from sites.admin_api.sysCodeManage.models import SystemCode
from sites.admin_api.sysCodeManage.serializers import (
    SystemCodeSerializer,
    SystemCodeCreateSerializer
)
from core.utils import create_api_response, generate_seq_code


class SystemCodeTreeView(APIView):
    """
    시스템 코드 트리 조회 API
    GET /sysCodeManage/syscode/code_tree/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        전체 시스템 코드를 트리 구조로 반환
        """
        try:
            # 최상위 코드들 조회 (부모가 없는 코드들)
            root_codes = SystemCode.objects.filter(
                sysCodeParentsSid__isnull=True,
                sysCodeUse='Y'
            ).order_by('sysCodeSort', 'sysCodeName')
            
            # 트리 구조로 직렬화
            serializer = SystemCodeSerializer(root_codes, many=True)
            
            return Response(
                create_api_response(True, '00', '조회 성공', serializer.data),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                create_api_response(False, '99', f'조회 실패: {str(e)}', None),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SystemCodeListView(APIView):
    """
    시스템 코드 목록 조회/생성 API
    GET /sysCodeManage/syscode/ - 목록 조회
    POST /sysCodeManage/syscode/ - 코드 생성
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        시스템 코드 목록 조회
        Query Parameters:
        - sysCodeParentsSid: 부모 코드 SID (선택)
        """
        try:
            sysCodeParentsSid = request.query_params.get('sysCodeParentsSid')
            
            queryset = SystemCode.objects.filter(sysCodeUse='Y')
            
            if sysCodeParentsSid:
                queryset = queryset.filter(sysCodeParentsSid=sysCodeParentsSid)
            else:
                # 부모가 없는 최상위 코드들만 조회
                queryset = queryset.filter(sysCodeParentsSid__isnull=True)
            
            queryset = queryset.order_by('sysCodeSort', 'sysCodeName')
            
            serializer = SystemCodeSerializer(queryset, many=True)
            
            return Response(
                create_api_response(True, '00', '조회 성공', serializer.data),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                create_api_response(False, '99', f'조회 실패: {str(e)}', None),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """
        시스템 코드 생성
        """
        try:
            serializer = SystemCodeCreateSerializer(data=request.data)
            
            if not serializer.is_valid():
                return Response(
                    create_api_response(
                        False,
                        '01',
                        '입력값이 올바르지 않습니다.',
                        serializer.errors
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # sysCodeSid 생성
            try:
                sysCodeSid = generate_seq_code('sysCode')
            except Exception as e:
                # 시퀀스 생성 실패 시 기본값 사용
                from datetime import datetime
                import hashlib
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                hash_part = hashlib.md5(f"sysCode{timestamp}".encode()).hexdigest()[:8].upper()
                sysCodeSid = f"SYS{timestamp}{hash_part}"
            
            # 코드 생성
            system_code = SystemCode.objects.create(
                sysCodeSid=sysCodeSid,
                **serializer.validated_data
            )
            
            result_serializer = SystemCodeSerializer(system_code)
            
            return Response(
                create_api_response(True, '00', '생성 성공', result_serializer.data),
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                create_api_response(False, '99', f'생성 실패: {str(e)}', None),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



