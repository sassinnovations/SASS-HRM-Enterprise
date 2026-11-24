"""Administrator-only, read-only feature-to-MySQL structural diagnostics.

Every screen maps to a representative API route and limited, reviewed core tables.
This does NOT test UI operations, write/read persistence, permissions at the owning
endpoint, or completeness of CRUD. Never claim full feature integration from it.
"""
from __future__ import annotations
import csv
from pathlib import Path
from fastapi import Depends, Query
from main import app, require_hr, DB_ENGINE

REGISTRY = Path(__file__).resolve().parent.parent / 'docs' / 'FEATURE_SCREEN_DATABASE_CONTRACTS.csv'


def screen_contracts() -> list[dict]:
    with REGISTRY.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def inspect_feature_screens(status: dict, registered_routes: set[tuple[str, str]]) -> dict:
    """Safe to run in isolated SQLite tests; only MySQL gets real schema assertions."""
    live = status.get('engine') == 'mysql' and status.get('database_reachable') is True
    present = set(status.get('tables') or ()) if live else set()
    failed_access = set(status.get('table_access_failures') or ()) if live else set()
    probed = bool(status.get('table_access_probed')) if live else False
    result = []
    for row in screen_contracts():
        names = [name for name in row['key_tables'].split(';') if name]
        route = row['representative_get_route']
        route_registered = ('GET', route) in registered_routes
        absent = [table for table in names if table not in present] if live else []
        blocked = [table for table in names if table in failed_access] if probed else []
        if not route_registered:
            state = 'missing_api'
        elif not live:
            state = 'not_live_verified'
        elif not names:
            state = 'no_table_mapping'
        elif absent:
            state = 'missing_tables'
        elif blocked:
            state = 'table_access_failed'
        else:
            state = 'structural_match' if probed else 'tables_present_not_probed'
        result.append({
            'feature_key': row['feature_key'],
            'feature_name': row['feature_name'],
            'feature_url': row['feature_url'],
            'domain': row['domain'],
            'settings_page': row['settings_page'],
            'representative_route': route,
            'api_registered': route_registered,
            'key_tables': names,
            'missing_tables': absent,
            'table_access_failures': blocked,
            'state': state,
            'end_to_end_verified': False,
        })
    return {
        'engine': status.get('engine'),
        'live_mysql_inspected': live,
        'table_access_probed': probed,
        'schema_complete': status.get('schema_complete') if live else None,
        'screen_count': len(result),
        'api_routes_registered': sum(r['api_registered'] for r in result),
        'structural_matches': sum(r['state'] == 'structural_match' for r in result),
        'missing_api_count': sum(r['state'] == 'missing_api' for r in result),
        'missing_table_screen_count': sum(r['state'] == 'missing_tables' for r in result),
        'not_live_verified_count': sum(r['state'] == 'not_live_verified' for r in result),
        'end_to_end_verified_count': 0,
        'screens': result,
        'note': ('One reviewed GET endpoint and key tables per screen. Read-only metadata/table-access results'
                 ' do not establish create/edit/delete authorization, full schema coverage for a feature,'
                 ' record persistence, synchronization, UI operation, or production readiness.'),
    }


@app.get('/api/admin/database/screen-integrations')
def screen_database_integrations(probe_tables: bool = Query(False), user=Depends(require_hr)):
    from mysql_schema_status import database_status
    # Uses raw MySQL + INFORMATION_SCHEMA, never the schema installer or HR rows.
    status = database_status(probe_tables=probe_tables, user=user)
    routes = {(method, route.path)
              for route in app.routes for method in getattr(route, 'methods', set())}
    return inspect_feature_screens(status, routes)
