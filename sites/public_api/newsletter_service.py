"""
뉴스레터 원장·통합 (newsLetterModelPlan.md §14)
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from sites.public_api.models import NewsletterSubscriber, PublicMemberShip


def normalize_email(email: str) -> str:
    return (email or '').strip().lower()


def sync_newsletter_subscriber_after_signup(
    member: PublicMemberShip,
    *,
    ip_address: str = '',
    user_agent: str = '',
) -> None:
    """회원가입 완료 시 뉴스레터 동의면 원장에 MEMBER_SIGNUP 기록(§2-2a)."""
    if not member.newsletter_agree:
        return
    email = normalize_email(member.email)
    if not email:
        return
    now = timezone.now()
    NewsletterSubscriber.objects.update_or_create(
        email=email,
        defaults={
            'name': (member.name or '')[:100],
            'signup_source': NewsletterSubscriber.SIGNUP_MEMBER_SIGNUP,
            'member_id': member.member_sid,
            'agree_privacy': True,
            'agree_marketing': True,
            'subscribe_status': NewsletterSubscriber.STATUS_SUBSCRIBED,
            'agree_datetime': now,
            'unsubscribe_datetime': None,
            'ip_address': (ip_address or '')[:45] or None,
            'user_agent': user_agent or None,
        },
    )


def merge_member_agreements_into_subscriber_ledger():
    """
    `newsletter_agree=True` 인 활성 회원을 `newsletter_subscriber` 원장에 MEMBER_SIGNUP 으로 upsert.
    통합 결과를 별도 테이블에 저장하는 것이 아니라 §3-1 원장 행을 회원 기준으로 보강한다(관리 §13-6 병합).
    MEMBER_AGREE 시각 대용은 `PublicMemberShip.updated_at`(§3-1a)을 `agree_datetime`에 반영한다.
    """
    created = 0
    updated = 0
    qs = PublicMemberShip.objects.filter(
        newsletter_agree=True,
        is_active=True,
        status=PublicMemberShip.STATUS_ACTIVE,
    ).exclude(email__exact='')
    with transaction.atomic():
        for m in qs.iterator():
            email = normalize_email(m.email or '')
            if not email:
                continue
            agree_ts = m.updated_at or timezone.now()
            _obj, was_created = NewsletterSubscriber.objects.update_or_create(
                email=email,
                defaults={
                    'name': (m.name or '')[:100],
                    'signup_source': NewsletterSubscriber.SIGNUP_MEMBER_SIGNUP,
                    'member_id': m.member_sid,
                    'agree_privacy': True,
                    'agree_marketing': True,
                    'subscribe_status': NewsletterSubscriber.STATUS_SUBSCRIBED,
                    'agree_datetime': agree_ts,
                    'unsubscribe_datetime': None,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
    return {'created': created, 'updated': updated, 'total': created + updated}


def get_combined_newsletter_list():
    """
    이메일별 최신 이벤트(시각)로 마케팅 동의 대상만 반환 (§14-7).
    각 항목: email, name, source, agree_marketing, latest_agree_at (ISO 문자열)
    """
    result: dict[str, dict] = {}

    for m in PublicMemberShip.objects.filter(is_active=True).iterator():
        raw = (m.email or '').strip()
        if not raw:
            continue
        email = normalize_email(raw)
        if m.newsletter_agree:
            ts = m.updated_at
            if ts:
                prev = result.get(email)
                if not prev or prev['datetime'] < ts:
                    result[email] = {
                        'email': email,
                        'name': (m.name or '')[:100],
                        'source': 'MEMBER',
                        'event': 'AGREE',
                        'datetime': ts,
                        'agree_marketing': True,
                    }

    for n in NewsletterSubscriber.objects.iterator():
        raw = (n.email or '').strip()
        if not raw:
            continue
        email = normalize_email(raw)

        if n.subscribe_status == NewsletterSubscriber.STATUS_SUBSCRIBED and n.agree_datetime:
            ts = n.agree_datetime
            prev = result.get(email)
            if not prev or prev['datetime'] < ts:
                result[email] = {
                    'email': email,
                    'name': (n.name or '')[:100] or email,
                    'source': 'NEWSLETTER',
                    'event': 'AGREE',
                    'datetime': ts,
                    'agree_marketing': bool(n.agree_marketing),
                }

        if n.subscribe_status == NewsletterSubscriber.STATUS_UNSUBSCRIBED and n.unsubscribe_datetime:
            ts = n.unsubscribe_datetime
            prev = result.get(email)
            if not prev or prev['datetime'] < ts:
                result[email] = {
                    'email': email,
                    'name': (n.name or '')[:100] or email,
                    'source': 'NEWSLETTER',
                    'event': 'UNSUBSCRIBE',
                    'datetime': ts,
                    'agree_marketing': bool(n.agree_marketing),
                }

    final_list = []
    for data in result.values():
        if data['event'] != 'AGREE':
            continue
        final_list.append(
            {
                'email': data['email'],
                'name': data['name'],
                'source': data['source'],
                'agree_marketing': data['agree_marketing'],
                'latest_agree_at': data['datetime'].isoformat() if data['datetime'] else None,
            }
        )
    final_list.sort(key=lambda x: x['email'])
    return final_list


def subscribe_from_modal(
    *,
    email: str,
    name: str,
    agree_privacy: bool,
    agree_marketing: bool,
    member: PublicMemberShip | None,
    ip_address: str,
    user_agent: str,
):
    """
    모달 구독 UPSERT (§2-2b).
    member: JWT로 확인된 회원 또는 None. 이메일이 회원 이메일과 일치할 때만 member_id·회원 동기화.
    Returns (success: bool, error_message: str | None)
    """
    email_norm = normalize_email(email)
    if not email_norm:
        return False, '이메일을 입력해 주세요.'
    if not agree_privacy or not agree_marketing:
        return False, '필수 동의 항목에 동의해 주세요.'

    now = timezone.now()
    sync_member = False
    member_pk = None
    if member is not None:
        if normalize_email(member.email) == email_norm:
            sync_member = True
            member_pk = member.member_sid

    dup = NewsletterSubscriber.objects.filter(email=email_norm).first()
    if dup and dup.subscribe_status == NewsletterSubscriber.STATUS_SUBSCRIBED:
        return False, '이미 구독된 이메일입니다.'

    with transaction.atomic():
        existing = (
            NewsletterSubscriber.objects.select_for_update()
            .filter(email=email_norm)
            .first()
        )
        if existing and existing.subscribe_status == NewsletterSubscriber.STATUS_SUBSCRIBED:
            return False, '이미 구독된 이메일입니다.'

        defaults = {
            'name': (name or '')[:100] or None,
            'signup_source': NewsletterSubscriber.SIGNUP_WEB_MODAL,
            'member_id': member_pk,
            'agree_privacy': True,
            'agree_marketing': True,
            'subscribe_status': NewsletterSubscriber.STATUS_SUBSCRIBED,
            'agree_datetime': now,
            'unsubscribe_datetime': None,
            'ip_address': (ip_address or '')[:45] or None,
            'user_agent': user_agent or None,
        }

        if existing:
            for k, v in defaults.items():
                setattr(existing, k, v)
            existing.save()
        else:
            NewsletterSubscriber.objects.create(email=email_norm, **defaults)

        if sync_member and member is not None:
            member.newsletter_agree = True
            member.save()

    return True, None
