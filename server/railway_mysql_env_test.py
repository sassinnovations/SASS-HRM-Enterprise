"""Offline configuration checks for the Saritha Railway deployment merge."""
import importlib
import os
import sys
import types
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mysql_backend import raw_mysql_connection


def check_vars(values, expected):
    fake_driver=types.ModuleType('pymysql')
    fake_driver.cursors=types.SimpleNamespace(DictCursor=object())
    fake_driver.connect=lambda **settings: settings
    with patch.dict(sys.modules, {'pymysql':fake_driver}), patch.dict(os.environ, values, clear=True):
        result=raw_mysql_connection()
    for key,value in expected.items():
        assert result[key]==value,(key,result.get(key),value)


def run():
    check_vars({'MYSQLHOST':'railway-db.internal','MYSQLPORT':'3306','MYSQLUSER':'hrm',
                'MYSQLPASSWORD':'test-secret','MYSQLDATABASE':'hrm_live'},
               {'host':'railway-db.internal','port':3306,'user':'hrm',
                'password':'test-secret','database':'hrm_live'})
    check_vars({'MYSQLHOST':'railway-db.internal','MYSQL_PORT':'3309','MYSQL_HOST':'custom-host',
                'MYSQL_USER':'preferred','MYSQL_DATABASE':'preferred-db'},
               {'host':'custom-host','port':3309,'user':'preferred','database':'preferred-db'})
    check_vars({}, {'host':'127.0.0.1','port':3307,'user':'sass_hrm_app','database':'sass_hrm'})
    print('PASS Railway MYSQLHOST fallback, explicit MYSQL_* override and local Docker defaults')


if __name__=='__main__':
    run()
