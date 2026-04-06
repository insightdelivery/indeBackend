"""
비디오/세미나 시리얼라이저
"""
from rest_framework import serializers
from sites.admin_api.video.models import Video
from sites.admin_api.video.source_type_utils import (
    SOURCE_FILE_UPLOAD,
    SOURCE_VIMEO,
    SOURCE_YOUTUBE,
    SOURCE_CHOICES,
    url_matches_source_type,
    infer_source_type_from_row,
)


def _norm_str(value):
    if value is None:
        return ''
    return str(value).strip()


def resolve_api_source_type(instance: Video) -> str:
    """
    GET 목록/상세 응답용 sourceType.
    세미나는 FILE_UPLOAD 고정. 비디오는 DB 값이 유효하면 사용하되,
    FILE_UPLOAD + Stream ID 없음 + videoUrl만 있는 레거시 행은 URL로 YOUTUBE/VIMEO 추론(videoPlan §6.4.2b).
    """
    if getattr(instance, 'contentType', None) == 'seminar':
        return SOURCE_FILE_UPLOAD
    raw = getattr(instance, 'sourceType', None) or ''
    st = _norm_str(raw)
    if st in SOURCE_CHOICES:
        if st == SOURCE_FILE_UPLOAD and not _norm_str(instance.videoStreamId) and _norm_str(instance.videoUrl):
            inferred = infer_source_type_from_row(None, instance.videoUrl)
            if inferred != SOURCE_FILE_UPLOAD:
                return inferred
        return st
    return infer_source_type_from_row(instance.videoStreamId, instance.videoUrl)


class VideoSerializer(serializers.ModelSerializer):
    """비디오 시리얼라이저 (전체 필드)"""

    displayId = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = [
            'id',
            'displayId',
            'contentType',
            'category',
            'title',
            'subtitle',
            'body',
            'videoStreamId',
            'videoUrl',
            'sourceType',
            'thumbnail',
            'speaker',
            'speaker_id',
            'visibility',
            'status',
            'allowComment',
            'viewCount',
            'rating',
            'commentCount',
            'tags',
            'questions',
            'attachments',
            'scheduledAt',
            'deletedAt',
            'deletedBy',
            'createdAt',
            'updatedAt',
        ]
        read_only_fields = [
            'id',
            'displayId',
            'viewCount',
            'commentCount',
            'createdAt',
            'updatedAt',
        ]

    def get_displayId(self, obj):
        """표시용 ID 반환"""
        return obj.get_display_id()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['sourceType'] = resolve_api_source_type(instance)
        return data

    def validate_title(self, value):
        """제목 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError('제목은 필수입니다.')
        return value.strip()

    def validate_contentType(self, value):
        """콘텐츠 타입 검증"""
        if value not in ['video', 'seminar']:
            raise serializers.ValidationError('콘텐츠 타입은 video 또는 seminar여야 합니다.')
        return value

    def validate_category(self, value):
        """카테고리 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError('카테고리는 필수입니다.')
        return value.strip()

    def validate_thumbnail(self, value):
        """썸네일 검증 - base64 데이터는 검증 건너뛰기"""
        if not value:
            return value

        if value.startswith('data:image'):
            return value

        if len(value) > 500:
            raise serializers.ValidationError('썸네일 URL은 500자를 초과할 수 없습니다.')

        return value


class VideoListSerializer(serializers.ModelSerializer):
    """비디오 목록 시리얼라이저 (간소화된 필드)"""

    displayId = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = [
            'id',
            'displayId',
            'contentType',
            'category',
            'title',
            'subtitle',
            'videoStreamId',
            'videoUrl',
            'sourceType',
            'thumbnail',
            'speaker',
            'speaker_id',
            'visibility',
            'status',
            'allowComment',
            'viewCount',
            'rating',
            'commentCount',
            'scheduledAt',
            'deletedAt',
            'deletedBy',
            'createdAt',
            'updatedAt',
        ]
        read_only_fields = [
            'id',
            'displayId',
            'viewCount',
            'commentCount',
            'createdAt',
            'updatedAt',
        ]

    def get_displayId(self, obj):
        """표시용 ID 반환"""
        return obj.get_display_id()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['sourceType'] = resolve_api_source_type(instance)
        return data


