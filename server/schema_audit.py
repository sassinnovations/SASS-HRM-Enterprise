"""SASS HRM MySQL schema audit and explicitly approved, additive repair.

Read-only by default. No passwords, payroll rows or email addresses are printed.
--install requires --confirm APPLY and a verified database backup.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCHEMA = ROOT / 'mysql_schema.sql'
TABLE_RE = re.compile(r'\bCREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?(\w+)`?\s*\(', re.I)
TABLE_EXCLUSIONS = {'migrations'}


def split_top_level(body: str) -> list[str]:
    result, chars, level, quote = [], [], 0, None
    for ch in body:
        if ch in "'\"`":
            if quote == ch:
                quote = None
            elif quote is None:
                quote = ch
        elif quote is None:
            if ch == '(':
                level += 1
            elif ch == ')':
                level -= 1
        if ch == ',' and level == 0 and quote is None:
            result.append(''.join(chars).strip())
            chars = []
        else:
            chars.append(ch)
    if chars:
        result.append(''.join(chars).strip())
    return result


def schema_columns(sql: str) -> dict[str, set[str]]:
    found = {}
    for match in TABLE_RE.finditer(sql):
        level, quote, end = 1, None, match.end()
        while end < len(sql) and level:
            ch = sql[end]
            if ch in "'\"`":
                if quote == ch:
                    quote = None
                elif quote is None:
                    quote = ch
            elif quote is None:
                if ch == '(':
                    level += 1
                elif ch == ')':
                    level -= 1
            end += 1
        if level:
            raise ValueError(f'Unbalanced column definition: {match.group(1)}')
        declarations, cols = split_top_level(sql[match.end():end - 1]), set()
        for declaration in declarations:
            word = declaration.split(None, 1)[0].strip('`"').lower() if declaration else ''
            if word.split('(', 1)[0] not in ('primary', 'foreign', 'unique', 'constraint', 'check', 'index', 'key', 'fulltext'):
                if not re.fullmatch(r'[a-z_][a-z0-9_]*', word):
                    raise ValueError(f'Invalid column token {word!r} in {match.group(1)}')
                cols.add(word)
        name = match.group(1).lower()
        if name in found:
            raise ValueError(f'Duplicate CREATE TABLE declaration: {name}')
        found[name] = cols
    return found


def source_coverage(required: dict[str, set[str]]) -> list[str]:
    errors = []
    for path in sorted(ROOT.glob('*.py')):
        if path.name.endswith('_test.py') or path.name in {'mysql_backend.py', 'schema_audit.py', 'mysql_schema_status.py'}:
            continue
        declarations = schema_columns(path.read_text(encoding='utf-8'))
        for table, cols in declarations.items():
            if table in TABLE_EXCLUSIONS:
                continue
            if table not in required:
                errors.append(f'{path.name} declares missing MySQL table {table}')
            elif (missing := cols - required[table]):
                errors.append(f'{path.name}: {table} missing columns {", ".join(sorted(missing))}')
    return errors


def get_required_schema() -> dict[str, set[str]]:
    sql = SCHEMA.read_text(encoding='utf-8')
    result = schema_columns(sql)
    if not result:
        raise ValueError('No MySQL CREATE TABLE definitions found')
    from mysql_backend import split_ddl
    statements = split_ddl(sql)
    create_count = sum(bool(TABLE_RE.search(s)) for s in statements)
    if create_count != len(result):
        raise ValueError(f'Invalid SQL delimiters: {create_count} statements for {len(result)} tables')
    for statement in statements:
        if TABLE_RE.match(statement) and 'ENGINE=InnoDB' not in statement:
            raise ValueError('All application tables must explicitly use InnoDB')
    return result


def field(row, name: str):
    """Read PyMySQL DictCursor fields independent of information_schema casing.

    MySQL 8 can return TABLE_NAME / COLUMN_NAME where older code assumes table_name.
    Aliases improve compatibility, but this fallback protects older drivers too.
    """
    if name in row:
        return row[name]
    # sqlite3.Row is mapping-like but has keys() rather than items(); this
    # helper is also used by the SQLite-development status endpoint.
    keys = row.keys() if hasattr(row, 'keys') else ()
    matches = [row[key] for key in keys if str(key).casefold() == name.casefold()]
    if len(matches) != 1:
        raise ValueError(f'Database metadata result did not contain expected field {name}')
    return matches[0]


def database_inventory(connection) -> tuple[str, set[str], set[tuple[str, str]]]:
    with connection.cursor() as cursor:
        cursor.execute('SELECT DATABASE() AS database_name')
        database = field(cursor.fetchone(), 'database_name')
        if not database:
            raise ValueError('No MySQL database selected')
        cursor.execute('''SELECT TABLE_NAME AS object_name FROM information_schema.tables
            WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE' ''')
        existing = {str(field(r, 'object_name')).lower() for r in cursor.fetchall()}
        cursor.execute('''SELECT TABLE_NAME AS object_name, COLUMN_NAME AS column_name
            FROM information_schema.columns WHERE table_schema = DATABASE()''')
        columns = {(str(field(r, 'object_name')).lower(), str(field(r, 'column_name')).lower())
                   for r in cursor.fetchall()}
    return str(database), existing, columns


def compare(required, existing, columns):
    absent_tables = sorted(set(required) - existing)
    absent_cols = sorted((table, column) for table, needed in required.items()
                         if table in existing for column in needed if (table, column) not in columns)
    return absent_tables, absent_cols


def live_check(required: dict[str, set[str]]) -> tuple[list[str], list[tuple[str, str]], int]:
    from mysql_backend import raw_mysql_connection
    connection = raw_mysql_connection()
    try:
        _, existing, columns = database_inventory(connection)
        missing_tables, missing_columns = compare(required, existing, columns)
        return missing_tables, missing_columns, len(existing)
    finally:
        connection.close()


def duplicate_work_email_count(connection, has_work_email: bool) -> int:
    # This query returns a count only. No account credentials or emails are retrieved.
    expression = "LOWER(COALESCE(NULLIF(TRIM(work_email), ''), email))" if has_work_email else 'LOWER(email)'
    with connection.cursor() as cursor:
        cursor.execute(f'''SELECT COUNT(*) AS duplicate_groups FROM (
            SELECT {expression} AS normalized_address FROM employees
            GROUP BY normalized_address HAVING COUNT(*) > 1
        ) AS duplicate_emails''')
        return int(field(cursor.fetchone(), 'duplicate_groups'))


def verify_preflight(connection, required, expected_database):
    database, existing, columns = database_inventory(connection)
    if database.casefold() != expected_database.casefold():
        raise ValueError(f'Refusing installation: connected to database {database!r}, not {expected_database!r}')
    if 'employees' not in existing:
        raise ValueError('Refusing repair: employees table missing; use the documented fresh-install process')
    missing_tables, missing_columns = compare(required, existing, columns)
    unsupported_columns = [f'{t}.{c}' for t, c in missing_columns if (t, c) != ('employees', 'work_email')]
    if unsupported_columns:
        raise ValueError('Refusing automatic changes: unreviewed missing columns: ' + ', '.join(unsupported_columns))
    duplicate_groups = duplicate_work_email_count(connection, ('employees', 'work_email') in columns)
    if duplicate_groups:
        raise ValueError(f'Refusing work-email migration: {duplicate_groups} groups of duplicate normalized emails')
    return missing_tables, missing_columns


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Read-only MySQL schema audit or explicitly authorized repair')
    parser.add_argument('--file-only', action='store_true', help='Check DDL declarations without a connection')
    parser.add_argument('--live', action='store_true', help='Read-only MySQL check')
    parser.add_argument('--install', action='store_true', help='Opt-in additive repair after a tested backup')
    parser.add_argument('--confirm', default='', help='Must be APPLY to permit database writes')
    parser.add_argument('--expected-database', default='sass_hrm', help='Database name safeguard for installation')
    args = parser.parse_args(argv)
    if args.file_only and (args.install or args.live):
        parser.error('--file-only cannot be combined with --live or --install')
    if args.install and (not args.live or args.confirm != 'APPLY'):
        parser.error('--install requires --live --confirm APPLY after verifying a backup')
    try:
        required = get_required_schema()
        issues = source_coverage(required)
        print(f'Expected tables in SASS HRM MySQL schema: {len(required)}')
        print(f'Backend CREATE TABLE coverage: {"PASS" if not issues else "FAIL"}')
        for issue in issues:
            print('SOURCE GAP:', issue)
        if issues:
            return 1
        if args.live:
            from mysql_backend import raw_mysql_connection
            raw = raw_mysql_connection()
            try:
                database, existing, columns = database_inventory(raw)
                missing_tables, missing_columns = compare(required, existing, columns)
                print(f'MySQL database: {database}; existing tables: {len(existing)}; expected: {len(required)}')
                if missing_tables:
                    print('MISSING TABLES:', ', '.join(missing_tables))
                for table, column in missing_columns:
                    print('MISSING COLUMN:', f'{table}.{column}')
                if args.install and (missing_tables or missing_columns):
                    verify_preflight(raw, required, args.expected_database)
                    print('Applying approved CREATE TABLE IF NOT EXISTS, missing indexes and work_email migration...')
                    # import explicitly; only this opt-in path makes DDL changes
                    from mysql_backend import install_schema
                    install_schema(raw)
                    print('MySQL DDL completed; no DROP / TRUNCATE / DELETE used.')
                    _, existing, columns = database_inventory(raw)
                    missing_tables, missing_columns = compare(required, existing, columns)
                if missing_tables or missing_columns:
                    print('FAIL: Schema is incomplete. Back up and use INSTALL_FULL_MYSQL_SCHEMA.bat only with approval.')
                    return 2
                print('PASS: all tables and columns exist')
            finally:
                raw.close()
        return 0
    except Exception as exc:
        # Avoid leaking passwords, SQL values, or employee data in MySQL errors.
        if isinstance(exc, ValueError):
            print('ERROR:', str(exc))
        else:
            print('ERROR:', type(exc).__name__, '(check MySQL availability and server logs; do not share passwords)')
        return 3


if __name__ == '__main__':
    sys.exit(main())
