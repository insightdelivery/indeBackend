"""
공지/FAQ/문의 관리자 권한 부여 (PublicMemberShip.is_staff=True)
사용법: python manage.py grant_staff 관리자이메일@example.com
"""
from django.core.management.base import BaseCommand
from sites.public_api.models import PublicMemberShip


class Command(BaseCommand):
    help = '지정한 이메일 회원에게 공지/FAQ/문의 관리자 권한(is_staff) 부여'

    def add_arguments(self, parser):
        parser.add_argument(
            'email',
            type=str,
            help='관리자로 지정할 회원의 이메일',
        )

    def handle(self, *args, **options):
        email = (options['email'] or '').strip().lower()
        if not email:
            self.stderr.write(self.style.ERROR('이메일을 입력하세요.'))
            return
        try:
            member = PublicMemberShip.objects.get(email=email)
        except PublicMemberShip.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'해당 이메일 회원이 없습니다: {email}'))
            return
        if member.is_staff:
            self.stdout.write(self.style.WARNING(f'이미 관리자 권한이 있습니다: {email}'))
            return
        member.is_staff = True
        member.save(update_fields=['is_staff'])
        self.stdout.write(self.style.SUCCESS(f'관리자 권한을 부여했습니다: {email} (member_sid={member.member_sid})'))
