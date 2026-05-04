"""공개 콘텐츠 저자 조회 (www 에디터 페이지 등)."""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from sites.admin_api.content_author.models import ContentAuthor
from sites.admin_api.content_author.s3_utils import profile_image_to_presigned
from core.utils import create_success_response, create_error_response


def _author_affiliation(ca: ContentAuthor) -> str:
    if ca.role == ContentAuthor.ROLE_DIRECTOR:
        return '디렉터'
    if ca.role == ContentAuthor.ROLE_EDITOR:
        return '에디터'
    return ''


class PublicContentAuthorProfileView(APIView):
    """GET /api/content-author/profile?author_id= — 저자 이름·소개·프로필(공개)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        raw = request.query_params.get('author_id', '').strip()
        if not raw:
            return Response(
                create_error_response('author_id가 필요합니다.', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            pk = int(raw, 10)
        except ValueError:
            return Response(
                create_error_response('author_id가 올바르지 않습니다.', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        if pk <= 0:
            return Response(
                create_error_response('author_id가 올바르지 않습니다.', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            ca = ContentAuthor.objects.get(author_id=pk)
        except ContentAuthor.DoesNotExist:
            return Response(
                create_error_response('저자를 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND,
            )
        img = (ca.profile_image or '').strip()
        if img:
            img = profile_image_to_presigned(img, expires_in=3600)
        else:
            img = None
        intro = (getattr(ca, 'editor_intro', None) or '').strip() or None
        data = {
            'author_id': ca.author_id,
            'name': ca.name,
            'authorAffiliation': _author_affiliation(ca),
            'authorProfileImage': img,
            'authorEditorIntro': intro,
        }
        return Response(
            create_success_response(data, '저자 프로필 조회 성공'),
            status=status.HTTP_200_OK,
        )
