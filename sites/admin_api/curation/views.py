"""
관리자 큐레이션 API — curationContentPlan.md §3·§4
한 큐레이션(Curation)에 여러 콘텐츠(CurationItem) 포함.
권한: MenuCodes.CURATION (SYS26511B001)
"""
from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import create_error_response, create_success_response
from sites.admin_api.authentication import AdminJWTAuthentication
from sites.admin_api.menu_codes import MenuCodes
from sites.admin_api.permissions import MenuPermission

from .curation_resolve import (
    effective_display_title,
    resolve_curation_target,
)
from .models import Curation, CurationItem


def _parse_datetime(val) -> timezone.datetime | None:
    if val is None or val == '':
        return None
    dt = parse_datetime(str(val))
    if dt is None:
        return None
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _body(data: dict, key: str, default=None):
    if not isinstance(data, dict):
        return default
    if key in data:
        return data.get(key)
    mapping = {
        'contentType': 'content_type',
        'contentCode': 'content_code',
        'isActive': 'is_active',
        'isExposed': 'is_exposed',
        'exposureStartDatetime': 'exposure_start_datetime',
        'exposureEndDatetime': 'exposure_end_datetime',
        'sortOrder': 'sort_order',
        'customTitle': 'custom_title',
    }
    alt = mapping.get(key, key)
    return data.get(alt, default)


def _item_admin_dict(it: CurationItem, resolved: dict | None) -> dict:
    orig = (resolved or {}).get('displayTitle') or ''
    return {
        'itemId': it.id,
        'contentType': it.content_type,
        'contentCode': it.content_code,
        'customTitle': it.custom_title,
        'sortOrder': it.sort_order,
        'displayTitle': effective_display_title(it.custom_title, orig),
        'originalTitle': orig,
        'thumbnail': (resolved or {}).get('thumbnail') or '',
        'categoryName': (resolved or {}).get('categoryName') or '',
        'summary': (resolved or {}).get('summary') or '',
        'resolveError': None if resolved else '콘텐츠를 찾을 수 없거나 유형이 맞지 않습니다.',
    }


def _curation_detail_dict(c: Curation) -> dict:
    items_out = []
    for it in c.items.order_by('sort_order', 'id'):
        resolved = resolve_curation_target(it.content_type, it.content_code)
        items_out.append(_item_admin_dict(it, resolved))
    return {
        'id': c.id,
        'name': c.name,
        'itemCount': c.items.count(),
        'isActive': c.is_active,
        'isExposed': c.is_exposed,
        'exposureStartDatetime': c.exposure_start_datetime.isoformat()
        if c.exposure_start_datetime
        else None,
        'exposureEndDatetime': c.exposure_end_datetime.isoformat()
        if c.exposure_end_datetime
        else None,
        'regDatetime': c.reg_datetime.isoformat() if c.reg_datetime else None,
        'items': items_out,
    }


def _enforce_single_homepage_exposure(c: Curation) -> None:
    """홈페이지 노출(is_exposed)은 한 큐레이션만 True. 현재 행이 True면 나머지는 False."""
    if not c.is_exposed:
        return
    Curation.objects.exclude(pk=c.pk).update(is_exposed=False)


def _curation_summary_dict(c: Curation) -> dict:
    return {
        'id': c.id,
        'name': c.name,
        'itemCount': c.items.count(),
        'isActive': c.is_active,
        'isExposed': c.is_exposed,
        'exposureStartDatetime': c.exposure_start_datetime.isoformat()
        if c.exposure_start_datetime
        else None,
        'exposureEndDatetime': c.exposure_end_datetime.isoformat()
        if c.exposure_end_datetime
        else None,
        'regDatetime': c.reg_datetime.isoformat() if c.reg_datetime else None,
    }


