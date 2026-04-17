import json
import re
import requests
from datetime import datetime
from datetime import timedelta
from typing import Any
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.conf import settings
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import create_error_response, create_success_response
from sites.admin_api.authentication import AdminJWTAuthentication
from sites.admin_api.menu_codes import MenuCodes
from sites.admin_api.permissions import MenuPermission

from .models import (
    KakaoTemplate,
    MessageBatch,
    MessageDetail,
    MessageSenderNumber,
    MessageSenderEmail,
    MessageTemplate,
)
from .aligo_sms import send_mass_with_aligo, fetch_sms_list_all
from .aligo_kakao import fetch_kakao_alimtalk_history_detail, send_alimtalk_with_aligo
from .email_dispatch import send_email_batch_details
from .serializers import (
    KakaoTemplateSerializer,
    MessageBatchCreateSerializer,
    MessageBatchListSerializer,
    MessageBatchSerializer,
    MessageSenderNumberSerializer,
    MessageSenderEmailSerializer,
    MessageTemplateSerializer,
)


def _is_valid_receiver_email(value: str) -> bool:
    v = (value or "").strip()
    if not v:
        return False
    try:
        validate_email(v)
        return True
    except DjangoValidationError:
        return False


def _aligo_button_n_json_for_send(btn_raw: Any) -> str | None:
    """알리고 알림톡 폼 필드 `button_1` 등에 넣는 JSON 문자열로 정규화한다."""
    if btn_raw is None or btn_raw == [] or btn_raw == {}:
        return None
    parsed: Any = btn_raw
    if isinstance(btn_raw, str):
        s = btn_raw.strip()
        if not s:
            return None
        try:
            parsed = json.loads(s)
        except json.JSONDecodeError:
            return s[:16000] if len(s) > 16000 else s
    try:
        if isinstance(parsed, list):
            wrapped: dict[str, Any] = {"button": parsed}
        elif isinstance(parsed, dict) and "button" in parsed:
            wrapped = parsed
        elif isinstance(parsed, dict):
            wrapped = {"button": [parsed]}
        else:
            return None
        btn_s = json.dumps(wrapped, ensure_ascii=False)
    except (TypeError, ValueError):
        return None
    if not btn_s:
        return None
    return btn_s[:16000] if len(btn_s) > 16000 else btn_s


def _kakao_alimtalk_extras_from_template(tpl: KakaoTemplate | None) -> tuple[str | None, str | None]:
    """알리고 `emtitle_1`, `button_1` — `KakaoTemplate.emtitle`·`buttons` 기준."""
    if tpl is None:
        return None, None
    raw_em = getattr(tpl, "emtitle", None)
    em_s = str(raw_em).strip()[:500] if raw_em is not None and str(raw_em).strip() else None
    btn_s = _aligo_button_n_json_for_send(tpl.buttons)
    return em_s, btn_s


class KakaoTemplateListCreateView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_code = MenuCodes.SMS_KAKAO_SEND

    def get(self, request):
        status_filter = request.query_params.get("status")
        qs = KakaoTemplate.objects.all()
        if status_filter:
            qs = qs.filter(status=status_filter)
        data = KakaoTemplateSerializer(qs, many=True).data
        return Response(create_success_response(data, "카카오 템플릿 목록 조회 성공"))

    def post(self, request):
        serializer = KakaoTemplateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                create_error_response(str(serializer.errors), "01"),
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response(
            create_success_response(serializer.data, "카카오 템플릿이 등록되었습니다."),
            status=status.HTTP_201_CREATED,
        )


