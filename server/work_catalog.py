"""HR administrator product catalog and project register, separate from equipment."""
import json
import sqlite3
from datetime import date, datetime, timezone
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, Path
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from main import DB_ENGINE, app, audit, db, require_hr, rows

Catalog = Literal['products', 'projects']
Id = Annotated[int, Path(ge=1, le=9223372036854775807)]
Category = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]

CATALOG_STATUSES = {
    'products': ('Active', 'Inactive'),
    'projects': ('Planned', 'Active', 'On Hold', 'Completed'),
}


class CatalogRecord(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')

    code: str = Field(min_length=1, max_length=48, pattern=r'^[A-Za-z0-9][A-Za-z0-9._-]*$')
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default='', max_length=3000)
    status: str | None = Field(default=None, max_length=24)
    category: str = Field(default='', max_length=80)
    owner_id: int | None = Field(default=None, gt=0, le=9223372036854775807)
    start_date: date | None = None
    end_date: date | None = None


class CatalogSettings(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')

    default_status: str = Field(min_length=1, max_length=24)
    categories: list[Category] = Field(max_length=60)


@app.on_event('startup')
def init_work_catalog():
    # The MySQL adapter installs server/mysql_schema.sql before serving requests.
    # The script below installs the corresponding additive tables for SQLite.
    if DB_ENGINE == 'mysql':
        return
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS hrm_work_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL CHECK(kind IN ('products','projects')),
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL,
            category TEXT NOT NULL,
            owner_id INTEGER REFERENCES employees(id) ON DELETE SET NULL,
            start_date TEXT,
            end_date TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            archived_at TEXT,
            UNIQUE(kind,code)
        );
        CREATE INDEX IF NOT EXISTS idx_hrm_work_catalog_visible
            ON hrm_work_catalog(kind,archived_at,id);
        CREATE TABLE IF NOT EXISTS hrm_work_catalog_settings (
            kind TEXT PRIMARY KEY CHECK(kind IN ('products','projects')),
            default_status TEXT NOT NULL,
            categories_json TEXT NOT NULL
        );
        """)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def read_settings(c, kind: Catalog):
    row = c.execute("SELECT default_status,categories_json FROM hrm_work_catalog_settings WHERE kind=?", (kind,)).fetchone()
    if row is None:
        return {'default_status': CATALOG_STATUSES[kind][0], 'categories': []}
    return {'default_status': row['default_status'], 'categories': json.loads(row['categories_json'])}


@app.get('/api/catalog/{kind}/settings')
def catalog_settings(kind: Catalog, user=Depends(require_hr)):
    with db() as c:
        return read_settings(c, kind)


@app.put('/api/catalog/{kind}/settings')
def save_catalog_settings(kind: Catalog, body: CatalogSettings, user=Depends(require_hr)):
    if body.default_status not in CATALOG_STATUSES[kind]:
        raise HTTPException(422, 'Choose a valid default status.')
    if len({s.casefold() for s in body.categories}) != len(body.categories):
        raise HTTPException(422, 'Category names must be unique.')
    with db() as c:
        c.execute("""INSERT INTO hrm_work_catalog_settings(kind,default_status,categories_json) VALUES(?,?,?)
            ON CONFLICT(kind) DO UPDATE SET default_status=excluded.default_status,categories_json=excluded.categories_json""",
                  (kind, body.default_status, json.dumps(body.categories, ensure_ascii=False)))
        audit(c, user['id'], 'catalog.settings.update', kind)
        return read_settings(c, kind)


FIELDS = 'id,code,name,description,status,category,owner_id,start_date,end_date'


@app.get('/api/catalog/{kind}')
def list_catalog(kind: Catalog, user=Depends(require_hr)):
    with db() as c:
        return rows(c.execute(f'SELECT {FIELDS} FROM hrm_work_catalog WHERE kind=? AND archived_at IS NULL ORDER BY id DESC', (kind,)))


def find_record(c, kind: Catalog, record_id: int):
    row = c.execute(f'SELECT {FIELDS} FROM hrm_work_catalog WHERE kind=? AND id=? AND archived_at IS NULL',
                    (kind, record_id)).fetchone()
    if row is None:
        raise HTTPException(404, 'Record not found.')
    return dict(row)


def record_values(c, kind: Catalog, body: CatalogRecord, prior=None):
    settings = read_settings(c, kind)
    status = body.status if body.status is not None else (prior['status'] if prior else settings['default_status'])
    if status not in CATALOG_STATUSES[kind]:
        raise HTTPException(422, 'Choose a valid status.')
    category = ''
    if body.category:
        offered = {s.casefold(): s for s in settings['categories']}
        category = offered.get(body.category.casefold())
        if category is None and prior and body.category.casefold() == prior['category'].casefold():
            category = prior['category']
        if category is None:
            raise HTTPException(422, 'Choose a configured category or leave it blank.')
    if kind == 'products' and (body.owner_id or body.start_date or body.end_date):
        raise HTTPException(422, 'Owner and dates are only available for projects.')
    if body.start_date and body.end_date and body.end_date < body.start_date:
        raise HTTPException(422, 'End date cannot be before the start date.')
    if body.owner_id is not None:
        owner = c.execute('SELECT account_active FROM employees WHERE id=?', (body.owner_id,)).fetchone()
        if owner is None or (not owner['account_active'] and (not prior or body.owner_id != prior['owner_id'])):
            raise HTTPException(422, 'Choose an active employee as owner.')
    return (body.code.upper(), body.name, body.description, status, category, body.owner_id,
            body.start_date.isoformat() if body.start_date else None, body.end_date.isoformat() if body.end_date else None)


@app.post('/api/catalog/{kind}', status_code=201)
def add_catalog_record(kind: Catalog, body: CatalogRecord, user=Depends(require_hr)):
    with db() as c:
        values = record_values(c, kind, body)
        now = stamp()
        try:
            result = c.execute("""INSERT INTO hrm_work_catalog
                (kind,code,name,description,status,category,owner_id,start_date,end_date,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (kind, *values, now, now))
        except sqlite3.IntegrityError as exc:
            raise HTTPException(409, 'That code already exists, including deleted records.') from exc
        record_id = result.lastrowid
        audit(c, user['id'], 'catalog.record.create', f'{kind}:{record_id}')
        return find_record(c, kind, record_id)


