from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone

from core.models import SysCodeManager
from sites.admin_api.authentication import AdminJWTAuthentication
from .serializers import (
    SysCodeManagerSerializer, 
    SysCodeManagerCreateSerializer,
    SysCodeManagerUpdateSerializer,
    SysCodeManagerListSerializer
)
from .services import SysCodeManagerService

class SysCodeManagerViewSet(viewsets.ModelViewSet):
    """SysCodeManager CRUD 뷰셋"""
    queryset = SysCodeManager.objects.all()
    serializer_class = SysCodeManagerSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [AdminJWTAuthentication]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['sysCodeUse', 'sysCodeParentsSid']
    search_fields = ['sysCodeSid', 'sysCodeName', 'sysCodeVal']
    ordering_fields = ['sysCodeSort', 'sysCodeRegDateTime', 'sysCodeSid']
    ordering = ['sysCodeSort', 'sysCodeSid']
    lookup_field = 'sysCodeSid'  # sysCodeSid를 lookup 필드로 사용

    def get_serializer_class(self):
        """액션에 따른 시리얼라이저 선택"""
        if self.action == 'create':
            return SysCodeManagerCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SysCodeManagerUpdateSerializer
        elif self.action == 'list':
            return SysCodeManagerListSerializer
        return SysCodeManagerSerializer

    def perform_create(self, serializer):
        """생성 시 서비스 로직을 통해 parentsSid 자동 설정"""
        validated_data = serializer.validated_data
        user_name = self.request.user.username if hasattr(self.request.user, 'username') else None
        
        # 서비스를 통해 생성 (parentsSid 자동 설정 포함)
        instance = SysCodeManagerService.create_sys_code(validated_data, user_name)
        
        # serializer 인스턴스 업데이트
        serializer.instance = instance

    def perform_update(self, serializer):
        """수정 시 서비스 로직을 통해 parentsSid 자동 설정"""
        validated_data = serializer.validated_data
        user_name = self.request.user.username if hasattr(self.request.user, 'username') else None
        
        # 서비스를 통해 수정 (parentsSid 자동 설정 포함)
        instance = SysCodeManagerService.update_sys_code(serializer.instance.sid, validated_data, user_name)
        
        # serializer 인스턴스 업데이트
        serializer.instance = instance
    
    def update(self, request, *args, **kwargs):
        """수정 시 커스텀 응답 제공"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # 수정된 데이터만 반환 (트리 전체 갱신 불필요)
        return Response({
            'message': '코드가 성공적으로 수정되었습니다.',
            'updated_data': {
                'sysCodeSid': instance.sysCodeSid,
                'sysCodeName': instance.sysCodeName,
                'sysCodeVal': instance.sysCodeVal,
                'sysCodeUse': instance.sysCodeUse,
                'sysCodeSort': instance.sysCodeSort,
                'sysCodeRegUserName': instance.sysCodeRegUserName,
                'sysCodeRegDateTime': instance.sysCodeRegDateTime
            }
        })
    


    @action(detail=False, methods=['get'])
    def code_tree(self, request):
        """전체 코드 트리 구조 조회"""
        def build_tree(parent_id='*'):
            # 같은 레벨에서 sysCodeSort로 정렬
            codes = self.queryset.filter(sysCodeParentsSid=parent_id, sysCodeUse='Y').order_by('sysCodeSort', 'sysCodeSid')
            
            tree = []
            for code in codes:
                node = {
                    'sid': code.sid,
                    'parentsSid': code.parentsSid,
                    'sysCodeSid': code.sysCodeSid,
                    'sysCodeParentsSid': code.sysCodeParentsSid,
                    'sysCodeName': code.sysCodeName,
                    'sysCodeValName': code.sysCodeValName,
                    'sysCodeVal': code.sysCodeVal,
                    'sysCodeVal1Name': code.sysCodeVal1Name,
                    'sysCodeVal1': code.sysCodeVal1,
                    'sysCodeVal2Name': code.sysCodeVal2Name,
                    'sysCodeVal2': code.sysCodeVal2,
                    'sysCodeVal3Name': code.sysCodeVal3Name,
                    'sysCodeVal3': code.sysCodeVal3,
                    'sysCodeVal4Name': code.sysCodeVal4Name,
                    'sysCodeVal4': code.sysCodeVal4,
                    'sysCodeUse': code.sysCodeUse,
                    'sysCodeSort': code.sysCodeSort,
                    'sysCodeRegUserName': code.sysCodeRegUserName,
                    'sysCodeRegDateTime': code.sysCodeRegDateTime,
                    'children': build_tree(code.sysCodeSid)
                }
                tree.append(node)
            return tree
        
        tree_data = build_tree()
        return Response(tree_data)

    @action(detail=False, methods=['get'])
    def by_parent(self, request):
        """특정 부모 코드의 하위 레벨만 조회"""
        parent_id = request.query_params.get('parent_id')
        if parent_id:
            queryset = self.queryset.filter(sysCodeParentsSid=parent_id)
        else:
            queryset = self.queryset.filter(sysCodeParentsSid='*')  # 최상위 코드
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def update_code(self, request, sysCodeSid=None):
        """코드 수정 액션"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save(sysCodeRegDateTime=timezone.now())
                return Response({
                    'message': '코드가 성공적으로 수정되었습니다.',
                    'data': serializer.data
                })
            return Response({
                'error': '수정 데이터가 올바르지 않습니다.',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': f'코드 수정 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def toggle_status(self, request, sysCodeSid=None):
        """코드 사용/미사용 상태 토글"""
        try:
            instance = self.get_object()
            current_status = instance.sysCodeUse
            new_status = 'N' if current_status == 'Y' else 'Y'
            
            instance.sysCodeUse = new_status
            instance.save(update_fields=['sysCodeUse'])
            
            return Response({
                'message': f'코드 상태가 {new_status}로 변경되었습니다.',
                'sysCodeSid': instance.sysCodeSid,
                'old_status': current_status,
                'new_status': new_status
            })
        except Exception as e:
            return Response({
                'error': f'상태 변경 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



