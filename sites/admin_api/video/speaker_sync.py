"""
출연자/강사 speaker_id → speaker 문자열 동기화 (아티클 author_id → author 와 동일 패턴).
"""
from sites.admin_api.content_author.models import ContentAuthor


def apply_video_speaker_sync(data: dict) -> None:
    """
    data를 제자리에서 수정한다.
    speaker_id가 유효하면 ContentAuthor.name으로 speaker를 덮어쓴다.
    speaker_id가 빈 값이면 None으로 정규화한다.
    """
    raw = data.get('speaker_id')
    if raw == '':
        data['speaker_id'] = None
        raw = None
    if raw is None:
        return
    try:
        if hasattr(raw, 'name'):
            ca = raw
            data['speaker'] = ca.name
            return
        pk = int(raw) if isinstance(raw, (str, int)) else getattr(
            raw, 'author_id', getattr(raw, 'pk', None)
        )
        if pk is not None:
            content_author = ContentAuthor.objects.get(author_id=pk)
            data['speaker'] = content_author.name
    except (ContentAuthor.DoesNotExist, ValueError, TypeError):
        pass
