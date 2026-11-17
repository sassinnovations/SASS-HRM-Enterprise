"""Safe live database connectivity check. 0=complete; 2=connection/schema error.

Requires the normal app MySQL environment. Does not read personal data, mutate
records or install the schema. Intended for a running *existing* deployment.
"""
import argparse
import os
import sys
from mysql_connection_audit import inspect_mysql_connection
from mysql_backend import raw_mysql_connection


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected-database', default=os.getenv('MYSQL_DATABASE', 'sass_hrm'))
    parser.add_argument('--probe-tables', action='store_true', help='Execute zero-row SELECT on all tables')
    args = parser.parse_args(argv)
    connection = None
    try:
        connection = raw_mysql_connection()
        result = inspect_mysql_connection(connection, args.expected_database, args.probe_tables)
    except Exception as exc:
        print(f'FAIL: MySQL verification unavailable ({type(exc).__name__}). Check credentials, schema and Docker.')
        return 2
    finally:
        if connection is not None:
            connection.close()
    print(f"MySQL connected. Tables: {result['table_count']}/{result['expected_table_count']}; "
          f"schema complete: {result['schema_complete']}")
    if args.probe_tables:
        print(f"Readable table definitions: {result['table_access_passed']}/{result['expected_table_count']}")
    print(f"Schema-only foundations (workflow integration not implemented): {result['schema_only_table_count']}")
    for key in ('missing_tables','missing_columns','missing_indexes','missing_foreign_keys','table_access_failures'):
        if result[key]:
            print(f"FAIL: {key} ({len(result[key])}): {', '.join(result[key][:20])}")
    if not result['schema_complete']:
        print('Do not reset volumes. Back up, review and apply appropriate additive migrations.')
        return 2
    print('PASS: database metadata and requested table access probes; business workflows need separate tests.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