class VideoCreateSerializer(serializers.ModelSerializer):
    """비디오 생성 시리얼라이저"""

    class Meta:
        model = Video
        fields = [
            'contentType',
            'category',
            'title',
            'subtitle',
            'body',
            'videoStreamId',
            'videoUrl',
            'sourceType',
            'thumbnail',
            'speaker',
            'speaker_id',
            'visibility',
            'status',
            'allowComment',
            'tags',
            'questions',
            'attachments',
            'scheduledAt',
        ]

    def validate_title(self, value):
        """제목 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError('제목은 필수입니다.')
        return value.strip()

    def validate_contentType(self, value):
        """콘텐츠 타입 검증"""
        if value not in ['video', 'seminar']:
            raise serializers.ValidationError('콘텐츠 타입은 video 또는 seminar여야 합니다.')
        return value

    def validate_category(self, value):
        """카테고리 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError('카테고리는 필수입니다.')
        return value.strip()

    def validate_thumbnail(self, value):
        """썸네일 검증 - base64 데이터는 검증 건너뛰기"""
        if not value:
            return value

        if value.startswith('data:image'):
            return value

        if len(value) > 500:
            raise serializers.ValidationError('썸네일 URL은 500자를 초과할 수 없습니다.')

        return value

    def validate(self, attrs):
        initial = self.initial_data or {}
        raw_sid = attrs.get('speaker_id', initial.get('speaker_id'))
        if raw_sid == '':
            attrs['speaker_id'] = None
            raw_sid = None
        sp = attrs.get('speaker')
        if sp is None:
            sp = initial.get('speaker')
        has_id = raw_sid is not None and raw_sid != ''
        has_name = sp is not None and str(sp).strip() != ''
        if not has_id and not has_name:
            raise serializers.ValidationError(
                {'speaker': '출연자/강사를 선택하거나 이름을 입력해주세요.'}
            )

        ct = attrs.get('contentType')
        stream = _norm_str(attrs.get('videoStreamId'))
        url = _norm_str(attrs.get('videoUrl'))
        st = attrs.get('sourceType')

        if ct == 'seminar':
            attrs['sourceType'] = SOURCE_FILE_UPLOAD
            attrs['videoUrl'] = None
            if url:
                raise serializers.ValidationError({'videoUrl': '세미나는 외부 영상 URL을 사용할 수 없습니다.'})
            if st and st != SOURCE_FILE_UPLOAD:
                raise serializers.ValidationError({'sourceType': '세미나는 FILE_UPLOAD만 가능합니다.'})
            if not stream:
                raise serializers.ValidationError({'videoStreamId': '세미나는 Cloudflare Stream 업로드 영상이 필요합니다.'})
            attrs['videoStreamId'] = stream
            return attrs

        st = attrs.get('sourceType')
        if not _norm_str(st) or st not in SOURCE_CHOICES:
            attrs['sourceType'] = SOURCE_FILE_UPLOAD
            st = SOURCE_FILE_UPLOAD

        if st == SOURCE_FILE_UPLOAD:
            attrs['videoUrl'] = None
            if not stream:
                raise serializers.ValidationError({'videoStreamId': '파일 업로드 모드에서는 Stream ID가 필요합니다.'})
            attrs['videoStreamId'] = stream
            return attrs

        if st not in (SOURCE_VIMEO, SOURCE_YOUTUBE):
            raise serializers.ValidationError({'sourceType': '외부 URL 모드는 VIMEO 또는 YOUTUBE여야 합니다.'})

        attrs['videoStreamId'] = None
        if not url:
            raise serializers.ValidationError({'videoUrl': 'Vimeo 또는 YouTube URL을 입력하세요.'})
        if not url_matches_source_type(st, url):
            raise serializers.ValidationError({'videoUrl': 'URL이 선택한 소스 유형과 일치하지 않습니다.'})
        attrs['videoUrl'] = url
        return attrs


