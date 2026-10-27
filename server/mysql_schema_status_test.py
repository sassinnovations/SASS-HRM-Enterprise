"""Database-status endpoint must accept MySQL 8/driver metadata casing."""
import os
os.environ.setdefault('SASS_HRM_TESTING','1')
os.environ.setdefault('DB_ENGINE','sqlite')
os.environ.setdefault('JWT_SECRET','temporary-regression-testing-secret-value-123456789012345678901234567890')
from contextlib import contextmanager
import mysql_schema_status as target
from schema_audit import get_required_schema

required=get_required_schema()
assert len(required)==105

class FakeResult:
    def __init__(self, data): self.data=data
    def fetchall(self): return self.data
    def fetchone(self): return self.data[0] if self.data else None

class FakeConnection:
    def __init__(self, uppercase, incomplete):
        self.uppercase,self.incomplete=uppercase,incomplete
    def execute(self, statement):
        keys=lambda name:name.upper() if self.uppercase else name.lower()
        if 'information_schema.tables' in statement:
            names=set(required)
            if self.incomplete: names.remove('profile_photos')
            return FakeResult([{keys('object_name'): t.upper() if self.uppercase else t} for t in names])
        if 'information_schema.columns' in statement:
            return FakeResult([{keys('object_name'):t,keys('column_name'):col}
                               for t,columns in required.items() if not (self.incomplete and t=='profile_photos')
                               for col in columns if not (self.incomplete and (t,col)==('employees','work_email'))])
        if 'MAX(version)' in statement: return FakeResult([{keys('version'):23}])
        raise AssertionError(statement)

@contextmanager
def fake_db(upper=False, incomplete=False):
    yield FakeConnection(upper,incomplete)

original_db, original_engine=target.db,target.DB_ENGINE
try:
    target.DB_ENGINE='mysql'
    for upper in (False,True):
        for incomplete in (False,True):
            target.db=lambda:fake_db(upper,incomplete)
            status=target.database_status(user={'id':1,'role':'admin'})
            assert status['expected_table_count']==105
            assert status['schema_complete'] is (not incomplete)
            assert ('profile_photos' in status['missing_tables']) is incomplete
            assert ('employees.work_email' in status['missing_columns']) is incomplete
            assert status['modules']['employees'] and status['schema_version']==23
            assert status['table_count']==105-int(incomplete)
finally:
    target.db,target.DB_ENGINE=original_db,original_engine
print('PASS: database status with mixed metadata casing and incomplete schema')
