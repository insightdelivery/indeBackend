"""
공개 API 뷰
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from core.models import Account, AuditLog
from sites.public_api.serializers import RegisterSerializer, LoginSerializer
from sites.public_api.utils import create_public_jwt_tokens


class RegisterView(APIView):
    """
    회원 가입 API
    이메일, 비밀번호, 이름 등으로 새 계정을 생성합니다.
    """
    permission_classes = [AllowAny]  # 회원 가입은 인증 불필요
    
    def post(self, request):
        """
        회원 가입 처리
        
        요청 파라미터:
        - email: 이메일 주소 (필수)
        - password: 비밀번호 (필수, 최소 8자)
        - password_confirm: 비밀번호 확인 (필수)
        - name: 이름 (필수)
        - phone: 전화번호 (선택)
        - birth_date: 생년월일 (선택, YYYY-MM-DD 형식)
        
        응답:
        - access_token: Access Token
        - refresh_token: Refresh Token
        - expires_in: Access Token 만료 시간 (초)
        - user: 사용자 정보
        """
        serializer = RegisterSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'error': '입력값이 올바르지 않습니다.',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 계정 생성
            user = Account.objects.create_user(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                name=serializer.validated_data.get('name', ''),
                phone=serializer.validated_data.get('phone', ''),
                birth_date=serializer.validated_data.get('birth_date'),
                is_active=True,
                is_staff=False,  # 일반 사용자는 스태프가 아님
                is_superuser=False,
            )
            
            # JWT 토큰 생성
            tokens = create_public_jwt_tokens(user)
            
            # 회원 가입 로그 기록
            AuditLog.objects.create(
                user_id=str(user.id),  # Account의 id 저장
                site_slug='public_api',
                action='create',
                resource='account',
                resource_id=str(user.id),
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'status': 'success', 'action': 'register'}
            )
            
            # 성공 응답
            return Response({
                'access_token': tokens['access_token'],
                'refresh_token': tokens['refresh_token'],
                'expires_in': tokens['expires_in'],
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'name': user.name,
                    'phone': user.phone,
                    'email_verified': user.email_verified,
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': f'회원 가입 처리 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class LoginView(APIView):
    """
    공개 API 로그인
    이메일과 비밀번호로 로그인하여 JWT 토큰을 발급받습니다.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        로그인 처리
        
        요청 파라미터:
        - email: 이메일 주소 (필수)
        - password: 비밀번호 (필수)
        """
        serializer = LoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'error': '입력값이 올바르지 않습니다.',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        try:
            # 사용자 조회
            try:
                user = Account.objects.get(email=email, is_active=True)
            except Account.DoesNotExist:
                return Response({
                    'error': '이메일 또는 비밀번호가 올바르지 않습니다.'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 비밀번호 확인
            if not user.check_password(password):
                # 로그인 실패 로그 기록
                AuditLog.objects.create(
                    user_id=str(user.id),  # Account의 id 저장
                    site_slug='public_api',
                    action='login',
                    resource='account',
                    resource_id=str(user.id),
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    details={'status': 'failed', 'reason': 'invalid_password'}
                )
                return Response({
                    'error': '이메일 또는 비밀번호가 올바르지 않습니다.'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # JWT 토큰 생성
            tokens = create_public_jwt_tokens(user)
            
            # 로그인 성공 로그 기록
            AuditLog.objects.create(
                user_id=str(user.id),  # Account의 id 저장
                site_slug='public_api',
                action='login',
                resource='account',
                resource_id=str(user.id),
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'status': 'success'}
            )
            
            # 성공 응답
            return Response({
                'access_token': tokens['access_token'],
                'refresh_token': tokens['refresh_token'],
                'expires_in': tokens['expires_in'],
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'name': user.name,
                    'phone': user.phone,
                    'email_verified': user.email_verified,
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'로그인 처리 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
