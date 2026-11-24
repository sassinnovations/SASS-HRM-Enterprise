"""v2.4.0: permission-scoped CSV exports, no new tables or demo records."""
from __future__ import annotations
import csv
import io
from datetime import date, timedelta
from fastapi import Depends, HTTPException, Query, Response
from main import app, audit, current_user, db, require_hr, rows


def safe_csv_cell(value: object) -> str:
    """Keep externally supplied values from being interpreted as spreadsheet formulas."""
    if value is None:
        return ''
    raw = str(value)
    if raw.lstrip('\t\r\n ').startswith(('=', '+', '-', '@')):
        return "'" + raw
    return raw


def csv_response(columns: list[str], data: list[dict], filename: str) -> Response:
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\r\n')
    writer.writerow(columns)
    for item in data:
        writer.writerow([safe_csv_cell(item.get(column)) for column in columns])
    return Response(content='\ufeff' + output.getvalue(), media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="{filename}"',
                 'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})


@app.get('/api/attendance/export-me.csv')
def export_my_attendance(
    start: date | None = None, end: date | None = None,
    user=Depends(current_user),
):
    """Personal download only; managers and HR cannot use this URL for other staff."""
    to_date = end or date.today()
    from_date = start or (to_date - timedelta(days=365))
    if to_date < from_date or (to_date - from_date).days > 366 or to_date > date.today():
        raise HTTPException(422, 'Choose a valid date range of no more than 366 days ending today or earlier')
    with db() as conn:
        data = rows(conn.execute("""SELECT day,check_in,check_out,status FROM attendance
            WHERE employee_id=? AND day BETWEEN ? AND ? ORDER BY day DESC LIMIT 370""",
            (user['id'], from_date.isoformat(), to_date.isoformat())))
        audit(conn, user['id'], 'attendance.export_self', 'employee:' + str(user['id']),
              f'{from_date.isoformat()} through {to_date.isoformat()}')
    return csv_response(['day','check_in','check_out','status'], data,
                        f'sass-my-attendance-{from_date}-{to_date}.csv')


@app.get('/api/audit/export.csv')
def export_audit_activity(
    limit: int = Query(500, ge=1, le=1000),
    user=Depends(require_hr),
):
    """HR administrators can export the latest 1-1000 events. Every export is itself audited."""
    with db() as conn:
        data = rows(conn.execute("""SELECT id,actor_id,action,target,details,created_at
            FROM audit_events ORDER BY id DESC LIMIT ?""", (limit,)))
        audit(conn, user['id'], 'audit.export', 'audit_events', f'row_limit={limit}')
    return csv_response(['id','actor_id','action','target','details','created_at'], data,
                        'sass-hrm-audit-activity.csv')
