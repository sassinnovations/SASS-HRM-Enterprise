"""Private, account-scoped calendar entries (v2.7, additive migration).

Calendar entries are user-authored personal notes, never employee/leave approvals.
The calendar API never accepts an employee ID from the client.
"""
from datetime import date, datetime, timezone
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
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
        ''')


class PersonalEventInput(BaseModel):
    day: date
    start_time: str = Field(default='', max_length=5)
    title: str = Field(min_length=2, max_length=120)
    notes: str = Field(default='', max_length=1000)

    @field_validator('start_time')
    @classmethod
    def check_time(cls, value):
        if value:
            try:
                parsed = datetime.strptime(value, '%H:%M')
                if parsed.strftime('%H:%M') != value:
                    raise ValueError('Time must be HH:MM (24-hour clock)')
            except ValueError as exc:
                raise ValueError('Time must be HH:MM (24-hour clock)') from exc
        return value

    @field_validator('title')
    @classmethod
    def check_title(cls, value):
        value = value.strip()
        if len(value) < 2:
            raise ValueError('An event title is required')
        return value


def event_values(body):
    return body.day.isoformat(), body.start_time, body.title, body.notes.strip()


@app.get('/api/calendar/personal')
def personal_calendar(user=Depends(current_user)):
    with db() as conn:
        return rows(conn.execute('''SELECT id,day,start_time,title,notes,created_at,updated_at
            FROM personal_calendar_events WHERE employee_id=?
            ORDER BY day ASC,start_time ASC,id ASC LIMIT 1000''', (user['id'],)))


@app.post('/api/calendar/personal', status_code=201)
def create_personal_event(body: PersonalEventInput, user=Depends(current_user)):
    timestamp = datetime.now(timezone.utc).isoformat()
    with db() as conn:
        result = conn.execute('''INSERT INTO personal_calendar_events
          (employee_id,day,start_time,title,notes,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?)''', (user['id'], *event_values(body), timestamp, timestamp))
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
