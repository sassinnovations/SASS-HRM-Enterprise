"""Offline read-only MySQL connection contract regression with a fake cursor."""
import os
os.environ.setdefault('SASS_HRM_TESTING', '1')
os.environ.setdefault('DB_ENGINE', 'sqlite')
os.environ.setdefault('JWT_SECRET', 'test-database-audit-secret-at-least-forty-characters-0000')

from schema_audit import get_required_schema
from mysql_feature_schema_integrity import SCHEMA, sql_objects
from mysql_connection_audit import inspect_mysql_connection, FOUNDATION_ONLY, CORE_MODULES

REQUIRED = get_required_schema()
_, INDEXES, FKS, _ = sql_objects(SCHEMA.read_text(encoding='utf-8'))
assert len(REQUIRED) == 270 and len(FOUNDATION_ONLY) == 131
assert all(all(n in REQUIRED for n in names) for names in CORE_MODULES.values())


class FakeMySQL:
    def __init__(self, *, incomplete=None, database='sass_hrm', deny=None, uppercase=False):
        self.incomplete, self.database, self.deny, self.uppercase = incomplete, database, deny, uppercase
        self.sql = []
        self.closed = False

    def cursor(self):
        parent = self
        class Cursor:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def execute(self, sql):
                normalized = sql.strip().lower()
                parent.sql.append(sql)
                if not normalized.startswith('select'):
                    raise AssertionError('Database verification must not write')
                def obj(**kwargs):
                    return {(k.upper() if parent.uppercase else k): v for k,v in kwargs.items()}
                if normalized.startswith('select database()'):
                    self.results = [obj(database_name=parent.database)]
                elif 'information_schema.tables' in normalized:
                    self.results = [obj(object_name=t) for t in REQUIRED if parent.incomplete != ('table', t)]
                elif 'information_schema.columns' in normalized:
                    self.results = [obj(object_name=t, column_name=c) for t,columns in REQUIRED.items()
                                    for c in columns if parent.incomplete != ('column',t,c)]
                elif 'information_schema.statistics' in normalized:
                    self.results = [obj(object_name=t,index_name=i) for t,i in INDEXES
                                    if parent.incomplete != ('index',t,i)]
                elif 'information_schema.key_column_usage' in normalized:
                    self.results = [obj(object_name=t,column_name=c,referenced_table=p,referenced_column=r)
                                    for t,c,p,r in FKS if parent.incomplete != ('fk',t,c,p,r)]
                elif normalized.startswith('select max(version)'):
                    self.results = [obj(schema_version=30)]
                elif normalized.startswith('select 1 from `') and normalized.endswith(' limit 0'):
                    table=normalized.split('`')[1]
                    if table == parent.deny:
                        raise PermissionError('fake permission denied')
                    self.results = []
                else:
                    raise AssertionError(sql)
            def fetchall(self): return self.results
            def fetchone(self): return self.results[0] if self.results else None
        return Cursor()
    def close(self): self.closed=True


for upper in (True, False):
    fake=FakeMySQL(uppercase=upper)
    result=inspect_mysql_connection(fake,'sass_hrm',probe_tables=True)
    assert result['schema_complete'] and result['table_count']==270
    assert result['table_access_passed']==270
    assert result['missing_indexes']==result['missing_foreign_keys']==[]
    assert result['schema_only_table_count']==131 and result['pre_expansion_table_count']==139
    assert all(result['modules'].values())
    assert len([x for x in fake.sql if x.lower().startswith('select 1 from `')]) == 270
    assert not any('password_hash' in x or 'SELECT *' in x.upper() for x in fake.sql)

for bad,field in [(('table','candidate_profiles'),'missing_tables'),
                  (('column','employees','id'),'missing_columns'),
                  (('index',*next(iter(INDEXES))),'missing_indexes'),
                  (('fk',*next(iter(FKS))),'missing_foreign_keys')]:
    result=inspect_mysql_connection(FakeMySQL(incomplete=bad), 'sass_hrm')
    assert not result['schema_complete'] and result[field]

result=inspect_mysql_connection(FakeMySQL(deny='salary_packages'),'sass_hrm',True)
assert result['table_access_passed']==269
assert result['table_access_failures']==['salary_packages'] and not result['schema_complete']
assert inspect_mysql_connection(FakeMySQL(),'sass_hrm')['table_access_passed'] is None
try:
    inspect_mysql_connection(FakeMySQL(database='unrelated'),'sass_hrm')
    raise AssertionError('Must reject wrong database')
except ValueError:
    pass
print('PASS: 270-table read-only connection audit, FK/index drift, 131 foundations and table privileges')
