"""허용 doc_type 7종 (wwwDocEtc.md §2.3, §4.5)"""

HOMEPAGE_DOC_TYPES_ORDERED = (
    'company_intro',
    'terms_of_service',
    'privacy_policy',
    'article_copyright',
    'video_copyright',
    'seminar_copyright',
    'recommended_search',
)

HOMEPAGE_DOC_TYPES = frozenset(HOMEPAGE_DOC_TYPES_ORDERED)
