"""휴대폰 번호 정규화 (회원가입 SMS 인증·중복 검사 공통)."""

from sites.public_api.models import PublicMemberShip


def normalize_phone_kr(raw: str) -> str:
    """
    숫자만 남기고 국내 휴대폰 형태로 맞춘다.
    - +82 10... → 010...
    """
    if not raw:
        return ''
    digits = ''.join(c for c in raw if c.isdigit())
    if not digits:
        return ''
    if digits.startswith('82') and len(digits) >= 11:
        digits = '0' + digits[2:]
    if len(digits) == 10 and digits.startswith('10'):
        digits = '0' + digits
    return digits


def is_valid_kr_mobile(normalized: str) -> bool:
    if not normalized:
        return False
    if len(normalized) < 10 or len(normalized) > 11:
        return False
    return normalized.startswith('01')


def phone_already_registered(normalized: str) -> bool:
    """활성·탈퇴 완료 제외 회원 중 동일 정규화 번호 존재 여부."""
    qs = PublicMemberShip.objects.filter(is_active=True).exclude(
        status=PublicMemberShip.STATUS_WITHDRAWN
    ).only('phone')
    for m in qs:
        if normalize_phone_kr(m.phone or '') == normalized:
            return True
    return False


def phone_registered_to_other_member(normalized: str, exclude_member_sid: int) -> bool:
    """다른 회원이 사용 중인 정규화 번호인지 (본인 제외). 회원정보 휴대폰 변경 SMS용."""
    qs = (
        PublicMemberShip.objects.filter(is_active=True)
        .exclude(status=PublicMemberShip.STATUS_WITHDRAWN)
        .exclude(member_sid=exclude_member_sid)
        .only('phone')
    )
    for m in qs:
        if normalize_phone_kr(m.phone or '') == normalized:
            return True
    return False
