"""
Article Highlight 비즈니스 로직 (articleHightlightPlan.md 15.4 겹침 검사 등)
"""
from django.db import transaction

from core.models import SysCodeManager
from sites.admin_api.articles.models import Article
from .models import ArticleHighlight


def sync_article_highlight_count(article_id: int) -> None:
    """article_highlight 행 수를 Article.highlightCount에 반영."""
    n = ArticleHighlight.objects.filter(article_id=article_id).count()
    Article.objects.filter(id=article_id).update(highlightCount=n)

DEFAULT_HIGHLIGHT_MAX_LENGTH = 500


def get_highlight_max_length() -> int:
    """SYS26312B005 — 하이라이트 최대 글자 수 (sysCodeVal). 없으면 기본값."""
    row = SysCodeManager.objects.filter(sysCodeSid='SYS26312B005', sysCodeUse='Y').first()
    if row and row.sysCodeVal:
        try:
            n = int(str(row.sysCodeVal).strip())
            if n > 0:
                return n
        except ValueError:
            pass
    return DEFAULT_HIGHLIGHT_MAX_LENGTH


def _check_overlap(user, article_id: int, paragraph_index: int, start_offset: int, end_offset: int) -> bool:
    """
    동일 article_id, user, paragraph_index 내 기존 하이라이트와 겹치면 True.
    [start_offset, end_offset) 과 기존 [s, e) 가 한 칸이라도 겹치면 겹침.
    """
    existing = ArticleHighlight.objects.filter(
        article_id=article_id,
        user=user,
        paragraph_index=paragraph_index,
    )
    for h in existing:
        # [start_offset, end_offset) vs [h.start_offset, h.end_offset)
        if not (end_offset <= h.start_offset or start_offset >= h.end_offset):
            return True
    return False


def create_highlights(user, payload_list: list, max_highlight_length: int | None = None) -> tuple[list, int | None]:
    """
    문단별 항목 리스트로 하이라이트 생성. 동일 highlight_group_id 부여.
    max_highlight_length: highlight_text 길이 제한 (None이면 검사 생략)
    Returns: (created ArticleHighlight list, highlight_group_id)
    """
    if not payload_list:
        return [], None

    article_id = payload_list[0].get('articleId')
    if not article_id:
        return [], None
    if not Article.objects.filter(id=article_id, deletedAt__isnull=True).exists():
        return [], None

    group_id = payload_list[0].get('highlightGroupId')
    created_list = []

    with transaction.atomic():
        for p in payload_list:
            aid = p.get('articleId')
            if aid != article_id:
                continue
            text = (p.get('highlightText') or '')[:65535]
            if max_highlight_length is not None and len(text) > max_highlight_length:
                raise ValueError(f'하이라이트는 {max_highlight_length}자 까지 가능합니다.')
            if _check_overlap(
                user,
                aid,
                p.get('paragraphIndex', 0),
                p.get('startOffset', 0),
                p.get('endOffset', 0),
            ):
                raise ValueError('해당 구간에 이미 하이라이트가 있습니다.')

        first_id = None
        for p in payload_list:
            aid = p.get('articleId')
            if aid != article_id:
                continue
            text = (p.get('highlightText') or '')[:65535]
            prefix = (p.get('prefixText') or '')[:255]
            suffix = (p.get('suffixText') or '')[:255]
            obj = ArticleHighlight(
                article_id=aid,
                user=user,
                highlight_group_id=first_id or 0,  # 첫 레코드는 0으로 저장 후 id로 갱신
                paragraph_index=p.get('paragraphIndex', 0),
                highlight_text=text,
                prefix_text=prefix,
                suffix_text=suffix,
                start_offset=p.get('startOffset', 0),
                end_offset=p.get('endOffset', 0),
                color=p.get('color') or 'yellow',
            )
            obj.save()
            if first_id is None:
                first_id = obj.id
                obj.highlight_group_id = obj.id
                obj.save(update_fields=['highlight_group_id'])
            else:
                obj.highlight_group_id = first_id
                obj.save(update_fields=['highlight_group_id'])
            created_list.append(obj)

    if article_id:
        sync_article_highlight_count(int(article_id))
    return created_list, first_id