class KakaoTemplateDetailView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_code = MenuCodes.SMS_KAKAO_SEND

    def put(self, request, template_id: int):
        try:
            template = KakaoTemplate.objects.get(id=template_id)
        except KakaoTemplate.DoesNotExist:
            return Response(create_error_response("템플릿을 찾을 수 없습니다.", "04"), status=status.HTTP_404_NOT_FOUND)
        serializer = KakaoTemplateSerializer(template, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(create_error_response(str(serializer.errors), "01"), status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(create_success_response(serializer.data, "카카오 템플릿이 수정되었습니다."))

    def delete(self, request, template_id: int):
        deleted_count, _ = KakaoTemplate.objects.filter(id=template_id).delete()
        if deleted_count == 0:
            return Response(create_error_response("템플릿을 찾을 수 없습니다.", "04"), status=status.HTTP_404_NOT_FOUND)
        return Response(create_success_response(None, "카카오 템플릿이 삭제되었습니다."))


class MessageBatchListCreateView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]

    def get_menu_code(self, request):
        if request.method == "GET":
            # 문자 내역 + 이메일 내역 메뉴 중 하나라도 읽기 허용 시 목록 조회 가능
            return (MenuCodes.SMS_KAKAO_HISTORY, MenuCodes.EMAIL_HISTORY)
        body = request.data if isinstance(request.data, dict) else {}
        if body.get("type") == MessageBatch.TYPE_EMAIL:
            return MenuCodes.EMAIL_SEND
        return MenuCodes.SMS_KAKAO_SEND

    def get(self, request):
        qs = MessageBatch.objects.all().prefetch_related("details")
        status_filter = request.query_params.get("status")
        type_filter = request.query_params.get("type")
        if status_filter:
            qs = qs.filter(status=status_filter)
        if type_filter:
            qs = qs.filter(type=type_filter)
        qs = qs.annotate(detail_count=Count("details")).order_by("-requested_at", "-id")
        data = MessageBatchListSerializer(qs, many=True).data
        return Response(create_success_response(data, "전송 배치 목록 조회 성공"))

    def post(self, request):
        serializer = MessageBatchCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                create_error_response(str(serializer.errors), "01"),
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = serializer.validated_data
        details_payload = payload.pop("details")
        now = timezone.now()
        batch_status = payload.get("status") or MessageBatch.STATUS_PROCESSING
        is_scheduled_request = batch_status == MessageBatch.STATUS_SCHEDULED
        scheduled_at = payload.get("scheduled_at")
        if is_scheduled_request:
            if scheduled_at is None:
                return Response(
                    create_error_response("예약 발송은 예약 일시(scheduled_at)가 필요합니다.", "01"),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            min_allowed = now + timedelta(minutes=10)
            if scheduled_at < min_allowed:
                return Response(
                    create_error_response("예약 발송 시간은 현재 기준 최소 10분 이후여야 합니다.", "01"),
                    status=status.HTTP_400_BAD_REQUEST,
                )

        with transaction.atomic():
            batch = MessageBatch.objects.create(
                **payload,
                total_count=len(details_payload),
                requested_at=now,
                created_by_id=str(getattr(request.user, "memberShipSid", "")),
            )
            details = []
            for d in details_payload:
                if batch.type == MessageBatch.TYPE_EMAIL:
                    raw_email = (d.get("receiver_email") or "").strip()
                    is_ok = _is_valid_receiver_email(raw_email)
                    details.append(
                        MessageDetail(
                            batch=batch,
                            receiver_name=d.get("receiver_name", ""),
                            receiver_phone="",
                            receiver_email=raw_email,
                            template_id=d.get("template_id"),
                            template_name=d.get("template_name", ""),
                            variables=d.get("variables", {}),
                            final_content=d.get("final_content", ""),
                            status=MessageDetail.STATUS_SUCCESS if is_ok else MessageDetail.STATUS_EXCLUDED,
                            error_reason="" if is_ok else "invalid_email",
                        )
                    )
                else:
                    phone = (d.get("receiver_phone") or "").strip()
                    phone = "".join(ch for ch in phone if ch.isdigit())
                    is_valid_phone = bool(re.match(r"^01\d{8,9}$", phone))
                    details.append(
                        MessageDetail(
                            batch=batch,
                            receiver_name=d.get("receiver_name", ""),
                            receiver_phone=phone,
                            receiver_email=d.get("receiver_email", ""),
                            template_id=d.get("template_id"),
                            template_name=d.get("template_name", ""),
                            variables=d.get("variables", {}),
                            final_content=d.get("final_content", ""),
                            status=MessageDetail.STATUS_SUCCESS if is_valid_phone else MessageDetail.STATUS_EXCLUDED,
                            error_reason="" if is_valid_phone else "invalid_phone",
                        )
                    )
            MessageDetail.objects.bulk_create(details)

            valid_details = [d for d in details if d.status == MessageDetail.STATUS_SUCCESS]
            batch.excluded_count = len(details) - len(valid_details)
            batch.success_count = 0
            batch.fail_count = 0

            if batch.type == MessageBatch.TYPE_SMS and valid_details:
                db_valid_details = list(
                    MessageDetail.objects.filter(batch=batch, status=MessageDetail.STATUS_SUCCESS).order_by("id")
                )
                phones = [d.receiver_phone for d in db_valid_details]
                messages = [d.final_content or batch.content for d in db_valid_details]
                reserve_at = timezone.localtime(scheduled_at) if is_scheduled_request else None
                send_result = send_mass_with_aligo(batch.sender, batch.title, phones, messages, reserve_at=reserve_at)
                batch.api_response_logs = [send_result.get("raw")] if send_result.get("raw") is not None else []
                if send_result.get("ok"):
                    msg_id = str(send_result.get("msg_id") or "")
                    batch.result_snapshot = {
                        "provider": "aligo",
                        "msg_id": msg_id,
                        "msg_type": str(send_result.get("msg_type") or ""),
                        "is_reserved": is_scheduled_request,
                    }
                    success_cnt = int(send_result.get("success_cnt") or 0)
                    # 알리고 send_mass 응답은 수신자별 성공/실패를 직접 주지 않으므로 순차 매핑
                    for idx, d in enumerate(db_valid_details):
                        if idx < success_cnt:
                            d.status = MessageDetail.STATUS_SUCCESS
                            d.external_code = msg_id
                            d.external_message = str(send_result.get("message") or "")
                            d.error_reason = ""
                            if not is_scheduled_request:
                                d.sent_at = now
                        else:
                            d.status = MessageDetail.STATUS_FAIL
                            d.error_reason = "provider_error"
                            d.external_message = str(send_result.get("message") or "")
                        d.save(update_fields=["status", "external_code", "external_message", "sent_at", "error_reason", "updated_at"])
                    batch.success_count = success_cnt
                    batch.fail_count = max(0, len(db_valid_details) - success_cnt)
                    batch.is_processed = True
                    if is_scheduled_request:
                        batch.status = MessageBatch.STATUS_SCHEDULED
                        batch.completed_at = None
                    else:
                        batch.status = MessageBatch.STATUS_COMPLETED if batch.fail_count == 0 else MessageBatch.STATUS_FAILED
                        batch.completed_at = now
                else:
                    for d in db_valid_details:
                        d.status = MessageDetail.STATUS_FAIL
                        d.error_reason = "provider_error"
                        d.external_message = str(send_result.get("message") or "알리고 발송 실패")
                        d.save(update_fields=["status", "external_message", "error_reason", "updated_at"])
                    batch.success_count = 0
                    batch.fail_count = len(db_valid_details)
                    batch.is_processed = True
                    batch.status = MessageBatch.STATUS_FAILED
                    batch.completed_at = now
            elif batch.type == MessageBatch.TYPE_KAKAO and valid_details:
                db_valid_details = list(
                    MessageDetail.objects.filter(batch=batch, status=MessageDetail.STATUS_SUCCESS).order_by("id")
                )
                tpl_row = None
                tid = None
                for d in db_valid_details:
                    if d.template_id:
                        tid = d.template_id
                        break
                if tid is None and isinstance(batch.request_snapshot, dict):
                    raw_tid = batch.request_snapshot.get("templateId")
                    try:
                        tid = int(raw_tid) if raw_tid is not None and str(raw_tid).strip() != "" else None
                    except (TypeError, ValueError):
                        tid = None
                if tid is not None:
                    tpl_row = KakaoTemplate.objects.filter(id=tid).first()
                reserve_at = timezone.localtime(scheduled_at) if is_scheduled_request and scheduled_at else None
                if not tpl_row:
                    for d in db_valid_details:
                        d.status = MessageDetail.STATUS_FAIL
                        d.error_reason = "missing_template"
                        d.save(update_fields=["status", "error_reason", "updated_at"])
                    batch.success_count = 0
                    batch.fail_count = len(db_valid_details)
                    batch.is_processed = True
                    batch.status = MessageBatch.STATUS_FAILED
                    batch.completed_at = now
                    batch.api_response_logs = []
                else:
                    senderkey = (getattr(settings, "ALIGO_KAKAO_SENDERKEY", "") or "").strip()
                    subj_base = (batch.title or "").strip() or (tpl_row.template_name or "알림")[:200]
                    items = [
                        {
                            "phone": d.receiver_phone,
                            "recvname": d.receiver_name or "",
                            "subject": subj_base,
                            "message": (d.final_content or batch.content or "").strip(),
                        }
                        for d in db_valid_details
                    ]
                    emt, btn = _kakao_alimtalk_extras_from_template(tpl_row)
                    send_result = send_alimtalk_with_aligo(
                        batch.sender,
                        senderkey,
                        tpl_row.template_code,
                        items,
                        reserve_at=reserve_at,
                        batch_emtitle=emt,
                        batch_button=btn,
                    )
                    batch.api_response_logs = [send_result.get("raw")] if send_result.get("raw") is not None else []
                    if send_result.get("ok"):
                        success_cnt = int(send_result.get("success_cnt") or 0)
                        mid = str(send_result.get("mid") or "")
                        batch.result_snapshot = {
                            "provider": "aligo_kakao",
                            "tpl_code": tpl_row.template_code,
                            "mid": mid,
                            "is_reserved": is_scheduled_request,
                        }
                        for idx, d in enumerate(db_valid_details):
                            if idx < success_cnt:
                                d.status = MessageDetail.STATUS_SUCCESS
                                d.external_code = mid
                                d.external_message = str(send_result.get("message") or "")
                                d.error_reason = ""
                                if not is_scheduled_request:
                                    d.sent_at = now
                            else:
                                d.status = MessageDetail.STATUS_FAIL
                                d.error_reason = "provider_error"
                                d.external_message = str(send_result.get("message") or "")
                            d.save(
                                update_fields=[
                                    "status",
                                    "external_code",
                                    "external_message",
                                    "sent_at",
                                    "error_reason",
                                    "updated_at",
                                ]
                            )
                        batch.success_count = success_cnt
                        batch.fail_count = max(0, len(db_valid_details) - success_cnt)
                        batch.is_processed = True
                        if is_scheduled_request:
                            batch.status = MessageBatch.STATUS_SCHEDULED
                            batch.completed_at = None
                        else:
                            batch.status = (
                                MessageBatch.STATUS_COMPLETED if batch.fail_count == 0 else MessageBatch.STATUS_FAILED
                            )
                            batch.completed_at = now
                    else:
                        for d in db_valid_details:
                            d.status = MessageDetail.STATUS_FAIL
                            d.error_reason = "provider_error"
                            d.external_message = str(send_result.get("message") or "알리고 알림톡 발송 실패")
                            d.save(update_fields=["status", "external_message", "error_reason", "updated_at"])
                        batch.success_count = 0
                        batch.fail_count = len(db_valid_details)
                        batch.is_processed = True
                        batch.status = MessageBatch.STATUS_FAILED
                        batch.completed_at = now
            elif batch.type == MessageBatch.TYPE_EMAIL and valid_details:
                if is_scheduled_request:
                    batch.success_count = len(valid_details)
                    batch.fail_count = 0
                    batch.is_processed = False
                    batch.status = MessageBatch.STATUS_SCHEDULED
                    batch.completed_at = None
                else:
                    out = send_email_batch_details(batch, now=now)
                    batch.success_count = out["success"]
                    batch.fail_count = out["fail"]
                    batch.api_response_logs = out.get("logs") or []
                    batch.result_snapshot = {
                        "provider": "gmail_smtp",
                        "via": "core.mail.send_email",
                    }
                    batch.is_processed = True
                    batch.completed_at = now
                    batch.status = (
                        MessageBatch.STATUS_COMPLETED
                        if out["fail"] == 0
                        else MessageBatch.STATUS_FAILED
                    )
            else:
                # SMS·카카오·이메일 외이거나, 유효 수신자 0건 등 — 외부 발송 없이 집계만
                batch.success_count = len(valid_details)
                batch.fail_count = 0
                if is_scheduled_request:
                    batch.is_processed = False
                    batch.status = MessageBatch.STATUS_SCHEDULED
                    batch.completed_at = None
                else:
                    batch.is_processed = True
                    batch.status = MessageBatch.STATUS_COMPLETED
                    batch.completed_at = now
            batch.save()

        out = MessageBatchSerializer(batch).data
        return Response(create_success_response(out, "전송 배치가 생성되었습니다."), status=status.HTTP_201_CREATED)


class MessageBatchKakaoAligoHistoryDetailView(APIView):
    """알리고 akv10 `/akv10/history/detail/` — 배치에 연결된 mid로 수신번호별 결과 조회."""

    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_codes = (MenuCodes.SMS_KAKAO_HISTORY, MenuCodes.EMAIL_HISTORY)

    def get(self, request, batch_id: int):
        try:
            batch = MessageBatch.objects.prefetch_related("details").get(id=batch_id)
        except MessageBatch.DoesNotExist:
            return Response(create_error_response("배치를 찾을 수 없습니다.", "04"), status=status.HTTP_404_NOT_FOUND)
        if batch.type != MessageBatch.TYPE_KAKAO:
            return Response(create_error_response("카카오 알림톡 배치만 조회할 수 있습니다.", "01"), status=status.HTTP_400_BAD_REQUEST)
        rs = batch.result_snapshot or {}
        if isinstance(rs, dict):
            prov = rs.get("provider")
            if prov not in (None, "", "aligo_kakao"):
                return Response(
                    create_error_response("알리고 알림톡으로 발송된 배치만 알리고 상세조회가 가능합니다.", "01"),
                    status=status.HTTP_400_BAD_REQUEST,
                )
        mid = str(rs.get("mid") or "").strip() if isinstance(rs, dict) else ""
        if not mid:
            first_detail = batch.details.exclude(external_code="").first()
            mid = str(first_detail.external_code or "").strip() if first_detail else ""
        if not mid:
            return Response(
                create_error_response("알리고 메시지 ID(mid)가 없습니다. 발송 완료 후 다시 시도해 주세요.", "01"),
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            page = int(request.query_params.get("page") or 1)
        except (TypeError, ValueError):
            page = 1
        try:
            limit = int(request.query_params.get("limit") or 50)
        except (TypeError, ValueError):
            limit = 50
        out = fetch_kakao_alimtalk_history_detail(mid, page=page, limit=limit)
        if not out.get("ok"):
            return Response(
                create_error_response(str(out.get("message") or "알리고 조회 실패"), "99"),
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(
            create_success_response(
                {
                    "mid": mid,
                    "list": out.get("list") or [],
                    "current_page": out.get("current_page"),
                    "total_page": out.get("total_page"),
                    "total_count": out.get("total_count"),
                },
                "알리고 알림톡 전송결과 상세",
            )
        )


class MessageBatchDetailView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_codes = (MenuCodes.SMS_KAKAO_HISTORY, MenuCodes.EMAIL_HISTORY)

    def get(self, request, batch_id: int):
        try:
            batch = MessageBatch.objects.get(id=batch_id)
        except MessageBatch.DoesNotExist:
            return Response(create_error_response("배치를 찾을 수 없습니다.", "04"), status=status.HTTP_404_NOT_FOUND)
        return Response(create_success_response(MessageBatchSerializer(batch).data, "배치 상세 조회 성공"))


class MessageBatchCancelView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_codes = (MenuCodes.SMS_KAKAO_HISTORY, MenuCodes.EMAIL_HISTORY)

    def post(self, request, batch_id: int):
        try:
            batch = MessageBatch.objects.get(id=batch_id)
        except MessageBatch.DoesNotExist:
            return Response(create_error_response("배치를 찾을 수 없습니다.", "04"), status=status.HTTP_404_NOT_FOUND)
        if batch.status != MessageBatch.STATUS_SCHEDULED:
            return Response(create_error_response("예약 상태에서만 취소 가능합니다.", "01"), status=status.HTTP_400_BAD_REQUEST)
        batch.status = MessageBatch.STATUS_CANCELED
        batch.canceled_at = timezone.now()
        batch.is_processed = True
        batch.save(update_fields=["status", "canceled_at", "is_processed", "updated_at"])
        return Response(create_success_response(MessageBatchSerializer(batch).data, "예약 발송이 취소되었습니다."))


class MessageBatchResendFailedView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_codes = (MenuCodes.SMS_KAKAO_HISTORY, MenuCodes.EMAIL_HISTORY)

    def post(self, request, batch_id: int):
        try:
            source = MessageBatch.objects.get(id=batch_id)
        except MessageBatch.DoesNotExist:
            return Response(create_error_response("원본 배치를 찾을 수 없습니다.", "04"), status=status.HTTP_404_NOT_FOUND)

        failed_details = list(source.details.filter(status=MessageDetail.STATUS_FAIL))
        if not failed_details:
            return Response(create_error_response("재전송할 실패 건이 없습니다.", "01"), status=status.HTTP_400_BAD_REQUEST)

        snap = dict(source.request_snapshot or {}) if isinstance(source.request_snapshot, dict) else {}
        snap["resend_from"] = source.id

        with transaction.atomic():
            new_batch = MessageBatch.objects.create(
                type=source.type,
                sender=source.sender,
                title=source.title,
                content=source.content,
                total_count=len(failed_details),
                status=MessageBatch.STATUS_PROCESSING,
                is_processed=False,
                created_by_id=str(getattr(request.user, "memberShipSid", "")),
                request_snapshot=snap,
            )
            clones = []
            for detail in failed_details:
                clones.append(
                    MessageDetail(
                        batch=new_batch,
                        receiver_name=detail.receiver_name,
                        receiver_phone=detail.receiver_phone,
                        receiver_email=detail.receiver_email,
                        template_id=detail.template_id,
                        template_name=detail.template_name,
                        variables=detail.variables,
                        final_content=detail.final_content,
                        status=MessageDetail.STATUS_SUCCESS,
                    )
                )
            MessageDetail.objects.bulk_create(clones)
            new_batch.excluded_count = 0

            now = timezone.now()
            if source.type == MessageBatch.TYPE_EMAIL:
                out = send_email_batch_details(new_batch, now=now)
                new_batch.success_count = out["success"]
                new_batch.fail_count = out["fail"]
                new_batch.api_response_logs = out.get("logs") or []
                new_batch.result_snapshot = {"provider": "gmail_smtp", "resend_from": source.id}
                new_batch.is_processed = True
                new_batch.completed_at = now
                new_batch.status = (
                    MessageBatch.STATUS_COMPLETED
                    if out["fail"] == 0
                    else MessageBatch.STATUS_FAILED
                )
            elif source.type == MessageBatch.TYPE_SMS:
                db_valid_details = list(
                    MessageDetail.objects.filter(batch=new_batch, status=MessageDetail.STATUS_SUCCESS).order_by("id")
                )
                phones = [d.receiver_phone for d in db_valid_details]
                messages = [d.final_content or new_batch.content for d in db_valid_details]
                send_result = send_mass_with_aligo(new_batch.sender, new_batch.title, phones, messages, reserve_at=None)
                new_batch.api_response_logs = [send_result.get("raw")] if send_result.get("raw") is not None else []
                if send_result.get("ok"):
                    msg_id = str(send_result.get("msg_id") or "")
                    new_batch.result_snapshot = {
                        "provider": "aligo",
                        "msg_id": msg_id,
                        "msg_type": str(send_result.get("msg_type") or ""),
                        "resend_from": source.id,
                    }
                    success_cnt = int(send_result.get("success_cnt") or 0)
                    for idx, d in enumerate(db_valid_details):
                        if idx < success_cnt:
                            d.status = MessageDetail.STATUS_SUCCESS
                            d.external_code = msg_id
                            d.external_message = str(send_result.get("message") or "")
                            d.error_reason = ""
                            d.sent_at = now
                        else:
                            d.status = MessageDetail.STATUS_FAIL
                            d.error_reason = "provider_error"
                            d.external_message = str(send_result.get("message") or "")
                        d.save(
                            update_fields=[
                                "status",
                                "external_code",
                                "external_message",
                                "sent_at",
                                "error_reason",
                                "updated_at",
                            ]
                        )
                    new_batch.success_count = success_cnt
                    new_batch.fail_count = max(0, len(db_valid_details) - success_cnt)
                    new_batch.is_processed = True
                    new_batch.completed_at = now
                    new_batch.status = (
                        MessageBatch.STATUS_COMPLETED
                        if new_batch.fail_count == 0
                        else MessageBatch.STATUS_FAILED
                    )
                else:
                    for d in db_valid_details:
                        d.status = MessageDetail.STATUS_FAIL
                        d.error_reason = "provider_error"
                        d.external_message = str(send_result.get("message") or "알리고 발송 실패")
                        d.save(update_fields=["status", "external_message", "error_reason", "updated_at"])
                    new_batch.success_count = 0
                    new_batch.fail_count = len(db_valid_details)
                    new_batch.is_processed = True
                    new_batch.status = MessageBatch.STATUS_FAILED
                    new_batch.completed_at = now
            elif source.type == MessageBatch.TYPE_KAKAO:
                db_valid_details = list(
                    MessageDetail.objects.filter(batch=new_batch, status=MessageDetail.STATUS_SUCCESS).order_by("id")
                )
                tpl_row = None
                tid = None
                for d in db_valid_details:
                    if d.template_id:
                        tid = d.template_id
                        break
                if tid is None and isinstance(snap, dict):
                    raw_tid = snap.get("templateId")
                    try:
                        tid = int(raw_tid) if raw_tid is not None and str(raw_tid).strip() != "" else None
                    except (TypeError, ValueError):
                        tid = None
                if tid is not None:
                    tpl_row = KakaoTemplate.objects.filter(id=tid).first()
                if not tpl_row:
                    for d in db_valid_details:
                        d.status = MessageDetail.STATUS_FAIL
                        d.error_reason = "missing_template"
                        d.save(update_fields=["status", "error_reason", "updated_at"])
                    new_batch.success_count = 0
                    new_batch.fail_count = len(db_valid_details)
                    new_batch.is_processed = True
                    new_batch.status = MessageBatch.STATUS_FAILED
                    new_batch.completed_at = now
                    new_batch.api_response_logs = []
                else:
                    senderkey = (getattr(settings, "ALIGO_KAKAO_SENDERKEY", "") or "").strip()
                    subj_base = (new_batch.title or "").strip() or (tpl_row.template_name or "알림")[:200]
                    items = [
                        {
                            "phone": d.receiver_phone,
                            "recvname": d.receiver_name or "",
                            "subject": subj_base,
                            "message": (d.final_content or new_batch.content or "").strip(),
                        }
                        for d in db_valid_details
                    ]
                    emt, btn = _kakao_alimtalk_extras_from_template(tpl_row)
                    send_result = send_alimtalk_with_aligo(
                        new_batch.sender,
                        senderkey,
                        tpl_row.template_code,
                        items,
                        reserve_at=None,
                        batch_emtitle=emt,
                        batch_button=btn,
                    )
                    new_batch.api_response_logs = [send_result.get("raw")] if send_result.get("raw") is not None else []
                    if send_result.get("ok"):
                        success_cnt = int(send_result.get("success_cnt") or 0)
                        mid = str(send_result.get("mid") or "")
                        new_batch.result_snapshot = {
                            "provider": "aligo_kakao",
                            "tpl_code": tpl_row.template_code,
                            "mid": mid,
                            "resend_from": source.id,
                        }
                        for idx, d in enumerate(db_valid_details):
                            if idx < success_cnt:
                                d.status = MessageDetail.STATUS_SUCCESS
                                d.external_code = mid
                                d.external_message = str(send_result.get("message") or "")
                                d.error_reason = ""
                                d.sent_at = now
                            else:
                                d.status = MessageDetail.STATUS_FAIL
                                d.error_reason = "provider_error"
                                d.external_message = str(send_result.get("message") or "")
                            d.save(
                                update_fields=[
                                    "status",
                                    "external_code",
                                    "external_message",
                                    "sent_at",
                                    "error_reason",
                                    "updated_at",
                                ]
                            )
                        new_batch.success_count = success_cnt
                        new_batch.fail_count = max(0, len(db_valid_details) - success_cnt)
                        new_batch.is_processed = True
                        new_batch.completed_at = now
                        new_batch.status = (
                            MessageBatch.STATUS_COMPLETED
                            if new_batch.fail_count == 0
                            else MessageBatch.STATUS_FAILED
                        )
                    else:
                        for d in db_valid_details:
                            d.status = MessageDetail.STATUS_FAIL
                            d.error_reason = "provider_error"
                            d.external_message = str(send_result.get("message") or "알리고 알림톡 발송 실패")
                            d.save(update_fields=["status", "external_message", "error_reason", "updated_at"])
                        new_batch.success_count = 0
                        new_batch.fail_count = len(db_valid_details)
                        new_batch.is_processed = True
                        new_batch.status = MessageBatch.STATUS_FAILED
                        new_batch.completed_at = now
            else:
                new_batch.success_count = len(clones)
                new_batch.fail_count = 0
                new_batch.is_processed = True
                new_batch.status = MessageBatch.STATUS_COMPLETED
                new_batch.completed_at = now

            new_batch.save()

        return Response(create_success_response(MessageBatchSerializer(new_batch).data, "실패 건 재전송이 생성되었습니다."))


class MessageSenderNumberListCreateView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_codes = (MenuCodes.SMS_SENDER_NUMBER, MenuCodes.SMS_KAKAO_SEND)

    def get(self, request):
        status_filter = request.query_params.get("status")
        qs = MessageSenderNumber.objects.filter(deleted_at__isnull=True)
        if status_filter:
            qs = qs.filter(status=status_filter)
        data = MessageSenderNumberSerializer(qs, many=True).data
        return Response(create_success_response(data, "발신번호 목록 조회 성공"))

    def post(self, request):
        serializer = MessageSenderNumberSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(create_error_response(str(serializer.errors), "01"), status=status.HTTP_400_BAD_REQUEST)
        normalized = serializer.validated_data["sender_number"]
        existing = MessageSenderNumber.objects.filter(sender_number=normalized).order_by("-id").first()

        # soft delete 된 번호는 신규 생성 대신 복구/갱신 처리
        if existing and existing.deleted_at is not None:
            existing.deleted_at = None
            existing.manager_name = serializer.validated_data.get("manager_name", "")
            existing.comment = serializer.validated_data.get("comment", "")
            existing.request_type = serializer.validated_data.get("request_type", existing.request_type)
            existing.status = serializer.validated_data.get("status", existing.status)
            existing.reject_reason = ""
            existing.processed_at = timezone.now() if existing.status == MessageSenderNumber.STATUS_APPROVED else None
            existing.created_by_id = str(getattr(request.user, "memberShipSid", ""))
            existing.save()
            out = MessageSenderNumberSerializer(existing).data
            return Response(create_success_response(out, "삭제된 발신번호가 복구되었습니다."), status=status.HTTP_200_OK)

        if existing and existing.deleted_at is None:
            return Response(create_error_response("이미 등록된 발신번호입니다.", "01"), status=status.HTTP_400_BAD_REQUEST)

        obj = serializer.save(
            created_by_id=str(getattr(request.user, "memberShipSid", "")),
            processed_at=timezone.now() if serializer.validated_data.get("status") == MessageSenderNumber.STATUS_APPROVED else None,
        )
        out = MessageSenderNumberSerializer(obj).data
        return Response(create_success_response(out, "발신번호가 등록되었습니다."), status=status.HTTP_201_CREATED)


class MessageSenderNumberDeleteView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_codes = (MenuCodes.SMS_SENDER_NUMBER, MenuCodes.SMS_KAKAO_SEND)

    def delete(self, request, sender_id: int):
        try:
            obj = MessageSenderNumber.objects.get(id=sender_id, deleted_at__isnull=True)
        except MessageSenderNumber.DoesNotExist:
            return Response(create_error_response("발신번호를 찾을 수 없습니다.", "04"), status=status.HTTP_404_NOT_FOUND)
        obj.deleted_at = timezone.now()
        obj.save(update_fields=["deleted_at", "updated_at"])
        return Response(create_success_response(None, "발신번호가 삭제되었습니다."))


class MessageSenderEmailListCreateView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_code = MenuCodes.EMAIL_SENDER_MANAGE

    def get(self, request):
        status_filter = request.query_params.get("status")
        qs = MessageSenderEmail.objects.filter(deleted_at__isnull=True)
        if status_filter:
            qs = qs.filter(status=status_filter)
        data = MessageSenderEmailSerializer(qs, many=True).data
        return Response(create_success_response(data, "발신 이메일 목록 조회 성공"))

    def post(self, request):
        serializer = MessageSenderEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(create_error_response(str(serializer.errors), "01"), status=status.HTTP_400_BAD_REQUEST)
        normalized = serializer.validated_data["sender_email"]
        existing = MessageSenderEmail.objects.filter(sender_email=normalized).order_by("-id").first()

        if existing and existing.deleted_at is not None:
            existing.deleted_at = None
            existing.manager_name = serializer.validated_data.get("manager_name", "")
            existing.comment = serializer.validated_data.get("comment", "")
            existing.request_type = serializer.validated_data.get("request_type", existing.request_type)
            existing.status = serializer.validated_data.get("status", existing.status)
            existing.reject_reason = ""
            existing.processed_at = timezone.now() if existing.status == MessageSenderEmail.STATUS_APPROVED else None
            existing.created_by_id = str(getattr(request.user, "memberShipSid", ""))
            existing.save()
            out = MessageSenderEmailSerializer(existing).data
            return Response(create_success_response(out, "삭제된 발신 이메일이 복구되었습니다."), status=status.HTTP_200_OK)

        if existing and existing.deleted_at is None:
            return Response(create_error_response("이미 등록된 발신 이메일입니다.", "01"), status=status.HTTP_400_BAD_REQUEST)

        obj = serializer.save(
            created_by_id=str(getattr(request.user, "memberShipSid", "")),
            processed_at=timezone.now()
            if serializer.validated_data.get("status") == MessageSenderEmail.STATUS_APPROVED
            else None,
        )
        out = MessageSenderEmailSerializer(obj).data
        return Response(create_success_response(out, "발신 이메일이 등록되었습니다."), status=status.HTTP_201_CREATED)


class MessageSenderEmailDeleteView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_code = MenuCodes.EMAIL_SENDER_MANAGE

    def delete(self, request, sender_id: int):
        try:
            obj = MessageSenderEmail.objects.get(id=sender_id, deleted_at__isnull=True)
        except MessageSenderEmail.DoesNotExist:
            return Response(create_error_response("발신 이메일을 찾을 수 없습니다.", "04"), status=status.HTTP_404_NOT_FOUND)
        obj.deleted_at = timezone.now()
        obj.save(update_fields=["deleted_at", "updated_at"])
        return Response(create_success_response(None, "발신 이메일이 삭제되었습니다."))


class MessageTemplateListCreateView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_codes = (MenuCodes.SMS_KAKAO_SEND, MenuCodes.EMAIL_SEND)

    def get(self, request):
        channel = request.query_params.get("channel")
        qs = MessageTemplate.objects.filter(is_active=True)
        if channel:
            qs = qs.filter(channel=channel)
        data = MessageTemplateSerializer(qs, many=True).data
        return Response(create_success_response(data, "템플릿 목록 조회 성공"))

    def post(self, request):
        serializer = MessageTemplateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(create_error_response(str(serializer.errors), "01"), status=status.HTTP_400_BAD_REQUEST)
        obj = serializer.save(created_by_id=str(getattr(request.user, "memberShipSid", "")))
        return Response(
            create_success_response(MessageTemplateSerializer(obj).data, "템플릿이 저장되었습니다."),
            status=status.HTTP_201_CREATED,
        )


class MessageTemplateDetailView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_codes = (MenuCodes.SMS_KAKAO_SEND, MenuCodes.EMAIL_SEND)

    def put(self, request, template_id: int):
        try:
            obj = MessageTemplate.objects.get(id=template_id, is_active=True)
        except MessageTemplate.DoesNotExist:
            return Response(create_error_response("템플릿을 찾을 수 없습니다.", "04"), status=status.HTTP_404_NOT_FOUND)
        serializer = MessageTemplateSerializer(obj, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(create_error_response(str(serializer.errors), "01"), status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(create_success_response(serializer.data, "템플릿이 수정되었습니다."))

    def delete(self, request, template_id: int):
        try:
            obj = MessageTemplate.objects.get(id=template_id, is_active=True)
        except MessageTemplate.DoesNotExist:
            return Response(create_error_response("템플릿을 찾을 수 없습니다.", "04"), status=status.HTTP_404_NOT_FOUND)
        obj.is_active = False
        obj.save(update_fields=["is_active", "updated_at"])
        return Response(create_success_response(None, "템플릿이 삭제되었습니다."))


class AligoRemainView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_code = MenuCodes.SMS_KAKAO_SEND

    def get(self, request):
        api_key = (getattr(settings, "ALIGO_API_KEY", "") or "").strip()
        user_id = (getattr(settings, "ALIGO_USER_ID", "") or "").strip()
        if not api_key or not user_id:
            return Response(
                create_error_response("ALIGO_API_KEY 또는 ALIGO_USER_ID가 설정되지 않았습니다.", "01"),
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            resp = requests.post(
                "https://apis.aligo.in/remain/",
                data={"key": api_key, "user_id": user_id},
                timeout=15,
            )
            resp.raise_for_status()
            payload = resp.json()
        except requests.RequestException:
            return Response(
                create_error_response("알리고 잔여건수 조회 중 네트워크 오류가 발생했습니다.", "99"),
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except ValueError:
            return Response(
                create_error_response("알리고 응답을 해석할 수 없습니다.", "99"),
                status=status.HTTP_502_BAD_GATEWAY,
            )

        code = str(payload.get("result_code", ""))
        if code != "1":
            return Response(
                create_error_response(payload.get("message") or "알리고 잔여건수 조회 실패", "01"),
                status=status.HTTP_400_BAD_REQUEST,
            )

        def to_int(v):
            try:
                return int(v)
            except (TypeError, ValueError):
                return 0

        result = {
            "sms_cnt": to_int(payload.get("SMS_CNT")),
            "lms_cnt": to_int(payload.get("LMS_CNT")),
            "mms_cnt": to_int(payload.get("MMS_CNT")),
            "raw": payload,
        }
        return Response(create_success_response(result, "알리고 잔여건수 조회 성공"))


def _normalize_phone(v: str) -> str:
    return "".join(ch for ch in (v or "") if ch.isdigit())


def _is_success_state(state_text: str) -> bool:
    s = (state_text or "").strip()
    return "완료" in s or "성공" in s


class MessageBatchSyncResultView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_code = MenuCodes.SMS_KAKAO_HISTORY

    def post(self, request, batch_id: int):
        try:
            batch = MessageBatch.objects.get(id=batch_id)
        except MessageBatch.DoesNotExist:
            return Response(create_error_response("배치를 찾을 수 없습니다.", "04"), status=status.HTTP_404_NOT_FOUND)

        if batch.type != MessageBatch.TYPE_SMS:
            return Response(create_error_response("문자(sms) 배치만 결과 동기화 가능합니다.", "01"), status=status.HTTP_400_BAD_REQUEST)

        msg_id = str((batch.result_snapshot or {}).get("msg_id") or "").strip()
        if not msg_id:
            # 과거 데이터 호환: detail 외부코드에서 fallback
            first_detail = batch.details.exclude(external_code="").first()
            msg_id = str(first_detail.external_code if first_detail else "").strip()
        if not msg_id:
            return Response(create_error_response("알리고 msg_id가 없어 동기화할 수 없습니다.", "01"), status=status.HTTP_400_BAD_REQUEST)

        sync_result = fetch_sms_list_all(msg_id)
        if not sync_result.get("ok"):
            return Response(create_error_response(str(sync_result.get("message") or "동기화 실패"), "99"), status=status.HTTP_502_BAD_GATEWAY)

        rows = sync_result.get("list") or []
        details = list(batch.details.all())
        detail_by_phone: dict[str, list[MessageDetail]] = {}
        for d in details:
            detail_by_phone.setdefault(_normalize_phone(d.receiver_phone), []).append(d)

        updated = 0
        pending = 0
        for row in rows:
            phone = _normalize_phone(str(row.get("receiver") or ""))
            if not phone or phone not in detail_by_phone:
                continue
            state_text = str(row.get("sms_state") or "")
            send_date = str(row.get("send_date") or "").strip()
            for d in detail_by_phone[phone]:
                if "전송중" in state_text or "대기" in state_text:
                    pending += 1
                    d.external_message = state_text
                    d.save(update_fields=["external_message", "updated_at"])
                    continue
                d.status = MessageDetail.STATUS_SUCCESS if _is_success_state(state_text) else MessageDetail.STATUS_FAIL
                d.external_message = state_text
                d.external_code = msg_id
                if send_date:
                    try:
                        d.sent_at = datetime.strptime(send_date, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass
                d.error_reason = "" if d.status == MessageDetail.STATUS_SUCCESS else "provider_result_sync_fail"
                d.save(update_fields=["status", "external_message", "external_code", "sent_at", "error_reason", "updated_at"])
                updated += 1

        success_count = batch.details.filter(status=MessageDetail.STATUS_SUCCESS).count()
        fail_count = batch.details.filter(status=MessageDetail.STATUS_FAIL).count()
        excluded_count = batch.details.filter(status=MessageDetail.STATUS_EXCLUDED).count()
        batch.success_count = success_count
        batch.fail_count = fail_count
        batch.excluded_count = excluded_count
        batch.api_response_logs = (batch.api_response_logs or []) + (sync_result.get("raw") or [])
        if pending > 0:
            batch.status = MessageBatch.STATUS_PROCESSING
        else:
            batch.status = MessageBatch.STATUS_COMPLETED if fail_count == 0 else MessageBatch.STATUS_FAILED
            batch.completed_at = timezone.now()
            batch.is_processed = True
        batch.save()

        return Response(
            create_success_response(
                {
                    "batch_id": batch.id,
                    "updated_count": updated,
                    "pending_count": pending,
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "excluded_count": excluded_count,
                },
                "알리고 상세결과 동기화 완료",
            )
        )
