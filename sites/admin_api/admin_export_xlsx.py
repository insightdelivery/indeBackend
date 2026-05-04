"""관리자 목록 엑셀 공통 (openpyxl + HttpResponse)."""
from __future__ import annotations

from io import BytesIO

from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook


def xlsx_http_response(wb: Workbook, filename_prefix: str) -> HttpResponse:
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    fn = f"{filename_prefix}_{timezone.localtime(timezone.now()).strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"
    resp = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="{fn}"'
    return resp


def format_excel_datetime(dt) -> str:
    if dt is None:
        return ""
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return timezone.localtime(dt).strftime("%Y-%m-%d %H:%M:%S")
