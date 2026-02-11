"""
Django project package.
"""
# PyMySQL을 MySQLdb로 사용하도록 설정 (mysqlclient 대신 사용)
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    # PyMySQL이 설치되지 않은 경우 무시 (mysqlclient 사용)
    pass

