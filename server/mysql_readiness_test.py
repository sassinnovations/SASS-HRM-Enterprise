"""Confirm readiness is a real zero-row DB check and diagnostics require auth."""
import os
import tempfile
from pathlib import Path

os.environ['SASS_HRM_TESTING'] = '1'
os.environ['DB_ENGINE'] = 'sqlite'
os.environ['JWT_SECRET'] = 'only-for-isolated-tests-very-long-hrm-secret-1234567890abcdef'

from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory() as directory:
    os.environ['DATABASE_PATH'] = str(Path(directory)/'test.db')
    import main
    import mysql_schema_status
    import mysql_backend
    with TestClient(main.app) as client:
        assert client.get('/api/ready').status_code == 200
        assert client.get('/api/admin/database/status').status_code == 401
        # Simulate a raw MySQL connection that supports the required zero-row reads.
        class Raw:
            def __init__(self, fail=False):self.fail=fail;self.seen=[];self.closed=False
            def cursor(self):
                raw=self
                class Cur:
                    def __enter__(self):return self
                    def __exit__(self,*args):return False
                    def execute(self,sql):
                        raw.seen.append(sql)
                        if raw.fail and 'salary_packages' in sql:raise OSError('Simulated missing table')
                return Cur()
            def close(self):self.closed=True
        original_engine, original_raw=main.DB_ENGINE,mysql_backend.raw_mysql_connection
        try:
            main.DB_ENGINE='mysql'
            good=Raw()
            mysql_backend.raw_mysql_connection=lambda:good
            assert client.get('/api/ready').status_code==200
            assert good.closed and len(good.seen)==8
            assert all(query.strip().lower().startswith('select ') for query in good.seen)
            bad=Raw(fail=True)
            mysql_backend.raw_mysql_connection=lambda:bad
            failure=client.get('/api/ready')
            assert failure.status_code==503 and bad.closed
            assert 'missing table' not in failure.text.lower()
        finally:
            main.DB_ENGINE=original_engine
            mysql_backend.raw_mysql_connection=original_raw
print('PASS: readiness checks actual tables, returns 503 on failure, and status requires login')
