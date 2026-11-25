"""Offline guard for full-module schema installers and read-only live metadata audit."""
from __future__ import annotations

from mysql_feature_schema_integrity import check_file_package, check_live, LEGACY_TABLES, sql_objects, SCHEMA
from schema_audit import missing_standalone_indexes
from mysql_backend import split_ddl
import re
import mysql_backend

expected, indexes, relations = check_file_package()
assert len(expected) == 272 and sum(map(len, expected.values())) == 2242
schema_tables, schema_indexes, schema_relations, order = sql_objects(SCHEMA.read_text())
assert set(schema_tables) == set(expected)
assert len(order) == len(expected)
assert indexes == schema_indexes and relations == schema_relations
assert len(indexes) >= 50 and len(relations) >= 100
assert LEGACY_TABLES <= set(expected)

class FakeConnection:
    def __init__(self, incomplete=None, name='sass_hrm'):
        self.incomplete = incomplete
        self.name = name
        self.statements = []
    def cursor(self):
        parent = self
        class Cursor:
            def __enter__(self):return self
            def __exit__(self, *_):return False
            def execute(self, statement):
                if not statement.lstrip().lower().startswith('select'):
                    raise AssertionError('Integrity verification must never write to the database')
                parent.statements.append(statement)
                if 'SELECT DATABASE()' in statement:
                    self.data = [{'DATABASE_NAME': parent.name}]
                elif 'information_schema.tables' in statement:
                    self.data = [{'OBJECT_NAME': table} for table in expected]
                elif 'information_schema.columns' in statement:
                    self.data = [{'OBJECT_NAME': table, 'COLUMN_NAME': col}
                                 for table, columns in expected.items() for col in columns]
                elif 'information_schema.statistics' in statement:
                    self.data = [{'OBJECT_NAME': table, 'INDEX_NAME': index}
                                 for table, index in indexes
                                 if parent.incomplete != ('index', table, index)]
                elif 'information_schema.key_column_usage' in statement:
                    self.data = [{'OBJECT_NAME': table, 'COLUMN_NAME': col,
                                  'REFERENCED_TABLE': ref, 'REFERENCED_COLUMN': refcol}
                                 for table, col, ref, refcol in relations
                                 if parent.incomplete != ('foreign_key', table, col, ref, refcol)]
                else:
                    raise AssertionError('Unexpected query: ' + statement)
            def fetchone(self):return self.data[0]
            def fetchall(self):return self.data
        return Cursor()
    def close(self):pass

old=mysql_backend.raw_mysql_connection
try:
    fake = FakeConnection()
    mysql_backend.raw_mysql_connection=lambda:fake
    assert check_live('sass_hrm', expected, indexes, relations) == 0
    assert len(fake.statements) == 5
    assert missing_standalone_indexes(fake) == []
    standalone = [re.match(r'^CREATE\s+(?:UNIQUE\s+)?INDEX\s+(\w+)\s+ON\s+(\w+)', statement, re.I).groups()
                  for statement in split_ddl(SCHEMA.read_text())
                  if re.match(r'^CREATE\s+(?:UNIQUE\s+)?INDEX\s+', statement, re.I)]
    first_index, first_table = standalone[0]
    missing = FakeConnection(('index', first_table.lower(), first_index.lower()))
    assert missing_standalone_indexes(missing) == [(first_table.lower(), first_index.lower())]
    table, index = next(iter(indexes))
    mysql_backend.raw_mysql_connection=lambda:FakeConnection(('index', table, index))
    assert check_live('sass_hrm', expected, indexes, relations) == 2
    rel = next(iter(relations))
    mysql_backend.raw_mysql_connection=lambda:FakeConnection(('foreign_key', *rel))
    assert check_live('sass_hrm', expected, indexes, relations) == 2
    mysql_backend.raw_mysql_connection=lambda:FakeConnection(name='wrong_schema')
    try:
        check_live('sass_hrm', expected, indexes, relations)
        raise AssertionError('Must reject incorrect database name')
    except ValueError as exc:
        assert 'refusing to audit wrong database' in str(exc)
finally:
    mysql_backend.raw_mysql_connection=old
print('PASS: full schema file parity, 272 tables, safe read-only metadata and missing-index/FK detection')
