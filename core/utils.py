"""
공통 유틸리티 함수
- API 응답 생성 함수
- 시퀀스 코드 생성
- 기타 공통 유틸리티
"""
import hashlib
import re
from datetime import datetime



def generate_seq_code(table_name):
    from .models import SeqMaster
    now = datetime.now()
    seq_yyyy = now.strftime("%Y")
    seq_yy = now.strftime("%y")
    seq_mm = str(int(now.strftime("%m")))  # 1~12
    seq_dd = now.strftime("%d")
    
    # 밀레니엄 코드 계산 (A->1000년도, B->2000년도, C->3000년도)
    yyc = ""
    if seq_yyyy.startswith("1"):
        yyc = "A"
    elif seq_yyyy.startswith("2"):
        yyc = "B"
    elif seq_yyyy.startswith("3"):
        yyc = "C"

    # 월 변환 (10->A, 11->B, 12->C)
    if seq_mm == "10":
        seq_mm = "A"
    elif seq_mm == "11":
        seq_mm = "B"
    elif seq_mm == "12":
        seq_mm = "C"

    seq_row = SeqMaster.objects.filter(seq_tablename=table_name).first()
    if not seq_row:
        raise Exception(f"시퀀스 정보가 없습니다: {table_name}")

    # 날짜 변경 여부 확인
    date_changed = False
    if seq_row.seq_yyyy and str(seq_row.seq_yyyy) != seq_yyyy:
        date_changed = True
    if seq_row.seq_yy and str(seq_row.seq_yy) != seq_yy:
        date_changed = True
    if seq_row.seq_yyc and str(seq_row.seq_yyc) != yyc:
        date_changed = True
    if seq_row.seq_mm and str(seq_row.seq_mm) != seq_mm:
        date_changed = True
    if seq_row.seq_dd and str(seq_row.seq_dd) != seq_dd:
        date_changed = True

    # 날짜가 변경되면 seq_value를 1로 초기화
    if date_changed:
        seq_row.seq_value = 1
    else:
        seq_row.seq_value += 1

    # 시퀀스 정보 갱신 (null이 아닌 필드만 업데이트)
    seq_row.seq_defa = 'Y' if date_changed else 'N'
    
    # null이 아닌 필드만 업데이트
    if seq_row.seq_yyyy is not None:
        seq_row.seq_yyyy = seq_yyyy
    if seq_row.seq_yy is not None:
        seq_row.seq_yy = seq_yy
    if seq_row.seq_mm is not None:
        seq_row.seq_mm = seq_mm
    if seq_row.seq_dd is not None:
        seq_row.seq_dd = seq_dd
    if seq_row.seq_yyc is not None:
        seq_row.seq_yyc = yyc
    
    seq_row.save()

    # 시퀀스 코드 구성
    code_parts = []
    
    # 1. seq_top
    if seq_row.seq_top:
        code_parts.append(seq_row.seq_top)
    
    # 2. 년도 (seq_yyyy 또는 seq_yy 중 하나는 꼭 있어야 함)
    if seq_row.seq_yyyy:
        code_parts.append(seq_row.seq_yyyy)
    elif seq_row.seq_yy:
        code_parts.append(seq_row.seq_yy)
    
    # 3. seq_mm (null이 아니면 넣음)
    if seq_row.seq_mm:
        code_parts.append(seq_row.seq_mm)
    
    # 4. seq_dd (null이 아니면 넣음)
    if seq_row.seq_dd:
        code_parts.append(seq_row.seq_dd)
    
    # 5. seq_yyc (밀레니엄 코드 - 일 다음에 위치)
    if seq_row.seq_yyc:
        code_parts.append(seq_row.seq_yyc)
    
    # 현재까지의 코드 길이 계산
    current_length = sum(len(part) for part in code_parts)
    
    # 6. 남은 자리수에 seq_value를 0으로 패딩하여 추가
    remaining_length = seq_row.seq_seatcount - current_length
    if remaining_length <= 0:
        raise Exception(f"시퀀스 자리수가 부족합니다: {seq_row.seq_seatcount}")
    
    print_value = "{:0" + str(remaining_length) + "d}"
    seq_value_str = print_value.format(seq_row.seq_value)
    code_parts.append(seq_value_str)
    
    # 최종 시퀀스 코드 생성
    insert_code = "".join(code_parts)
    
    return insert_code




def create_api_response(success, error_code, message, result=None):
    """
    API 응답 생성 (기본 형식)
    
    Args:
        success: 성공 여부 (bool)
        error_code: 오류 코드 (str)
        message: 메시지 (str)
        result: 결과 데이터 (dict, optional)
    
    Returns:
        dict: IndeAPIResponse 형식의 응답
    """
    response = {
        "IndeAPIResponse": {
            "ErrorCode": error_code,
            "Message": message,
        }
    }
    
    if result is not None:
        response["IndeAPIResponse"]["Result"] = result
    
    return response


def create_success_response(result=None, message='정상적으로 처리되었습니다.'):
    """
    성공 응답 생성
    
    Args:
        result: 결과 데이터 (dict, optional)
        message: 메시지 (str, optional)
    
    Returns:
        dict: IndeAPIResponse 형식의 성공 응답
    """
    return create_api_response(True, '00', message, result)


def create_error_response(message='처리 중 오류가 발생했습니다.', error_code='99'):
    """
    오류 응답 생성
    
    Args:
        message: 오류 메시지 (str, optional)
        error_code: 오류 코드 (str, optional)
    
    Returns:
        dict: IndeAPIResponse 형식의 오류 응답
    """
    return create_api_response(False, error_code, message)


