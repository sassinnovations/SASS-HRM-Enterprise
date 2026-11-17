"""Privacy-conscious multi-modal attendance extensions.

Photo attendance records a consented, encrypted JPEG as evidence, not a face-recognition
match. Fingerprint and iris are device-side biometric checks: only a signed, matched
assertion is accepted and no biometric sample or template enters SASS HRM.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sqlite3
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from typing import Literal
from zoneinfo import ZoneInfo

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, HTTPException, Query, Request, Response
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field

from main import app, db, rows, current_user, require_hr, audit

MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_IMAGE_PIXELS = 8_000_000
PHOTO_RETENTION_DAYS = 30


def _now() -> datetime:
    # Match the organization's configured timezone (not the Docker container timezone).
    name = os.getenv('ATTENDANCE_TIMEZONE', 'Asia/Kolkata')
    try:
        return datetime.now(ZoneInfo(name))
    except Exception as exc:
        raise RuntimeError('Set ATTENDANCE_TIMEZONE to a valid IANA timezone') from exc


def _cipher() -> Fernet | None:
    key = os.getenv('ATTENDANCE_PHOTO_FERNET_KEY', '').strip()
    if not key:
        return None
    try:
        return Fernet(key.encode('ascii'))
    except (ValueError, TypeError) as exc:
        raise RuntimeError('Invalid ATTENDANCE_PHOTO_FERNET_KEY. Generate a valid Fernet key.') from exc


def _devices() -> dict[str,str]:
    raw = os.getenv('ATTENDANCE_DEVICE_SECRETS_JSON', '{}').strip()
    try:
        data = json.loads(raw)
        if not isinstance(data, dict) or any(not isinstance(k,str) or not re.fullmatch('[A-Za-z0-9_-]{3,64}',k)
              or not isinstance(v,str) or len(v) < 32 for k,v in data.items()):
            raise ValueError('Expected mapping of device ID to 32+ character secret')
        return data
    except (ValueError, TypeError) as exc:
        raise RuntimeError('Invalid ATTENDANCE_DEVICE_SECRETS_JSON: use a JSON object with strong device secrets') from exc


@app.on_event('startup')
def initialize_attendance_modalities():
    with db() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS attendance_capture_events (
          id INTEGER PRIMARY KEY,
          employee_id INTEGER NOT NULL REFERENCES employees(id),
          work_day TEXT NOT NULL,
          event_type TEXT NOT NULL,
          method TEXT NOT NULL,
          occurred_at TEXT NOT NULL,
          recorded_by INTEGER REFERENCES employees(id),
          device_id TEXT NOT NULL DEFAULT '',
          note TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_attendance_capture_employee ON attendance_capture_events(employee_id,work_day);
        CREATE TABLE IF NOT EXISTS attendance_photo_evidence (
          event_id INTEGER PRIMARY KEY REFERENCES attendance_capture_events(id) ON DELETE CASCADE,
          ciphertext BLOB NOT NULL,
          created_at TEXT NOT NULL,
          expires_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS attendance_device_nonces (
          device_id TEXT NOT NULL,
          nonce TEXT NOT NULL,
          used_at TEXT NOT NULL,
          PRIMARY KEY(device_id,nonce)
        );
        ''')


def _record(conn, employee_id: int, day: str, clock: str, event: str, method: str, actor: int | None,
            occurred_at: str, device_id: str = '', note: str = '') -> int:
    row=conn.execute('SELECT * FROM attendance WHERE employee_id=? AND day=?',(employee_id,day)).fetchone()
    if event=='check-in':
        if row and row['check_in']:
            raise HTTPException(409,'Already checked in on this work date')
        if row:
            conn.execute("UPDATE attendance SET check_in=?,status='Present' WHERE id=?",(clock,row['id']))
        else:
            conn.execute("INSERT INTO attendance(employee_id,day,check_in,status) VALUES(?,?,?,'Present')",(employee_id,day,clock))
    else:
        if not row or not row['check_in']:
            raise HTTPException(409,'Check in before checking out')
        if row['check_out']:
            raise HTTPException(409,'Already checked out on this work date')
        # Keep clock times sane for same-day records.
        if clock < row['check_in']:
            raise HTTPException(422,'Check-out time must not precede check-in time')
        conn.execute('UPDATE attendance SET check_out=? WHERE id=?',(clock,row['id']))
    cur=conn.execute('''INSERT INTO attendance_capture_events
      (employee_id,work_day,event_type,method,occurred_at,recorded_by,device_id,note)
      VALUES(?,?,?,?,?,?,?,?)''',(employee_id,day,event,method,occurred_at,actor,device_id,note))
    audit(conn,actor or employee_id,'attendance.'+method.lower().replace(' ','_'),f'employee:{employee_id}',f'{event} on {day}; event:{cur.lastrowid}')
    return cur.lastrowid


class ManualPunch(BaseModel):
    employee_id: int = Field(gt=0)
    work_day: date
    check_in: str
    check_out: str | None = None
    reason: str = Field(min_length=8,max_length=500)


@app.post('/api/attendance/manual',status_code=201)
def manual_attendance(body:ManualPunch,user=Depends(require_hr)):
    if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',body.check_in):
        raise HTTPException(422,'Use HH:MM check-in time')
    if body.check_out is not None and (not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',body.check_out) or body.check_out<=body.check_in):
        raise HTTPException(422,'Check-out must be after check-in on the same day')
    if not body.reason.strip():
        raise HTTPException(422,'Provide a meaningful reason for manual attendance')
    current_day=_now().date()
    if body.work_day>current_day or (current_day-body.work_day).days>90:
        raise HTTPException(422,'Manual attendance is limited to today or the past 90 days')
    with db() as conn:
        employee=conn.execute('SELECT id FROM employees WHERE id=? AND account_active=1',(body.employee_id,)).fetchone()
        if not employee:
            raise HTTPException(404,'Active employee not found')
        # Never silently overwrite a logged punch; use the existing approved correction workflow.
        if conn.execute('SELECT 1 FROM attendance WHERE employee_id=? AND day=?',(body.employee_id,body.work_day.isoformat())).fetchone():
            raise HTTPException(409,'Attendance already exists. Use Attendance Corrections to modify it.')
        stamp=_now().isoformat()
        conn.execute('INSERT INTO attendance(employee_id,day,check_in,check_out,status) VALUES(?,?,?,?,?)',
                     (body.employee_id,body.work_day.isoformat(),body.check_in,body.check_out,'Present'))
        cur=conn.execute('''INSERT INTO attendance_capture_events
          (employee_id,work_day,event_type,method,occurred_at,recorded_by,note) VALUES(?,?,?,?,?,?,?)''',
          (body.employee_id,body.work_day.isoformat(),'manual-entry','Manual',stamp,user['id'],body.reason.strip()))
        audit(conn,user['id'],'attendance.manual_entry',f'employee:{body.employee_id}',
              f'{body.work_day.isoformat()}; {body.check_in}-{body.check_out or "open"}; reason={body.reason.strip()}')
    return {'id':cur.lastrowid,'message':'Manual attendance recorded','status':'Present'}


@app.get('/api/attendance/methods')
def attendance_methods(user=Depends(current_user)):
    return {'manual_enabled': True,
            'photo_enabled': _cipher() is not None and os.getenv('ATTENDANCE_PHOTO_ENABLED','0')=='1',
            'fingerprint_enabled': any(True for _ in _devices()) and os.getenv('ATTENDANCE_DEVICE_ENABLED','0')=='1',
            'iris_enabled': any(True for _ in _devices()) and os.getenv('ATTENDANCE_DEVICE_ENABLED','0')=='1',
            'photo_retention_days':PHOTO_RETENTION_DAYS,
            'photo_notice':'Camera photo is evidence only, not automated face recognition. Employee consent is required.',
            'device_notice':'Fingerprint/iris require a configured scanner and a signed device gateway; no raw biometric data is stored.'}


def _normalize_photo(source: bytes) -> bytes:
    try:
        with Image.open(BytesIO(source)) as im:
            if im.format not in {'JPEG','PNG','WEBP'} or getattr(im,'is_animated',False):
                raise HTTPException(422,'Only static JPEG, PNG or WebP photos are supported')
            if im.width*im.height > MAX_IMAGE_PIXELS:
                raise HTTPException(413,'Photo dimensions exceed safe limits')
            im.load()
            normalized=ImageOps.exif_transpose(im).convert('RGB')
            normalized.thumbnail((640,640),Image.Resampling.LANCZOS)
            buf=BytesIO(); normalized.save(buf,'JPEG',quality=82,optimize=True)
            return buf.getvalue()
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError,ValueError) as exc:
        raise HTTPException(422,'The camera image is invalid') from exc


@app.post('/api/attendance/photo',status_code=201)
async def photo_attendance(request:Request, action:Literal['check-in','check-out']=Query('check-in'),
                           consent:bool=Query(False),user=Depends(current_user)):
    cipher=_cipher()
    if cipher is None or os.getenv('ATTENDANCE_PHOTO_ENABLED','0')!='1':
        raise HTTPException(503,'Photo attendance is disabled until HR IT configures encrypted photo storage')
    if not consent:
        raise HTTPException(422,'Explicit consent is required for this photo submission. Use manual attendance instead.')
    if request.headers.get('content-type','').split(';')[0].lower() not in {'image/jpeg','image/png','image/webp'}:
        raise HTTPException(415,'Only JPEG, PNG and WebP camera photos are accepted')
    raw=bytearray()
    async for part in request.stream():
        raw.extend(part)
        if len(raw)>MAX_IMAGE_BYTES:
            raise HTTPException(413,'Maximum photo upload size is 2 MiB')
    if not raw:
        raise HTTPException(422,'Capture a photo first')
    encrypted=cipher.encrypt(_normalize_photo(raw))
    moment=_now();day=moment.date().isoformat(); stamp=moment.isoformat()
    with db() as conn:
        event_id=_record(conn,user['id'],day,moment.strftime('%H:%M'),action,'Photo',user['id'],stamp)
        expires=(datetime.now(timezone.utc)+timedelta(days=PHOTO_RETENTION_DAYS)).isoformat()
        conn.execute('INSERT INTO attendance_photo_evidence(event_id,ciphertext,created_at,expires_at) VALUES(?,?,?,?)',
                     (event_id,encrypted,datetime.now(timezone.utc).isoformat(),expires))
        # Minimize retained photos, preserving the attendance event audit metadata.
        conn.execute('DELETE FROM attendance_photo_evidence WHERE expires_at<?',(datetime.now(timezone.utc).isoformat(),))
    return {'id':event_id,'message':'Photo evidence saved and attendance '+action+' recorded','method':'Photo'}


@app.get('/api/attendance/photo-evidence/{event_id}')
def photo_evidence(event_id:int,user=Depends(current_user)):
    cipher=_cipher()
    if cipher is None:
        raise HTTPException(503,'Photo evidence encryption is not configured')
    with db() as conn:
        result=conn.execute('''SELECT e.employee_id,p.ciphertext,p.expires_at FROM attendance_photo_evidence p
          JOIN attendance_capture_events e ON e.id=p.event_id WHERE p.event_id=?''',(event_id,)).fetchone()
        if not result or result['expires_at']<datetime.now(timezone.utc).isoformat():
            raise HTTPException(404,'Photo evidence not found or expired')
        if user['role']!='admin' and result['employee_id']!=user['id']:
            raise HTTPException(403,'Only the employee and HR administrators may view photo evidence')
        try:
            data=cipher.decrypt(bytes(result['ciphertext']))
        except InvalidToken as exc:
            raise HTTPException(503,'Unable to decrypt stored photo evidence') from exc
    return Response(data,media_type='image/jpeg',headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})


@app.delete('/api/attendance/photo-evidence/{event_id}')
def remove_photo_evidence(event_id:int,user=Depends(current_user)):
    with db() as conn:
        event=conn.execute('SELECT employee_id FROM attendance_capture_events WHERE id=? AND method=?',(event_id,'Photo')).fetchone()
        if not event:
            raise HTTPException(404,'Photo evidence not found')
        if user['role']!='admin' and event['employee_id']!=user['id']:
            raise HTTPException(403,'Only the employee and HR administrators may remove photo evidence')
        conn.execute('DELETE FROM attendance_photo_evidence WHERE event_id=?',(event_id,))
        audit(conn,user['id'],'attendance.photo_deleted',f'event:{event_id}')
    return {'message':'Photo deleted; attendance log preserved'}


@app.get('/api/attendance/capture-events')
def capture_events(user=Depends(current_user)):
    with db() as conn:
        conn.execute('DELETE FROM attendance_photo_evidence WHERE expires_at<?',(datetime.now(timezone.utc).isoformat(),))
        base='''SELECT e.id,e.employee_id,e.work_day,e.event_type,e.method,e.occurred_at,e.device_id,
          p.event_id AS has_photo,person.name AS employee_name
          FROM attendance_capture_events e JOIN employees person ON person.id=e.employee_id
          LEFT JOIN attendance_photo_evidence p ON p.event_id=e.id'''
        if user['role']=='admin':
            return rows(conn.execute(base+' ORDER BY e.id DESC LIMIT 100'))
        if user['role']=='manager':
            return rows(conn.execute(base+''' WHERE person.id=? OR person.manager_id=? ORDER BY e.id DESC LIMIT 100''',
                (user['id'],user['id'])))
        return rows(conn.execute(base+' WHERE e.employee_id=? ORDER BY e.id DESC LIMIT 100',(user['id'],)))


class SignedPunch(BaseModel):
    device_id:str=Field(min_length=3,max_length=64,pattern=r'^[A-Za-z0-9_-]+$')
    employee_code:str=Field(min_length=1,max_length=64)
    modality:Literal['fingerprint','iris']
    action:Literal['check-in','check-out']
    matched:Literal[True]
    observed_at:datetime
    nonce:str=Field(min_length=16,max_length=128,pattern=r'^[A-Za-z0-9_-]+$')


@app.post('/api/attendance/biometric/device-event',status_code=201)
async def signed_device_event(request:Request):
    # Not a browser API: hardware gateway signs the exact raw request body.
    if os.getenv('ATTENDANCE_DEVICE_ENABLED','0')!='1':
        raise HTTPException(503,'Biometric device gateway is not configured')
    raw=await request.body()
    if not raw or len(raw)>4096:
        raise HTTPException(413,'Device event payload is too large')
    try:
        body=SignedPunch.model_validate_json(raw)
    except Exception as exc:
        raise HTTPException(422,'Invalid device assertion') from exc
    secret=_devices().get(body.device_id)
    supplied=request.headers.get('X-SASS-Device-Signature','')
    if not secret or not re.fullmatch(r'[0-9a-f]{64}',supplied):
        raise HTTPException(401,'Unregistered device or missing signature')
    expected=hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,supplied):
        raise HTTPException(401,'Invalid device signature')
    if body.observed_at.tzinfo is None or abs((datetime.now(timezone.utc)-body.observed_at.astimezone(timezone.utc)).total_seconds())>180:
        raise HTTPException(422,'Device clock must be within three minutes of server time')
    moment=_now();day=moment.date().isoformat()
    with db() as conn:
        emp=conn.execute('SELECT id FROM employees WHERE code=? AND account_active=1',(body.employee_code,)).fetchone()
        if not emp:
            raise HTTPException(404,'Employee not found or inactive')
        try:
            conn.execute('INSERT INTO attendance_device_nonces(device_id,nonce,used_at) VALUES(?,?,?)',
                         (body.device_id,body.nonce,datetime.now(timezone.utc).isoformat()))
        except sqlite3.IntegrityError as exc:
            raise HTTPException(409,'Device event was already processed') from exc
        event_id=_record(conn,emp['id'],day,moment.strftime('%H:%M'),body.action,
                         'Fingerprint' if body.modality=='fingerprint' else 'Iris',None,moment.isoformat(),body.device_id)
        # Expire replay nonces after 24 h. Old messages always fail the timestamp check.
        conn.execute('DELETE FROM attendance_device_nonces WHERE used_at<?',
                     ((datetime.now(timezone.utc)-timedelta(days=1)).isoformat(),))
    return {'id':event_id,'message':'Device verification recorded','method':body.modality,'status':'Present'}