@app.put('/api/catalog/{kind}/{record_id}')
def edit_catalog_record(kind: Catalog, record_id: Id, body: CatalogRecord, user=Depends(require_hr)):
    with db() as c:
        prior = find_record(c, kind, record_id)
        values = record_values(c, kind, body, prior)
        try:
            c.execute("""UPDATE hrm_work_catalog
                SET code=?,name=?,description=?,status=?,category=?,owner_id=?,start_date=?,end_date=?,updated_at=?
                WHERE kind=? AND id=? AND archived_at IS NULL""", (*values, stamp(), kind, record_id))
        except sqlite3.IntegrityError as exc:
            raise HTTPException(409, 'That code already exists, including deleted records.') from exc
        record = find_record(c, kind, record_id)
        audit(c, user['id'], 'catalog.record.update', f'{kind}:{record_id}')
        return record


@app.delete('/api/catalog/{kind}/{record_id}')
def delete_catalog_record(kind: Catalog, record_id: Id, user=Depends(require_hr)):
    now = stamp()
    with db() as c:
        result = c.execute("""UPDATE hrm_work_catalog SET archived_at=?,updated_at=?
            WHERE kind=? AND id=? AND archived_at IS NULL""", (now, now, kind, record_id))
        if result.rowcount != 1:
            raise HTTPException(404, 'Record not found.')
        audit(c, user['id'], 'catalog.record.delete', f'{kind}:{record_id}')
    return {'id': record_id, 'deleted': True}
