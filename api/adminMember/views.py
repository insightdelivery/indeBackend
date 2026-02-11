"""
관리자 회원 API 뷰
로그인, 회원가입 등
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone
from datetime import datetime
from api.models import AdminMemberShip
from core.models import AuditLog
from api.adminMember.serializers import AdminRegisterSerializer, AdminLoginSerializer, AdminUpdateSerializer
from api.adminMember.utils import create_admin_member_jwt_tokens
from sites.admin_api.authentication import AdminJWTAuthentication


class AdminRegisterView(APIView):
    """
    관리자 회원 가입 API
    관리자 페이지 회원으로 가입합니다.
    토큰 인증이 필요합니다.
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        관리자 회원 가입 처리
        
        요청 파라미터:
        - memberShipId: 회원 ID (필수)
        - password: 비밀번호 (필수, 최소 8자)
        - password_confirm: 비밀번호 확인 (필수)
        - memberShipName: 이름 (필수)
        - memberShipEmail: 이메일 (필수)
        - memberShipPhone: 전화번호 (선택)
        - memberShipLevel: 회원 레벨 (선택, 기본값: 1)
        - is_admin: 관리자 여부 (선택, 기본값: false)
        
        응답:
        - access_token: Access Token
        - refresh_token: Refresh Token
        - expires_in: Access Token 만료 시간 (초)
        - user: 사용자 정보
        """
        serializer = AdminRegisterSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'error': '입력값이 올바르지 않습니다.',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 인증 확인
            if not hasattr(request, 'user') or not request.user:
                return Response({
                    'error': '인증이 필요합니다. 로그인 후 다시 시도해주세요.'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # request.user가 AdminMemberShip인지 확인
            if not isinstance(request.user, AdminMemberShip):
                return Response({
                    'error': '이 API는 관리자 회원(AdminMemberShip)만 사용할 수 있습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # memberShipSid는 모델의 default 함수에서 자동 생성됨
            # 관리자 회원 생성
            from django.contrib.auth.hashers import make_password
            
            admin_member = AdminMemberShip(
                memberShipId=serializer.validated_data['memberShipId'],
                memberShipName=serializer.validated_data['memberShipName'],
                memberShipEmail=serializer.validated_data['memberShipEmail'],
                memberShipPhone=serializer.validated_data.get('memberShipPhone', ''),
                memberShipLevel=serializer.validated_data.get('memberShipLevel', 1),
                is_admin=serializer.validated_data.get('is_admin', False),
                is_active=True,
                memberShipPassword=make_password(serializer.validated_data['password']),  # 비밀번호 해시화
            )
            
            # 저장 (memberShipSid가 자동 생성됨)
            admin_member.save()
            
            # 회원 가입 로그 기록 (등록한 관리자 정보 기록)
            AuditLog.objects.create(
                user_id=str(request.user.memberShipSid),  # 등록한 관리자의 memberShipSid 저장
                site_slug='admin_api',
                action='create',
                resource='adminMemberShip',
                resource_id=str(admin_member.memberShipSid),
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={
                    'status': 'success',
                    'action': 'register',
                    'created_memberShipId': admin_member.memberShipId,
                    'created_memberShipName': admin_member.memberShipName,
                    'created_by': request.user.memberShipId,
                }
            )
            
            # 성공 응답 (토큰은 반환하지 않음, 등록만 수행)
            return Response({
                'message': '관리자가 성공적으로 등록되었습니다.',
                'user': {
                    'memberShipSid': str(admin_member.memberShipSid),
                    'memberShipId': admin_member.memberShipId,
                    'memberShipName': admin_member.memberShipName,
                    'memberShipEmail': admin_member.memberShipEmail,
                    'memberShipPhone': admin_member.memberShipPhone,
                    'memberShipLevel': admin_member.memberShipLevel,
                    'is_admin': admin_member.is_admin,
                    'is_active': admin_member.is_active,
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


class AdminLoginView(APIView):
    """
    관리자 회원 로그인 API
    memberShipId와 비밀번호로 로그인하여 JWT 토큰을 발급받습니다.
    """
    permission_classes = [AllowAny]  # 로그인은 인증 불필요
    
    def post(self, request):
        """
        관리자 회원 로그인 처리
        
        요청 파라미터:
        - memberShipId: 회원 ID (필수)
        - password: 비밀번호 (필수)
        
        응답:
        - access_token: Access Token (15분 만료)
        - refresh_token: Refresh Token (7일 만료)
        - expires_in: Access Token 만료 시간 (초)
        - user: 사용자 정보
        """
        print(f"\n{'='*60}")
        print(f"[Login Debug] 로그인 API 호출됨")
        print(f"[Login Debug] 요청 데이터: {request.data}")
        print(f"{'='*60}")
        
        serializer = AdminLoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            print(f"[Login Debug] ❌ 시리얼라이저 검증 실패: {serializer.errors}")
            return Response({
                'error': '입력값이 올바르지 않습니다.',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        memberShipId = serializer.validated_data['memberShipId']
        password = serializer.validated_data['password']
        
        print(f"[Login Debug] 시리얼라이저 검증 성공")
        print(f"[Login Debug] memberShipId: {memberShipId}")
        print(f"[Login Debug] password 길이: {len(password)}")
        
        try:
            # 관리자 회원 조회
            print(f"[Login Debug] 관리자 조회 시작...")
            print(f"[Login Debug] 조회 조건: memberShipId='{memberShipId}', is_active=True")
            
            try:
                admin_member = AdminMemberShip.objects.get(
                    memberShipId=memberShipId,
                    is_active=True
                )
                print(f"[Login Debug] ✅ 관리자 조회 성공")
                print(f"[Login Debug] 조회된 관리자 SID: {admin_member.memberShipSid}")
                print(f"[Login Debug] 조회된 관리자 이름: {admin_member.memberShipName}")
            except AdminMemberShip.DoesNotExist:
                print(f"[Login Debug] ❌ 관리자를 찾을 수 없습니다!")
                print(f"[Login Debug] memberShipId='{memberShipId}'로 조회 시도")
                
                # is_active 조건 없이 조회해보기
                try:
                    admin_inactive = AdminMemberShip.objects.get(memberShipId=memberShipId)
                    print(f"[Login Debug] ⚠️  관리자는 존재하지만 is_active={admin_inactive.is_active} (비활성화됨)")
                except AdminMemberShip.DoesNotExist:
                    print(f"[Login Debug] ❌ memberShipId='{memberShipId}'로 등록된 관리자가 없습니다")
                    # 모든 관리자 ID 목록 출력 (디버깅용)
                    all_admins = AdminMemberShip.objects.all()[:5]
                    print(f"[Login Debug] 등록된 관리자 목록 (최대 5명):")
                    for admin in all_admins:
                        print(f"  - {admin.memberShipId} (활성: {admin.is_active})")
                
                return Response({
                    'error': '회원 ID 또는 비밀번호가 올바르지 않습니다.'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 비밀번호 확인 (디버깅 정보 출력)
            print(f"\n{'='*60}")
            print(f"[Login Debug] 로그인 시도")
            print(f"{'='*60}")
            print(f"[Login Debug] memberShipId: {memberShipId}")
            print(f"[Login Debug] 입력된 비밀번호: '{password}' (길이: {len(password)})")
            print(f"[Login Debug] 관리자 SID: {admin_member.memberShipSid}")
            print(f"[Login Debug] 관리자 이름: {admin_member.memberShipName}")
            print(f"[Login Debug] is_active: {admin_member.is_active}")
            
            # DB에 저장된 비밀번호 확인
            stored_password = admin_member.memberShipPassword
            print(f"[Login Debug] DB에 저장된 비밀번호 해시:")
            print(f"  - None인가: {stored_password is None}")
            print(f"  - 빈 문자열인가: {stored_password == '' if stored_password else 'N/A'}")
            print(f"  - 길이: {len(stored_password) if stored_password else 0}")
            if stored_password:
                print(f"  - 해시 형식: {stored_password[:80]}...")
                print(f"  - 전체 해시: {stored_password}")
            else:
                print(f"  - ⚠️  비밀번호가 NULL이거나 빈 문자열입니다!")
            
            # 비밀번호가 없거나 빈 문자열인 경우
            if not stored_password or stored_password.strip() == '':
                print(f"[Login Debug] ❌ 비밀번호가 저장되지 않았습니다!")
                return Response({
                    'error': '비밀번호가 설정되지 않았습니다. 관리자에게 문의하세요.'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 비밀번호 확인
            print(f"[Login Debug] check_password() 호출 중...")
            password_check_result = admin_member.check_password(password)
            print(f"[Login Debug] check_password() 결과: {password_check_result}")
            
            if not password_check_result:
                # 추가 디버깅: 직접 check_password 테스트
                from django.contrib.auth.hashers import check_password as django_check_password
                direct_check = django_check_password(password, stored_password)
                print(f"[Login Debug] 직접 django_check_password() 결과: {direct_check}")
                
                # 비밀번호를 새로 해시화해서 비교
                from django.contrib.auth.hashers import make_password
                new_hash = make_password(password)
                print(f"[Login Debug] 입력한 비밀번호를 새로 해시화:")
                print(f"  - 새 해시: {new_hash[:80]}...")
                print(f"  - 저장된 해시와 동일한가: {stored_password == new_hash}")
                print(f"  - 새 해시로 검증: {django_check_password(password, new_hash)}")
                
                # 로그인 실패 로그 기록
                AuditLog.objects.create(
                    user_id=str(admin_member.memberShipSid),  # memberShipSid 저장
                    site_slug='admin_api',
                    action='login',
                    resource='adminMemberShip',
                    resource_id=str(admin_member.memberShipSid),
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    details={
                        'status': 'failed',
                        'reason': 'invalid_password',
                        'memberShipId': memberShipId,
                        'password_length': len(password),
                        'stored_hash_length': len(admin_member.memberShipPassword) if admin_member.memberShipPassword else 0,
                    }
                )
                return Response({
                    'error': '회원 ID 또는 비밀번호가 올바르지 않습니다.'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 마지막 로그인 시간 및 로그인 횟수 업데이트
            admin_member.last_login = timezone.now()
            admin_member.login_count += 1
            admin_member.save(update_fields=['last_login', 'login_count'])
            
            # JWT 토큰 생성
            tokens = create_admin_member_jwt_tokens(admin_member)
            
            # 로그인 성공 로그 기록
            AuditLog.objects.create(
                user_id=str(admin_member.memberShipSid),  # memberShipSid 저장
                site_slug='admin_api',
                action='login',
                resource='adminMemberShip',
                resource_id=str(admin_member.memberShipSid),
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={
                    'status': 'success',
                    'memberShipId': admin_member.memberShipId,
                    'memberShipName': admin_member.memberShipName,
                }
            )
            
            # 성공 응답
            return Response({
                'access_token': tokens['access_token'],
                'refresh_token': tokens['refresh_token'],
                'expires_in': tokens['expires_in'],
                'user': {
                    'memberShipSid': str(admin_member.memberShipSid),
                    'memberShipId': admin_member.memberShipId,
                    'memberShipName': admin_member.memberShipName,
                    'memberShipEmail': admin_member.memberShipEmail,
                    'memberShipPhone': admin_member.memberShipPhone,
                    'memberShipLevel': admin_member.memberShipLevel,
                    'is_admin': admin_member.is_admin,
                    'last_login': admin_member.last_login.strftime('%Y-%m-%d %H:%M:%S') if admin_member.last_login else None,
                    'login_count': admin_member.login_count,
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            print(f"\n{'='*60}")
            print(f"[Login Debug] ❌ 예외 발생!")
            print(f"[Login Debug] 오류 타입: {type(e).__name__}")
            print(f"[Login Debug] 오류 메시지: {str(e)}")
            print(f"[Login Debug] 전체 트레이스백:")
            print(error_traceback)
            print(f"{'='*60}\n")
            
            return Response({
                'error': f'로그인 처리 중 오류가 발생했습니다: {str(e)}',
                'error_type': type(e).__name__,
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class TokenRefreshView(APIView):
    """
    액세스 토큰으로 액세스 토큰과 리프레시 토큰 모두 갱신하는 API
    액세스 토큰이 만료되기 전에 새로운 토큰 쌍을 발급받습니다.
    만료된 토큰도 허용하여 토큰 갱신이 가능하도록 합니다.
    """
    permission_classes = [AllowAny]  # 인증 없이도 접근 가능 (토큰은 수동 검증)
    
    def post(self, request):
        """
        토큰 갱신 처리
        
        요청:
        - Authorization 헤더에 Bearer {access_token} 포함 (만료된 토큰도 허용)
        
        응답:
        - access_token: 새로운 Access Token
        - refresh_token: 새로운 Refresh Token
        - expires_in: Access Token 만료 시간 (초)
        - user: 사용자 정보
        """
        try:
            import jwt
            from django.conf import settings
            from datetime import timezone as dt_timezone
            
            # Authorization 헤더에서 토큰 추출
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if not auth_header or not auth_header.startswith('Bearer '):
                return Response({
                    'error': 'Authorization 헤더에 Bearer 토큰이 필요합니다.'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            token = auth_header.split(' ')[1]
            
            # 토큰 디코딩 (만료된 토큰도 허용)
            try:
                payload = jwt.decode(
                    token,
                    settings.JWT_SECRET_KEY,
                    algorithms=[settings.JWT_ALGORITHM],
                    options={"verify_exp": False}  # 만료 검증 비활성화
                )
            except jwt.InvalidTokenError:
                return Response({
                    'error': '유효하지 않은 토큰입니다.'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 토큰 타입 확인 (access 토큰만 허용)
            if payload.get('token_type') != 'access':
                return Response({
                    'error': 'Access 토큰만 사용할 수 있습니다.'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 사이트 확인
            if payload.get('site') != 'admin_api':
                return Response({
                    'error': '잘못된 사이트 토큰입니다.'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 사용자 조회
            user_id = payload.get('user_id')
            if not user_id:
                return Response({
                    'error': '토큰에 사용자 ID가 없습니다.'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            try:
                user = AdminMemberShip.objects.get(memberShipSid=user_id, is_active=True)
            except AdminMemberShip.DoesNotExist:
                return Response({
                    'error': '사용자를 찾을 수 없습니다.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # 현재 토큰의 발급 시간 확인
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                try:
                    payload = jwt.decode(
                        token,
                        settings.JWT_SECRET_KEY,
                        algorithms=[settings.JWT_ALGORITHM],
                        options={"verify_exp": False}  # 만료 검증은 나중에
                    )
                    token_issued_at = payload.get('iat')
                    if token_issued_at:
                        token_issued_at = datetime.fromtimestamp(token_issued_at, tz=dt_timezone.utc)
                        
                        # 사용자의 마지막 토큰 발급 시간 확인
                        if user.token_issued_at and token_issued_at < user.token_issued_at:
                            # 로그아웃 후 발급된 토큰이므로 무효화
                            return Response({
                                'error': '이 토큰은 로그아웃되어 무효화되었습니다.'
                            }, status=status.HTTP_401_UNAUTHORIZED)
                except jwt.InvalidTokenError:
                    return Response({
                        'error': '유효하지 않은 토큰입니다.'
                    }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 새로운 JWT 토큰 생성
            tokens = create_admin_member_jwt_tokens(user)
            
            # 토큰 갱신 로그 기록
            AuditLog.objects.create(
                user_id=str(user.memberShipSid),
                site_slug='admin_api',
                action='update',
                resource='adminMemberShip',
                resource_id=str(user.memberShipSid),
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={
                    'status': 'success',
                    'action': 'token_refresh',
                    'memberShipId': user.memberShipId,
                    'memberShipName': user.memberShipName,
                }
            )
            
            return Response({
                'access_token': tokens['access_token'],
                'refresh_token': tokens['refresh_token'],
                'expires_in': tokens['expires_in'],
                'user': {
                    'memberShipSid': str(user.memberShipSid),
                    'memberShipId': user.memberShipId,
                    'memberShipName': user.memberShipName,
                    'memberShipEmail': user.memberShipEmail,
                    'memberShipPhone': user.memberShipPhone,
                    'memberShipLevel': user.memberShipLevel,
                    'is_admin': user.is_admin,
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'토큰 갱신 처리 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AdminLogoutView(APIView):
    """
    관리자 회원 로그아웃 API
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        관리자 회원 로그아웃 처리
        로그아웃 시 모든 토큰을 무효화하고 로그아웃 로그를 기록합니다.
        """
        try:
            # request.user가 AdminMemberShip인지 확인
            if hasattr(request.user, 'memberShipSid'):
                # AdminMemberShip인 경우
                resource_id = str(request.user.memberShipSid)
                member_id = request.user.memberShipId
                member_name = request.user.memberShipName
                
                # 토큰 무효화: token_issued_at을 현재 시간으로 업데이트
                # 이렇게 하면 이전에 발급된 모든 토큰이 무효화됨
                request.user.token_issued_at = timezone.now()
                request.user.save(update_fields=['token_issued_at'])
            else:
                # Account인 경우 (하위 호환성)
                resource_id = str(request.user.id)
                member_id = request.user.email
                member_name = request.user.name
            
            # 로그아웃 로그 기록
            AuditLog.objects.create(
                user_id=resource_id,  # memberShipSid 저장
                site_slug='admin_api',
                action='logout',
                resource='adminMemberShip',
                resource_id=resource_id,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={
                    'status': 'success',
                    'memberShipId': member_id,
                    'memberShipName': member_name,
                }
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


class AdminListView(APIView):
    """
    관리자 목록 조회 API
    액세스 토큰이 유효한 관리자만 조회 가능
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        관리자 목록 조회
        
        요청:
        - Authorization 헤더에 Bearer {access_token} 포함
        
        응답:
        - admins: 관리자 목록 배열
        - total: 전체 관리자 수
        """
        try:
            import jwt
            from django.conf import settings
            from datetime import timezone as dt_timezone
            
            # request.user가 AdminMemberShip인지 확인
            if not isinstance(request.user, AdminMemberShip):
                return Response({
                    'error': '이 API는 관리자 회원(AdminMemberShip)만 사용할 수 있습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # 현재 토큰의 발급 시간 확인 (토큰 무효화 체크)
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                try:
                    payload = jwt.decode(
                        token,
                        settings.JWT_SECRET_KEY,
                        algorithms=[settings.JWT_ALGORITHM],
                        options={"verify_exp": False}  # 만료 검증은 나중에
                    )
                    token_issued_at = payload.get('iat')
                    if token_issued_at:
                        token_issued_at = datetime.fromtimestamp(token_issued_at, tz=dt_timezone.utc)
                        
                        # 사용자의 마지막 토큰 발급 시간 확인
                        if request.user.token_issued_at and token_issued_at < request.user.token_issued_at:
                            # 로그아웃 후 발급된 토큰이므로 무효화
                            return Response({
                                'error': '이 토큰은 로그아웃되어 무효화되었습니다.'
                            }, status=status.HTTP_401_UNAUTHORIZED)
                except jwt.InvalidTokenError:
                    return Response({
                        'error': '유효하지 않은 토큰입니다.'
                    }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 관리자 목록 조회 (비밀번호 제외)
            admin_members = AdminMemberShip.objects.all().order_by('-created_at')
            
            # 관리자 목록을 딕셔너리로 변환
            admin_list = []
            for admin in admin_members:
                admin_list.append({
                    'memberShipSid': str(admin.memberShipSid),
                    'memberShipId': admin.memberShipId,
                    'memberShipName': admin.memberShipName,
                    'memberShipEmail': admin.memberShipEmail,
                    'memberShipPhone': admin.memberShipPhone or '',
                    'memberShipLevel': admin.memberShipLevel,
                    'is_admin': admin.is_admin,
                    'is_active': admin.is_active,
                    'last_login': admin.last_login.strftime('%Y-%m-%d %H:%M:%S') if admin.last_login else None,
                    'login_count': admin.login_count,
                    'created_at': admin.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'updated_at': admin.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                })
            
            # 조회 로그 기록
            AuditLog.objects.create(
                user_id=str(request.user.memberShipSid),
                site_slug='admin_api',
                action='read',
                resource='adminMemberShip',
                resource_id='list',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={
                    'status': 'success',
                    'action': 'list',
                    'memberShipId': request.user.memberShipId,
                    'memberShipName': request.user.memberShipName,
                    'total_count': len(admin_list),
                }
            )
            
            return Response({
                'admins': admin_list,
                'total': len(admin_list),
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'관리자 목록 조회 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AdminUpdateView(APIView):
    """
    관리자 회원 수정 API
    관리자 정보를 수정합니다.
    토큰 인증이 필요합니다.
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def put(self, request, memberShipSid=None):
        """
        관리자 회원 수정 처리
        
        요청 파라미터:
        - memberShipSid: 수정할 관리자의 SID (URL 파라미터 또는 body)
        - memberShipName: 이름 (선택)
        - memberShipEmail: 이메일 (선택)
        - memberShipPhone: 전화번호 (선택)
        - memberShipLevel: 회원 레벨 (선택)
        - is_admin: 관리자 여부 (선택)
        - is_active: 활성화 여부 (선택)
        - password: 비밀번호 (변경 시에만 입력, 선택)
        - password_confirm: 비밀번호 확인 (변경 시에만 입력, 선택)
        
        응답:
        - user: 수정된 사용자 정보
        """
        # memberShipSid가 URL 파라미터로 전달되지 않으면 body에서 가져오기
        if not memberShipSid:
            memberShipSid = request.data.get('memberShipSid')
        
        if not memberShipSid:
            return Response({
                'error': 'memberShipSid가 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = AdminUpdateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'error': '입력값이 올바르지 않습니다.',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # request.user가 AdminMemberShip인지 확인
            if not isinstance(request.user, AdminMemberShip):
                return Response({
                    'error': '이 API는 관리자 회원(AdminMemberShip)만 사용할 수 있습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # 수정할 관리자 조회
            try:
                admin_member = AdminMemberShip.objects.get(memberShipSid=memberShipSid)
            except AdminMemberShip.DoesNotExist:
                return Response({
                    'error': '관리자를 찾을 수 없습니다.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # 이메일 중복 확인 (자기 자신 제외)
            if 'memberShipEmail' in serializer.validated_data:
                email = serializer.validated_data['memberShipEmail']
                if AdminMemberShip.objects.filter(memberShipEmail=email).exclude(memberShipSid=memberShipSid).exists():
                    return Response({
                        'error': '이미 사용 중인 이메일입니다.'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # 수정할 필드 업데이트
            if 'memberShipName' in serializer.validated_data:
                admin_member.memberShipName = serializer.validated_data['memberShipName']
            if 'memberShipEmail' in serializer.validated_data:
                admin_member.memberShipEmail = serializer.validated_data['memberShipEmail']
            if 'memberShipPhone' in serializer.validated_data:
                admin_member.memberShipPhone = serializer.validated_data['memberShipPhone']
            if 'memberShipLevel' in serializer.validated_data:
                admin_member.memberShipLevel = serializer.validated_data['memberShipLevel']
            if 'is_admin' in serializer.validated_data:
                admin_member.is_admin = serializer.validated_data['is_admin']
            if 'is_active' in serializer.validated_data:
                admin_member.is_active = serializer.validated_data['is_active']
            
            # 비밀번호 변경
            if 'password' in serializer.validated_data and serializer.validated_data['password']:
                admin_member.set_password(serializer.validated_data['password'])
            
            # 저장
            admin_member.save()
            
            # 수정 로그 기록
            AuditLog.objects.create(
                user_id=str(request.user.memberShipSid),  # 수정한 관리자의 memberShipSid 저장
                site_slug='admin_api',
                action='update',
                resource='adminMemberShip',
                resource_id=str(admin_member.memberShipSid),
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={
                    'status': 'success',
                    'action': 'update',
                    'updated_memberShipId': admin_member.memberShipId,
                    'updated_memberShipName': admin_member.memberShipName,
                    'updated_by': request.user.memberShipId,
                    'updated_fields': list(serializer.validated_data.keys()),
                }
            )
            
            # 성공 응답
            return Response({
                'message': '관리자 정보가 성공적으로 수정되었습니다.',
                'user': {
                    'memberShipSid': str(admin_member.memberShipSid),
                    'memberShipId': admin_member.memberShipId,
                    'memberShipName': admin_member.memberShipName,
                    'memberShipEmail': admin_member.memberShipEmail,
                    'memberShipPhone': admin_member.memberShipPhone,
                    'memberShipLevel': admin_member.memberShipLevel,
                    'is_admin': admin_member.is_admin,
                    'is_active': admin_member.is_active,
                    'last_login': admin_member.last_login.strftime('%Y-%m-%d %H:%M:%S') if admin_member.last_login else None,
                    'login_count': admin_member.login_count,
                    'created_at': admin_member.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'updated_at': admin_member.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'관리자 수정 처리 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AdminDeleteView(APIView):
    """
    관리자 회원 삭제 API
    관리자를 삭제합니다 (실제로는 is_active를 False로 설정).
    토큰 인증이 필요합니다.
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, memberShipSid=None):
        """
        관리자 회원 삭제 처리 (실제로는 비활성화)
        
        요청 파라미터:
        - memberShipSid: 삭제할 관리자의 SID (URL 파라미터 또는 body)
        
        응답:
        - message: 삭제 완료 메시지
        """
        # memberShipSid가 URL 파라미터로 전달되지 않으면 body에서 가져오기
        if not memberShipSid:
            memberShipSid = request.data.get('memberShipSid')
        
        if not memberShipSid:
            return Response({
                'error': 'memberShipSid가 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # request.user가 AdminMemberShip인지 확인
            if not isinstance(request.user, AdminMemberShip):
                return Response({
                    'error': '이 API는 관리자 회원(AdminMemberShip)만 사용할 수 있습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # 자기 자신을 삭제하려는 경우 방지
            if str(request.user.memberShipSid) == str(memberShipSid):
                return Response({
                    'error': '자기 자신을 삭제할 수 없습니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 삭제할 관리자 조회
            try:
                admin_member = AdminMemberShip.objects.get(memberShipSid=memberShipSid)
            except AdminMemberShip.DoesNotExist:
                return Response({
                    'error': '관리자를 찾을 수 없습니다.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # 이미 비활성화된 경우
            if not admin_member.is_active:
                return Response({
                    'error': '이미 삭제된 관리자입니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 관리자 정보 저장 (로그용)
            deleted_member_id = admin_member.memberShipId
            deleted_member_name = admin_member.memberShipName
            
            # 실제로는 삭제하지 않고 is_active를 False로 설정
            admin_member.is_active = False
            admin_member.save(update_fields=['is_active'])
            
            # 삭제 로그 기록
            AuditLog.objects.create(
                user_id=str(request.user.memberShipSid),  # 삭제한 관리자의 memberShipSid 저장
                site_slug='admin_api',
                action='delete',
                resource='adminMemberShip',
                resource_id=str(admin_member.memberShipSid),
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={
                    'status': 'success',
                    'action': 'delete',
                    'deleted_memberShipId': deleted_member_id,
                    'deleted_memberShipName': deleted_member_name,
                    'deleted_by': request.user.memberShipId,
                }
            )
            
            # 성공 응답
            return Response({
                'message': '관리자가 성공적으로 삭제되었습니다.'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'관리자 삭제 처리 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

