"""
IndeJSONRenderer
모든 API 응답을 IndeAPIResponse 형식으로 자동 변환
"""
from rest_framework.renderers import JSONRenderer
from rest_framework import status


class IndeJSONRenderer(JSONRenderer):
    """
    Inde API 응답 형식으로 자동 변환하는 렌더러
    
    응답 형식:
    {
        "IndeAPIResponse": {
            "ErrorCode": "00",
            "Message": "정상적으로 처리되었습니다.",
            "Result": { ... }
        }
    }
    """
    
    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        응답 데이터를 IndeAPIResponse 형식으로 변환
        
        Args:
            data: 원본 응답 데이터
            accepted_media_type: 미디어 타입
            renderer_context: 렌더러 컨텍스트 (status_code 포함)
        
        Returns:
            bytes: JSON 인코딩된 응답
        """
        response = renderer_context.get('response') if renderer_context else None
        status_code = response.status_code if response else status.HTTP_200_OK
        
        # 이미 IndeAPIResponse 형식인 경우 그대로 반환
        if isinstance(data, dict) and 'IndeAPIResponse' in data:
            return super().render(data, accepted_media_type, renderer_context)
        
        # 상태 코드에 따라 ErrorCode와 Message 결정
        if 200 <= status_code < 300:
            error_code = '00'
            message = '정상적으로 처리되었습니다.'
        elif 400 <= status_code < 500:
            error_code = '40'
            message = '요청이 올바르지 않습니다.'
            # 오류 메시지가 있으면 사용
            if isinstance(data, dict) and 'error' in data:
                message = data.get('error', message)
            elif isinstance(data, dict) and 'detail' in data:
                message = data.get('detail', message)
        else:
            error_code = '50'
            message = '서버 오류가 발생했습니다.'
            # 오류 메시지가 있으면 사용
            if isinstance(data, dict) and 'error' in data:
                message = data.get('error', message)
            elif isinstance(data, dict) and 'detail' in data:
                message = data.get('detail', message)
        
        # IndeAPIResponse 형식으로 변환
        formatted_data = {
            "IndeAPIResponse": {
                "ErrorCode": error_code,
                "Message": message,
            }
        }
        
        # 데이터가 있으면 Result에 포함
        if data is not None:
            # 오류 응답인 경우 error 필드 제거
            if isinstance(data, dict):
                result_data = {k: v for k, v in data.items() if k not in ['error', 'detail']}
                if result_data:
                    formatted_data["IndeAPIResponse"]["Result"] = result_data
            else:
                formatted_data["IndeAPIResponse"]["Result"] = data
        
        return super().render(formatted_data, accepted_media_type, renderer_context)


