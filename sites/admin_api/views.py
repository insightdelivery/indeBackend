"""
관리자 API 뷰
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
from sites.admin_api.serializers import LoginSerializer, RefreshTokenSerializer
from sites.admin_api.utils import create_admin_jwt_tokens
from sites.admin_api.authentication import AdminJWTAuthentication
from core.models import Account, AuditLog


class LoginView(APIView):
    """
    관리자 로그인 API
    이메일과 비밀번호로 로그인하여 JWT 토큰을 발급받습니다.
    """
    permission_classes = [AllowAny]  # 로그인은 인증 불필요
    
    def post(self, request):
        """
        로그인 처리
        
        요청 파라미터:
        - email: 이메일 주소 (필수)
        - password: 비밀번호 (필수)
        
        응답:
        - access_token: Access Token (15분 만료)
        - refresh_token: Refresh Token (7일 만료)
        - expires_in: Access Token 만료 시간 (초)
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
            
            # 관리자 권한 확인
            if not user.is_staff:
                return Response({
                    'error': '관리자 권한이 없습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # 비밀번호 확인
            if not user.check_password(password):
                # 로그인 실패 로그 기록
                AuditLog.objects.create(
                    user_id=str(user.id),  # Account의 id 저장
                    site_slug='admin_api',
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
            tokens = create_admin_jwt_tokens(user)
            
            # 로그인 성공 로그 기록
            AuditLog.objects.create(
                user_id=str(user.id),  # Account의 id 저장
                site_slug='admin_api',
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
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
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


class RefreshTokenView(APIView):
    """
    JWT 토큰 갱신 API
    Refresh Token을 사용하여 새로운 Access Token을 발급받습니다.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        토큰 갱신 처리
        
        요청 파라미터:
        - refresh_token: Refresh Token (필수)
        
        응답:
        - access_token: 새로운 Access Token
        - expires_in: Access Token 만료 시간 (초)
        """
        serializer = RefreshTokenSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'error': '입력값이 올바르지 않습니다.',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        refresh_token = serializer.validated_data['refresh_token']
        
        try:
            import jwt
            from django.conf import settings
            
            # Refresh Token 검증
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # 토큰 타입 확인
            if payload.get('token_type') != 'refresh':
                return Response({
                    'error': 'Invalid token type'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 사용자 조회
            user_id = payload.get('user_id')
            user = Account.objects.get(id=user_id, is_active=True, is_staff=True)
            
            # 새로운 Access Token 생성
            tokens = create_admin_jwt_tokens(user)
            
            return Response({
                'access_token': tokens['access_token'],
                'expires_in': tokens['expires_in'],
            }, status=status.HTTP_200_OK)
            
        except jwt.ExpiredSignatureError:
            return Response({
                'error': 'Refresh token has expired'
            }, status=status.HTTP_401_UNAUTHORIZED)
        except jwt.InvalidTokenError:
            return Response({
                'error': 'Invalid refresh token'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Account.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Token refresh failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogoutView(APIView):
    """
    로그아웃 API
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        로그아웃 처리
        로그아웃 로그를 기록합니다.
        """
        try:
            # 로그아웃 로그 기록
            # request.user가 Account 또는 AdminMemberShip일 수 있음
            user_id_value = str(request.user.id) if hasattr(request.user, 'id') else str(request.user.memberShipSid) if hasattr(request.user, 'memberShipSid') else None
            
            AuditLog.objects.create(
                user_id=user_id_value,  # Account의 id 또는 AdminMemberShip의 memberShipSid 저장
                site_slug='admin_api',
                action='logout',
                resource='account',
                resource_id=user_id_value,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'status': 'success'}
            )
            
            return Response({
                'message': '로그아웃되었습니다.'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'로그아웃 처리 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

