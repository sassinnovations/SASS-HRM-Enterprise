"""Inspect the five workspace screens' MySQL dependencies without reading HR rows."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from mysql_backend import raw_mysql_connection
from schema_audit import database_inventory, get_required_schema

# Shared identity and audit tables each screen relies on for authenticated writes.
SHARED = ('employees', 'audit_events')
WORKSPACE_TABLES = {
    'Team leave & coverage planner': (
        'leave_requests', 'holidays', 'leave_coverage_settings', 'leave_coverage_warning_options',
        'leave_coverage_manual_plans', 'leave_coverage_personal_preferences',
    ),
    'My requests & shortcuts': (
        'leave_requests', 'tickets', 'expenses', 'offboarding', 'work_mode_requests',
        'service_requests', 'attendance_corrections', 'hr_tasks', 'employee_workspace_shortcuts',
        'self_service_preferences', 'self_service_drafts', 'self_service_draft_organization', 'self_service_draft_views',
    ),
    'Notification inbox': (
        'notifications', 'archived_notifications', 'employee_inbox_preferences',
        'employee_inbox_reminders', 'employee_inbox_display_defaults',
    ),
    'My calendar': (
        'leave_requests', 'shift_assignments', 'shifts', 'holidays', 'interviews', 'work_mode_requests',
        'personal_calendar_events', 'employee_calendar_preferences', 'employee_calendar_agenda_preferences', 'employee_calendar_categories',
        'personal_calendar_event_categories',
    ),
    'My Account Security': (
        'account_login_events', 'login_attempts', 'employee_security_preferences',
        'employee_security_checklist', 'employee_security_checklist_settings',
    ),
}


def relevant_schema(required):
    names = set(SHARED).union(*WORKSPACE_TABLES.values())
    missing = names - set(required)
    if missing:
        raise ValueError('Bundled schema missing workspace tables: ' + ', '.join(sorted(missing)))
    return {name: required[name] for name in sorted(names)}


def inspect_live(conn, expected, relevant, *, inventory=None):
    """Can be used with a raw PyMySQL connection. No DDL, DML, or row reads."""
    if inventory is None:
        inventory = database_inventory
    with conn.cursor() as cursor:
        cursor.execute('START TRANSACTION READ ONLY')
    database, tables, columns = inventory(conn)
    if database != expected:
        raise ValueError('Connected MySQL database is not the expected database.')
    problems = {}
    with conn.cursor() as cursor:
        for name, required in relevant.items():
            if name not in tables:
                problems[name] = ['table missing']
                continue
            missing = sorted(column for column in required if (name, column) not in columns)
            if missing:
                problems[name] = ['missing columns: ' + ', '.join(missing)]
                continue
            # Name comes from this module's static list, never from user-supplied SQL.
            try:
                cursor.execute(f'SELECT 1 FROM `{name}` LIMIT 0')
            except Exception:
                problems[name] = ['table cannot be opened with the configured account']
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Inspect the database named in server/.env')
    args = parser.parse_args(argv)
    relevant = relevant_schema(get_required_schema())
    if not args.live:
        print(f'PASS: {len(relevant)} MySQL tables declared for the five workspace pages (packaged schema only).')
        return 0
    load_dotenv(Path(__file__).with_name('.env'))
    expected = os.getenv('MYSQL_DATABASE') or os.getenv('MYSQLDATABASE') or 'sass_hrm'
    try:
        conn = raw_mysql_connection()
        try:
            problems = inspect_live(conn, expected, relevant)
        finally:
            conn.close()
    except ValueError as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    except Exception:
        print('FAIL: Could not inspect the configured MySQL database. Check its connection and permissions.',
              file=sys.stderr)
        return 1
    for page, own in WORKSPACE_TABLES.items():
        issues = [(name, msg) for name in (*SHARED, *own) for msg in problems.get(name, ())]
        print(f'{"FAIL" if issues else "PASS"}: {page}')
        for name, msg in issues:
            print(f'  {name}: {msg}')
    if problems:
        print('Schema or access incomplete. Back up and review the additive upgrade; never reset the volume.')
    else:
        print(f'All {len(relevant)} required tables and columns are visible. No HR records were read or changed.')
    return int(bool(problems))


if __name__ == '__main__':
    sys.exit(main())
