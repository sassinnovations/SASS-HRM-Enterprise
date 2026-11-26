"""Private, account-scoped calendar entries (v2.7, additive migration).

Calendar entries are user-authored personal notes, never employee/leave approvals.
The calendar API never accepts an employee ID from the client.
"""
from datetime import date, datetime, timezone
from sqlite3 import IntegrityError
from unicodedata import normalize
from typing import Literal
from fastapi import Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from main import DB_ENGINE, app, audit, current_user, db, rows


@app.on_event('startup')
def create_sqlite_personal_calendar():
    if DB_ENGINE == 'mysql':
        return
    with db() as conn:
        conn.executescript('''CREATE TABLE IF NOT EXISTS personal_calendar_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER NOT NULL,
          day TEXT NOT NULL, start_time TEXT NOT NULL DEFAULT '',
          title TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
          FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_calendar_owner_day ON personal_calendar_events(employee_id,day);
        CREATE TABLE IF NOT EXISTS employee_calendar_preferences (
          employee_id INTEGER PRIMARY KEY REFERENCES employees(id) ON DELETE CASCADE,
          week_start TEXT NOT NULL DEFAULT 'monday',
          visibility TEXT NOT NULL DEFAULT 'all',
          default_start_time TEXT NOT NULL DEFAULT '',
          include_private_export INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS employee_calendar_agenda_preferences (
          employee_id INTEGER PRIMARY KEY REFERENCES employees(id) ON DELETE CASCADE,
          preferred_view TEXT NOT NULL DEFAULT 'month',
          agenda_days INTEGER NOT NULL DEFAULT 14
        );
        CREATE TABLE IF NOT EXISTS employee_calendar_categories (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
          name TEXT NOT NULL, name_key TEXT NOT NULL,
          color TEXT NOT NULL DEFAULT 'blue',
          UNIQUE(employee_id,name_key)
        );
        CREATE TABLE IF NOT EXISTS personal_calendar_event_categories (
          event_id INTEGER PRIMARY KEY REFERENCES personal_calendar_events(id) ON DELETE CASCADE,
          category_id INTEGER NOT NULL REFERENCES employee_calendar_categories(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_calendar_category_events ON personal_calendar_event_categories(category_id);
        ''')


def validate_start_time(value: str) -> str:
    if value:
        try:
            parsed = datetime.strptime(value, '%H:%M')
            if parsed.strftime('%H:%M') != value:
                raise ValueError('Time must be HH:MM (24-hour clock)')
        except ValueError as exc:
            raise ValueError('Time must be HH:MM (24-hour clock)') from exc
    return value


class PersonalEventInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    day: date
    start_time: str = Field(default='', max_length=5)
    title: str = Field(min_length=2, max_length=120)
    notes: str = Field(default='', max_length=1000)
    category_id: int | None = Field(default=None, gt=0)

    @field_validator('start_time')
    @classmethod
    def check_time(cls, value):
        return validate_start_time(value)

    @field_validator('title')
    @classmethod
    def check_title(cls, value):
        value = value.strip()
        if len(value) < 2:
            raise ValueError('An event title is required')
        return value


def event_values(body):
    return body.day.isoformat(), body.start_time, body.title, body.notes.strip()


class PersonalCalendarPreferences(BaseModel):
    model_config = ConfigDict(extra='forbid')
    week_start: Literal['monday', 'sunday'] = 'monday'
    visibility: Literal['all', 'personal', 'official'] = 'all'
    default_start_time: str = Field(default='', max_length=5)
    include_private_export: bool = False
    preferred_view: Literal['month', 'agenda'] = 'month'
    agenda_days: Literal[7, 14, 30] = 14

    @field_validator('default_start_time')
    @classmethod
    def check_default_time(cls, value):
        return validate_start_time(value)


def _calendar_preferences(conn, employee_id: int) -> PersonalCalendarPreferences:
    saved = conn.execute('''SELECT week_start,visibility,default_start_time,include_private_export
      FROM employee_calendar_preferences WHERE employee_id=?''', (employee_id,)).fetchone()
    agenda = conn.execute('''SELECT preferred_view,agenda_days FROM employee_calendar_agenda_preferences
      WHERE employee_id=?''', (employee_id,)).fetchone()
    values = dict(saved) if saved else {}
    if agenda:
        values.update(dict(agenda))
    return PersonalCalendarPreferences(**values)


@app.get('/api/calendar/preferences')
def get_calendar_preferences(response: Response, user=Depends(current_user)):
    response.headers['Cache-Control'] = 'no-store'
    with db() as conn:
        return _calendar_preferences(conn, user['id'])