def _parse_items_payload(raw) -> list[dict]:
    if raw is None:
        raise ValueError('items 필드가 필요합니다.')
    if not isinstance(raw, list):
        raise ValueError('items는 배열이어야 합니다.')
    if len(raw) < 1:
        raise ValueError('콘텐츠(items)를 1개 이상 넣어 주세요.')
    out: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for i, row in enumerate(raw):
        if not isinstance(row, dict):
            raise ValueError('items 항목 형식이 올바르지 않습니다.')
        ct = str(row.get('contentType') or row.get('content_type') or '').strip().upper()
        cc = row.get('contentCode')
        if cc is None:
            cc = row.get('content_code')
        try:
            code = int(cc)
        except (TypeError, ValueError):
            raise ValueError('각 항목에 contentCode(정수)가 필요합니다.')
        if ct not in CurationItem.ContentType:
            raise ValueError('contentType은 ARTICLE, VIDEO, SEMINAR 만 허용됩니다.')
        key = (ct, code)
        if key in seen:
            raise ValueError('items 안에 동일한 콘텐츠(타입+코드)가 중복되었습니다.')
        seen.add(key)
        try:
            so = int(row.get('sortOrder', row.get('sort_order', i)))
        except (TypeError, ValueError):
            so = i
        tv = row.get('title')
        if tv is None:
            tv = row.get('customTitle') or row.get('custom_title')
        custom = None if tv in (None, '') else str(tv).strip() or None
        out.append(
            {
                'content_type': ct,
                'content_code': code,
                'sort_order': max(0, so),
                'custom_title': custom,
            }
        )
    return out


def _validate_and_resolve_items(rows: list[dict]) -> None:
    for r in rows:
        if not resolve_curation_target(r['content_type'], r['content_code']):
            raise ValueError(
                f"콘텐츠를 찾을 수 없습니다: {r['content_type']} #{r['content_code']}",
            )


