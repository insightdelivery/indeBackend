from django.contrib import admin
from .models import Inquiry


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "inquiry_type",
        "user",
        "status",
        "answer_email_sent_at",
        "answer_email_opened_at",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("title", "content")
