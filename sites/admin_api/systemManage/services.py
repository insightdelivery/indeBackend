from django.db import transaction, models
from django.utils import timezone
from core.models import SysCodeManager
from core.utils import generate_seq_code

class SysCodeManagerService:
    """SysCodeManager 비즈니스 로직 서비스"""
    
    @staticmethod
    def create_sys_code(data, user_name=None):
        """시스템 코드 생성"""
        try:
            with transaction.atomic():
                # sysCodeSid 자동 생성 (가이드라인에 따라 generate_seq_code 함수 사용)
                if 'sysCodeSid' not in data or not data['sysCodeSid']:
                    data['sysCodeSid'] = generate_seq_code('sysCodeManager')
                else:
                    # sysCodeSid 중복 체크
                    if SysCodeManager.objects.filter(sysCodeSid=data['sysCodeSid']).exists():
                        raise ValueError(f"sysCodeSid '{data['sysCodeSid']}'는 이미 존재합니다.")
                
                # sysCodeParentsSid를 가지고 parentsSid 자동 설정
                if 'sysCodeParentsSid' in data and data['sysCodeParentsSid']:
                    try:
                        parent_code = SysCodeManager.objects.get(sysCodeSid=data['sysCodeParentsSid'])
                        data['parentsSid'] = parent_code.sid
                    except SysCodeManager.DoesNotExist:
                        raise ValueError(f"부모 코드 '{data['sysCodeParentsSid']}'를 찾을 수 없습니다.")
                else:
                    # sysCodeParentsSid가 없거나 빈 값이면 오류 발생
                    raise ValueError("부모 코드(sysCodeParentsSid)는 필수 입력 항목입니다.")
                
                # 등록자 정보 설정
                if user_name:
                    data['sysCodeRegUserName'] = user_name
                data['sysCodeRegDateTime'] = timezone.now()
                
                # 정렬 순서 자동 설정
                if 'sysCodeSort' not in data or not data['sysCodeSort']:
                    max_sort = SysCodeManager.objects.filter(
                        sysCodeParentsSid=data.get('sysCodeParentsSid', '')
                    ).aggregate(max_sort=models.Max('sysCodeSort'))['max_sort'] or 0
                    data['sysCodeSort'] = max_sort + 1
                
                sys_code = SysCodeManager.objects.create(**data)
                return sys_code
                
        except Exception as e:
            raise ValueError(f"시스템 코드 생성 실패: {str(e)}")
    
    @staticmethod
    def update_sys_code(sid, data, user_name=None):
        """시스템 코드 수정"""
        try:
            with transaction.atomic():
                sys_code = SysCodeManager.objects.get(sid=sid)
                
                # sysCodeSid 변경 시 중복 체크
                if 'sysCodeSid' in data and data['sysCodeSid'] != sys_code.sysCodeSid:
                    if SysCodeManager.objects.filter(sysCodeSid=data['sysCodeSid']).exclude(sid=sid).exists():
                        raise ValueError(f"sysCodeSid '{data['sysCodeSid']}'는 이미 존재합니다.")
                
                # sysCodeParentsSid를 가지고 parentsSid 자동 설정
                if 'sysCodeParentsSid' in data and data['sysCodeParentsSid']:
                    try:
                        parent_code = SysCodeManager.objects.get(sysCodeSid=data['sysCodeParentsSid'])
                        data['parentsSid'] = parent_code.sid
                    except SysCodeManager.DoesNotExist:
                        raise ValueError(f"부모 코드 '{data['sysCodeParentsSid']}'를 찾을 수 없습니다.")
                elif 'sysCodeParentsSid' in data and not data['sysCodeParentsSid']:
                    # sysCodeParentsSid가 빈 값이면 오류 발생
                    raise ValueError("부모 코드(sysCodeParentsSid)는 필수 입력 항목입니다.")
                
                # 수정자 정보 설정
                if user_name:
                    data['sysCodeRegUserName'] = user_name
                data['sysCodeRegDateTime'] = timezone.now()
                
                for field, value in data.items():
                    if hasattr(sys_code, field):
                        setattr(sys_code, field, value)
                
                sys_code.save()
                return sys_code
                
        except SysCodeManager.DoesNotExist:
            raise ValueError(f"SID {sid}인 시스템 코드를 찾을 수 없습니다.")
        except Exception as e:
            raise ValueError(f"시스템 코드 수정 실패: {str(e)}")
    
    @staticmethod
    def delete_sys_code(sid):
        """시스템 코드 삭제 (실제 삭제 대신 비활성화)"""
        try:
            with transaction.atomic():
                sys_code = SysCodeManager.objects.get(sid=sid)
                
                # 하위 코드가 있는지 확인
                if SysCodeManager.objects.filter(sysCodeParentsSid=sys_code.sysCodeSid).exists():
                    raise ValueError("하위 코드가 있는 코드는 삭제할 수 없습니다.")
                
                # 실제 삭제 대신 비활성화
                sys_code.sysCodeUse = 'N'
                sys_code.save()
                
                return True
                
        except SysCodeManager.DoesNotExist:
            raise ValueError(f"SID {sid}인 시스템 코드를 찾을 수 없습니다.")
        except Exception as e:
            raise ValueError(f"시스템 코드 삭제 실패: {str(e)}")
    
    @staticmethod
    def get_code_tree(parent_id='*'):
        """전체 코드 트리 구조 조회"""
        def build_tree_recursive(parent_id):
            codes = SysCodeManager.objects.filter(
                sysCodeParentsSid=parent_id, 
                sysCodeUse='Y'
            ).order_by('sysCodeSort', 'sysCodeSid')
            
            tree = []
            for code in codes:
                node = {
                    'sid': code.sid,
                    'parentsSid': code.parentsSid,
                    'sysCodeSid': code.sysCodeSid,
                    'sysCodeParentsSid': code.sysCodeParentsSid,
                    'sysCodeName': code.sysCodeName,
                    'sysCodeValName': code.sysCodeValName,
                    'sysCodeVal': code.sysCodeVal,
                    'sysCodeVal1Name': code.sysCodeVal1Name,
                    'sysCodeVal1': code.sysCodeVal1,
                    'sysCodeVal2Name': code.sysCodeVal2Name,
                    'sysCodeVal2': code.sysCodeVal2,
                    'sysCodeVal3Name': code.sysCodeVal3Name,
                    'sysCodeVal3': code.sysCodeVal3,
                    'sysCodeVal4Name': code.sysCodeVal4Name,
                    'sysCodeVal4': code.sysCodeVal4,
                    'sysCodeUse': code.sysCodeUse,
                    'sysCodeSort': code.sysCodeSort,
                    'sysCodeRegUserName': code.sysCodeRegUserName,
                    'sysCodeRegDateTime': code.sysCodeRegDateTime,
                    'children': build_tree_recursive(code.sysCodeSid)
                }
                tree.append(node)
            return tree
        
        return build_tree_recursive(parent_id)
    
    @staticmethod
    def get_codes_by_parent(parent_id='*'):
        """특정 부모 코드의 하위 레벨만 조회"""
        return SysCodeManager.objects.filter(
            sysCodeParentsSid=parent_id,
            sysCodeUse='Y'
        ).order_by('sysCodeSort', 'sysCodeSid')