class CurationPreviewView(APIView):
    """GET /curation/preview — 콘텐츠 코드 검증·미리보기"""

    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_code = MenuCodes.CURATION

    def get(self, request):
        ct = (request.query_params.get('contentType') or '').strip().upper()
        code_raw = request.query_params.get('contentCode')
        try:
            code = int(code_raw)
        except (TypeError, ValueError):
            return Response(
                create_error_response('contentCode는 정수여야 합니다.', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        if ct not in CurationItem.ContentType:
            return Response(
                create_error_response('contentType은 ARTICLE, VIDEO, SEMINAR 중 하나여야 합니다.', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        resolved = resolve_curation_target(ct, code)
        if not resolved:
            return Response(
                create_error_response('해당 콘텐츠를 찾을 수 없거나 타입이 일치하지 않습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            create_success_response(
                {
                    'displayTitle': resolved['displayTitle'],
                    'thumbnail': resolved['thumbnail'],
                    'categoryName': resolved['categoryName'],
                    'summary': resolved['summary'],
                },
                '조회 성공',
            ),
            status=status.HTTP_200_OK,
        )


class CurationListCreateView(APIView):
    """GET/POST /curation/"""

    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_code = MenuCodes.CURATION

    def get(self, request):
        rows = Curation.objects.prefetch_related('items').all().order_by('-is_exposed', '-reg_datetime')
        items = [_curation_summary_dict(c) for c in rows]
        return Response(
            create_success_response({'items': items}, '큐레이션 목록 조회 성공'),
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        try:
            parsed_items = _parse_items_payload(data.get('items'))
        except ValueError as e:
            return Response(create_error_response(str(e), '01'), status=status.HTTP_400_BAD_REQUEST)
        try:
            _validate_and_resolve_items(parsed_items)
        except ValueError as e:
            return Response(create_error_response(str(e), '01'), status=status.HTTP_400_BAD_REQUEST)

        name_raw = data.get('name')
        if name_raw is None or not str(name_raw).strip():
            return Response(
                create_error_response('특집 제목은 필수입니다.', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        name = str(name_raw).strip()
        is_active = bool(_body(data, 'isActive', True))
        is_exposed = bool(_body(data, 'isExposed', False))
        start = _parse_datetime(_body(data, 'exposureStartDatetime'))
        end = _parse_datetime(_body(data, 'exposureEndDatetime'))

        try:
            with transaction.atomic():
                c = Curation.objects.create(
                    name=name,
                    is_active=is_active,
                    is_exposed=is_exposed,
                    exposure_start_datetime=start,
                    exposure_end_datetime=end,
                )
                for r in parsed_items:
                    CurationItem.objects.create(
                        curation=c,
                        content_type=r['content_type'],
                        content_code=r['content_code'],
                        sort_order=r['sort_order'],
                        custom_title=r['custom_title'],
                    )
                _enforce_single_homepage_exposure(c)
        except IntegrityError:
            return Response(
                create_error_response('저장에 실패했습니다.(중복 항목 등)', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        c.refresh_from_db()
        return Response(
            create_success_response(_curation_detail_dict(c), '등록되었습니다.'),
            status=status.HTTP_201_CREATED,
        )


class CurationDetailView(APIView):
    """GET/PUT/PATCH/DELETE /curation/<id> (id = 큐레이션 PK)"""

    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated, MenuPermission]
    menu_code = MenuCodes.CURATION

    def get(self, request, pk):
        try:
            c = Curation.objects.prefetch_related('items').get(pk=pk)
        except Curation.DoesNotExist:
            return Response(
                create_error_response('항목을 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            create_success_response(_curation_detail_dict(c), '조회 성공'),
            status=status.HTTP_200_OK,
        )

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, *, partial: bool):
        try:
            c = Curation.objects.prefetch_related('items').get(pk=pk)
        except Curation.DoesNotExist:
            return Response(
                create_error_response('항목을 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND,
            )
        data = request.data if isinstance(request.data, dict) else {}

        def has(*keys: str) -> bool:
            return any(k in data for k in keys)

        replace_items: list[dict] | None = None
        try:
            if not partial:
                replace_items = _parse_items_payload(data.get('items'))
            elif 'items' in data:
                replace_items = _parse_items_payload(data.get('items'))
        except ValueError as e:
            return Response(create_error_response(str(e), '01'), status=status.HTTP_400_BAD_REQUEST)

        if replace_items is not None:
            try:
                _validate_and_resolve_items(replace_items)
            except ValueError as e:
                return Response(create_error_response(str(e), '01'), status=status.HTTP_400_BAD_REQUEST)

        if not partial or 'name' in data:
            nv = data.get('name')
            c.name = None if nv in (None, '') else str(nv).strip() or None

        if not partial or has('isActive', 'is_active'):
            c.is_active = bool(_body(data, 'isActive', c.is_active))

        if not partial or has('isExposed', 'is_exposed'):
            c.is_exposed = bool(_body(data, 'isExposed', c.is_exposed))

        if not partial or has('exposureStartDatetime', 'exposure_start_datetime'):
            c.exposure_start_datetime = _parse_datetime(_body(data, 'exposureStartDatetime', None))

        if not partial or has('exposureEndDatetime', 'exposure_end_datetime'):
            c.exposure_end_datetime = _parse_datetime(_body(data, 'exposureEndDatetime', None))

        effective_name = (c.name or '').strip()
        if not effective_name:
            return Response(
                create_error_response('특집 제목은 필수입니다.', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        c.name = effective_name

        try:
            with transaction.atomic():
                c.save()
                _enforce_single_homepage_exposure(c)
                if replace_items is not None:
                    c.items.all().delete()
                    for r in replace_items:
                        CurationItem.objects.create(
                            curation=c,
                            content_type=r['content_type'],
                            content_code=r['content_code'],
                            sort_order=r['sort_order'],
                            custom_title=r['custom_title'],
                        )
        except IntegrityError:
            return Response(
                create_error_response('저장에 실패했습니다.(중복 항목 등)', '01'),
                status=status.HTTP_400_BAD_REQUEST,
            )

        c.refresh_from_db()
        c = Curation.objects.prefetch_related('items').get(pk=c.pk)
        return Response(
            create_success_response(_curation_detail_dict(c), '수정되었습니다.'),
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk):
        try:
            c = Curation.objects.get(pk=pk)
        except Curation.DoesNotExist:
            return Response(
                create_error_response('항목을 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND,
            )
        c.delete()
        return Response(
            create_success_response({'id': int(pk), 'deleted': True}, '삭제되었습니다.'),
            status=status.HTTP_200_OK,
        )
