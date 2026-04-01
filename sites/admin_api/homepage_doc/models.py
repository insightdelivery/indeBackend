from django.db import models


class HomepageDocInfo(models.Model):
    """
    홈페이지 정적 문서 — 기획: _docsRules/1_planDoc/wwwDocEtc.md
    물리 테이블 homepage_doc_info, doc_type당 1행·총 8행(UNIQUE) 고정.
    """

    doc_type = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        db_comment=(
            '문서 종류 코드. 허용 7값만: company_intro(회사소개), terms_of_service(이용약관), '
            'privacy_policy(개인정보취급방침), article_copyright(아티클 저작권), video_copyright(비디오 저작권), '
            'seminar_copyright(세미나 저작권), recommended_search(추천검색어), '
            'external_links(외부링크: 인재채용/광고협업 URL). 행당 UNIQUE.'
        ),
    )
    title = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_comment=(
            'www 페이지 제목·메타 등 표시용. NULL 허용. recommended_search는 title=search, '
            'external_links는 title=external_links 고정 관례.'
        ),
    )
    body_html = models.TextField(
        db_comment=(
            'HTML 본문(빈 문자열 허용). 회사소개/약관/개인정보는 RichText, 저작권·추천검색어는 Textarea 반영, '
            'external_links는 JSON 문자열(인재채용/광고협업 URL) 저장. '
            '이미지는 base64 DB 저장 금지 — 백엔드 PUT에서 S3 URL로 치환 후 저장.'
        ),
    )
    is_published = models.BooleanField(
        default=True,
        db_comment='true일 때만 www 공개 GET(/api/homepage-docs/...)으로 노출. false면 404.',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_comment='생성 일시',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        db_comment='최종 수정 일시',
    )

    class Meta:
        db_table = 'homepage_doc_info'
        ordering = ['doc_type']

    def __str__(self):
        return self.doc_type
