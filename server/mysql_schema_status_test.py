"""Admin-only database status uses the read-only raw MySQL connection."""
import os
os.environ.setdefault('SASS_HRM_TESTING','1')
os.environ.setdefault('DB_ENGINE','sqlite')
os.environ.setdefault('JWT_SECRET','temporary-regression-testing-secret-value-123456789012345678901234567890')
from fastapi import HTTPException
import main
import mysql_backend
import mysql_schema_status as target
from mysql_connection_audit_test import FakeMySQL

old_engine, old_factory = target.DB_ENGINE, mysql_backend.raw_mysql_connection
try:
    target.DB_ENGINE='mysql'
    fake=FakeMySQL(uppercase=True)
    mysql_backend.raw_mysql_connection=lambda:fake
    result=target.database_status(probe_tables=True,user={'id':1,'role':'admin'})
    assert result['schema_complete'] and result['table_access_passed']==270
    assert result['schema_only_table_count']==131
    assert fake.closed
    # Wrong schema fails closed; no migrations are attempted by this endpoint.
    mysql_backend.raw_mysql_connection=lambda:FakeMySQL(database='not_sass_hrm')
    try:
        target.database_status(probe_tables=False,user={'id':1,'role':'admin'})
        raise AssertionError('Must reject wrong database')
    except HTTPException as e:
        assert e.status_code==503
    # SQLite development fallback remains usable for isolated tests.
    target.DB_ENGINE='sqlite'
    from contextlib import contextmanager
    class FakeSqlite:
        def execute(self,sql):
            class Rows:
                def fetchall(self):return [{'name':'employees'},{'name':'attendance'}]
            return Rows()
    @contextmanager
    def fake_db(): yield FakeSqlite()
    old_db=target.db
    try:
        target.db=fake_db
        status=target.database_status(user={'id':1,'role':'admin'})
        assert status['engine']=='sqlite' and status['schema_complete'] is None
        assert status['table_count']==2
    finally:target.db=old_db
finally:
    target.DB_ENGINE=old_engine
    mysql_backend.raw_mysql_connection=old_factory
print('PASS: database status is read-only and rejects incorrect live database')
