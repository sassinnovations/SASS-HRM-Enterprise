"""Verify the workspace DDL with MySQL 8.4 itself, without a server connection.

Set MYSQLD to a local MySQL 8.4 server binary (and, for a relocated Linux
package, optionally MYSQLD_BASEDIR, MYSQLD_MESSAGES_DIR and MYSQLD_PLUGIN_DIR).
Only a new OS temporary data directory is created; no app .env file is read.

    MYSQLD=/path/to/mysqld python tests/workspace_mysql_schema_smoke.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'server'))
from mysql_backend import split_ddl


def module_assert(expression):
    return f'INSERT INTO qa_assertions(ok) SELECT IF(({expression}),1,0)'


def install_smoke_sql():
    d = ROOT/'database'
    current = (ROOT/'server/mysql_schema.sql').read_text(encoding='utf-8')
    migration = (d/'28_WORKSPACE_PERSISTENT_SETTINGS_ADD_ONLY.sql').read_text(encoding='utf-8')
    installer = (d/'02_FRESH_INSTALL_ALL_IN_ONE.sql').read_text(encoding='utf-8')
    view_defaults = (d/'29_WORKSPACE_VIEW_DEFAULTS_ADD_ONLY.sql').read_text(encoding='utf-8')
    previous, separator, tail = current.partition(view_defaults)
    assert separator and not tail.strip()
    old, separator, tail = previous.partition(migration)
    assert separator and not tail.strip()
    statements = split_ddl(installer)
    statements += [module_assert("(SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='sass_hrm' AND TABLE_TYPE='BASE TABLE' AND TABLE_NAME<>'qa_assertions')=288")]
    statements.insert(-1, 'CREATE TABLE qa_assertions (ok INT NOT NULL CHECK(ok=1))')
    statements += [
        'CREATE DATABASE sass_workspace_upgrade_qa',
        'USE sass_workspace_upgrade_qa',
    ] + split_ddl(old) + [
        'CREATE TABLE qa_assertions (ok INT NOT NULL CHECK(ok=1))',
        module_assert("(SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND TABLE_TYPE='BASE TABLE')=281"),
        """INSERT INTO employees(id,code,name,email,work_email,role,designation,department,location,work_mode,join_date,password_hash,account_active,session_version)
           VALUES(1,'QA','Synthetic QA','qa@example.invalid','qa@example.invalid','employee','QA','QA','QA','Hybrid','2025-01-01','SYNTHETIC_NO_PASSWORD',1,0)""",
        """INSERT INTO leave_requests(id,employee_id,start_date,end_date,leave_type,reason,days,status,created_at)
           VALUES(1,1,'2026-11-25','2026-11-25','Personal','Synthetic reason',1,'Approved','2026-11-25T10:00:00')""",
        """INSERT INTO self_service_drafts(id,employee_id,kind,title,notes,created_at,updated_at)
           VALUES(1,1,'leave','Old private draft','Old draft note','2026-11-25T10:00:00','2026-11-25T10:00:00')""",
        """INSERT INTO notifications(id,employee_id,title,body,is_read,created_at)
           VALUES(1,1,'Existing HR notice','Synthetic notice',0,'2026-11-25T10:00:00')""",
        "INSERT INTO employee_inbox_preferences(employee_id,unread_only,compact_view) VALUES(1,1,1)",
        """INSERT INTO personal_calendar_events(id,employee_id,day,start_time,title,notes,created_at,updated_at)
            VALUES(1,1,'2026-11-25','11:00','Old private event','Old event note','2026-11-25T10:00:00','2026-11-25T10:00:00')""",
        "INSERT INTO account_login_events(id,employee_id,created_at) VALUES(1,1,'2026-11-25T10:00:00')",
        "INSERT INTO employee_security_checklist(id,employee_id,title,completed,updated_at) VALUES(1,1,'Old security item',0,'2026-11-25T10:00:00')",
    ] + split_ddl(migration)*2 + [
        module_assert("(SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND TABLE_TYPE='BASE TABLE')=287"),
        module_assert("(SELECT count(*) FROM leave_requests WHERE id=1 AND status='Approved')=1"),
        module_assert("(SELECT count(*) FROM notifications WHERE id=1 AND title='Existing HR notice')=1"),
        "START TRANSACTION",
        "SELECT n.id,a.notification_id AS archive_id FROM notifications n LEFT JOIN archived_notifications a ON a.notification_id=n.id WHERE n.employee_id=1 AND n.id IN (1) ORDER BY n.id FOR UPDATE OF n",
        "ROLLBACK",
        module_assert("(SELECT count(*) FROM employee_inbox_preferences WHERE employee_id=1 AND unread_only=1 AND compact_view=1)=1"),
        module_assert("(SELECT count(*) FROM account_login_events WHERE id=1 AND employee_id=1)=1"),
        module_assert("(SELECT count(*) FROM employee_security_checklist WHERE id=1 AND title='Old security item')=1"),
        module_assert("(SELECT count(*) FROM self_service_drafts WHERE id=1 AND title='Old private draft')=1"),
        module_assert("(SELECT count(*) FROM personal_calendar_events WHERE id=1 AND title='Old private event')=1"),
        "INSERT INTO leave_coverage_personal_preferences(employee_id,show_holidays,plan_status,my_assignments_only) VALUES(1,0,'Confirmed',1)",
        "INSERT INTO self_service_draft_organization(draft_id,stage,pinned,updated_at) VALUES(1,'ready',1,'2026-11-25T10:00:00')",
        "INSERT INTO employee_inbox_display_defaults(employee_id,notification_order,notification_page_size,reminder_view) VALUES(1,'oldest',10,'due')",
        """INSERT INTO employee_inbox_display_defaults(employee_id,notification_order,notification_page_size,reminder_view) VALUES(1,'newest',50,'upcoming')
           ON DUPLICATE KEY UPDATE notification_order=VALUES(notification_order),notification_page_size=VALUES(notification_page_size),reminder_view=VALUES(reminder_view)""",
        "INSERT INTO employee_calendar_categories(id,employee_id,name,name_key,color) VALUES(1,1,'QA Work','qa work','violet')",
        "INSERT INTO personal_calendar_event_categories(event_id,category_id) VALUES(1,1)",
        "INSERT INTO employee_security_checklist_settings(employee_id,status_filter,sort_order,default_due) VALUES(1,'due','newest','week')",
        module_assert("(SELECT COUNT(*) FROM leave_coverage_personal_preferences WHERE plan_status='Confirmed')=1"),
        module_assert("(SELECT COUNT(*) FROM self_service_drafts d JOIN self_service_draft_organization o ON o.draft_id=d.id WHERE d.id=1 AND o.pinned=1)=1"),
        module_assert("(SELECT COUNT(*) FROM employee_inbox_display_defaults WHERE notification_page_size=50 AND reminder_view='upcoming')=1"),
        module_assert("(SELECT COUNT(*) FROM personal_calendar_event_categories WHERE event_id=1 AND category_id=1)=1"),
        module_assert("(SELECT COUNT(*) FROM employee_security_checklist_settings WHERE default_due='week')=1"),
    ] + split_ddl(view_defaults)*2 + [
        module_assert("(SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND TABLE_TYPE='BASE TABLE')=289"),
        module_assert("(SELECT COUNT(*) FROM employee_calendar_categories WHERE id=1 AND name='QA Work')=1"),
        module_assert("(SELECT COUNT(*) FROM self_service_draft_organization WHERE draft_id=1 AND stage='ready')=1"),
        "INSERT INTO self_service_draft_views(employee_id,module_filter,draft_view,sort_order) VALUES(1,'leave','pinned','title')",
        "INSERT INTO employee_calendar_agenda_preferences(employee_id,preferred_view,agenda_days) VALUES(1,'agenda',30)",
        module_assert("(SELECT COUNT(*) FROM self_service_draft_views WHERE employee_id=1 AND draft_view='pinned')=1"),
        module_assert("(SELECT COUNT(*) FROM employee_calendar_agenda_preferences WHERE employee_id=1 AND preferred_view='agenda' AND agenda_days=30)=1"),
        "DELETE FROM employee_calendar_categories WHERE id=1",
        module_assert("(SELECT COUNT(*) FROM personal_calendar_event_categories)=0"),
        module_assert("(SELECT COUNT(*) FROM personal_calendar_events WHERE id=1)=1"),
        "DELETE FROM self_service_drafts WHERE id=1",
        module_assert("(SELECT COUNT(*) FROM self_service_draft_organization)=0"),
    ]
    # MySQL's bootstrap file expects one complete statement per line.
    return '\n'.join(' '.join(stmt.splitlines())+';' for stmt in statements)+'\n'


def main():
    binary = os.environ.get('MYSQLD', 'mysqld')
    result = subprocess.run([binary,'--no-defaults','--version'],capture_output=True,text=True,check=True)
    if 'Ver 8.4.' not in result.stdout:
        raise SystemExit('This smoke test requires a MySQL 8.4 executable.')
    with tempfile.TemporaryDirectory(prefix='sass-workspace-mysql-') as tmp:
        tmp = Path(tmp)
        sql = tmp/'init.sql'
        sql.write_text(install_smoke_sql(),encoding='utf-8')
        log = tmp/'mysql.log'
        args = [binary,'--no-defaults','--initialize-insecure','--mysqlx=0','--secure-file-priv=NULL',
                '--innodb-buffer-pool-size=64M',f'--datadir={tmp/"data"}',f'--init-file={sql}',f'--log-error={log}']
        for key,opt in (('MYSQLD_BASEDIR','basedir'),('MYSQLD_MESSAGES_DIR','lc-messages-dir'),('MYSQLD_PLUGIN_DIR','plugin-dir')):
            if os.environ.get(key):
                args.append(f'--{opt}={os.environ[key]}')
        result = subprocess.run(args, check=False)
        if result.returncode:
            if log.exists():
                print(log.read_text(encoding='utf-8'),file=sys.stderr)
            raise SystemExit(result.returncode)
        for name in ('sass_hrm','sass_workspace_upgrade_qa'):
            if not (tmp/'data'/name/'qa_assertions.ibd').exists():
                raise SystemExit('MySQL did not execute the expected smoke assertions.')
    print('PASS real MySQL 8.4 DDL: 288-table fresh install, both additive upgrades reapplied twice, old synthetic rows, new settings and cascades.')


if __name__=='__main__':
    main()
