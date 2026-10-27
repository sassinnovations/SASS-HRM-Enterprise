"""Attendance corrections, document register, and HR readiness checks. Legacy BLOB vault is disabled."""
from __future__ import annotations

import base64
import binascii
import hashlib
import re
import os
import socket
import struct
from cryptography.fernet import Fernet, InvalidToken
from datetime import date, datetime, timezone, timedelta
from typing import Literal

from fastapi import Depends, HTTPException, Response
from pydantic import BaseModel, Field, model_validator

from main import app, db, rows, current_user, require_hr, require_manager, audit
from enterprise import inform, now


# A vault is available only with a dedicated encryption key and a live ClamAV
# clamd service. Missing or unreachable services block upload and download.
VAULT_PREFIX=b'SASSENC1:'
def vault_cipher():
    key=os.getenv('VAULT_FERNET_KEY','').strip()
    if not key:
        raise HTTPException(503,'Vault unavailable: VAULT_FERNET_KEY is not configured')
    try: return Fernet(key.encode('ascii'))
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(503,'Vault encryption key is invalid') from exc

def clamd_connect():
    host=os.getenv('VAULT_AV_HOST','').strip()
    if not host:
        raise HTTPException(503,'Vault unavailable: malware scanner is not configured')
    port=int(os.getenv('VAULT_AV_PORT','3310'))
    try:
        sock=socket.create_connection((host,port),timeout=5)
        sock.settimeout(8)
        return sock
    except OSError as exc:
        raise HTTPException(503,'Vault unavailable: malware scanner cannot be reached') from exc

def ensure_secure_vault():
    cipher=vault_cipher()
    with clamd_connect() as sock:
        try:
            sock.sendall(b'zPING\0')
            if b'PONG' not in sock.recv(1024):raise OSError('Invalid scanner health reply')
        except OSError as exc:
            raise HTTPException(503,'Vault malware scanner is not responding') from exc
    return cipher

def scan_file(blob):
    # ClamAV INSTREAM framing (zINSTREAM + uint32 network-order chunks).
    with clamd_connect() as sock:
        try:
            sock.sendall(b'zINSTREAM\0')
            for off in range(0,len(blob),16384):
                chunk=blob[off:off+16384]
                sock.sendall(struct.pack('!I',len(chunk))+chunk)
            sock.sendall(struct.pack('!I',0))
            reply=sock.recv(4096).decode('utf-8','replace')
        except OSError as exc:
            raise HTTPException(503,'Vault scan failed; file was not stored') from exc
    if 'FOUND' in reply:raise HTTPException(422,'Malware scanner rejected this document')
    if 'OK' not in reply:raise HTTPException(503,'Malware scanner did not confirm a clean file')

@app.get('/api/vault/status')
def vault_status(user=Depends(current_user)):
    try:
        ensure_secure_vault()
        return {'enabled':True,'message':'Encrypted document storage and malware scanning are available. Document permissions still apply.'}
    except HTTPException:
        return {'enabled':False,'message':'Vault uploads and downloads require a vault encryption key and a running ClamAV scanner. Contact your administrator.'}

MAX_BYTES = 2 * 1024 * 1024
ALLOWED_TYPES = {
    'application/pdf': ('.pdf',),
    'image/png': ('.png',),
    'image/jpeg': ('.jpg', '.jpeg'),
    'text/plain': ('.txt',),
}