def create_custom_error_response(error_code, message):
    """
    커스텀 오류 응답 생성
    
    Args:
        error_code: 커스텀 오류 코드 (str)
        message: 오류 메시지 (str)
    
    Returns:
        dict: IndeAPIResponse 형식의 커스텀 오류 응답
    """
    return create_api_response(False, error_code, message)


def generate_seq_code(table_name):
    """
    시퀀스 코드 생성
    seqMaster 테이블을 기반으로 시퀀스 코드를 생성합니다.
    
    Args:
        table_name: 테이블명 (str)
    
    Returns:
        str: 시퀀스 코드
    """
    from core.models import SeqMaster
    
    now = datetime.now()
    seq_yyyy = now.strftime("%Y")
    seq_yy = now.strftime("%y")
    seq_mm = str(int(now.strftime("%m")))  # 1~12
    seq_dd = now.strftime("%d")
    
    # 밀레니엄 코드 계산 (A->1000년도, B->2000년도, C->3000년도)
    yyc = ""
    if seq_yyyy.startswith("1"):
        yyc = "A"
    elif seq_yyyy.startswith("2"):
        yyc = "B"
    elif seq_yyyy.startswith("3"):
        yyc = "C"

    # 월 변환 (10->A, 11->B, 12->C)
    if seq_mm == "10":
        seq_mm = "A"
    elif seq_mm == "11":
        seq_mm = "B"
    elif seq_mm == "12":
        seq_mm = "C"

    seq_row = SeqMaster.objects.filter(seq_tablename=table_name).first()
    if not seq_row:
        raise Exception(f"시퀀스 정보가 없습니다: {table_name}")

    # 날짜 변경 여부 확인
    date_changed = False
    if seq_row.seq_yyyy and str(seq_row.seq_yyyy) != seq_yyyy:
        date_changed = True
    if seq_row.seq_yy and str(seq_row.seq_yy) != seq_yy:
        date_changed = True
    if seq_row.seq_yyc and str(seq_row.seq_yyc) != yyc:
        date_changed = True
    if seq_row.seq_mm and str(seq_row.seq_mm) != seq_mm:
        date_changed = True
    if seq_row.seq_dd and str(seq_row.seq_dd) != seq_dd:
        date_changed = True

    # 날짜가 변경되면 seq_value를 1로 초기화
    if date_changed:
        seq_row.seq_value = 1
    else:
        seq_row.seq_value = (seq_row.seq_value or 0) + 1

    # 시퀀스 정보 갱신
    if seq_row.seq_yyyy is not None:
        seq_row.seq_yyyy = seq_yyyy
    if seq_row.seq_yy is not None:
        seq_row.seq_yy = seq_yy
    if seq_row.seq_mm is not None:
        seq_row.seq_mm = seq_mm
    if seq_row.seq_dd is not None:
        seq_row.seq_dd = seq_dd
    if seq_row.seq_yyc is not None:
        seq_row.seq_yyc = yyc
    
    seq_row.save()

    # 시퀀스 코드 구성
    code_parts = []
    
    # 1. seq_top
    if seq_row.seq_top:
        code_parts.append(seq_row.seq_top)
    
    # 2. 년도 (seq_yyyy 또는 seq_yy 중 하나는 꼭 있어야 함)
    if seq_row.seq_yyyy:
        code_parts.append(seq_row.seq_yyyy)
    elif seq_row.seq_yy:
        code_parts.append(seq_row.seq_yy)
    
    # 3. seq_mm (null이 아니면 넣음)
    if seq_row.seq_mm:
        code_parts.append(seq_row.seq_mm)
    
    # 4. seq_dd (null이 아니면 넣음)
    if seq_row.seq_dd:
        code_parts.append(seq_row.seq_dd)
    
    # 5. seq_yyc (밀레니엄 코드 - 일 다음에 위치)
    if seq_row.seq_yyc:
        code_parts.append(seq_row.seq_yyc)
    
    # 현재까지의 코드 길이 계산
    current_length = sum(len(part) for part in code_parts)
    
    # 6. 남은 자리수에 seq_value를 0으로 패딩하여 추가
    remaining_length = (seq_row.seq_seatcount or 10) - current_length
    if remaining_length <= 0:
        raise Exception(f"시퀀스 자리수가 부족합니다: {seq_row.seq_seatcount}")
    
    print_value = "{:0" + str(remaining_length) + "d}"
    seq_value_str = print_value.format(seq_row.seq_value)
    code_parts.append(seq_value_str)
    
    # 최종 시퀀스 코드 생성
    insert_code = "".join(code_parts)
    
    return insert_code


class CommonUtils:
    """공통 유틸리티 클래스"""
    
    @staticmethod
    def generate_hash(data):
        """
        데이터 해시 생성
        
        Args:
            data: 해시할 데이터 (str)
        
        Returns:
            str: SHA256 해시값
        """
        return hashlib.sha256(str(data).encode()).hexdigest()
    
    @staticmethod
    def validate_email(email):
        """
        이메일 유효성 검사
        
        Args:
            email: 이메일 주소 (str)
        
        Returns:
            bool: 유효성 여부
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_phone(phone):
        """
        전화번호 유효성 검사 (한국 형식)
        
        Args:
            phone: 전화번호 (str)
        
        Returns:
            bool: 유효성 여부
        """
        # 하이픈 제거 후 검사
        phone_clean = phone.replace('-', '').replace(' ', '')
        pattern = r'^01[0-9]{8,9}$|^0[2-9][0-9]{7,9}$'
        return re.match(pattern, phone_clean) is not None
    
    @staticmethod
    def format_datetime(dt):
        """
        날짜/시간을 "YYYY-MM-DD HH:MM:SS" 형식으로 변환
        
        Args:
            dt: datetime 객체 또는 문자열
        
        Returns:
            str: 포맷된 날짜/시간 문자열
        """
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except:
                return dt
        
        if isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        
        return str(dt)


