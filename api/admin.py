from django.contrib import admin
from api.models import AdminMemberShip


@admin.register(AdminMemberShip)
class AdminMemberShipAdmin(admin.ModelAdmin):
    list_display = ['memberShipId', 'memberShipName', 'memberShipEmail', 'memberShipLevel', 'is_admin', 'is_active', 'last_login', 'created_at']
    list_filter = ['is_active', 'is_admin', 'memberShipLevel', 'created_at']
    search_fields = ['memberShipId', 'memberShipName', 'memberShipEmail', 'memberShipPhone']
    readonly_fields = ['memberShipSid', 'created_at', 'updated_at', 'last_login', 'login_count']
    fieldsets = (
        ('기본 정보', {
            'fields': ('memberShipSid', 'memberShipId', 'memberShipPassword', 'memberShipName', 'memberShipEmail', 'memberShipPhone')
        }),
        ('권한 및 레벨', {
            'fields': ('memberShipLevel', 'is_admin', 'is_active')
        }),
        ('로그인 정보', {
            'fields': ('last_login', 'login_count')
        }),
        ('타임스탬프', {
            'fields': ('created_at', 'updated_at')
        }),
    )

# Register your models here.