@app.on_event('startup')
def initialize_operations_v09():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS attendance_corrections (
          id INTEGER PRIMARY KEY,
          employee_id INTEGER NOT NULL REFERENCES employees(id),
          work_day TEXT NOT NULL,
          proposed_in TEXT NOT NULL,
          proposed_out TEXT NOT NULL,
          reason TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','Approved','Rejected','Cancelled')),
          created_at TEXT NOT NULL, decided_by INTEGER REFERENCES employees(id),
          decided_at TEXT, decision_note TEXT NOT NULL DEFAULT '');
        CREATE INDEX IF NOT EXISTS idx_corrections_employee ON attendance_corrections(employee_id,status);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_corrections_pending
          ON attendance_corrections(employee_id,work_day) WHERE status='Pending';
        CREATE TABLE IF NOT EXISTS document_vault (
          id INTEGER PRIMARY KEY,
          employee_id INTEGER NOT NULL REFERENCES employees(id),
          uploaded_by INTEGER NOT NULL REFERENCES employees(id),
          filename TEXT NOT NULL, mime_type TEXT NOT NULL,
          category TEXT NOT NULL, byte_count INTEGER NOT NULL,
          sha256 TEXT NOT NULL, contents BLOB NOT NULL,
          created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_document_vault_employee ON document_vault(employee_id,id);
        ''')


def can_view_employee(user, employee_id, conn, allow_manager=False):
    if user['role']=='admin' or user['id']==employee_id:
        return True
    if allow_manager and user['role']=='manager':
        return conn.execute('SELECT 1 FROM employees WHERE id=? AND manager_id=?',
                            (employee_id,user['id'])).fetchone() is not None
    return False


class CorrectionIn(BaseModel):
    work_day:date
    proposed_in:str=Field(pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    proposed_out:str=Field(pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    reason:str=Field(min_length=8,max_length=500)
    @model_validator(mode='after')
    def validate_shift(self):
        if self.proposed_out<=self.proposed_in:
            raise ValueError('Check-out must be later than check-in (same-day shifts only)')
        if self.work_day>date.today() or self.work_day<date.today()-timedelta(days=90):
            raise ValueError('Correction must be within the past 90 days and not in the future')
        return self

class CorrectionDecision(BaseModel):
    decision:Literal['Approved','Rejected']
    note:str=Field(default='',max_length=300)


@app.get('/api/attendance/corrections')
def list_corrections(user=Depends(current_user)):
    with db() as c:
        sql='''SELECT x.id,x.employee_id,x.work_day,x.proposed_in,x.proposed_out,x.reason,
            x.status,x.created_at,x.decided_by,x.decided_at,x.decision_note,
            e.name AS employee_name,e.manager_id
            FROM attendance_corrections x JOIN employees e ON e.id=x.employee_id'''
        if user['role']=='admin':
            return rows(c.execute(sql+' ORDER BY x.id DESC'))
        if user['role']=='manager':
            return rows(c.execute(sql+' WHERE x.employee_id=? OR e.manager_id=? ORDER BY x.id DESC',(user['id'],user['id'])))
        return rows(c.execute(sql+' WHERE x.employee_id=? ORDER BY x.id DESC',(user['id'],)))


@app.post('/api/attendance/corrections',status_code=201)
def request_correction(body:CorrectionIn,user=Depends(current_user)):
    with db() as c:
        existing=c.execute("SELECT id FROM attendance_corrections WHERE employee_id=? AND work_day=? AND status='Pending'",
                           (user['id'],body.work_day.isoformat())).fetchone()
        if existing:raise HTTPException(409,'A correction is already pending for this date')
        result=c.execute('''INSERT INTO attendance_corrections(employee_id,work_day,proposed_in,proposed_out,reason,created_at)
                           VALUES(?,?,?,?,?,?)''',
                         (user['id'],body.work_day.isoformat(),body.proposed_in,body.proposed_out,body.reason.strip(),now()))
        audit(c,user['id'],'attendance.correction_requested',f'correction:{result.lastrowid}')
        return {'id':result.lastrowid,'status':'Pending'}


@app.post('/api/attendance/corrections/{correction_id}/cancel')
def cancel_correction(correction_id:int,user=Depends(current_user)):
    with db() as c:
        item=c.execute('SELECT * FROM attendance_corrections WHERE id=?',(correction_id,)).fetchone()
        if not item:raise HTTPException(404,'Correction not found')
        if item['employee_id']!=user['id']:raise HTTPException(403,'Only the owner can cancel a correction')
        if item['status']!='Pending':raise HTTPException(409,'Only pending corrections can be cancelled')
        c.execute("UPDATE attendance_corrections SET status='Cancelled' WHERE id=?",(correction_id,))
        audit(c,user['id'],'attendance.correction_cancelled',f'correction:{correction_id}')
        return {'status':'Cancelled'}


@app.post('/api/attendance/corrections/{correction_id}/decision')
def decide_correction(correction_id:int,body:CorrectionDecision,user=Depends(require_manager)):
    with db() as c:
        item=c.execute('''SELECT x.*,e.manager_id FROM attendance_corrections x
                          JOIN employees e ON e.id=x.employee_id WHERE x.id=?''',(correction_id,)).fetchone()
        if not item:raise HTTPException(404,'Correction not found')
        if item['employee_id']==user['id']:raise HTTPException(403,'You cannot approve your own attendance')
        if user['role']=='manager' and item['manager_id']!=user['id']:
            raise HTTPException(403,'This employee is not your direct report')
        if item['status']!='Pending':raise HTTPException(409,'Correction already decided')
        if body.decision=='Approved':
            c.execute('''INSERT INTO attendance(employee_id,day,check_in,check_out,status)
              VALUES(?,?,?,?,?) ON CONFLICT(employee_id,day)
              DO UPDATE SET check_in=excluded.check_in,check_out=excluded.check_out,status=excluded.status''',
              (item['employee_id'],item['work_day'],item['proposed_in'],item['proposed_out'],'Present'))
        c.execute('''UPDATE attendance_corrections SET status=?,decided_by=?,decided_at=?,decision_note=? WHERE id=?''',
                  (body.decision,user['id'],now(),body.note.strip(),correction_id))
        inform(c,item['employee_id'],'Attendance correction reviewed',
               f'Your request for {item["work_day"]} was {body.decision.lower()}.')
        audit(c,user['id'],'attendance.correction_decided',f'correction:{correction_id}',body.decision)
        return {'status':body.decision,'attendance_updated':body.decision=='Approved'}


class VaultFileIn(BaseModel):
    employee_id:int=Field(gt=0)
    filename:str=Field(min_length=1,max_length=130)
    mime_type:Literal['application/pdf','image/png','image/jpeg','text/plain']
    category:Literal['Employment','Education','Identity','Payroll','Other']='Other'
    data_base64:str=Field(min_length=4,max_length=3_000_000)


def safe_name(name):
    if name != name.split('/')[-1] or name != name.split('\\')[-1] or any(ord(c)<32 for c in name):
        raise HTTPException(422,'Invalid filename')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 _.()\-]{0,128}',name):
        raise HTTPException(422,'Unsupported filename')
    return name


def validate_document(blob, filename, mime):
    if not blob or len(blob)>MAX_BYTES:raise HTTPException(413,'File must be between 1 byte and 2 MiB')
    if not filename.lower().endswith(ALLOWED_TYPES[mime]):raise HTTPException(422,'Filename and media type mismatch')
    if mime=='application/pdf' and not blob.startswith(b'%PDF-'):raise HTTPException(422,'Invalid PDF header')
    if mime=='image/png' and not blob.startswith(b'\x89PNG\r\n\x1a\n'):raise HTTPException(422,'Invalid PNG header')
    if mime=='image/jpeg' and not blob.startswith(b'\xff\xd8\xff'):raise HTTPException(422,'Invalid JPEG header')
    if mime=='text/plain':
        try:blob.decode('utf-8')
        except UnicodeDecodeError:raise HTTPException(422,'Text files must be UTF-8')
        if b'\x00' in blob:raise HTTPException(422,'Binary text file blocked')


@app.get('/api/vault/files')
def vault_files(user=Depends(current_user)):
    with db() as c:
        sql='''SELECT f.id,f.employee_id,f.uploaded_by,f.filename,f.mime_type,f.category,
            f.byte_count,f.sha256,f.created_at,e.name AS employee_name
            FROM document_vault f JOIN employees e ON e.id=f.employee_id'''
        if user['role']=='admin':return rows(c.execute(sql+' ORDER BY f.id DESC'))
        return rows(c.execute(sql+' WHERE f.employee_id=? ORDER BY f.id DESC',(user['id'],)))


@app.post('/api/vault/files',status_code=201)
def vault_upload(body:VaultFileIn,user=Depends(current_user)):
    cipher=ensure_secure_vault()
    name=safe_name(body.filename)
    try:payload=base64.b64decode(body.data_base64,validate=True)
    except (binascii.Error,ValueError):raise HTTPException(422,'Invalid Base64 content')
    validate_document(payload,name,body.mime_type)
    scan_file(payload)
    protected=VAULT_PREFIX+cipher.encrypt(payload)
    with db() as c:
        if not can_view_employee(user,body.employee_id,c):raise HTTPException(403,'Private files belong to you or HR')
        if not c.execute('SELECT id FROM employees WHERE id=?',(body.employee_id,)).fetchone():raise HTTPException(404,'Employee not found')
        existing=c.execute('SELECT COUNT(*) FROM document_vault WHERE employee_id=?',(body.employee_id,)).fetchone()[0]
        if existing>=30:raise HTTPException(409,'Storage limit: 30 files per employee')
        digest=hashlib.sha256(payload).hexdigest()
        result=c.execute('''INSERT INTO document_vault(employee_id,uploaded_by,filename,mime_type,category,byte_count,sha256,contents,created_at)
                           VALUES(?,?,?,?,?,?,?,?,?)''',
                         (body.employee_id,user['id'],name,body.mime_type,body.category,len(payload),digest,protected,now()))
        audit(c,user['id'],'vault.file_uploaded',f'vault:{result.lastrowid}',f'bytes={len(payload)}')
        return {'id':result.lastrowid,'filename':name,'byte_count':len(payload),'sha256':digest}


@app.get('/api/vault/files/{file_id}/download')
def vault_download(file_id:int,user=Depends(current_user)):
    cipher=ensure_secure_vault()
    with db() as c:
        file=c.execute('SELECT * FROM document_vault WHERE id=?',(file_id,)).fetchone()
        if not file:raise HTTPException(404,'File not found')
        if not can_view_employee(user,file['employee_id'],c):raise HTTPException(403,'Private file access denied')
        payload=bytes(file['contents'])
        if not payload.startswith(VAULT_PREFIX):raise HTTPException(409,'Legacy unencrypted record cannot be downloaded; contact your administrator')
        try: plaintext=cipher.decrypt(payload[len(VAULT_PREFIX):])
        except InvalidToken:raise HTTPException(409,'Unable to decrypt this file; contact your administrator')
        audit(c,user['id'],'vault.file_downloaded',f'vault:{file_id}')
        return Response(content=plaintext,media_type='application/octet-stream',headers={
          'Content-Disposition':f'attachment; filename="{file["filename"]}"',
          'X-Content-Type-Options':'nosniff','Cache-Control':'no-store'})


@app.delete('/api/vault/files/{file_id}')
def vault_delete(file_id:int,user=Depends(current_user)):
    ensure_secure_vault()
    with db() as c:
        file=c.execute('SELECT * FROM document_vault WHERE id=?',(file_id,)).fetchone()
        if not file:raise HTTPException(404,'File not found')
        if not can_view_employee(user,file['employee_id'],c):raise HTTPException(403,'Private file access denied')
        c.execute('DELETE FROM document_vault WHERE id=?',(file_id,))
        audit(c,user['id'],'vault.file_deleted',f'vault:{file_id}')
        return {'deleted':True}


@app.get('/api/admin/readiness')
def readiness(user=Depends(require_hr)):
    with db() as c:
        def count(sql,*args):return c.execute(sql,args).fetchone()[0]
        active=count('SELECT COUNT(*) FROM employees WHERE account_active=1')
        missing_pay=count('''SELECT COUNT(*) FROM employees e LEFT JOIN salary_packages s ON s.employee_id=e.id
                           WHERE e.account_active=1 AND s.employee_id IS NULL''')
        orphan_managers=count('''SELECT COUNT(*) FROM employees e LEFT JOIN employees m ON m.id=e.manager_id
                             WHERE e.account_active=1 AND e.role='employee'
                               AND (e.manager_id IS NULL OR m.account_active=0 OR m.id IS NULL)''')
        unsigned=count('''SELECT COUNT(*) FROM employees e CROSS JOIN policies p
          LEFT JOIN policy_acknowledgements a ON a.employee_id=e.id AND a.policy_id=p.id AND a.revision=p.revision
          WHERE e.account_active=1 AND a.id IS NULL''')
        pending_corrections=count("SELECT COUNT(*) FROM attendance_corrections WHERE status='Pending'")
        open_tickets=count("SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress')")
        pending_expenses=count("SELECT COUNT(*) FROM expenses WHERE status='Pending'")
        open_onboarding=count("SELECT COUNT(*) FROM onboarding WHERE status NOT IN ('Completed')")
        summary=[
          {'key':'salary','title':'Salary package setup','count':missing_pay,'route':'payrollengine','detail':'Active employees without a configured salary package'},
          {'key':'reporting','title':'Reporting line quality','count':orphan_managers,'route':'employees','detail':'Active employees without an active reporting manager'},
          {'key':'policies','title':'Unacknowledged policies','count':unsigned,'route':'compliance','detail':'Current policy revisions not yet acknowledged by active employees'},
          {'key':'attendance','title':'Attendance corrections awaiting approval','count':pending_corrections,'route':'corrections','detail':'Pending time record changes'},
          {'key':'tickets','title':'Open HR support tickets','count':open_tickets,'route':'helpdesk','detail':'Support tickets needing attention'},
          {'key':'expenses','title':'Expense approvals awaiting review','count':pending_expenses,'route':'expenses','detail':'Pending reimbursement approvals'},
          {'key':'onboarding','title':'Incomplete onboarding tasks','count':open_onboarding,'route':'onboarding','detail':'Employee joining tasks not completed'},
        ]
        return {'active_employees':active,'issues':summary,'total_open_items':sum(x['count'] for x in summary),
                'disclaimer':'Operational checks are not a legal, regulatory or security compliance audit.'}
