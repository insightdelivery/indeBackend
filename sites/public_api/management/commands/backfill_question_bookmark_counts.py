"""
content_question(ARTICLE) 집계 → Article.questionCount,
content_question_answer(ARTICLE) 집계 → Article.answeredQuestionCount (질문당 distinct, 답변 행 수 합이 아님),
publicUserActivityLog(BOOKMARK) 집계 → Article·Video.bookmarkCount 백필.

  python manage.py backfill_question_bookmark_counts
  python manage.py backfill_question_bookmark_counts --dry-run
  python manage.py backfill_question_bookmark_counts --only questions
  python manage.py backfill_question_bookmark_counts --only bookmarks

북마크 수는 LibraryStatsBookmark 와 동일하게 activityType=BOOKMARK 인 행 전체를 센다.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import CharField, Count, F, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Cast, Coalesce

from apps.content_question.models import ContentQuestion, ContentQuestionAnswer
from sites.admin_api.articles.models import Article
from sites.admin_api.video.models import Video
from sites.public_api.models import PublicUserActivityLog


def _question_count_subquery_article():
    return (
        ContentQuestion.objects.filter(
            content_type=ContentQuestion.CONTENT_TYPE_ARTICLE,
            content_id=OuterRef("pk"),
        )
        .values("content_id")
        .annotate(cnt=Count("question_id"))
        .values("cnt")[:1]
    )


def _answered_distinct_question_subquery_article():
    """질문별로 답변이 1건이라도 있으면 1로만 집계(여러 사용자·여러 행이어도 question_id당 1)."""
    return (
        ContentQuestionAnswer.objects.filter(
            content_type=ContentQuestionAnswer.CONTENT_TYPE_ARTICLE,
            content_id=OuterRef("pk"),
        )
        .values("content_id")
        .annotate(cnt=Count("question_id", distinct=True))
        .values("cnt")[:1]
    )


def _bookmark_subquery(content_type: str):
    return (
        PublicUserActivityLog.objects.filter(
            content_type=content_type,
            activity_type="BOOKMARK",
            content_code=Cast(OuterRef("pk"), CharField()),
        )
        .values("content_code")
        .annotate(cnt=Count("public_user_activity_log_id"))
        .values("cnt")[:1]
    )


class Command(BaseCommand):
    help = (
        "Article.questionCount ← content_question(ARTICLE) 건수, "
        "Article.answeredQuestionCount ← 답변이 있는 질문 수(question_id DISTINCT), "
        "Article·Video.bookmarkCount ← publicUserActivityLog BOOKMARK 건수로 일괄 반영합니다."
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
            metavar="questions|bookmarks|all",
            help="questions / bookmarks / all(기본).",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        only = (options.get("only") or "all").strip().lower()
        if only not in ("", "all", "questions", "bookmarks"):
            self.stderr.write(self.style.ERROR("--only 은 questions | bookmarks | all 만 허용됩니다."))
            return

        do_questions = only in ("", "all", "questions")
        do_bookmarks = only in ("", "all", "bookmarks")

        q_sq = Subquery(_question_count_subquery_article(), output_field=IntegerField())
        aq_sq = Subquery(
            _answered_distinct_question_subquery_article(), output_field=IntegerField()
        )
        bm_art_sq = Subquery(_bookmark_subquery("ARTICLE"), output_field=IntegerField())
        bm_vid_sq = Subquery(_bookmark_subquery("VIDEO"), output_field=IntegerField())
        bm_sem_sq = Subquery(_bookmark_subquery("SEMINAR"), output_field=IntegerField())

        if dry_run:
            if do_questions:
                q_mis = (
                    Article.objects.annotate(_actual=Coalesce(q_sq, Value(0)))
                    .exclude(questionCount=F("_actual"))
                    .count()
                )
                self.stdout.write(
                    self.style.WARNING(f"[dry-run] questionCount 불일치: Article {q_mis}건")
                )
                a_mis = (
                    Article.objects.annotate(_actual=Coalesce(aq_sq, Value(0)))
                    .exclude(answeredQuestionCount=F("_actual"))
                    .count()
                )
                self.stdout.write(
                    self.style.WARNING(
                        f"[dry-run] answeredQuestionCount 불일치(질문당 distinct): Article {a_mis}건"
                    )
                )
            if do_bookmarks:
                a_bm = (
                    Article.objects.annotate(_actual=Coalesce(bm_art_sq, Value(0)))
                    .exclude(bookmarkCount=F("_actual"))
                    .count()
                )
                v_bm = (
                    Video.objects.filter(contentType="video")
                    .annotate(_actual=Coalesce(bm_vid_sq, Value(0)))
                    .exclude(bookmarkCount=F("_actual"))
                    .count()
                )
                s_bm = (
                    Video.objects.filter(contentType="seminar")
                    .annotate(_actual=Coalesce(bm_sem_sq, Value(0)))
                    .exclude(bookmarkCount=F("_actual"))
                    .count()
                )
                self.stdout.write(
                    self.style.WARNING(
                        f"[dry-run] bookmarkCount 불일치: Article {a_bm}건, "
                        f"Video(video) {v_bm}건, Video(seminar) {s_bm}건"
                    )
                )
            return

        with transaction.atomic():
            if do_questions:
                n_q = Article.objects.update(
                    questionCount=Coalesce(Subquery(_question_count_subquery_article()), Value(0)),
                    answeredQuestionCount=Coalesce(
                        Subquery(_answered_distinct_question_subquery_article()), Value(0)
                    ),
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"questionCount·answeredQuestionCount 반영: Article {n_q}행"
                    )
                )
            if do_bookmarks:
                n_a = Article.objects.update(
                    bookmarkCount=Coalesce(Subquery(_bookmark_subquery("ARTICLE")), Value(0))
                )
                n_v = Video.objects.filter(contentType="video").update(
                    bookmarkCount=Coalesce(Subquery(_bookmark_subquery("VIDEO")), Value(0))
                )
                n_s = Video.objects.filter(contentType="seminar").update(
                    bookmarkCount=Coalesce(Subquery(_bookmark_subquery("SEMINAR")), Value(0))
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"bookmarkCount 반영: Article {n_a}행, Video(video) {n_v}행, Video(seminar) {n_s}행"
                    )
                )

        self.stdout.write(self.style.SUCCESS("백필 완료"))
