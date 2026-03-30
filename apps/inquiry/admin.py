from django.contrib import admin
from .models import Inquiry


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ("title", "inquiry_type", "user", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("title", "content")
