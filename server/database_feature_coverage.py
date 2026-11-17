"""Inventory of declared MySQL tables and detectable backend SQL references.

Static SQL references do not prove endpoint functionality or correctness.
A database table without a static reference may be accessed dynamically; manual
review is still required before declaring an end-to-end feature complete.
"""
from __future__ import annotations

import argparse
import ast
import csv
import io
import re
from pathlib import Path

from schema_audit import get_required_schema
from mysql_connection_audit import FOUNDATION_ONLY

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent/'database'/'FEATURE_TABLE_COVERAGE.csv'
SQL_REF = re.compile(r'\b(?:FROM|JOIN|INTO|UPDATE|TABLE|REFERENCES)\s+[`\"]?([a-z_][a-z0-9_]*)', re.I)
EXCLUDE = {'mysql_connection_audit.py', 'mysql_schema_status.py',
           'mysql_feature_schema_integrity.py', 'schema_audit.py', 'database_feature_coverage.py',
           'check_all_mysql_connections.py', 'deployment_probe.py'}


def detect_references() -> dict[str, set[str]]:
    required = get_required_schema()
    ref: dict[str, set[str]] = {table:set() for table in required}
    for path in ROOT.glob('*.py'):
        if path.name.endswith('_test.py') or path.name in EXCLUDE:
            continue
        syntax = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        for node in ast.walk(syntax):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                for candidate in SQL_REF.findall(node.value):
                    if candidate.lower() in required:
                        ref[candidate.lower()].add(path.name)
    return ref


def render() -> tuple[str,dict]:
    ref = detect_references()
    buffer = io.StringIO(newline='')
    writer = csv.writer(buffer, lineterminator='\n')
    writer.writerow(['Table','Schema category','Direct backend SQL reference','Referencing modules','Workflow certification'])
    for table,modules in sorted(ref.items()):
        category = 'Database foundation only' if table in FOUNDATION_ONLY else 'Existing HRM schema'
        writer.writerow([table,category,'Yes' if modules else 'No',', '.join(sorted(modules)), 'Not established by schema audit'])
    return buffer.getvalue(),{'tables':len(ref),'direct_references':sum(bool(v) for v in ref.values()),
                              'foundation_only':len(FOUNDATION_ONLY),
                              'uncited_existing':len({t for t,v in ref.items() if not v and t not in FOUNDATION_ONLY})}


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true',help='Do not overwrite: verify current CSV')
    args=parser.parse_args(argv)
    text,counts=render()
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding='utf-8') != text:
            raise SystemExit('FAIL: feature-to-database CSV inventory is out of sync')
    else:
        OUT.write_text(text,encoding='utf-8')
    if counts['uncited_existing']:
        raise SystemExit(f'REVIEW: {counts["uncited_existing"]} existing tables lack detectable static SQL references')
    print('PASS:', counts, '(static code references only; not a live workflow test)')


if __name__ == '__main__':main()
