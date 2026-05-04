"""
뉴스레터 공개 API (newsLetterModelPlan.md §2)
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from sites.public_api.models import PublicMemberShip
from sites.public_api.newsletter_service import subscribe_from_modal
from sites.public_api.utils import get_token_from_request, verify_jwt_token


def _client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or ''


def _optional_member(request) -> PublicMemberShip | None:
    token = get_token_from_request(request)
    payload = verify_jwt_token(token, token_type='access') if token else None
    if not payload:
        return None
    user_id = payload.get('user_id')
    try:
        return PublicMemberShip.objects.get(member_sid=int(user_id), is_active=True)
    except (PublicMemberShip.DoesNotExist, ValueError, TypeError):
        return None


class NewsletterSubscribeView(APIView):
    """POST /api/newsletter/subscribe (§2-1, §2-4)"""
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        email = (data.get('email') or '').strip()
        name = (data.get('name') or '').strip()
        agree_privacy = bool(data.get('agreePrivacy'))
        agree_marketing = bool(data.get('agreeMarketing'))

        try:
            validate_email(email)
        except ValidationError:
            return Response({'error': '올바른 이메일 형식이 아닙니다.'}, status=status.HTTP_400_BAD_REQUEST)

        member = _optional_member(request)
        ok, err = subscribe_from_modal(
            email=email,
            name=name,
            agree_privacy=agree_privacy,
            agree_marketing=agree_marketing,
            member=member,
            ip_address=_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '') or '',
        )
        if not ok:
            return Response({'error': err or '처리할 수 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'b2n2027ApiResponse': {
                    'ErrorCode': '00',
                    'Message': '구독 완료',
                    'Result': {},
                }
            },
            status=status.HTTP_200_OK,
        )
