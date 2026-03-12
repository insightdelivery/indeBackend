#!/usr/bin/env python
import os
import sys


def main() -> None:
    # settings는 base만 사용. 환경별 차이는 ENV_MODE + .env 파일로 처리.
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.base"
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django가 설치되어 있는지 확인해주세요. "
            "requirements.txt를 설치한 뒤 다시 시도하세요."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

