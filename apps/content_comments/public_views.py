from __future__ import annotations

from django.db import transaction
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from core.utils import create_success_response, create_error_response
from sites.public_api.library_useractivity_views import _get_member

from apps.content_comments.models import ContentComment
from apps.content_comments.services import validate_content_type, get_content_gate, bump_comment_count


def _mask_text(c: ContentComment) -> str:
    # www에서는 삭제된 댓글을 노출하지 않으므로, 여기서는 정상 텍스트만 처리
    return c.comment_text or ""


def _user_payload(c: ContentComment):
    u = c.user
    return {
        "id": int(u.member_sid),
        "nickname": u.nickname,
        "isAdmin": bool(u.is_staff),
    }


def _can_edit(member, c: ContentComment) -> bool:
    if not member:
        return False
    if c.is_deleted:
        return False
    # www에서는 관리자 대댓글 수정 불가
    if c.depth == 2:
        return False
    return int(c.user_id) == int(member.pk)


def _can_delete(member, c: ContentComment) -> bool:
    if not member:
        return False
    if c.is_deleted:
        return False
    if bool(getattr(member, "is_staff", False)):
        return True
    return int(c.user_id) == int(member.pk) and c.depth == 1


class PublicCommentListCreateView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        ct = validate_content_type(request.query_params.get("type") or request.query_params.get("content_type") or "")
        raw_id = request.query_params.get("id") or request.query_params.get("content_id") or ""
        try:
            cid = int(str(raw_id).strip(), 10)
        except Exception:
            cid = 0

        if not ct or cid <= 0:
            return Response(create_error_response("잘못된 요청입니다."), status=status.HTTP_400_BAD_REQUEST)

        gate = get_content_gate(ct, cid)
        if not gate.exists:
            return Response(create_error_response("콘텐츠를 찾을 수 없습니다.", "01"), status=status.HTTP_404_NOT_FOUND)

        # allowComment=false면 www에서 댓글이 보이면 안 됨 → 빈 리스트 반환
        if not gate.allow_comment:
            return Response(create_success_response({"list": [], "total": 0}, "댓글이 비활성화되었습니다."), status=status.HTTP_200_OK)

        member = _get_member(request)

        roots = list(
            ContentComment.objects.filter(
                content_type=ct,
                content_id=cid,
                depth=1,
                is_deleted=False,
            )
            .select_related("user")
            .order_by("-created_at", "-id")[:200]
        )
        root_ids = [c.id for c in roots]
        replies = []
        if root_ids:
            replies = list(
                ContentComment.objects.filter(parent_id__in=root_ids, depth=2, is_deleted=False)
                .select_related("user")
                .order_by("created_at", "id")[:400]
            )
        by_parent = {}
        for r in replies:
            by_parent.setdefault(int(r.parent_id), []).append(r)

        out = []
        for c in roots:
            out.append(
                {
                    "id": int(c.id),
                    "user": _user_payload(c),
                    "text": _mask_text(c),
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "is_deleted": False,
                    "is_mine": bool(member and int(member.pk) == int(c.user_id)),
                    "can_edit": _can_edit(member, c),
                    "can_delete": _can_delete(member, c),
                    "replies": [
                        {
                            "id": int(r.id),
                            "user": _user_payload(r),
                            "text": _mask_text(r),
                            "created_at": r.created_at.isoformat() if r.created_at else None,
                            "is_deleted": False,
                            "is_admin_reply": bool(r.user.is_staff),
                            "is_mine": bool(member and int(member.pk) == int(r.user_id)),
                            "can_edit": False,
                            "can_delete": _can_delete(member, r),
                        }
                        for r in by_parent.get(int(c.id), [])
                    ],
                }
            )

        return Response(
            create_success_response({"list": out, "total": len(roots) + len(replies)}, "댓글 조회 성공"),
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        member = _get_member(request)
        if not member:
            return Response(create_error_response("로그인이 필요합니다."), status=status.HTTP_401_UNAUTHORIZED)

        body = request.data if isinstance(request.data, dict) else {}
        ct = validate_content_type(str(body.get("content_type") or body.get("type") or ""))
        content_id_raw = body.get("content_id") or body.get("id")
        parent_id_raw = body.get("parent_id")
        text = str(body.get("comment_text") or body.get("text") or "").strip()

        try:
            cid = int(str(content_id_raw).strip(), 10)
        except Exception:
            cid = 0
        try:
            parent_id = int(str(parent_id_raw).strip(), 10) if parent_id_raw is not None else None
        except Exception:
            parent_id = None

        if not text:
            return Response(create_error_response("내용을 입력해주세요."), status=status.HTTP_400_BAD_REQUEST)

        if parent_id:
            # parent 기반으로 derive 가능
            parent = ContentComment.objects.select_related("user").filter(id=parent_id).first()
            if not parent:
                return Response(create_error_response("잘못된 parent_id"), status=status.HTTP_400_BAD_REQUEST)
            if ct is None or cid <= 0:
                ct = parent.content_type
                cid = int(parent.content_id)
            # parent_id 무결성(동일 content 범위)
            if parent.content_type != ct or int(parent.content_id) != int(cid):
                return Response(create_error_response("잘못된 parent_id"), status=status.HTTP_400_BAD_REQUEST)
            if parent.depth != 1:
                return Response(create_error_response("대댓글은 댓글에만 가능"), status=status.HTTP_400_BAD_REQUEST)
            if not bool(getattr(member, "is_staff", False)):
                return Response(create_error_response("관리자만 대댓글 작성 가능"), status=status.HTTP_403_FORBIDDEN)
        else:
            if ct is None or cid <= 0:
                return Response(create_error_response("잘못된 요청입니다."), status=status.HTTP_400_BAD_REQUEST)

        gate = get_content_gate(ct, cid)
        if not gate.exists:
            return Response(create_error_response("콘텐츠를 찾을 수 없습니다.", "01"), status=status.HTTP_404_NOT_FOUND)
        if not gate.allow_comment:
            return Response(create_error_response("댓글이 비활성화되었습니다."), status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            if parent_id:
                parent = ContentComment.objects.select_for_update().filter(id=parent_id).first()
                if not parent:
                    return Response(create_error_response("잘못된 parent_id"), status=status.HTTP_400_BAD_REQUEST)
                if parent.content_type != ct or int(parent.content_id) != int(cid) or parent.depth != 1:
                    return Response(create_error_response("잘못된 parent_id"), status=status.HTTP_400_BAD_REQUEST)
                c = ContentComment.objects.create(
                    content_type=ct,
                    content_id=cid,
                    user=member,
                    parent=parent,
                    depth=2,
                    comment_text=text,
                )
            else:
                c = ContentComment.objects.create(
                    content_type=ct,
                    content_id=cid,
                    user=member,
                    parent=None,
                    depth=1,
                    comment_text=text,
                )
            bump_comment_count(ct, cid, 1)

        return Response(
            create_success_response(
                {
                    "id": int(c.id),
                    "depth": int(c.depth),
                },
                "댓글 작성 성공",
            ),
            status=status.HTTP_200_OK,
        )


class PublicCommentDetailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def patch(self, request, comment_id: int):
        member = _get_member(request)
        if not member:
            return Response(create_error_response("로그인이 필요합니다."), status=status.HTTP_401_UNAUTHORIZED)

        c = ContentComment.objects.select_related("user").filter(id=comment_id).first()
        if not c:
            return Response(create_error_response("댓글을 찾을 수 없습니다.", "01"), status=status.HTTP_404_NOT_FOUND)
        if c.is_deleted:
            return Response(create_error_response("삭제된 댓글입니다."), status=status.HTTP_400_BAD_REQUEST)
        if c.depth != 1:
            return Response(create_error_response("수정할 수 없습니다."), status=status.HTTP_403_FORBIDDEN)
        if int(c.user_id) != int(member.pk):
            return Response(create_error_response("수정 권한이 없습니다."), status=status.HTTP_403_FORBIDDEN)

        gate = get_content_gate(c.content_type, int(c.content_id))
        if not gate.exists or not gate.allow_comment:
            return Response(create_error_response("댓글이 비활성화되었습니다."), status=status.HTTP_403_FORBIDDEN)

        body = request.data if isinstance(request.data, dict) else {}
        text = str(body.get("comment_text") or body.get("text") or "").strip()
        if not text:
            return Response(create_error_response("내용을 입력해주세요."), status=status.HTTP_400_BAD_REQUEST)

        c.comment_text = text
        c.save(update_fields=["comment_text", "updated_at"])
        return Response(create_success_response({"id": int(c.id)}, "댓글 수정 성공"), status=status.HTTP_200_OK)

    def delete(self, request, comment_id: int):
        member = _get_member(request)
        if not member:
            return Response(create_error_response("로그인이 필요합니다."), status=status.HTTP_401_UNAUTHORIZED)

        c = ContentComment.objects.select_related("user").filter(id=comment_id).first()
        if not c:
            return Response(create_error_response("댓글을 찾을 수 없습니다.", "01"), status=status.HTTP_404_NOT_FOUND)
        if c.is_deleted:
            return Response(create_success_response({"id": int(c.id)}, "이미 삭제된 댓글입니다."), status=status.HTTP_200_OK)

        if not _can_delete(member, c):
            return Response(create_error_response("삭제 권한이 없습니다."), status=status.HTTP_403_FORBIDDEN)

        gate = get_content_gate(c.content_type, int(c.content_id))
        # allowComment=false라도 삭제는 허용(본인/관리자)
        if not gate.exists:
            return Response(create_error_response("콘텐츠를 찾을 수 없습니다.", "01"), status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            # 중복 감소 방지
            locked = ContentComment.objects.select_for_update().filter(id=c.id).first()
            if not locked:
                return Response(create_error_response("댓글을 찾을 수 없습니다.", "01"), status=status.HTTP_404_NOT_FOUND)
            if not locked.is_deleted:
                locked.soft_delete(by=member)
                bump_comment_count(locked.content_type, int(locked.content_id), -1)

        return Response(create_success_response({"id": int(c.id)}, "댓글 삭제 성공"), status=status.HTTP_200_OK)

