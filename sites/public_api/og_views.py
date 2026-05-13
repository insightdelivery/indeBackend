"""
Dynamic OG Rendering for SNS crawlers.

Nginx should proxy crawler requests for existing frontend detail URLs
(`/article/detail?id=...`, `/video/detail?id=...`, `/seminar/detail?id=...`) to
these Django views. Because nginx already performs crawler detection, these
views always return metadata HTML and never redirect back to the frontend.
"""
import re
from html import escape
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.views import View

from sites.admin_api.articles.models import Article
from sites.admin_api.articles.utils import get_presigned_thumbnail_url as get_article_thumbnail_url
from sites.admin_api.content_publish_syscodes import STATUS_PUBLISHED
from sites.admin_api.video.models import Video
from sites.admin_api.video.utils import get_presigned_thumbnail_url as get_video_thumbnail_url


DEFAULT_OG_IMAGE_PATH = "/indeOgLogo.jpeg?v=2"


def public_origin(request) -> str:
    forwarded_host = (request.META.get("HTTP_X_FORWARDED_HOST") or "").split(",")[0].strip()
    host = forwarded_host or request.get_host()
    forwarded_proto = (request.META.get("HTTP_X_FORWARDED_PROTO") or "").split(",")[0].strip()
    scheme = forwarded_proto or request.scheme

    # If nginx proxies with the public host preserved, prefer that. API hosts
    # should not leak into canonical/og:url.
    if (
        forwarded_host
        and host
        and not host.startswith("api.")
        and not host.startswith("admin-api.")
        and not host.endswith(":8000")
        and not host.endswith(":8001")
    ):
        return f"{scheme}://{host}".rstrip("/")

    return getattr(settings, "PUBLIC_WWW_ORIGIN", "https://inde.kr").rstrip("/")


def detail_url(request, section: str, content_id: int) -> str:
    origin = public_origin(request)
    query = urlencode({"id": str(content_id)})
    return f"{origin}/{section}/detail?{query}"


def absolute_image_url(request, image_url: str | None) -> str:
    raw = (image_url or "").strip()
    origin = public_origin(request)
    if not raw:
        return f"{origin}{DEFAULT_OG_IMAGE_PATH}"
    if raw.startswith("//"):
        return f"https:{raw}"
    if re.match(r"^https?://", raw, flags=re.IGNORECASE):
        return raw
    if raw.startswith("/"):
        return f"{origin}{raw}"
    return raw


def plain_text_excerpt(html: str | None, max_len: int = 180) -> str:
    text = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", html or "", flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_len:
        return text
    return f"{text[: max_len - 1].rstrip()}…"


def og_html(
    *,
    title: str,
    description: str,
    image_url: str,
    page_url: str,
    og_type: str = "article",
) -> str:
    safe_title = escape(title or "InDe")
    safe_description = escape(description or "InDe 콘텐츠")
    safe_image = escape(image_url)
    safe_url = escape(page_url)
    safe_type = escape(og_type)

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title} | InDe</title>
  <meta name="description" content="{safe_description}">
  <link rel="canonical" href="{safe_url}">
  <meta property="og:title" content="{safe_title}">
  <meta property="og:description" content="{safe_description}">
  <meta property="og:image" content="{safe_image}">
  <meta property="og:image:alt" content="{safe_title}">
  <meta property="og:url" content="{safe_url}">
  <meta property="og:type" content="{safe_type}">
  <meta property="og:site_name" content="InDe">
  <meta property="og:locale" content="ko_KR">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{safe_title}">
  <meta name="twitter:description" content="{safe_description}">
  <meta name="twitter:image" content="{safe_image}">
</head>
<body>
  <p><a href="{safe_url}">{safe_title}</a></p>
</body>
</html>"""


def content_id_from_request(request):
    raw = (request.GET.get("id") or "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


class ArticleOgDetailView(View):
    def get(self, request):
        article_id = content_id_from_request(request)
        if not article_id:
            return HttpResponseBadRequest("Missing or invalid id")

        article = (
            Article.objects.filter(id=article_id, deletedAt__isnull=True, status=STATUS_PUBLISHED)
            .only("id", "title", "subtitle", "content", "thumbnail")
            .first()
        )
        if not article:
            return HttpResponse("Content not found", status=404)

        thumb = get_article_thumbnail_url(article.thumbnail, expires_in=3600) if article.thumbnail else None
        description = (article.subtitle or "").strip() or plain_text_excerpt(article.content)
        html = og_html(
            title=article.title,
            description=description,
            image_url=absolute_image_url(request, thumb),
            page_url=detail_url(request, "article", article.id),
            og_type="article",
        )
        return HttpResponse(html, content_type="text/html; charset=utf-8")


class VideoOgDetailView(View):
    content_type = "video"

    def get(self, request):
        video_id = content_id_from_request(request)
        if not video_id:
            return HttpResponseBadRequest("Missing or invalid id")

        video = (
            Video.objects.filter(
                id=video_id,
                contentType=self.content_type,
                deletedAt__isnull=True,
                status=STATUS_PUBLISHED,
            )
            .only("id", "title", "subtitle", "body", "thumbnail", "contentType")
            .first()
        )
        if not video:
            return HttpResponse("Content not found", status=404)

        thumb = get_video_thumbnail_url(video.thumbnail, expires_in=3600) if video.thumbnail else None
        description = (video.subtitle or "").strip() or plain_text_excerpt(video.body)
        html = og_html(
            title=video.title,
            description=description,
            image_url=absolute_image_url(request, thumb),
            page_url=detail_url(request, self.content_type, video.id),
            og_type="website",
        )
        return HttpResponse(html, content_type="text/html; charset=utf-8")


class SeminarOgDetailView(VideoOgDetailView):
    content_type = "seminar"