class VideoUpdateSerializer(serializers.ModelSerializer):
    """비디오 수정 시리얼라이저"""

    class Meta:
        model = Video
        fields = [
            'contentType',
            'category',
            'title',
            'subtitle',
            'body',
            'videoStreamId',
            'videoUrl',
            'sourceType',
            'thumbnail',
            'speaker',
            'speaker_id',
            'visibility',
            'status',
            'allowComment',
            'tags',
            'questions',
            'attachments',
            'scheduledAt',
        ]
        extra_kwargs = {
            'title': {'required': False},
            'contentType': {'required': False},
            'category': {'required': False},
            'videoUrl': {'required': False},
            'sourceType': {'required': False},
            'speaker': {'required': False},
            'speaker_id': {'required': False},
        }

    def validate_title(self, value):
        """제목 검증"""
        if value is not None and not value.strip():
            raise serializers.ValidationError('제목은 필수입니다.')
        return value.strip() if value else value

    def validate_contentType(self, value):
        """콘텐츠 타입 검증"""
        if value is not None and value not in ['video', 'seminar']:
            raise serializers.ValidationError('콘텐츠 타입은 video 또는 seminar여야 합니다.')
        return value

    def validate_category(self, value):
        """카테고리 검증"""
        if value is not None and not value.strip():
            raise serializers.ValidationError('카테고리는 필수입니다.')
        return value.strip() if value else value

    def validate_visibility(self, value):
        """공개 범위 검증"""
        if value is not None and not value.strip():
            raise serializers.ValidationError('공개 범위는 필수입니다.')
        return value.strip() if value else value

    def validate_status(self, value):
        """상태 검증"""
        if value is not None and not value.strip():
            raise serializers.ValidationError('상태는 필수입니다.')
        return value.strip() if value else value

    def validate_thumbnail(self, value):
        """썸네일 검증 - base64 데이터는 검증 건너뛰기"""
        if not value:
            return value

        if value.startswith('data:image'):
            return value

        if len(value) > 500:
            raise serializers.ValidationError('썸네일 URL은 500자를 초과할 수 없습니다.')

        return value

    def validate(self, attrs):
        inst = self.instance
        ct = attrs.get('contentType', inst.contentType)
        raw_st = attrs.get('sourceType', getattr(inst, 'sourceType', None))
        st = _norm_str(raw_st) if raw_st is not None else ''
        if not st or st not in SOURCE_CHOICES:
            st = SOURCE_FILE_UPLOAD

        merged_stream = _norm_str(attrs['videoStreamId']) if 'videoStreamId' in attrs else _norm_str(inst.videoStreamId)
        merged_url = _norm_str(attrs['videoUrl']) if 'videoUrl' in attrs else _norm_str(inst.videoUrl)

        if ct == 'seminar':
            if 'sourceType' in attrs and attrs['sourceType'] != SOURCE_FILE_UPLOAD:
                raise serializers.ValidationError({'sourceType': '세미나는 FILE_UPLOAD만 가능합니다.'})
            attrs['sourceType'] = SOURCE_FILE_UPLOAD
            if 'videoUrl' in attrs and _norm_str(attrs.get('videoUrl')):
                raise serializers.ValidationError({'videoUrl': '세미나는 외부 영상 URL을 사용할 수 없습니다.'})
            if _norm_str(inst.videoUrl):
                attrs['videoUrl'] = None
            if not merged_stream:
                raise serializers.ValidationError({'videoStreamId': '세미나는 업로드 영상(Stream)이 필요합니다.'})
            return attrs

        if st == SOURCE_FILE_UPLOAD:
            attrs['sourceType'] = SOURCE_FILE_UPLOAD
            attrs['videoUrl'] = None
            if not merged_stream:
                raise serializers.ValidationError({'videoStreamId': '파일 업로드 모드에서는 Stream 영상이 필요합니다.'})
            return attrs

        if st not in (SOURCE_VIMEO, SOURCE_YOUTUBE):
            raise serializers.ValidationError({'sourceType': '비디오 외부 소스는 VIMEO 또는 YOUTUBE여야 합니다.'})

        attrs['sourceType'] = st
        attrs['videoStreamId'] = None
        if not merged_url:
            raise serializers.ValidationError({'videoUrl': '외부 영상 URL을 입력하세요.'})
        if not url_matches_source_type(st, merged_url):
            raise serializers.ValidationError({'videoUrl': 'URL이 선택한 소스(Vimeo/YouTube)와 일치하지 않습니다.'})
        attrs['videoUrl'] = merged_url
        return attrs
