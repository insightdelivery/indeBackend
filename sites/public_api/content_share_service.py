"""
회원 short 공유 링크 — contentShareLinkCopy.md §5.3, §10.15
"""
from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Any, Dict, Optional

from django.db import connection
from django.utils import timezone

from core.models import SysCodeManager

ALPHABET = string.ascii_letters + string.digits
FALLBACK_TTL_HOURS = 24
MAX_SHORT_RETRIES = 5


def _random_short_code() -> str:
    length = secrets.randbelow(3) + 8  # 8~10
    return ''.join(secrets.choice(ALPHABET) for _ in range(length))


def _random_share_token() -> str:
    """§10.15.3: 64 hex chars (32 bytes), never reuse — new value each INSERT/UPDATE."""
    return secrets.token_hex(32)


def get_share_link_ttl_hours() -> int:
    """SYS26326B001 — sysCodeVal = 유효 시간(시간). 없거나 비정상 시 fallback."""
    try:
        row = SysCodeManager.objects.filter(sysCodeSid='SYS26326B001', sysCodeUse='Y').first()
        if row and row.sysCodeVal:
            h = int(float(row.sysCodeVal.strip()))
            if 1 <= h <= 8760:
                return h
    except (ValueError, TypeError, AttributeError):
        pass
    return FALLBACK_TTL_HOURS


def _is_duplicate_key(exc: BaseException) -> bool:
    s = str(exc)
    return '1062' in s or 'Duplicate entry' in s or 'duplicate key' in s.lower()


def _expiry_aware_for_compare(expiry) -> Optional[datetime]:
    """MySQL DATETIME(naive)은 UTC로 간주해 now()와 동일 기준으로 비교."""
    if expiry is None:
        return None
    if timezone.is_aware(expiry):
        return expiry
    return timezone.make_aware(expiry, dt_timezone.utc)


def ensure_share_link(user_id: int, content_type: str, content_id: int) -> dict:
    """
    §5.3: 미만료면 반환만, 만료면 UPDATE(short_code+share_token), 없으면 INSERT.
    share_token 재사용 금지(§10.15.11).
    Returns dict: mode, short_code, expired_at (datetime)
    """
    ct = content_type.strip().upper()
    now = timezone.now()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, short_code, expired_at
            FROM content_share_link
            WHERE user_id = %s AND content_type = %s AND content_id = %s
            """,
            [user_id, ct, content_id],
        )
        row = cursor.fetchone()

    ttl = timedelta(hours=get_share_link_ttl_hours())
    new_expired = now + ttl

    if row:
        link_id, short_code, expired_at = row
        exp_cmp = _expiry_aware_for_compare(expired_at)
        if exp_cmp is not None and exp_cmp > now:
            return {'mode': 'active', 'short_code': short_code, 'expired_at': expired_at}
        last_err = None
        for _ in range(MAX_SHORT_RETRIES):
            code = _random_short_code()
            token = _random_share_token()
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE content_share_link
                        SET short_code = %s, share_token = %s, expired_at = %s, updated_at = NOW()
                        WHERE id = %s
                        """,
                        [code, token, new_expired, link_id],
                    )
                return {'mode': 'renewed', 'short_code': code, 'expired_at': new_expired}
            except Exception as e:
                last_err = e
                if _is_duplicate_key(e):
                    continue
                raise
        raise RuntimeError(f'short_code/share_token collision after {MAX_SHORT_RETRIES} retries') from last_err

    last_err = None
    for _ in range(MAX_SHORT_RETRIES):
        code = _random_short_code()
        token = _random_share_token()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO content_share_link
                        (content_type, content_id, user_id, short_code, share_token, expired_at, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    """,
                    [ct, content_id, user_id, code, token, new_expired],
                )
            return {'mode': 'issued', 'short_code': code, 'expired_at': new_expired}
        except Exception as e:
            last_err = e
            if _is_duplicate_key(e):
                continue
            raise
    raise RuntimeError(f'short_code/share_token collision after {MAX_SHORT_RETRIES} retries') from last_err


def resolve_short_code(short_code: str) -> Optional[Dict[str, Any]]:
    """
    short_code로 행 조회. 없으면 None.
    Returns: content_type, content_id, expired (bool)
    """
    sc = (short_code or '').strip()
    if not sc or len(sc) > 12:
        return None
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT content_type, content_id,
                   CASE WHEN expired_at > UTC_TIMESTAMP() THEN 0 ELSE 1 END AS is_expired
            FROM content_share_link
            WHERE short_code = %s
            """,
            [sc],
        )
        row = cursor.fetchone()
    if not row:
        return None
    ct, cid, is_expired = row
    return {
        'content_type': ct,
        'content_id': int(cid),
        'expired': bool(is_expired),
    }


def resolve_share_token(token: str) -> Optional[Dict[str, Any]]:
    """
    share_token으로 행 조회(entitlement). 없으면 None.
    Returns: content_type, content_id, expired (bool)
    """
    t = (token or '').strip()
    if not t or len(t) > 64:
        return None
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT content_type, content_id,
                   CASE WHEN expired_at > UTC_TIMESTAMP() THEN 0 ELSE 1 END AS is_expired
            FROM content_share_link
            WHERE share_token = %s
            """,
            [t],
        )
        row = cursor.fetchone()
    if not row:
        return None
    ct, cid, is_expired = row
    return {
        'content_type': ct,
        'content_id': int(cid),
        'expired': bool(is_expired),
    }


def get_row_for_visit_by_short_code(short_code: str) -> Optional[Dict[str, Any]]:
    """
    GET /s/{shortCode} 처리: short_code로 행 조회 + share_token·만료 시각.
    Returns: content_type, content_id, expired, share_token, expired_at (datetime)
    """
    sc = (short_code or '').strip()
    if not sc or len(sc) > 12:
        return None
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT content_type, content_id, share_token, expired_at,
                   CASE WHEN expired_at > UTC_TIMESTAMP() THEN 0 ELSE 1 END AS is_expired
            FROM content_share_link
            WHERE short_code = %s
            """,
            [sc],
        )
        row = cursor.fetchone()
    if not row:
        return None
    ct, cid, stok, exp_at, is_expired = row
    return {
        'content_type': ct,
        'content_id': int(cid),
        'expired': bool(is_expired),
        'share_token': stok,
        'expired_at': exp_at,
    }


def get_short_code_for_copy_entitlement(
    share_token: str, content_type: str, content_id: int
) -> Optional[str]:
    """
    §10.16: share_access 쿠키의 share_token + 요청 콘텐츠 일치 + 미만료일 때만 short_code 반환.
    """
    ct = (content_type or '').strip().upper()
    if ct not in ('ARTICLE', 'VIDEO', 'SEMINAR'):
        return None
    try:
        cid = int(content_id)
    except (TypeError, ValueError):
        return None
    if cid < 1:
        return None
    t = (share_token or '').strip()
    if not t or len(t) > 64:
        return None
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT short_code
            FROM content_share_link
            WHERE share_token = %s
              AND content_type = %s
              AND content_id = %s
              AND expired_at > UTC_TIMESTAMP()
            """,
            [t, ct, cid],
        )
        row = cursor.fetchone()
    if not row:
        return None
    return row[0]
