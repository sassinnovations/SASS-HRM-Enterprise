"""v2.9 professional profiles and HR-governed official identity corrections.

Professional directory information is intentionally separate from private_profiles,
payroll, authentication credentials and HR work-history metadata.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from io import BytesIO
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import Depends, HTTPException, Request, Response
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field, field_validator
from main import app, db, rows, current_user, require_hr, audit
from enterprise import inform

# Uploaded portraits are decoded, normalized, resized, and stripped of EXIF metadata.
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_PIXELS = 8_000_000



def utcnow():
    return datetime.now(timezone.utc).isoformat()


@app.on_event('startup')
def initialize_profile_v29():
    with db() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS professional_profiles (
          employee_id INTEGER PRIMARY KEY REFERENCES employees(id),
          preferred_name TEXT NOT NULL DEFAULT '',
          headline TEXT NOT NULL DEFAULT '',
          biography TEXT NOT NULL DEFAULT '',
          work_phone TEXT NOT NULL DEFAULT '',
          timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
          language TEXT NOT NULL DEFAULT 'en',
          directory_visible INTEGER NOT NULL DEFAULT 1,
          avatar_color TEXT NOT NULL DEFAULT '#3C6DF0',
          updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS profile_photos (
          employee_id INTEGER PRIMARY KEY REFERENCES employees(id) ON DELETE CASCADE,
          mime_type TEXT NOT NULL,
          photo_bytes BLOB NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS profile_change_requests (
          id INTEGER PRIMARY KEY,
          employee_id INTEGER NOT NULL REFERENCES employees(id),
          field_name TEXT NOT NULL,
          requested_value TEXT NOT NULL,
          reason TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'Pending',
          requested_at TEXT NOT NULL,
          reviewed_by INTEGER REFERENCES employees(id),
          reviewed_at TEXT,
          review_note TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_profile_changes_owner ON profile_change_requests(employee_id,status);
        ''')


class ProfessionalProfileIn(BaseModel):
    preferred_name: str = Field(default='', max_length=80)
    headline: str = Field(default='', max_length=140)
    biography: str = Field(default='', max_length=750)
    work_phone: str = Field(default='', max_length=32)
    timezone: str = Field(default='Asia/Kolkata', max_length=80)
    language: Literal['en','hi','te','ta','kn'] = 'en'
    directory_visible: bool = True
    avatar_color: str = '#3C6DF0'

    @field_validator('preferred_name','headline','biography','work_phone',mode='after')
    @classmethod
    def trim(cls, value: str):
        return value.strip()

    @field_validator('avatar_color')
    @classmethod
    def valid_color(cls, value: str):
        if not re.fullmatch(r'#[0-9A-Fa-f]{6}',value):
            raise ValueError('Avatar color must be a six-digit hex color')
        return value.upper()

    @field_validator('timezone')
    @classmethod
    def valid_timezone(cls, value: str):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError, KeyError):
            raise ValueError('Select a valid IANA timezone') from None
        return value

    @field_validator('work_phone')
    @classmethod
    def valid_work_phone(cls,value:str):
        if value and not re.fullmatch(r'[+0-9() .-]{5,32}',value):
            raise ValueError('Enter a valid work telephone number')
        return value


def professional_row(conn,employee_id:int):
    result=conn.execute('''SELECT e.id,e.code,e.name,e.email,e.work_email,e.role,e.designation,e.department,
          e.location,e.work_mode,e.join_date,e.manager_id,
          COALESCE(p.preferred_name,'') AS preferred_name,
          COALESCE(p.headline,'') AS headline,
          COALESCE(p.biography,'') AS biography,
          COALESCE(p.work_phone,'') AS work_phone,
          COALESCE(p.timezone,'Asia/Kolkata') AS timezone,
          COALESCE(p.language,'en') AS language,
          COALESCE(p.directory_visible,1) AS directory_visible,
          COALESCE(p.avatar_color,e.avatar_color) AS avatar_color,
          COALESCE(p.updated_at,'') AS profile_updated_at,
          EXISTS(SELECT 1 FROM profile_photos ph WHERE ph.employee_id=e.id) AS has_photo
          FROM employees e LEFT JOIN professional_profiles p ON p.employee_id=e.id
          WHERE e.id=?''',(employee_id,)).fetchone()
    if result is None:
        raise HTTPException(404,'Employee not found')
    return dict(result)


@app.get('/api/profile/me')
def my_profile(user=Depends(current_user)):
    with db() as conn:
        return professional_row(conn,user['id'])


@app.put('/api/profile/me')
def update_my_profile(body:ProfessionalProfileIn,user=Depends(current_user)):
    values=body.model_dump()
    with db() as conn:
        before=professional_row(conn,user['id'])
        keys=list(values.keys())
        existing=conn.execute('SELECT employee_id FROM professional_profiles WHERE employee_id=?',(user['id'],)).fetchone()
        if existing:
            conn.execute('UPDATE professional_profiles SET '+','.join(k+'=?' for k in keys)+',updated_at=? WHERE employee_id=?',
                         [*(int(values[k]) if k=='directory_visible' else values[k] for k in keys),utcnow(),user['id']])
        else:
            conn.execute('INSERT INTO professional_profiles(employee_id,'+','.join(keys)+',updated_at) VALUES('+','.join('?' for _ in range(len(keys)+2))+')',
                         [user['id'],*(int(values[k]) if k=='directory_visible' else values[k] for k in keys),utcnow()])
        if before['avatar_color']!=values['avatar_color']:
            conn.execute('UPDATE employees SET avatar_color=? WHERE id=?',(values['avatar_color'],user['id']))
        changed=[key for key in keys if before[key]!=values[key]]
        if changed:
            audit(conn,user['id'],'profile.self_updated',f'employee:{user["id"]}',','.join(changed))
        return professional_row(conn,user['id'])




def _photo_response(conn, employee_id: int):
    photo=conn.execute('SELECT mime_type,photo_bytes FROM profile_photos WHERE employee_id=?',(employee_id,)).fetchone()
    if not photo:
        raise HTTPException(404,'No profile photo available')
    return Response(content=bytes(photo['photo_bytes']),media_type=photo['mime_type'],headers={
        'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'
    })


@app.get('/api/profile/me/photo')
def my_profile_photo(user=Depends(current_user)):
    with db() as conn:
        return _photo_response(conn,user['id'])


@app.get('/api/profile/directory/{employee_id}/photo')
def directory_profile_photo(employee_id:int,user=Depends(current_user)):
    with db() as conn:
        visible=conn.execute("""SELECT 1 FROM employees e
          LEFT JOIN professional_profiles p ON p.employee_id=e.id
          WHERE e.id=? AND e.account_active=1 AND COALESCE(p.directory_visible,1)=1""",(employee_id,)).fetchone()
        if not visible:
            raise HTTPException(404,'Photo not available in directory')
        return _photo_response(conn,employee_id)


@app.put('/api/profile/me/photo')
async def upload_my_photo(request:Request,user=Depends(current_user)):
    if request.headers.get('content-type','').split(';')[0].lower() not in {'image/jpeg','image/png','image/webp'}:
        raise HTTPException(415,'Choose a JPEG, PNG or WebP image')
    data=bytearray()
    async for part in request.stream():
        data.extend(part)
        if len(data)>MAX_UPLOAD_BYTES:
            raise HTTPException(413,'Profile image must be 2 MB or smaller')
    if not data:
        raise HTTPException(422,'Choose a profile image')
    try:
        with Image.open(BytesIO(data)) as picture:
            if picture.format not in {'JPEG','PNG','WEBP'} or getattr(picture,'is_animated',False):
                raise HTTPException(422,'Only static JPEG, PNG and WebP images are supported')
            if picture.width*picture.height>MAX_PIXELS:
                raise HTTPException(413,'Image dimensions are too large')
            picture.load()
            clean=ImageOps.exif_transpose(picture).convert('RGB')
            clean.thumbnail((512,512),Image.Resampling.LANCZOS)
            result=BytesIO()
            clean.save(result,format='JPEG',quality=85,optimize=True)
            normalized=result.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(422,'The selected file is not a valid supported image') from exc
    with db() as conn:
        existing=conn.execute('SELECT 1 FROM profile_photos WHERE employee_id=?',(user['id'],)).fetchone()
        if existing:
            conn.execute('UPDATE profile_photos SET mime_type=?,photo_bytes=?,updated_at=? WHERE employee_id=?',
                         ('image/jpeg',normalized,utcnow(),user['id']))
        else:
            conn.execute('INSERT INTO profile_photos(employee_id,mime_type,photo_bytes,updated_at) VALUES(?,?,?,?)',
                         (user['id'],'image/jpeg',normalized,utcnow()))
        audit(conn,user['id'],'profile.photo.updated',f'employee:{user["id"]}',f'normalized_jpeg_bytes={len(normalized)}')
    return {'has_photo':True,'message':'Profile photo saved'}


@app.delete('/api/profile/me/photo')
def delete_my_photo(user=Depends(current_user)):
    with db() as conn:
        removed=conn.execute('DELETE FROM profile_photos WHERE employee_id=?',(user['id'],))
        if removed.rowcount:
            audit(conn,user['id'],'profile.photo.deleted',f'employee:{user["id"]}','')
    return {'has_photo':False,'message':'Profile photo removed'}


@app.delete('/api/profile/me/optional')
def clear_optional_profile(user=Depends(current_user)):
    """Do not delete workforce identity, credentials, permissions, or HR-managed fields."""
    with db() as conn:
        conn.execute('DELETE FROM profile_photos WHERE employee_id=?',(user['id'],))
        conn.execute('DELETE FROM professional_profiles WHERE employee_id=?',(user['id'],))
        conn.execute("UPDATE employees SET avatar_color='#3C6DF0' WHERE id=?",(user['id'],))
        audit(conn,user['id'],'profile.optional_cleared',f'employee:{user["id"]}','professional metadata and avatar removed')
        return professional_row(conn,user['id'])

@app.get('/api/profile/directory')
def profile_directory(user=Depends(current_user)):
    # Only opted-in professional details are returned; no private_profiles join.
    with db() as conn:
        entries=rows(conn.execute('''SELECT e.id,e.name,e.designation,e.department,e.location,
           COALESCE(p.preferred_name,'') AS preferred_name,
           COALESCE(p.headline,'') AS headline,
           COALESCE(p.biography,'') AS biography,
           COALESCE(p.work_phone,'') AS work_phone,
           COALESCE(p.avatar_color,e.avatar_color) AS avatar_color,
           EXISTS(SELECT 1 FROM profile_photos ph WHERE ph.employee_id=e.id) AS has_photo
           FROM employees e LEFT JOIN professional_profiles p ON p.employee_id=e.id
           WHERE e.account_active=1 AND COALESCE(p.directory_visible,1)=1 ORDER BY e.name LIMIT 500'''))
        return entries


class NameCorrectionIn(BaseModel):
    requested_value:str = Field(min_length=2,max_length=100)
    reason:str = Field(min_length=6,max_length=450)
    @field_validator('requested_value','reason')
    @classmethod
    def strip_text(cls,value):
        result=value.strip()
        if len(result)<2: raise ValueError('A full name is required')
        return result


@app.get('/api/profile/me/requests')
def own_profile_requests(user=Depends(current_user)):
    with db() as conn:
        return rows(conn.execute('''SELECT id,field_name,requested_value,reason,status,requested_at,
          reviewed_at,review_note FROM profile_change_requests WHERE employee_id=? ORDER BY id DESC LIMIT 100''',(user['id'],)))


@app.post('/api/profile/me/requests',status_code=201)
def request_name_correction(body:NameCorrectionIn,user=Depends(current_user)):
    with db() as conn:
        if conn.execute("SELECT 1 FROM profile_change_requests WHERE employee_id=? AND field_name='name' AND status='Pending'",(user['id'],)).fetchone():
            raise HTTPException(409,'You already have a pending name correction')
        if body.requested_value.lower()==user['name'].lower():
            raise HTTPException(422,'Requested name is unchanged')
        item=conn.execute('''INSERT INTO profile_change_requests(employee_id,field_name,requested_value,reason,status,requested_at)
                VALUES(?,?,?,?,?,?)''',(user['id'],'name',body.requested_value,body.reason,'Pending',utcnow()))
        audit(conn,user['id'],'profile.correction.requested',f'profile_change_request:{item.lastrowid}','name')
        return {'id':item.lastrowid,'status':'Pending'}


@app.get('/api/profile/admin/requests')
def profile_requests_for_hr(user=Depends(require_hr)):
    with db() as conn:
        return rows(conn.execute('''SELECT r.id,r.employee_id,e.name AS employee_name,e.email AS employee_email,
          r.field_name,r.requested_value,r.reason,r.status,r.requested_at,
          r.reviewed_at,r.review_note FROM profile_change_requests r
          JOIN employees e ON e.id=r.employee_id ORDER BY r.id DESC LIMIT 200'''))


class CorrectionDecision(BaseModel):
    decision:Literal['Approved','Rejected']
    review_note:str=Field(default='',max_length=450)


@app.post('/api/profile/admin/requests/{request_id}/decision')
def decide_profile_correction(request_id:int,body:CorrectionDecision,user=Depends(require_hr)):
    with db() as conn:
        request=conn.execute('SELECT * FROM profile_change_requests WHERE id=?',(request_id,)).fetchone()
        if not request: raise HTTPException(404,'Request not found')
        if request['status']!='Pending':raise HTTPException(409,'Request already reviewed')
        if request['employee_id']==user['id']:raise HTTPException(403,'Administrators cannot approve their own name corrections')
        if body.decision=='Rejected' and len(body.review_note.strip())<5:
            raise HTTPException(422,'Rejection requires a review note')
        # Conditional update prevents two concurrent reviewers from both deciding the same request.
        updated=conn.execute('''UPDATE profile_change_requests SET status=?,reviewed_by=?,reviewed_at=?,review_note=?
          WHERE id=? AND status='Pending' ''',(body.decision,user['id'],utcnow(),body.review_note.strip(),request_id))
        if updated.rowcount!=1:raise HTTPException(409,'Request already reviewed')
        if body.decision=='Approved':
            conn.execute('UPDATE employees SET name=? WHERE id=?',(request['requested_value'],request['employee_id']))
        audit(conn,user['id'],'profile.correction.'+body.decision.lower(),f'profile_change_request:{request_id}','name')
        inform(conn,request['employee_id'],'Profile correction reviewed',f'Your official name correction was {body.decision.lower()}.')
        return {'status':body.decision,'request_id':request_id}


@app.get('/api/profile/admin/overview')
def profile_admin_overview(user=Depends(require_hr)):
    with db() as conn:
        members=rows(conn.execute('''SELECT e.id,e.name,e.code,e.email,e.role,e.designation,e.department,e.location,
          e.account_active,COALESCE(p.preferred_name,'') AS preferred_name,
          COALESCE(p.headline,'') AS headline,COALESCE(p.work_phone,'') AS work_phone,
          COALESCE(p.directory_visible,1) AS directory_visible,
          COALESCE(p.updated_at,'') AS profile_updated_at
          FROM employees e LEFT JOIN professional_profiles p ON p.employee_id=e.id
          ORDER BY e.name LIMIT 500'''))
        # Overview intentionally omits private contact fields, bio, passwords and preferences.
        return members
