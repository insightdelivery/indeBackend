#!/usr/bin/env python
import os
import sys


def main() -> None:
    # 로컬 개발 기본 설정을 사용합니다.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
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

