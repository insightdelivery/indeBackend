"""
아티클 본문 미리보기 — 비회원용 content 축약 (previewLength = 0~100 %).
HTML에서 태그를 제거한 뒤 글자 수 기준으로 앞부분만 반환한다.
"""
from __future__ import annotations

import html as html_module
import re

_TAG_RE = re.compile(r'<[^>]+>', re.DOTALL)


def plain_text_from_html(html: str) -> str:
    if not html or not str(html).strip():
        return ''
    text = _TAG_RE.sub(' ', str(html))
    text = html_module.unescape(text)
    return ' '.join(text.split())


def preview_content_html(full_html: str, percent: int | None) -> tuple[str, bool]:
    """
    Returns (content_for_response, was_truncated).
    percent: DB previewLength (0~100). None → 50.
    """
    if not full_html or not str(full_html).strip():
        return full_html, False

    p = int(percent) if percent is not None else 50
    p = max(0, min(100, p))

    if p >= 100:
        return full_html, False

    plain = plain_text_from_html(full_html)
    if not plain:
        return full_html, False

    total = len(plain)
    n = (total * p) // 100
    if p > 0 and n == 0:
        n = 1

    if n >= total:
        return full_html, False

    snippet = plain[:n].rstrip()
    if n < total:
        snippet += '…'

    safe = html_module.escape(snippet)
    return f'<p>{safe}</p>', True
