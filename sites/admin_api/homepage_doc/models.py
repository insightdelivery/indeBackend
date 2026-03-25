from django.db import models


class HomepageDocInfo(models.Model):
    """홈페이지 정적 문서 (회사소개·약관·개인정보·저작권 3종) — 테이블명 homepage_doc_info"""

    doc_type = models.CharField(max_length=32, unique=True, db_index=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    body_html = models.TextField()
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'homepage_doc_info'
        ordering = ['doc_type']

    def __str__(self):
        return self.doc_type