@app.put('/api/calendar/preferences')
def save_calendar_preferences(body: PersonalCalendarPreferences, user=Depends(current_user)):
    with db() as conn:
        conn.execute('''INSERT INTO employee_calendar_preferences
          (employee_id,week_start,visibility,default_start_time,include_private_export)
          VALUES (?,?,?,?,?) ON CONFLICT(employee_id) DO UPDATE SET
          week_start=excluded.week_start, visibility=excluded.visibility,
          default_start_time=excluded.default_start_time,
          include_private_export=excluded.include_private_export''',
          (user['id'], body.week_start, body.visibility, body.default_start_time, int(body.include_private_export)))
        if {'preferred_view', 'agenda_days'} & body.model_fields_set:
            # Legacy callers do not send agenda settings and must not reset them.
            agenda = _calendar_preferences(conn, user['id'])
            preferred_view = body.preferred_view if 'preferred_view' in body.model_fields_set else agenda.preferred_view
            agenda_days = body.agenda_days if 'agenda_days' in body.model_fields_set else agenda.agenda_days
            conn.execute('''INSERT INTO employee_calendar_agenda_preferences (employee_id,preferred_view,agenda_days)
                            VALUES(?,?,?) ON CONFLICT(employee_id) DO UPDATE SET
                            preferred_view=excluded.preferred_view,agenda_days=excluded.agenda_days''',
                         (user['id'], preferred_view, agenda_days))
        audit(conn, user['id'], 'calendar.preferences.updated', 'personal_calendar')
        return _calendar_preferences(conn, user['id'])


class CalendarCategoryInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=2, max_length=48)
    color: Literal['blue', 'green', 'violet', 'amber', 'rose'] = 'blue'

    @field_validator('name')
    @classmethod
    def check_name(cls, value):
        name = normalize('NFC', ' '.join(value.split()))
        if len(name) < 2 or len(name) > 48 or any(ord(character) < 32 for character in name):
            raise ValueError('Enter a category name of 2–48 characters')
        return name


def _category_name_key(name: str) -> str:
    return normalize('NFC', name.casefold())


def _owned_category(conn, owner_id: int, category_id: int):
    category = conn.execute('SELECT id FROM employee_calendar_categories WHERE employee_id=? AND id=?',
                            (owner_id, category_id)).fetchone()
    if not category:
        raise HTTPException(404, 'Personal calendar category not found')


def _assign_category(conn, owner_id: int, event_id: int, category_id: int | None):
    if category_id is None:
        conn.execute('DELETE FROM personal_calendar_event_categories WHERE event_id=?', (event_id,))
        return
    _owned_category(conn, owner_id, category_id)
    try:
        conn.execute('''INSERT INTO personal_calendar_event_categories (event_id,category_id) VALUES(?,?)
                        ON CONFLICT(event_id) DO UPDATE SET category_id=excluded.category_id''',
                     (event_id, category_id))
    except IntegrityError as exc:
        raise HTTPException(409, 'The event or category was removed. Refresh and try again.') from exc


@app.get('/api/calendar/categories')
def calendar_categories(response: Response, user=Depends(current_user)):
    response.headers['Cache-Control'] = 'no-store'
    with db() as conn:
        return rows(conn.execute('''SELECT c.id,c.name,c.color,COUNT(e.id) AS event_count
            FROM employee_calendar_categories c
            LEFT JOIN personal_calendar_event_categories tag ON tag.category_id=c.id
            LEFT JOIN personal_calendar_events e ON e.id=tag.event_id AND e.employee_id=c.employee_id
            WHERE c.employee_id=? GROUP BY c.id,c.name,c.color,c.name_key ORDER BY c.name_key,c.id''', (user['id'],)))


@app.post('/api/calendar/categories', status_code=201)
def create_calendar_category(body: CalendarCategoryInput, user=Depends(current_user)):
    with db() as conn:
        try:
            result = conn.execute('INSERT INTO employee_calendar_categories(employee_id,name,name_key,color) VALUES(?,?,?,?)',
                                  (user['id'], body.name, _category_name_key(body.name), body.color))
        except IntegrityError as exc:
            raise HTTPException(409, 'A category with that name already exists.') from exc
        audit(conn, user['id'], 'calendar.category.created', f'calendar_category:{result.lastrowid}')
    return {'id': result.lastrowid, 'name': body.name, 'color': body.color, 'event_count': 0}


