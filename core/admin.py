from django.contrib import admin
from core.models import Account, AuditLog, SeqMaster


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['email', 'name', 'phone', 'is_active', 'is_staff', 'email_verified', 'created_at']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'email_verified']
    search_fields = ['email', 'name', 'phone']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'site_slug', 'action', 'resource', 'resource_id', 'ip_address', 'created_at']
    list_filter = ['site_slug', 'action', 'created_at']
    search_fields = ['user_id', 'resource', 'resource_id', 'ip_address']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'


@admin.register(SeqMaster)
class SeqMasterAdmin(admin.ModelAdmin):
    list_display = ['seq_tablename', 'seq_top', 'seq_seatcount', 'seq_value', 'seq_yyyy', 'seq_yy', 'seq_mm', 'seq_dd', 'seq_yyc']
    list_filter = ['seq_tablename']
    search_fields = ['seq_tablename', 'seq_top']
    readonly_fields = ['seqSid']
    fieldsets = (
        ('기본 정보', {
            'fields': ('seqSid', 'seq_top', 'seq_tablename', 'seq_seatcount')
        }),
        ('시퀀스 값', {
            'fields': ('seq_value',)
        }),
        ('날짜 정보', {
            'fields': ('seq_yyyy', 'seq_yy', 'seq_yyc', 'seq_mm', 'seq_dd')
        }),
    )


