"""
아티클 API 뷰
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.core.paginator import Paginator
from datetime import datetime
import logging

from sites.admin_api.articles.models import Article

logger = logging.getLogger(__name__)
from sites.admin_api.articles.serializers import (
    ArticleSerializer,
    ArticleListSerializer,
    ArticleCreateSerializer,
    ArticleUpdateSerializer,
)
from sites.admin_api.articles.utils import (
    replace_base64_images_with_s3_urls,
    upload_thumbnail_to_s3,
    delete_article_images,
    extract_s3_keys_from_content,
    convert_s3_urls_to_presigned,
    get_presigned_thumbnail_url,
)
from sites.admin_api.authentication import AdminJWTAuthentication
from core.utils import create_success_response, create_error_response
from core.s3_storage import S3Storage, get_s3_storage


class ArticleListView(APIView):
    """
    아티클 목록 조회 API
    GET /article/list
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        아티클 목록 조회 (페이지네이션, 필터링, 검색 지원)
        
        Query Parameters:
        - page: 페이지 번호 (기본값: 1)
        - pageSize: 페이지 크기 (기본값: 20)
        - startDate: 시작 날짜 (YYYY-MM-DD)
        - endDate: 종료 날짜 (YYYY-MM-DD)
        - category: 카테고리 (sysCodeSid)
        - visibility: 공개 범위 (sysCodeSid)
        - status: 발행 상태 (sysCodeSid)
        - search: 검색어 (제목, 본문, 작성자)
        """
        try:
            # 쿼리 파라미터 파싱
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('pageSize', 20))
            start_date = request.query_params.get('startDate')
            end_date = request.query_params.get('endDate')
            category = request.query_params.get('category')
            visibility = request.query_params.get('visibility')
            status_filter = request.query_params.get('status')
            search = request.query_params.get('search')
            
            # 기본 쿼리셋
            # status가 'deleted'인 경우 삭제된 항목만 조회, 그 외에는 삭제되지 않은 항목만 조회
            if status_filter == 'deleted':
                queryset = Article.objects.filter(deletedAt__isnull=False)
            else:
                queryset = Article.objects.filter(deletedAt__isnull=True)
            
            # 날짜 필터링
            if start_date:
                try:
                    start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                    queryset = queryset.filter(createdAt__gte=start_datetime)
                except ValueError:
                    pass
            
            if end_date:
                try:
                    end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                    # 하루 종료 시각까지 포함
                    end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
                    queryset = queryset.filter(createdAt__lte=end_datetime)
                except ValueError:
                    pass
            
            # 카테고리 필터링
            if category:
                queryset = queryset.filter(category=category)
            
            # 공개 범위 필터링
            if visibility:
                queryset = queryset.filter(visibility=visibility)
            
            # 상태 필터링
            # status='deleted'인 경우는 이미 deletedAt__isnull=False로 필터링했으므로
            # status 필터링은 건너뛰거나, 또는 status='deleted'가 아닌 경우에만 적용
            if status_filter and status_filter != 'deleted':
                queryset = queryset.filter(status=status_filter)
            elif status_filter == 'deleted':
                # 삭제된 항목은 status='deleted'인 것만 조회
                queryset = queryset.filter(status='deleted')
            
            # 검색 (제목, 본문, 작성자)
            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) |
                    Q(content__icontains=search) |
                    Q(author__icontains=search) |
                    Q(subtitle__icontains=search)
                )
            
            # 정렬 (최신순)
            queryset = queryset.order_by('-createdAt')
            
            # 페이지네이션
            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)
            
            # 시리얼라이저
            serializer = ArticleListSerializer(page_obj.object_list, many=True)
            articles_data = serializer.data
            
            # 각 아티클의 썸네일을 Presigned URL로 변환
            for article_data in articles_data:
                if article_data.get('thumbnail'):
                    article_data['thumbnail'] = get_presigned_thumbnail_url(
                        article_data['thumbnail'], 
                        expires_in=3600
                    )
            
            # 응답 데이터 구성
            result = {
                'articles': articles_data,
                'total': paginator.count,
                'page': page,
                'pageSize': page_size,
            }
            
            return Response(
                create_success_response(result, '아티클 목록 조회 성공'),
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                create_error_response(f'아티클 목록 조회 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ArticleDetailView(APIView):
    """
    아티클 상세 조회/수정/삭제 API
    GET /article/{id} - 상세 조회
    PUT /article/{id} - 수정
    DELETE /article/{id} - 삭제
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, id):
        """
        아티클 상세 조회
        """
        try:
            article = Article.objects.get(id=id, deletedAt__isnull=True)
            serializer = ArticleSerializer(article)
            data = serializer.data.copy()
            
            # 본문의 S3 이미지 URL을 Presigned URL로 변환
            if data.get('content'):
                data['content'] = convert_s3_urls_to_presigned(data['content'], expires_in=3600)
            
            # 썸네일 URL을 Presigned URL로 변환
            if data.get('thumbnail'):
                data['thumbnail'] = get_presigned_thumbnail_url(data['thumbnail'], expires_in=3600)
            
            return Response(
                create_success_response(data, '아티클 조회 성공'),
                status=status.HTTP_200_OK
            )
            
        except Article.DoesNotExist:
            return Response(
                create_error_response('아티클을 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                create_error_response(f'아티클 조회 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request, id):
        """
        아티클 수정
        """
        try:
            article = Article.objects.get(id=id, deletedAt__isnull=True)
            
            # request.data에서 id 제거 (URL 파라미터로 받음)
            update_data = request.data.copy()
            if 'id' in update_data:
                del update_data['id']
            
            # 기존 이미지 키 추출 (나중에 삭제하기 위해)
            old_content = article.content
            old_thumbnail = article.thumbnail
            old_content_keys = extract_s3_keys_from_content(old_content) if old_content else []
            old_thumbnail_key = None
            if old_thumbnail:
                old_thumbnail_key = S3Storage.extract_key_from_url(old_thumbnail)
            
            # 썸네일 처리: base64 데이터는 나중에 S3 업로드 후 저장하므로
            # 시리얼라이저 검증을 위해 임시로 처리
            # request.data에서 직접 가져오기 (update_data는 나중에 수정될 수 있음)
            thumbnail_from_request = request.data.get('thumbnail')
            
            # 썸네일이 명시적으로 전송된 경우만 처리
            if 'thumbnail' in request.data:
                if thumbnail_from_request and thumbnail_from_request.startswith('data:image'):
                    # base64 데이터는 나중에 처리하므로 임시로 기존 값 유지 (시리얼라이저 검증 통과용)
                    update_data['thumbnail'] = old_thumbnail if old_thumbnail else None
                elif thumbnail_from_request == '' or thumbnail_from_request is None:
                    # 빈 문자열이거나 None인 경우 삭제로 처리 (시리얼라이저 검증 통과용)
                    update_data['thumbnail'] = None
                # URL인 경우는 그대로 유지 (update_data에 이미 포함됨)
            
            serializer = ArticleUpdateSerializer(article, data=update_data, partial=False)
            
            if not serializer.is_valid():
                # validation 오류 상세 정보 반환
                error_message = '입력값이 올바르지 않습니다.'
                if serializer.errors:
                    error_details = []
                    for field, errors in serializer.errors.items():
                        if isinstance(errors, list):
                            error_details.append(f"{field}: {', '.join(str(e) for e in errors)}")
                        else:
                            error_details.append(f"{field}: {str(errors)}")
                    if error_details:
                        error_message = '; '.join(error_details)
                
                return Response(
                    create_error_response(
                        error_message,
                        '01'
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 시리얼라이저로 저장
            serializer.save()
            
            # 본문의 base64 이미지를 S3 URL로 교체
            new_content = update_data.get('content', '')
            if new_content and new_content != old_content:
                # base64 이미지가 있는지 확인
                if 'data:image' in new_content:
                    new_content_with_urls, uploaded_keys = replace_base64_images_with_s3_urls(new_content, article.id)
                    article.content = new_content_with_urls
                    article.save(update_fields=['content'])
                    
                    # 기존 이미지 중 사용되지 않는 것 삭제
                    new_content_keys = extract_s3_keys_from_content(article.content)
                    keys_to_delete = set(old_content_keys) - set(new_content_keys)
                    s3_storage = get_s3_storage()
                    for key in keys_to_delete:
                        s3_storage.delete_file(key)
            
            # 썸네일을 S3에 업로드 (변경된 경우에만)
            # request.data에서 원본 thumbnail 값 가져오기 (base64 데이터일 수 있음)
            # 'thumbnail' 키가 request.data에 있는지 확인 (프론트엔드에서 명시적으로 보낸 경우)
            logger.info(f"썸네일 업데이트 체크. request.data에 'thumbnail' 키 존재: {'thumbnail' in request.data}")
            if 'thumbnail' in request.data:
                original_thumbnail = request.data.get('thumbnail')
                logger.info(f"썸네일 데이터 받음. 길이: {len(original_thumbnail) if original_thumbnail else 0}, 시작: {original_thumbnail[:50] if original_thumbnail else 'None'}...")
                
                # 썸네일이 빈 문자열이거나 None인 경우 삭제
                if original_thumbnail is None or original_thumbnail == '':
                    # 썸네일 삭제
                    if old_thumbnail_key:
                        s3_storage = get_s3_storage()
                        s3_storage.delete_file(old_thumbnail_key)
                    article.thumbnail = None
                    article.save(update_fields=['thumbnail'])
                # 썸네일이 실제로 변경된 경우에만 처리
                # base64 데이터이거나, URL이지만 기존 URL과 다른 경우
                else:
                    logger.info(f"썸네일 업데이트 처리 시작. original_thumbnail 시작: {original_thumbnail[:50] if original_thumbnail else 'None'}..., old_thumbnail: {old_thumbnail[:50] if old_thumbnail else 'None'}...")
                    
                    # base64 데이터인 경우 S3에 업로드
                    if original_thumbnail.startswith('data:image'):
                        logger.info("base64 썸네일 데이터를 S3에 업로드합니다.")
                        thumbnail_url = upload_thumbnail_to_s3(original_thumbnail, article.id)
                        if thumbnail_url:
                            logger.info(f"썸네일 업로드 성공. URL: {thumbnail_url}")
                            article.thumbnail = thumbnail_url
                            article.save(update_fields=['thumbnail'])
                            
                            # 기존 썸네일 삭제 (새로 업로드한 썸네일과 다른 키인 경우에만)
                            if old_thumbnail_key:
                                # 새로 업로드한 썸네일의 키 추출
                                new_thumbnail_key = S3Storage.extract_key_from_url(thumbnail_url)
                                logger.info(f"기존 썸네일 키: {old_thumbnail_key}, 새 썸네일 키: {new_thumbnail_key}")
                                
                                # 기존 썸네일과 새 썸네일이 다른 경우에만 삭제
                                if old_thumbnail_key != new_thumbnail_key:
                                    s3_storage = get_s3_storage()
                                    try:
                                        s3_storage.delete_file(old_thumbnail_key)
                                        logger.info(f"기존 썸네일 삭제 성공: {old_thumbnail_key}")
                                    except Exception as e:
                                        logger.error(f"기존 썸네일 삭제 실패: {e}")
                                else:
                                    logger.info(f"기존 썸네일과 새 썸네일이 동일한 키이므로 삭제하지 않습니다: {old_thumbnail_key}")
                        else:
                            logger.error("썸네일 업로드 실패: upload_thumbnail_to_s3가 None을 반환했습니다.")
                    # URL인 경우 (이미 S3 URL이거나 다른 URL)
                    else:
                        # 기존 썸네일과 다른 URL인 경우에만 업데이트
                        if original_thumbnail != old_thumbnail:
                            logger.info(f"썸네일 URL 업데이트: {original_thumbnail}")
                            article.thumbnail = original_thumbnail
                            article.save(update_fields=['thumbnail'])
                            
                            # 기존 썸네일이 S3 URL이었고, 새로운 URL이 다른 S3 URL인 경우 삭제
                            if old_thumbnail_key and old_thumbnail and old_thumbnail.startswith('https://') and 's3' in old_thumbnail:
                                # 새로운 URL도 S3 URL이고 기존 키와 다른 경우에만 삭제
                                new_thumbnail_key = S3Storage.extract_key_from_url(original_thumbnail) if original_thumbnail.startswith('https://') and 's3' in original_thumbnail else None
                                if new_thumbnail_key and new_thumbnail_key != old_thumbnail_key:
                                    s3_storage = get_s3_storage()
                                    try:
                                        s3_storage.delete_file(old_thumbnail_key)
                                        logger.info(f"기존 썸네일 삭제 성공: {old_thumbnail_key}")
                                    except Exception as e:
                                        logger.error(f"기존 썸네일 삭제 실패: {e}")
            
            # 결과 시리얼라이저
            result_serializer = ArticleSerializer(article)
            data = result_serializer.data.copy()
            
            # 본문의 S3 이미지 URL을 Presigned URL로 변환
            if data.get('content'):
                data['content'] = convert_s3_urls_to_presigned(data['content'], expires_in=3600)
            
            # 썸네일 URL을 Presigned URL로 변환
            if data.get('thumbnail'):
                data['thumbnail'] = get_presigned_thumbnail_url(data['thumbnail'], expires_in=3600)
            
            return Response(
                create_success_response(data, '아티클 수정 성공'),
                status=status.HTTP_200_OK
            )
            
        except Article.DoesNotExist:
            return Response(
                create_error_response('아티클을 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                create_error_response(f'아티클 수정 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, id):
        """
        아티클 소프트 삭제
        """
        try:
            article = Article.objects.get(id=id, deletedAt__isnull=True)
            
            # 삭제자 정보 가져오기
            deleted_by = None
            if hasattr(request.user, 'memberShipName'):
                deleted_by = request.user.memberShipName
            elif hasattr(request.user, 'name'):
                deleted_by = request.user.name
            elif hasattr(request.user, 'email'):
                deleted_by = request.user.email
            
            # 소프트 삭제
            article.soft_delete(deleted_by=deleted_by)
            
            return Response(
                create_success_response({'message': '아티클이 삭제되었습니다.'}, '아티클 삭제 성공'),
                status=status.HTTP_200_OK
            )
            
        except Article.DoesNotExist:
            return Response(
                create_error_response('아티클을 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                create_error_response(f'아티클 삭제 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ArticleCreateView(APIView):
    """
    아티클 생성 API
    POST /article/create
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        아티클 생성
        """
        try:
            serializer = ArticleCreateSerializer(data=request.data)
            
            if not serializer.is_valid():
                return Response(
                    create_error_response(
                        '입력값이 올바르지 않습니다.',
                        '01'
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 아티클 생성 (임시로 ID를 얻기 위해)
            # 먼저 아티클을 생성하고, 이미지 처리를 위해 ID가 필요
            validated_data = serializer.validated_data.copy()
            content = validated_data.get('content', '')
            # 원본 request.data에서 thumbnail 가져오기 (base64 데이터일 수 있음)
            # 'thumbnail' 키가 있는지 확인 (프론트엔드에서 명시적으로 보낸 경우)
            thumbnail_data_from_request = None
            if 'thumbnail' in request.data:
                thumbnail_data_from_request = request.data.get('thumbnail')
                logger.info(f"아티클 등록 시 썸네일 데이터 받음. 길이: {len(thumbnail_data_from_request) if thumbnail_data_from_request else 0}, 시작: {thumbnail_data_from_request[:50] if thumbnail_data_from_request else 'None'}...")
            
            # base64 썸네일인 경우 validated_data에서 제거 (나중에 S3 업로드 후 저장)
            # URL인 경우만 validated_data에 포함
            if thumbnail_data_from_request and thumbnail_data_from_request.startswith('data:image'):
                validated_data['thumbnail'] = None  # base64는 나중에 처리
            elif thumbnail_data_from_request:
                validated_data['thumbnail'] = thumbnail_data_from_request  # URL인 경우
            else:
                validated_data['thumbnail'] = None  # 썸네일이 없는 경우
            
            # 아티클 생성
            article = Article.objects.create(**validated_data)
            logger.info(f"아티클 생성 완료. ID: {article.id}")
            
            # 본문의 base64 이미지를 S3 URL로 교체
            if content:
                logger.info(f"본문 이미지 처리 시작. content 길이: {len(content)}")
                new_content, uploaded_keys = replace_base64_images_with_s3_urls(content, article.id)
                if new_content != content:
                    article.content = new_content
                    article.save(update_fields=['content'])
                    logger.info(f"본문 이미지 업로드 완료. 업로드된 이미지 수: {len(uploaded_keys)}")
            
            # 썸네일을 S3에 업로드 (원본 request.data에서 가져옴)
            if thumbnail_data_from_request:
                logger.info(f"아티클 등록 시 썸네일 업로드 시작. article_id: {article.id}, thumbnail_data 길이: {len(thumbnail_data_from_request)}")
                thumbnail_url = upload_thumbnail_to_s3(thumbnail_data_from_request, article.id)
                if thumbnail_url:
                    logger.info(f"썸네일 업로드 성공. URL: {thumbnail_url}")
                    article.thumbnail = thumbnail_url
                    article.save(update_fields=['thumbnail'])
                else:
                    logger.error(f"썸네일 업로드 실패: upload_thumbnail_to_s3가 None을 반환했습니다.")
            else:
                logger.info("썸네일 데이터가 없어 업로드를 건너뜁니다.")
            
            # 결과 시리얼라이저
            result_serializer = ArticleSerializer(article)
            data = result_serializer.data.copy()
            
            # 본문의 S3 이미지 URL을 Presigned URL로 변환
            if data.get('content'):
                data['content'] = convert_s3_urls_to_presigned(data['content'], expires_in=3600)
            
            # 썸네일 URL을 Presigned URL로 변환
            if data.get('thumbnail'):
                data['thumbnail'] = get_presigned_thumbnail_url(data['thumbnail'], expires_in=3600)
            
            return Response(
                create_success_response(data, '아티클 생성 성공'),
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                create_error_response(f'아티클 생성 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ArticleUpdateView(APIView):
    """
    아티클 수정 API
    PUT /article/{id}
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def put(self, request, id):
        """
        아티클 전체 수정
        """
        try:
            article = Article.objects.get(id=id, deletedAt__isnull=True)
            
            serializer = ArticleUpdateSerializer(article, data=request.data, partial=False)
            
            if not serializer.is_valid():
                return Response(
                    create_error_response(
                        '입력값이 올바르지 않습니다.',
                        '01'
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer.save()
            
            # 결과 시리얼라이저
            result_serializer = ArticleSerializer(article)
            
            return Response(
                create_success_response(result_serializer.data, '아티클 수정 성공'),
                status=status.HTTP_200_OK
            )
            
        except Article.DoesNotExist:
            return Response(
                create_error_response('아티클을 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                create_error_response(f'아티클 수정 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ArticleDeleteView(APIView):
    """
    아티클 삭제 API (소프트 삭제)
    DELETE /article/{id}
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, id):
        """
        아티클 소프트 삭제
        """
        try:
            article = Article.objects.get(id=id, deletedAt__isnull=True)
            
            # 삭제자 정보 가져오기
            deleted_by = None
            if hasattr(request.user, 'memberShipName'):
                deleted_by = request.user.memberShipName
            elif hasattr(request.user, 'name'):
                deleted_by = request.user.name
            elif hasattr(request.user, 'email'):
                deleted_by = request.user.email
            
            # 소프트 삭제
            article.soft_delete(deleted_by=deleted_by)
            
            return Response(
                create_success_response({'message': '아티클이 삭제되었습니다.'}, '아티클 삭제 성공'),
                status=status.HTTP_200_OK
            )
            
        except Article.DoesNotExist:
            return Response(
                create_error_response('아티클을 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                create_error_response(f'아티클 삭제 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ArticleBatchDeleteView(APIView):
    """
    아티클 일괄 삭제 API (소프트 삭제)
    DELETE /article/batch-delete
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def delete(self, request):
        """
        아티클 일괄 소프트 삭제
        Body: { "ids": [1, 2, 3, ...] }
        """
        try:
            ids = request.data.get('ids', [])
            
            if not ids or not isinstance(ids, list):
                return Response(
                    create_error_response('아티클 ID 목록이 필요합니다.', '01'),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 삭제자 정보 가져오기
            deleted_by = None
            if hasattr(request.user, 'memberShipName'):
                deleted_by = request.user.memberShipName
            elif hasattr(request.user, 'name'):
                deleted_by = request.user.name
            elif hasattr(request.user, 'email'):
                deleted_by = request.user.email
            
            # 일괄 삭제
            articles = Article.objects.filter(id__in=ids, deletedAt__isnull=True)
            count = articles.count()
            
            for article in articles:
                article.soft_delete(deleted_by=deleted_by)
                # 관련 이미지 삭제 (S3에서)
                delete_article_images(article.id)
            
            return Response(
                create_success_response(
                    {'message': f'{count}개의 아티클이 삭제되었습니다.', 'count': count},
                    '아티클 일괄 삭제 성공'
                ),
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                create_error_response(f'아티클 일괄 삭제 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ArticleBatchStatusView(APIView):
    """
    아티클 상태 일괄 변경 API
    PUT /article/batch-status
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        """
        아티클 상태 일괄 변경
        Body: { "ids": [1, 2, 3, ...], "status": "published" }
        """
        try:
            ids = request.data.get('ids', [])
            new_status = request.data.get('status')
            
            if not ids or not isinstance(ids, list):
                return Response(
                    create_error_response('아티클 ID 목록이 필요합니다.', '01'),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not new_status:
                return Response(
                    create_error_response('상태값이 필요합니다.', '01'),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 상태 일괄 변경
            articles = Article.objects.filter(id__in=ids, deletedAt__isnull=True)
            count = articles.count()
            
            articles.update(status=new_status)
            
            return Response(
                create_success_response(
                    {'message': f'{count}개의 아티클 상태가 변경되었습니다.', 'count': count},
                    '아티클 상태 일괄 변경 성공'
                ),
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                create_error_response(f'아티클 상태 일괄 변경 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ArticleRestoreView(APIView):
    """
    아티클 복구 API
    POST /article/{id}/restore
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, id):
        """
        삭제된 아티클 복구
        """
        try:
            article = Article.objects.get(id=id)
            
            if article.deletedAt is None:
                return Response(
                    create_error_response('삭제된 아티클이 아닙니다.', '01'),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 복구
            article.restore()
            
            # 결과 시리얼라이저
            result_serializer = ArticleSerializer(article)
            
            return Response(
                create_success_response(result_serializer.data, '아티클 복구 성공'),
                status=status.HTTP_200_OK
            )
            
        except Article.DoesNotExist:
            return Response(
                create_error_response('아티클을 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                create_error_response(f'아티클 복구 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ArticleHardDeleteView(APIView):
    """
    아티클 영구 삭제 API
    DELETE /article/{id}/hard-delete
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, id):
        """
        아티클 영구 삭제
        """
        try:
            article = Article.objects.get(id=id)
            
            # 관련 이미지 삭제 (S3에서)
            delete_article_images(article.id)
            
            # 영구 삭제
            article.delete()
            
            return Response(
                create_success_response({'message': '아티클이 영구 삭제되었습니다.'}, '아티클 영구 삭제 성공'),
                status=status.HTTP_200_OK
            )
            
        except Article.DoesNotExist:
            return Response(
                create_error_response('아티클을 찾을 수 없습니다.', '01'),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                create_error_response(f'아티클 영구 삭제 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ArticleExportView(APIView):
    """
    아티클 엑셀 다운로드 API
    GET /article/export
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        아티클 엑셀 다운로드
        Query Parameters: 목록 조회와 동일한 필터링 파라미터 지원
        """
        try:
            # 쿼리 파라미터 파싱 (목록 조회와 동일)
            start_date = request.query_params.get('startDate')
            end_date = request.query_params.get('endDate')
            category = request.query_params.get('category')
            visibility = request.query_params.get('visibility')
            status_filter = request.query_params.get('status')
            search = request.query_params.get('search')
            
            # 기본 쿼리셋 (삭제되지 않은 항목만)
            queryset = Article.objects.filter(deletedAt__isnull=True)
            
            # 필터링 (목록 조회와 동일한 로직)
            if start_date:
                try:
                    start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                    queryset = queryset.filter(createdAt__gte=start_datetime)
                except ValueError:
                    pass
            
            if end_date:
                try:
                    end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                    end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
                    queryset = queryset.filter(createdAt__lte=end_datetime)
                except ValueError:
                    pass
            
            if category:
                queryset = queryset.filter(category=category)
            
            if visibility:
                queryset = queryset.filter(visibility=visibility)
            
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) |
                    Q(content__icontains=search) |
                    Q(author__icontains=search) |
                    Q(subtitle__icontains=search)
                )
            
            queryset = queryset.order_by('-createdAt')
            
            # 시리얼라이저
            serializer = ArticleListSerializer(queryset, many=True)
            articles_data = serializer.data
            
            # 각 아티클의 썸네일을 Presigned URL로 변환
            for article_data in articles_data:
                if article_data.get('thumbnail'):
                    article_data['thumbnail'] = get_presigned_thumbnail_url(
                        article_data['thumbnail'], 
                        expires_in=3600
                    )
            
            # 엑셀 다운로드는 프론트엔드에서 처리하거나 별도 라이브러리 필요
            # 여기서는 JSON 형식으로 반환 (프론트엔드에서 엑셀 변환)
            return Response(
                create_success_response(articles_data, '엑셀 다운로드 데이터 조회 성공'),
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                create_error_response(f'엑셀 다운로드 실패: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

