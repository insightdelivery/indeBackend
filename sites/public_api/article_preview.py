"""
아티클 본문 미리보기 — 비회원용 content 축약 (previewLength = 0~100 %).

평문 길이 기준으로 앞부분만 보여 주되, 가능하면 <p>·제목·인용·목록 등
블록 태그 구조를 유지한다(구버전은 전부 한 줄 <p>평문으로만 반환).
"""
from __future__ import annotations

import html as html_module
import re

_TAG_RE = re.compile(r'<[^>]+>', re.DOTALL)

# script/style 제거(미리보기 조합 시 안전)
_SCRIPT_STYLE_RE = re.compile(
    r'<script\b[^>]*>[\s\S]*?</script>|<style\b[^>]*>[\s\S]*?</style>',
    re.I,
)

# 본문에서 자주 쓰이는 블록 단위(에디터 HTML 기준). 비탐욕 매칭.
_BLOCK_RE = re.compile(
    r'<p\b[^>]*>[\s\S]*?</p>'
    r'|<h[1-6]\b[^>]*>[\s\S]*?</h[1-6]>'
    r'|<blockquote\b[^>]*>[\s\S]*?</blockquote>'
    r'|<ul\b[^>]*>[\s\S]*?</ul>'
    r'|<ol\b[^>]*>[\s\S]*?</ol>',
    re.I,
)


def plain_text_from_html(html: str) -> str:
    if not html or not str(html).strip():
        return ''
    text = _TAG_RE.sub(' ', str(html))
    text = html_module.unescape(text)
    return ' '.join(text.split())


def _legacy_single_paragraph_preview(plain: str, n: int, total: int) -> tuple[str, bool]:
    """태그를 모두 제거한 뒤 한 줄 <p>만 반환 (폴백)."""
    snippet = plain[:n].rstrip()
    if n < total:
        snippet += '…'
    safe = html_module.escape(snippet)
    return f'<p>{safe}</p>', True


def _truncate_block_to_plain_budget(block: str, remain: int) -> str:
    """블록 HTML을 평문 remain 자까지 잘라 동일 래퍼를 유지한다. 서식 태그는 잘린 꼬리에서 제거."""
    if remain <= 0:
        return ''
    m = re.match(r'^<(p|h[1-6]|blockquote)(\b[^>]*)>([\s\S]*)</\1>\s*$', block.strip(), re.I)
    if m:
        tag, attrs, inner = m.group(1), m.group(2), m.group(3)
        inner_plain = plain_text_from_html(inner)
        if len(inner_plain) <= remain:
            return block
        cut = inner_plain[:remain].rstrip() + '…'
        return f'<{tag}{attrs}>{html_module.escape(cut)}</{tag}>'
    mu = re.match(r'^(<ul)(\b[^>]*>)([\s\S]*)(</ul>\s*)$', block.strip(), re.I)
    if mu:
        inner_plain = plain_text_from_html(mu.group(3))
        if len(inner_plain) <= remain:
            return block
        cut = inner_plain[:remain].rstrip() + '…'
        return f'{mu.group(1)}{mu.group(2)}<li>{html_module.escape(cut)}</li>{mu.group(4)}'
    mo = re.match(r'^(<ol)(\b[^>]*>)([\s\S]*)(</ol>\s*)$', block.strip(), re.I)
    if mo:
        inner_plain = plain_text_from_html(mo.group(3))
        if len(inner_plain) <= remain:
            return block
        cut = inner_plain[:remain].rstrip() + '…'
        return f'{mo.group(1)}{mo.group(2)}<li>{html_module.escape(cut)}</li>{mo.group(4)}'
    bp = plain_text_from_html(block)
    if len(bp) <= remain:
        return block
    cut = bp[:remain].rstrip() + '…'
    return f'<p>{html_module.escape(cut)}</p>'


def _structured_preview(full_html: str, n: int, total: int) -> tuple[str, bool] | None:
    """
    블록 단위로 평문 예산을 소비해 HTML을 이어 붙인다.
    매칭 블록이 없으면 None (호출측에서 레거시 처리).
    """
    blocks = list(_BLOCK_RE.finditer(full_html))
    if not blocks:
        return None

    out_chunks: list[str] = []
    used = 0

    first_start = blocks[0].start()
    if first_start > 0:
        preamble = full_html[:first_start]
        pp = plain_text_from_html(preamble)
        if pp:
            if len(pp) <= n:
                out_chunks.append(preamble)
                used = len(pp)
            else:
                # 앞머리만 평문으로
                snippet = pp[:n].rstrip() + '…'
                out_chunks.append(f'<p>{html_module.escape(snippet)}</p>')
                return ''.join(out_chunks), True

    for m in blocks:
        block = m.group(0)
        bp = plain_text_from_html(block)
        gap = 1 if out_chunks else 0
        if used + gap + len(bp) <= n:
            out_chunks.append(block)
            used += gap + len(bp)
            continue
        if used + gap < n:
            remain = n - used - gap
            tail = _truncate_block_to_plain_budget(block, remain)
            if tail:
                out_chunks.append(tail)
        return ''.join(out_chunks), True

    if used < total:
        return ''.join(out_chunks), True
    return ''.join(out_chunks), False


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

    cleaned = _SCRIPT_STYLE_RE.sub('', str(full_html))
    plain = plain_text_from_html(cleaned)
    if not plain:
        return full_html, False

    total = len(plain)
    n = (total * p) // 100
    if p > 0 and n == 0:
        n = 1

    if n >= total:
        return full_html, False

    structured = _structured_preview(cleaned, n, total)
    if structured is not None:
        return structured

    return _legacy_single_paragraph_preview(plain, n, total)
