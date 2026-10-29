"""MySQL 8.4 adapter for SASS HRM's existing parameterized API queries.

The v0.9 API originally targeted SQLite. This adapter intentionally preserves the
small sqlite3 connection/cursor interface in that API, while using InnoDB MySQL.
It is a development bridge, not a production ORM/migration replacement.
"""
from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

SCHEMA_FILE = Path(__file__).with_name('mysql_schema.sql')
_schema_initialized = False
_lock = Lock()


def raw_mysql_connection():
    try:
        import pymysql
    except ImportError as e:
        raise RuntimeError('MySQL driver missing. Run: pip install -r requirements.txt') from e
    # MYSQL_* is the app's own config. MYSQLHOST-style names are Railway's MySQL plugin references.
    host = os.getenv('MYSQL_HOST') or os.getenv('MYSQLHOST') or '127.0.0.1'
    port = os.getenv('MYSQL_PORT') or os.getenv('MYSQLPORT') or '3306'
    user = os.getenv('MYSQL_USER') or os.getenv('MYSQLUSER') or 'sass_hrm_app'
    password = os.getenv('MYSQL_PASSWORD', os.getenv('MYSQLPASSWORD', ''))
    database = os.getenv('MYSQL_DATABASE') or os.getenv('MYSQLDATABASE') or 'sass_hrm'
    return pymysql.connect(
        host=host,
        port=int(port),
        user=user,
        password=password,
        database=database,
        charset='utf8mb4',
        connect_timeout=8,
        read_timeout=30,
        write_timeout=30,
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
    )


def split_ddl(text: str):
    """Our versioned schema has simple DDL separated by semicolons, no stored routines."""
    clean='\n'.join(line for line in text.splitlines() if not line.lstrip().startswith('--'))
    return [statement.strip() for statement in clean.split(';') if statement.strip()]