@app.patch('/api/calendar/categories/{category_id}')
def edit_calendar_category(category_id: int, body: CalendarCategoryInput, user=Depends(current_user)):
    with db() as conn:
        _owned_category(conn, user['id'], category_id)
        try:
            conn.execute('UPDATE employee_calendar_categories SET name=?,name_key=?,color=? WHERE id=? AND employee_id=?',
                         (body.name, _category_name_key(body.name), body.color, category_id, user['id']))
        except IntegrityError as exc:
            raise HTTPException(409, 'A category with that name already exists.') from exc
        audit(conn, user['id'], 'calendar.category.updated', f'calendar_category:{category_id}')
    return {'message': 'Category updated'}


@app.delete('/api/calendar/categories/{category_id}')
def delete_calendar_category(category_id: int, user=Depends(current_user)):
    with db() as conn:
        result = conn.execute('DELETE FROM employee_calendar_categories WHERE id=? AND employee_id=?',
                              (category_id, user['id']))
        if not result.rowcount:
            raise HTTPException(404, 'Personal calendar category not found')
        audit(conn, user['id'], 'calendar.category.deleted', f'calendar_category:{category_id}')
    return {'message': 'Category removed. Its events are now uncategorized.'}


@app.get('/api/calendar/personal')
def personal_calendar(response: Response, start: date | None = None, end: date | None = None,
                      user=Depends(current_user)):
    response.headers['Cache-Control'] = 'no-store'
    if (start is None) != (end is None) or (start is not None and end is not None
        and (end < start or (end - start).days > 62)):
        raise HTTPException(422, 'Use a valid date range of up to 63 days.')
    statement = '''SELECT e.id,e.day,e.start_time,e.title,e.notes,e.created_at,e.updated_at,
        c.id AS category_id,c.name AS category_name,c.color AS category_color
        FROM personal_calendar_events e
        LEFT JOIN personal_calendar_event_categories tag ON tag.event_id=e.id
        LEFT JOIN employee_calendar_categories c ON c.id=tag.category_id AND c.employee_id=e.employee_id
        WHERE e.employee_id=?'''
    params = (user['id'],)
    if start is not None and end is not None:
        statement += ' AND e.day BETWEEN ? AND ?'
        params += (start.isoformat(), end.isoformat())
    statement += ' ORDER BY e.day ASC,e.start_time ASC,e.id ASC LIMIT 1000'
    with db() as conn:
        return rows(conn.execute(statement, params))


@app.post('/api/calendar/personal', status_code=201)
def create_personal_event(body: PersonalEventInput, user=Depends(current_user)):
    timestamp = datetime.now(timezone.utc).isoformat()
    with db() as conn:
        result = conn.execute('''INSERT INTO personal_calendar_events
          (employee_id,day,start_time,title,notes,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?)''', (user['id'], *event_values(body), timestamp, timestamp))
        if body.category_id is not None:
            _assign_category(conn, user['id'], result.lastrowid, body.category_id)
        audit(conn, user['id'], 'calendar.personal.created', f'personal_event:{result.lastrowid}')
    return {'id':result.lastrowid, 'message':'Personal event added'}


@app.patch('/api/calendar/personal/{event_id}')
def edit_personal_event(event_id: int, body: PersonalEventInput, user=Depends(current_user)):
    with db() as conn:
        owned = conn.execute('SELECT id FROM personal_calendar_events WHERE id=? AND employee_id=?', (event_id, user['id'])).fetchone()
        if not owned:
            raise HTTPException(404, 'Personal event not found')
        conn.execute('''UPDATE personal_calendar_events
            SET day=?,start_time=?,title=?,notes=?,updated_at=?
            WHERE id=? AND employee_id=?''', (*event_values(body),datetime.now(timezone.utc).isoformat(), event_id, user['id']))
        # Older clients, including AI actions, omit category_id and keep the assigned category.
        if 'category_id' in body.model_fields_set:
            _assign_category(conn, user['id'], event_id, body.category_id)
        audit(conn, user['id'], 'calendar.personal.updated', f'personal_event:{event_id}')
    return {'message':'Personal event updated'}


@app.delete('/api/calendar/personal/{event_id}')
def delete_personal_event(event_id: int, user=Depends(current_user)):
    with db() as conn:
        record = conn.execute('SELECT id FROM personal_calendar_events WHERE id=? AND employee_id=?', (event_id, user['id'])).fetchone()
        if not record:
            raise HTTPException(404, 'Personal event not found')
        conn.execute('DELETE FROM personal_calendar_events WHERE id=? AND employee_id=?',(event_id, user['id']))
        audit(conn, user['id'], 'calendar.personal.deleted', f'personal_event:{event_id}')
    return {'message':'Personal event removed'}
