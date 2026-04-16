from __future__ import annotations

from django.db import transaction
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.utils import create_success_response, create_error_response
from sites.admin_api.authentication import AdminJWTAuthentication
from sites.admin_api.permissions import MenuPermission
from core.models import Account
from sites.public_api.models import PublicMemberShip

from apps.content_comments.models import ContentComment
from apps.content_comments.services import validate_content_type, get_content_gate, bump_comment_count


def _mask_text(c: ContentComment) -> str:
    return "삭제된 댓글입니다" if c.is_deleted else (c.comment_text or "")


def _resolve_public_admin_member(account: Account) -> PublicMemberShip | None:
    if not account:
        return None
    return (
        PublicMemberShip.objects.filter(email=account.email, is_active=True, is_staff=True).order_by("-member_sid").first()
    )


class AdminCommentListByContentView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]

    def get(self, request):
        ct = validate_content_type(request.query_params.get("contentType") or request.query_params.get("content_type") or "")
        raw_id = request.query_params.get("contentId") or request.query_params.get("content_id") or ""
        try:
            cid = int(str(raw_id).strip(), 10)
        except Exception:
            cid = 0

        if not ct or cid <= 0:
            return Response(create_error_response("잘못된 요청입니다."), status=status.HTTP_400_BAD_REQUEST)

        gate = get_content_gate(ct, cid)
        if not gate.exists:
            return Response(create_error_response("콘텐츠를 찾을 수 없습니다.", "01"), status=status.HTTP_404_NOT_FOUND)

        roots = list(
            ContentComment.objects.filter(content_type=ct, content_id=cid, depth=1)
            .select_related("user")
            .order_by("-created_at", "-id")[:300]
        )
        root_ids = [c.id for c in roots]
        replies = []
        if root_ids:
            replies = list(
                ContentComment.objects.filter(parent_id__in=root_ids, depth=2)
                .select_related("user")
                .order_by("created_at", "id")[:600]
            )
        by_parent = {}
        for r in replies:
            by_parent.setdefault(int(r.parent_id), []).append(r)

        def user_payload(c: ContentComment):
            u = c.user
            return {"id": int(u.member_sid), "email": u.email, "nickname": u.nickname, "isAdmin": bool(u.is_staff)}

        out = []
        for c in roots:
            out.append(
                {
                    "id": int(c.id),
                    "user": user_payload(c),
                    "text": _mask_text(c),
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "is_deleted": bool(c.is_deleted),
                    "replies": [
                        {
                            "id": int(r.id),
                            "user": user_payload(r),
                            "text": _mask_text(r),
                            "created_at": r.created_at.isoformat() if r.created_at else None,
                            "is_deleted": bool(r.is_deleted),
                        }
                        for r in by_parent.get(int(c.id), [])
                    ],
                }
            )

        staff_members = list(
            PublicMemberShip.objects.filter(is_active=True, is_staff=True)
            .order_by("member_sid")
            .values("member_sid", "nickname", "email")
        )
        staff_list = [
            {
                "member_sid": int(x["member_sid"]),
                "nickname": x.get("nickname") or "",
                "email": x.get("email") or "",
            }
            for x in staff_members
        ]

        return Response(
            create_success_response(
                {
                    "list": out,
                    "total": len(roots) + len(replies),
                    "staffMembers": staff_list,
                },
                "댓글 조회 성공",
            ),
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        """
        관리자 대댓글 작성
        body:
          - parent_id (필수)
          - comment_text (필수)
          - admin_member_sid (선택) : publicMemberShip.member_sid (is_staff=1)
        """
        user = request.user
        account = user if isinstance(user, Account) else None
        default_admin_member = _resolve_public_admin_member(account) if account else None

        body = request.data if isinstance(request.data, dict) else {}
        parent_id_raw = body.get("parent_id")
        admin_member_sid_raw = body.get("admin_member_sid")
        text = str(body.get("comment_text") or body.get("text") or "").strip()
        try:
            parent_id = int(str(parent_id_raw).strip(), 10)
        except Exception:
            parent_id = 0
        try:
            admin_member_sid = int(str(admin_member_sid_raw).strip(), 10) if admin_member_sid_raw is not None else None
        except Exception:
            admin_member_sid = None
        if parent_id <= 0 or not text:
            return Response(create_error_response("잘못된 요청입니다."), status=status.HTTP_400_BAD_REQUEST)

        parent = ContentComment.objects.filter(id=parent_id).first()
        if not parent:
            return Response(create_error_response("잘못된 parent_id"), status=status.HTTP_400_BAD_REQUEST)
        if parent.depth != 1:
            return Response(create_error_response("대댓글은 댓글에만 가능"), status=status.HTTP_400_BAD_REQUEST)

        admin_member = None
        if admin_member_sid is not None:
            admin_member = (
                PublicMemberShip.objects.filter(member_sid=admin_member_sid, is_active=True, is_staff=True).first()
            )
            if not admin_member:
                return Response(
                    create_error_response("선택한 관리자 작성자(member_sid)가 유효하지 않습니다."),
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            admin_member = default_admin_member
            if not admin_member:
                return Response(
                    create_error_response("publicMemberShip에 관리자 계정이 없습니다."),
                    status=status.HTTP_400_BAD_REQUEST,
                )

        with transaction.atomic():
            parent = ContentComment.objects.select_for_update().filter(id=parent_id).first()
            if not parent or parent.depth != 1:
                return Response(create_error_response("잘못된 parent_id"), status=status.HTTP_400_BAD_REQUEST)
            c = ContentComment.objects.create(
                content_type=parent.content_type,
                content_id=int(parent.content_id),
                user=admin_member,
                parent=parent,
                depth=2,
                comment_text=text,
            )
            # 관리자 대댓글은 commentCount 증가 없음

        return Response(create_success_response({"id": int(c.id)}, "대댓글 작성 성공"), status=status.HTTP_200_OK)


class AdminCommentDetailView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]

    def patch(self, request, comment_id: int):
        """
        관리자 대댓글 수정(관리자 댓글만)
        """
        body = request.data if isinstance(request.data, dict) else {}
        text = str(body.get("comment_text") or body.get("text") or "").strip()
        if not text:
            return Response(create_error_response("내용을 입력해주세요."), status=status.HTTP_400_BAD_REQUEST)

        c = ContentComment.objects.select_related("user").filter(id=comment_id).first()
        if not c:
            return Response(create_error_response("댓글을 찾을 수 없습니다.", "01"), status=status.HTTP_404_NOT_FOUND)
        if c.is_deleted:
            return Response(create_error_response("삭제된 댓글입니다."), status=status.HTTP_400_BAD_REQUEST)
        if c.depth != 2 or not bool(c.user.is_staff):
            return Response(create_error_response("관리자 대댓글만 수정할 수 있습니다."), status=status.HTTP_403_FORBIDDEN)

        c.comment_text = text
        c.save(update_fields=["comment_text", "updated_at"])
        return Response(create_success_response({"id": int(c.id)}, "댓글 수정 성공"), status=status.HTTP_200_OK)

    def delete(self, request, comment_id: int):
        c = ContentComment.objects.filter(id=comment_id).first()
        if not c:
            return Response(create_error_response("댓글을 찾을 수 없습니다.", "01"), status=status.HTTP_404_NOT_FOUND)
        if c.is_deleted:
            return Response(create_success_response({"id": int(c.id)}, "이미 삭제된 댓글입니다."), status=status.HTTP_200_OK)

        with transaction.atomic():
            locked = ContentComment.objects.select_for_update().filter(id=comment_id).first()
            if not locked:
                return Response(create_error_response("댓글을 찾을 수 없습니다.", "01"), status=status.HTTP_404_NOT_FOUND)
            if not locked.is_deleted:
                locked.soft_delete(by=None)
                # 관리자 대댓글(depth 2) 삭제는 차감 없음. 루트만 차감.
                if int(locked.depth) == 1:
                    bump_comment_count(locked.content_type, int(locked.content_id), -1)

        return Response(create_success_response({"id": int(c.id)}, "댓글 삭제 성공"), status=status.HTTP_200_OK)

