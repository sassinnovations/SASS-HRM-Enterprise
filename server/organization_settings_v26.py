"""SASS organization settings and office directory (additive, admin-scoped).

Preferences are configuration metadata only: they do not retroactively change
payroll, statutory rules, approved policies, leave balances or attendance.
"""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from main import DB_ENGINE, app, audit, db, require_hr, current_user


def now_utc():
    return datetime.now(timezone.utc).isoformat()


@app.on_event('startup')
def create_sqlite_organization_settings():
    # MySQL uses the additive, CREATE TABLE IF NOT EXISTS migrations in mysql_schema.sql.
    if DB_ENGINE == 'mysql':
        return
    with db() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS organization_preferences (
            id INTEGER PRIMARY KEY, currency TEXT NOT NULL,
            date_format TEXT NOT NULL, week_start TEXT NOT NULL,
            fiscal_year_start_month INTEGER NOT NULL, hours_per_day INTEGER NOT NULL,
            updated_at TEXT NOT NULL, updated_by INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS organization_offices (
            id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE, city TEXT NOT NULL, country TEXT NOT NULL,
            address TEXT NOT NULL, timezone TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL, updated_by INTEGER NOT NULL
        );
        ''')


class Preferences(BaseModel):
    currency: Literal['INR', 'USD', 'GBP', 'EUR', 'AED', 'CAD', 'AUD'] = 'INR'
    date_format: Literal['DD/MM/YYYY', 'MM/DD/YYYY', 'YYYY-MM-DD'] = 'DD/MM/YYYY'
    week_start: Literal['Monday', 'Sunday', 'Saturday'] = 'Monday'
    fiscal_year_start_month: int = Field(default=4, ge=1, le=12)
    hours_per_day: int = Field(default=8, ge=1, le=16)


DEFAULT_PREFERENCES = Preferences().model_dump()


@app.get('/api/admin/organization/settings')
def read_preferences(user=Depends(require_hr)):
    with db() as conn:
        record = conn.execute('''SELECT currency,date_format,week_start,
            fiscal_year_start_month,hours_per_day,updated_at FROM organization_preferences WHERE id=1''').fetchone()
    return dict(record) if record else {**DEFAULT_PREFERENCES, 'updated_at': None}


@app.put('/api/admin/organization/settings')
def save_preferences(body: Preferences, user=Depends(require_hr)):
    fields = body.model_dump()
    timestamp = now_utc()
    with db() as conn:
        if conn.execute('SELECT 1 FROM organization_preferences WHERE id=1').fetchone():
            conn.execute('''UPDATE organization_preferences SET currency=?,date_format=?,
                week_start=?,fiscal_year_start_month=?,hours_per_day=?,
                updated_at=?,updated_by=? WHERE id=1''',
                (*fields.values(), timestamp, user['id']))
        else:
            conn.execute('''INSERT INTO organization_preferences
                (id,currency,date_format,week_start,fiscal_year_start_month,hours_per_day,updated_at,updated_by)
                VALUES(1,?,?,?,?,?,?,?)''', (*fields.values(), timestamp, user['id']))
        audit(conn, user['id'], 'organization.preferences.updated', 'organization:1')
    return {'message': 'Workspace preferences saved', **fields}


class Office(BaseModel):
    code: str = Field(min_length=2, max_length=24)
    name: str = Field(min_length=2, max_length=120)
    city: str = Field(min_length=2, max_length=90)
    country: str = Field(min_length=2, max_length=80)
    address: str = Field(default='', max_length=500)
    timezone: str = Field(min_length=3, max_length=80)
    is_active: bool = True


def validate_office(body: Office):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{1,23}', body.code.strip()):
        raise HTTPException(422, 'Office code must be 2–24 letters, digits, underscores or hyphens')
    if any(not getattr(body, field).strip() for field in ('name', 'city', 'country')):
        raise HTTPException(422, 'Office name, city and country are required')
    try:
        ZoneInfo(body.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(422, 'Use an IANA timezone such as Asia/Kolkata')


def office_values(body: Office):
    return (body.code.strip().upper(), body.name.strip(), body.city.strip(),
            body.country.strip(), body.address.strip(), body.timezone, int(body.is_active))


def check_duplicates(conn, code: str, name: str, exclude: int = -1):
    row = conn.execute('''SELECT id FROM organization_offices
        WHERE (LOWER(code)=LOWER(?) OR LOWER(name)=LOWER(?)) AND id<>?''',
        (code, name, exclude)).fetchone()
    if row:
        raise HTTPException(409, 'An office already uses this code or name')


@app.get('/api/admin/organization/offices')
def get_offices(user=Depends(require_hr)):
    with db() as conn:
        return [dict(r) for r in conn.execute('''SELECT o.*,
          (SELECT COUNT(*) FROM employees e WHERE e.location=o.name) AS employee_count
          FROM organization_offices o ORDER BY o.name''').fetchall()]


@app.post('/api/admin/organization/offices', status_code=201)
def create_office(body: Office, user=Depends(require_hr)):
    validate_office(body)
    values = office_values(body)
    try:
        with db() as conn:
            check_duplicates(conn, values[0], values[1])
            conn.execute('''INSERT INTO organization_offices
                (code,name,city,country,address,timezone,is_active,updated_at,updated_by)
                VALUES(?,?,?,?,?,?,?,?,?)''', (*values, now_utc(), user['id']))
            audit(conn, user['id'], 'organization.office.created', f'office:{values[0]}')
    except sqlite3.IntegrityError:
        raise HTTPException(409, 'Office code or name already exists')
    return {'message': 'Office created'}


@app.put('/api/admin/organization/offices/{office_id}')
def update_office(office_id: int, body: Office, user=Depends(require_hr)):
    validate_office(body)
    values = office_values(body)
    try:
        with db() as conn:
            old = conn.execute('SELECT * FROM organization_offices WHERE id=?', (office_id,)).fetchone()
            if not old:
                raise HTTPException(404, 'Office not found')
            # Employees use textual location names. Renaming an occupied office could break
            # the location association, so ask HR to move employees before renaming.
            assigned = conn.execute('SELECT COUNT(*) FROM employees WHERE location=?', (old['name'],)).fetchone()[0]
            if assigned and (values[1] != old['name'] or not body.is_active):
                raise HTTPException(409, 'Reassign employees before renaming or deactivating this office')
            check_duplicates(conn, values[0], values[1], office_id)
            conn.execute('''UPDATE organization_offices SET code=?,name=?,city=?,country=?,
                address=?,timezone=?,is_active=?,updated_at=?,updated_by=? WHERE id=?''',
                (*values, now_utc(), user['id'], office_id))
            audit(conn, user['id'], 'organization.office.updated', f'office:{office_id}')
    except sqlite3.IntegrityError:
        raise HTTPException(409, 'Office code or name already exists')
    return {'message': 'Office updated'}


@app.get('/api/organization/identity')
def organization_identity(user=Depends(current_user)):
    """Workplace label for signed-in staff; never reveals private admin settings."""
    with db() as conn:
        record = conn.execute('SELECT name FROM organization_profile WHERE id=1').fetchone()
    return {'name': record['name'] if record else 'SASS Innovations'}
