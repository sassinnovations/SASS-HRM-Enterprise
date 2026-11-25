"""Additive HRIS quality import schema parity and non-destructive migration checks."""
from pathlib import Path
import re
from mysql_backend import split_ddl
from mysql_feature_schema_integrity import check_file_package,sql_objects,QUALITY_IMPORT_ADD_ONLY,SCHEMA

required,indexes,relations=check_file_package()
assert len(required)==272 and sum(map(len,required.values()))==2242
assert len(indexes)==331 and len(relations)==505
sql=QUALITY_IMPORT_ADD_ONLY.read_text()
tables,add_indexes,add_relations,order=sql_objects(sql)
assert order==['hr_data_quality_import_settings','hr_data_quality_import_history']
assert len(split_ddl(sql))==3 and len(add_indexes)==1 and len(add_relations)==2
assert add_indexes<=indexes and add_relations<=relations
assert all(not re.match(r'^(INSERT|UPDATE|DELETE|ALTER|DROP|TRUNCATE|REPLACE)\b',s,re.I) for s in split_ddl(sql))
assert 'filename' in required['hr_data_quality_import_history'] and 'mapping_json' in required['hr_data_quality_import_settings']
print('PASS: HR data import adds exactly two safe MySQL tables, one index, two employee FK constraints; no existing data writes')