def install_schema(connection):
    """Apply v1 schema once. Existing tables are never dropped or overwritten."""
    global _schema_initialized
    if _schema_initialized:
        return
    with _lock:
        if _schema_initialized:
            return
        with connection.cursor() as cur:
            cur.execute("SELECT GET_LOCK('sass_hrm_schema_v1', 30) AS acquired")
            if cur.fetchone()['acquired'] != 1:
                raise RuntimeError('Could not acquire MySQL schema migration lock')
            try:
                statements=split_ddl(SCHEMA_FILE.read_text(encoding='utf-8'))
                for statement in statements:
                    index=re.match(r'CREATE (?:UNIQUE )?INDEX\s+(\w+)\s+ON\s+(\w+)\s*\(',statement,re.I)
                    if index:
                        cur.execute('SELECT COUNT(*) AS n FROM information_schema.statistics '
                                    'WHERE table_schema=DATABASE() AND table_name=%s AND index_name=%s',
                                    (index.group(2),index.group(1)))
                        if cur.fetchone()['n']:
                            continue
                    cur.execute(statement)
                # v4.3 additive migration: existing employee accounts retain IDs, password hashes and sessions.
                cur.execute('''SELECT COUNT(*) AS n FROM information_schema.columns
                    WHERE table_schema=DATABASE() AND table_name='employees' AND column_name='work_email' ''')
                if cur.fetchone()['n'] == 0:
                    cur.execute('ALTER TABLE employees ADD COLUMN work_email VARCHAR(191) NULL')
                cur.execute("UPDATE employees SET work_email=LOWER(email) WHERE work_email IS NULL OR TRIM(work_email)=''")
                cur.execute('''SELECT COUNT(*) AS n FROM information_schema.statistics
                    WHERE table_schema=DATABASE() AND table_name='employees' AND index_name='ux_employees_work_email' ''')
                if cur.fetchone()['n'] == 0:
                    cur.execute('CREATE UNIQUE INDEX ux_employees_work_email ON employees(work_email)')
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (22,'v4.3 stored work email, account profile editor and developer tier',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (23,'v4.4 sanitized user-uploaded professional photos',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (24,'v4.5 private successful sign-in activity and security review',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (1,'Initial full HRMS schema',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (2,'Additive Talent Operations v1.7 schema',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (3,'Additive Compensation Operations v1.8 review records',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (4,'Additive Culture Operations v1.9 review and recognition history',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (5,'Additive Employee Services v2.0 custody, reviews and preferences',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (6,'Additive Account Administration v2.5 password reset table',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (7,'Additive Organization Settings and Offices v2.6',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (8,'Private personal calendar events v2.7',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (9,'Professional profiles and approved name corrections v2.9',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (10,'v3.0 notification inbox and workflow settings',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (11,'v3.1 private workspace shortcuts',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (12,'v3.3 reusable account credentials and restricted access tiers',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (13,'v3.2 compensation workflow configuration',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (14,'v3.4 talent and employee service administration guidance',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (15,'v3.5 auditable manual workflow reminder dispatches',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (16,'v3.7 role-scoped global search personal saved queries',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (17,'v3.8 HR data quality and review queue',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (18,'v3.9 performance cycles, self assessment and check-ins',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (19,'v4.0 individual development plans and requested manager feedback',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (20,'v4.1 role-scoped employee performance follow-ups',datetime.now(timezone.utc).isoformat()))
                cur.execute('INSERT IGNORE INTO schema_migrations(version,description,applied_at) VALUES(%s,%s,%s)',
                            (21,'v4.2 private performance evidence and append-only goal check-ins',datetime.now(timezone.utc).isoformat()))
                connection.commit()
                _schema_initialized=True
            finally:
                cur.execute("SELECT RELEASE_LOCK('sass_hrm_schema_v1')")


def rewrite_sql(sql: str) -> str:
    """Translate limited SQLite placeholders and upsert forms used by this API."""
    sql=re.sub(r'\bINSERT\s+OR\s+IGNORE\b','INSERT IGNORE',sql,flags=re.I)
    sql=re.sub(r'\bON\s+CONFLICT\s*\([^)]*\)\s+DO\s+UPDATE\s+SET\s+',
               'ON DUPLICATE KEY UPDATE ',sql,flags=re.I|re.S)
    sql=re.sub(r'\bexcluded\.(\w+)\b',r'VALUES(\1)',sql,flags=re.I)
    # All API SQL uses bind parameters rather than embedding question marks in literals.
    return sql.replace('?', '%s')


class MySQLRow(dict):
    """A dict row that also supports sqlite3.Row style numeric indexing."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class BufferedResult:
    def __init__(self, records=(), lastrowid=None, rowcount=0):
        self._records=[MySQLRow(record) for record in records]
        self._at=0
        self.lastrowid=lastrowid
        self.rowcount=rowcount
    def fetchone(self):
        if self._at>=len(self._records):return None
        row=self._records[self._at]
        self._at+=1
        return row
    def fetchall(self):
        out=self._records[self._at:]
        self._at=len(self._records)
        return out
    def __iter__(self):
        while True:
            row=self.fetchone()
            if row is None:break
            yield row


class MySQLCompatConnection:
    def __init__(self, raw):self.raw=raw
    def execute(self, sql: str, params=()):
        pragma=re.match(r'^\s*PRAGMA\s+table_info\((\w+)\)\s*$', sql, re.I)
        if pragma:
            # Emulate the one SQLite metadata query used for incremental columns.
            with self.raw.cursor() as cur:
                cur.execute('SELECT column_name AS name FROM information_schema.columns '
                            'WHERE table_schema=DATABASE() AND table_name=%s ORDER BY ordinal_position',
                            (pragma.group(1),))
                records=cur.fetchall()
                return BufferedResult(records,rowcount=len(records))
        with self.raw.cursor() as cur:
            try:
                cur.execute(rewrite_sql(sql),tuple(params))
            except Exception as e:
                try:
                    import pymysql
                    if isinstance(e,pymysql.err.IntegrityError):
                        # API handlers already catch sqlite3.IntegrityError for 409s.
                        raise sqlite3.IntegrityError(str(e)) from e
                except ImportError:pass
                raise
            return BufferedResult(cur.fetchall() if cur.description else (),cur.lastrowid,cur.rowcount)
    def executescript(self, sql):
        # MySQL DDL is installed by install_schema() from mysql_schema.sql.
        # Legacy API startup hooks only register tables. No sample rows are inserted.
        if not _schema_initialized:
            raise RuntimeError('MySQL schema must initialize before legacy startup hooks')
    def commit(self):self.raw.commit()
    def rollback(self):self.raw.rollback()
    def close(self):self.raw.close()


@contextmanager
def mysql_db():
    raw=raw_mysql_connection()
    try:
        install_schema(raw)
        conn=MySQLCompatConnection(raw)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    finally:
        raw.close()

