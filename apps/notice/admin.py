from django.contrib import admin
from .models import Notice


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ("title", "is_pinned", "view_count", "created_at")
    list_filter = ("is_pinned",)
    search_fields = ("title", "content")
