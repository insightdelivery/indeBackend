"""
콘텐츠 저자 Django Admin (선택)
"""
from django.contrib import admin
from .models import ContentAuthor, ContentAuthorContentType


class ContentAuthorContentTypeInline(admin.TabularInline):
    model = ContentAuthorContentType
    extra = 0


@admin.register(ContentAuthor)
class ContentAuthorAdmin(admin.ModelAdmin):
    list_display = ['author_id', 'name', 'role', 'status', 'member_ship_sid', 'created_at']
    list_filter = ['role', 'status', 'created_at']
    search_fields = ['name', 'member_ship_sid']
    inlines = [ContentAuthorContentTypeInline]
    readonly_fields = ['author_id', 'created_at', 'updated_at']


@admin.register(ContentAuthorContentType)
class ContentAuthorContentTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'author', 'content_type']
    list_filter = ['content_type']
