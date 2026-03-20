def normalize_link_url(value) -> str | None:
    """빈 문자열·공백만 → None."""
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None
