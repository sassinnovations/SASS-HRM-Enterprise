"""v2.9 professional profiles and HR-governed official identity corrections.

Professional directory information is intentionally separate from private_profiles,
payroll, authentication credentials and HR work-history metadata.
"""
from __future__ import annotations

import re
import json
from datetime import datetime, timezone
from io import BytesIO
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import Depends, HTTPException, Request, Response
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, field_validator
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
        CREATE TABLE IF NOT EXISTS official_work_detail_requests (
          id INTEGER PRIMARY KEY,
          employee_id INTEGER NOT NULL REFERENCES employees(id),
          payload_json TEXT NOT NULL,
          baseline_json TEXT NOT NULL,
          change_reason TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'Pending',
          requested_at TEXT NOT NULL,
          reviewed_by INTEGER REFERENCES employees(id),
          reviewed_at TEXT,
          review_note TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_official_detail_requests_employee ON official_work_detail_requests(employee_id,status);
        CREATE INDEX IF NOT EXISTS idx_official_detail_requests_status ON official_work_detail_requests(status,requested_at);
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


def _text(value, default=''):
    if value is None:
        return default
    return value if isinstance(value, str) else str(value)


def professional_payload(row: dict) -> dict:
    """Always return a JSON object. Missing professional fields stay blank, never null."""
    email = _text(row.get('email'))
    join_date = _text(row.get('join_date'))
    return {
        'id': row.get('id'),
        'code': _text(row.get('code')),
        'name': _text(row.get('name')),
        'email': email,
        'work_email': _text(row.get('work_email')) or email,
        'role': _text(row.get('role')),
        'designation': _text(row.get('designation')),
        'department': _text(row.get('department')),
        'location': _text(row.get('location')),
        'work_mode': _text(row.get('work_mode')),
        'join_date': join_date[:10] if join_date else '',
        'manager_id': row.get('manager_id'),
        'preferred_name': _text(row.get('preferred_name')),
        'headline': _text(row.get('headline')),
        'biography': _text(row.get('biography')),
        'work_phone': _text(row.get('work_phone')),
        'timezone': _text(row.get('timezone'), 'Asia/Kolkata'),
        'language': _text(row.get('language'), 'en'),
        'directory_visible': 0 if row.get('directory_visible') in (0, False, '0') else 1,
        'avatar_color': _text(row.get('avatar_color'), '#3C6DF0') or '#3C6DF0',
        'profile_updated_at': _text(row.get('profile_updated_at') or row.get('updated_at')),
        'has_photo': bool(row.get('has_photo')),
    }


_PROFILE_SQL = '''SELECT e.id,e.code,e.name,e.email,e.work_email,e.role,e.designation,e.department,
          e.location,e.work_mode,e.join_date,e.manager_id,
          COALESCE((SELECT t.tier FROM account_access_tiers t WHERE t.employee_id=e.id LIMIT 1),e.role) AS access_tier,
          COALESCE(p.preferred_name,'') AS preferred_name,
          COALESCE(p.headline,'') AS headline,
          COALESCE(p.biography,'') AS biography,
          COALESCE(p.work_phone,'') AS work_phone,
          COALESCE(p.timezone,'Asia/Kolkata') AS timezone,
          COALESCE(p.language,'en') AS language,
          COALESCE(p.directory_visible,1) AS directory_visible,
          COALESCE(p.avatar_color,e.avatar_color,'#3C6DF0') AS avatar_color,
          COALESCE(p.updated_at,'') AS profile_updated_at,
          EXISTS(SELECT 1 FROM profile_photos ph WHERE ph.employee_id=e.id) AS has_photo
          FROM employees e LEFT JOIN professional_profiles p ON p.employee_id=e.id
          WHERE e.id=?'''
_EMPLOYEE_SQL = '''SELECT e.id,e.code,e.name,e.email,e.work_email,e.role,e.designation,e.department,
          e.location,e.work_mode,e.join_date,e.manager_id,e.avatar_color
          FROM employees e WHERE e.id=?'''


def professional_row(conn,employee_id:int):
    try:
        result=conn.execute(_PROFILE_SQL,(employee_id,)).fetchone()
    except Exception:
        # Older databases may not have the professional-profile tables yet.
        if hasattr(conn,'rollback'):
            conn.rollback()
        result=conn.execute(_EMPLOYEE_SQL,(employee_id,)).fetchone()
    if result is None:
        raise HTTPException(404,'Employee not found')
    return professional_payload(dict(result))


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


# Official employment details: employees and HR Sub-Admins propose changes; an
# HR Administrator reviews them. The existing admin editor remains immediate.
OFFICIAL_FIELDS = ('code','name','work_email','designation','department','location','work_mode','join_date')

class OfficialDetailsRequestIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    code: str = Field(min_length=3,max_length=50)
    name: str = Field(min_length=2,max_length=100)
    work_email: str = Field(min_length=6,max_length=200)
    designation: str = Field(min_length=2,max_length=120)
    department: str = Field(min_length=2,max_length=100)
    location: str = Field(min_length=2,max_length=100)
    work_mode: Literal['Remote','Hybrid','On-site']
    join_date: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    change_reason: str = Field(min_length=6,max_length=450)


def _official_snapshot(row):
    return {key: str(row[key] if row[key] is not None else '')[:10] if key=='join_date' else str(row[key] or '') for key in OFFICIAL_FIELDS}


def _normalize_official_request(body:OfficialDetailsRequestIn):
    from accounts_v25 import EMAIL
    from datetime import date
    values={key:getattr(body,key).strip() if isinstance(getattr(body,key),str) else getattr(body,key) for key in OFFICIAL_FIELDS}
    values['work_email']=values['work_email'].lower()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{2,49}', values['code']):
        raise HTTPException(422,'Invalid employee code')
    if not EMAIL.fullmatch(values['work_email']):
        raise HTTPException(422,'Enter a valid work email')
    if any(len(values[k])<2 for k in ('name','designation','department','location')):
        raise HTTPException(422,'Official work details require at least two characters')
    try:
        date.fromisoformat(values['join_date'])
    except ValueError:
        raise HTTPException(422,'Enter a valid joining date') from None
    return values


@app.get('/api/profile/me/official-change-requests')
def my_official_changes(user=Depends(current_user)):
    with db() as conn:
        results=rows(conn.execute('''SELECT id,payload_json,change_reason,status,requested_at,
          reviewed_at,review_note FROM official_work_detail_requests
          WHERE employee_id=? ORDER BY id DESC LIMIT 50''',(user['id'],)))
    for item in results:
        item['requested_fields']=json.loads(item.pop('payload_json'))
    return results


@app.post('/api/profile/me/official-change-requests',status_code=201)
def propose_official_changes(body:OfficialDetailsRequestIn,user=Depends(current_user)):
    values=_normalize_official_request(body)
    if user['role']=='admin':
        raise HTTPException(403,'HR administrators use Save official details for immediate authorized changes')
    reason=body.change_reason.strip()
    if len(reason)<6:raise HTTPException(422,'Provide a change reason of at least 6 characters')
    with db() as conn:
        row=conn.execute('''SELECT code,name,work_email,designation,department,location,work_mode,join_date
          FROM employees WHERE id=? AND account_active=1''',(user['id'],)).fetchone()
        if row is None:raise HTTPException(404,'Employee account not found')
        existing=_official_snapshot(row)
        requested={key:value for key,value in values.items() if value != existing[key]}
        if not requested:raise HTTPException(422,'Change at least one official field before submitting')
        if conn.execute("SELECT 1 FROM official_work_detail_requests WHERE employee_id=? AND status='Pending' LIMIT 1",(user['id'],)).fetchone():
            raise HTTPException(409,'You already have a pending official-details request')
        result=conn.execute('''INSERT INTO official_work_detail_requests
            (employee_id,payload_json,baseline_json,change_reason,status,requested_at)
            VALUES(?,?,?,?,?,?)''', (user['id'],json.dumps(requested,ensure_ascii=False),
                  json.dumps(existing,ensure_ascii=False),reason,'Pending',utcnow()))
        audit(conn,user['id'],'profile.official_change.requested',f'official_work_detail_request:{result.lastrowid}',
              'Requested fields: '+','.join(requested))
        return {'id':result.lastrowid,'status':'Pending','requested_fields':requested}


@app.get('/api/profile/admin/official-change-requests')
def review_official_changes_list(user=Depends(require_hr)):
    with db() as conn:
        results=rows(conn.execute('''SELECT r.id,r.employee_id,e.name AS employee_name,e.email AS employee_email,
           r.payload_json,r.change_reason,r.status,r.requested_at,r.reviewed_at,r.review_note
           FROM official_work_detail_requests r JOIN employees e ON e.id=r.employee_id
           ORDER BY r.id DESC LIMIT 200'''))
    for item in results:
        item['requested_fields']=json.loads(item.pop('payload_json'))
    return results


@app.post('/api/profile/admin/official-change-requests/{request_id}/decision')
def decide_official_changes(request_id:int,body:CorrectionDecision,user=Depends(require_hr)):
    from accounts_v25 import AccountProfileEdit, apply_official_profile_change
    with db() as conn:
        request=conn.execute('SELECT * FROM official_work_detail_requests WHERE id=?',(request_id,)).fetchone()
        if request is None:raise HTTPException(404,'Official-details request not found')
        if request['status']!='Pending':raise HTTPException(409,'Request has already been reviewed')
        if int(request['employee_id'])==int(user['id']):raise HTTPException(403,'You cannot approve your own official-details request')
        if body.decision=='Rejected' and len(body.review_note.strip())<5:
            raise HTTPException(422,'Rejection requires a review note')
        if body.decision=='Approved':
            row=conn.execute('''SELECT id,code,name,email,work_email,designation,department,location,
              work_mode,join_date FROM employees WHERE id=? AND account_active=1''',(request['employee_id'],)).fetchone()
            if row is None:raise HTTPException(409,'Employee account is inactive or unavailable')
            baseline=json.loads(request['baseline_json'])
            if _official_snapshot(row)!=baseline:
                raise HTTPException(409,'Official details changed since the request was submitted; reject it and ask the employee to resubmit')
            values={**baseline,**json.loads(request['payload_json'])}
            patch=AccountProfileEdit(**{**values,'email':row['email'],'change_reason':request['change_reason']})
            apply_official_profile_change(conn,int(request['employee_id']),patch,user['id'])
        change=conn.execute('''UPDATE official_work_detail_requests SET status=?,reviewed_by=?,reviewed_at=?,review_note=?
            WHERE id=? AND status='Pending' ''', (body.decision,user['id'],utcnow(),body.review_note.strip(),request_id))
        if change.rowcount!=1:raise HTTPException(409,'Already reviewed')
        audit(conn,user['id'],'profile.official_change.'+body.decision.lower(),f'official_work_detail_request:{request_id}',
              'Employee '+str(request['employee_id']))
        inform(conn,int(request['employee_id']),'Official work details reviewed',
               'Your requested official work details were '+body.decision.lower()+'.')
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
