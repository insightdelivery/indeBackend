"""
content_comments(깊이 1)·article_highlight 집계 → Article.commentCount·highlightCount·Video.commentCount 백필.

  python manage.py backfill_comment_and_highlight_counts
  python manage.py backfill_comment_and_highlight_counts --dry-run
  python manage.py backfill_comment_and_highlight_counts --only comments
  python manage.py backfill_comment_and_highlight_counts --only highlights

댓글 수는 루트 댓글(depth=1, is_deleted=False)만 센다. 하이라이트는 아티클만(Video에는 필드 없음).
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, F, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce

from apps.content_comments.models import ContentComment
from apps.highlight.models import ArticleHighlight
from sites.admin_api.articles.models import Article
from sites.admin_api.video.models import Video


def _comment_root_subquery(content_type: str):
    return (
        ContentComment.objects.filter(
            content_type=content_type,
            depth=1,
            is_deleted=False,
            content_id=OuterRef("pk"),
        )
        .values("content_id")
        .annotate(cnt=Count("id"))
        .values("cnt")
    )


def _highlight_count_subquery():
    return (
        ArticleHighlight.objects.filter(article_id=OuterRef("pk"))
        .values("article_id")
        .annotate(cnt=Count("id"))
        .values("cnt")
    )


class Command(BaseCommand):
    help = (
        "content_comments 의 루트 댓글 수를 Article·Video.commentCount 에, "
        "article_highlight 행 수를 Article.highlightCount 에 일괄 반영합니다."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="UPDATE 없이 저장값과 실제 집계가 다른 행 개수만 출력합니다.",
        )
        parser.add_argument(
            "--only",
            type=str,
            default="",
            metavar="comments|highlights|all",
            help="comments / highlights / all(기본).",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        only = (options.get("only") or "all").strip().lower()
        if only not in ("", "all", "comments", "highlights"):
            self.stderr.write(self.style.ERROR("--only 은 comments | highlights | all 만 허용됩니다."))
            return

        do_comments = only in ("", "all", "comments")
        do_highlights = only in ("", "all", "highlights")

        article_comment_sq = Subquery(
            _comment_root_subquery(ContentComment.CONTENT_TYPE_ARTICLE),
            output_field=IntegerField(),
        )
        video_comment_sq = Subquery(
            _comment_root_subquery(ContentComment.CONTENT_TYPE_VIDEO),
            output_field=IntegerField(),
        )
        seminar_comment_sq = Subquery(
            _comment_root_subquery(ContentComment.CONTENT_TYPE_SEMINAR),
            output_field=IntegerField(),
        )
        hl_sq = Subquery(_highlight_count_subquery(), output_field=IntegerField())

        if dry_run:
            if do_comments:
                a_mis = (
                    Article.objects.annotate(_actual=Coalesce(article_comment_sq, Value(0)))
                    .exclude(commentCount=F("_actual"))
                    .count()
                )
                v_mis = (
                    Video.objects.filter(contentType="video")
                    .annotate(_actual=Coalesce(video_comment_sq, Value(0)))
                    .exclude(commentCount=F("_actual"))
                    .count()
                )
                s_mis = (
                    Video.objects.filter(contentType="seminar")
                    .annotate(_actual=Coalesce(seminar_comment_sq, Value(0)))
                    .exclude(commentCount=F("_actual"))
                    .count()
                )
                self.stdout.write(
                    self.style.WARNING(
                        f"[dry-run] commentCount 불일치: Article {a_mis}건, Video {v_mis}건, Seminar {s_mis}건"
                    )
                )
            if do_highlights:
                h_mis = (
                    Article.objects.annotate(_actual=Coalesce(hl_sq, Value(0)))
                    .exclude(highlightCount=F("_actual"))
                    .count()
                )
                self.stdout.write(
                    self.style.WARNING(f"[dry-run] highlightCount 불일치: Article {h_mis}건")
                )
            return

        with transaction.atomic():
            if do_comments:
                n_art = Article.objects.update(
                    commentCount=Coalesce(Subquery(_comment_root_subquery(ContentComment.CONTENT_TYPE_ARTICLE)), Value(0))
                )
                n_vid = Video.objects.filter(contentType="video").update(
                    commentCount=Coalesce(Subquery(_comment_root_subquery(ContentComment.CONTENT_TYPE_VIDEO)), Value(0))
                )
                n_sem = Video.objects.filter(contentType="seminar").update(
                    commentCount=Coalesce(
                        Subquery(_comment_root_subquery(ContentComment.CONTENT_TYPE_SEMINAR)),
                        Value(0),
                    )
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"commentCount 반영: Article {n_art}행, Video(video) {n_vid}행, Video(seminar) {n_sem}행"
                    )
                )
            if do_highlights:
                n_hl = Article.objects.update(
                    highlightCount=Coalesce(Subquery(_highlight_count_subquery()), Value(0))
                )
                self.stdout.write(self.style.SUCCESS(f"highlightCount 반영: Article {n_hl}행"))

        self.stdout.write(self.style.SUCCESS("백필 완료"))
