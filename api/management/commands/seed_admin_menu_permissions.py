"""
기존 관리자에게 user_permissions가 없으면 admin_role 템플릿으로 채움.
운영 배포 후 1회 실행 권장.
"""
from django.core.management.base import BaseCommand

from api.models import AdminMemberShip, UserPermission
from api.services.admin_permissions import assign_default_permissions


class Command(BaseCommand):
    help = "user_permissions가 비어 있는 AdminMemberShip에 템플릿 권한 부여"

    def handle(self, *args, **options):
        qs = AdminMemberShip.objects.filter(is_active=True)
        n = 0
        for user in qs:
            if user.memberShipLevel == 1:
                continue
            if UserPermission.objects.filter(user=user).exists():
                continue
            assign_default_permissions(user)
            n += 1
            self.stdout.write(self.style.SUCCESS(f"seeded: {user.memberShipId}"))
        self.stdout.write(self.style.NOTICE(f"done. updated={n}"))
