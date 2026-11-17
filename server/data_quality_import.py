"""HR data-quality import settings and safely previewed employee HRIS imports.

Never overwrites an existing employee, stores uploaded files, or activates imported accounts.
All employee changes are committed in one database transaction after a signed preview.
"""
from __future__ import annotations

import base64
import binascii
import csv
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import sqlite3
import zipfile
from xml.etree import ElementTree
from datetime import date, datetime, timedelta, timezone
from pathlib import PurePath
from typing import Literal

from fastapi import Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field, ValidationError
from main import app, audit, db, hash_password, require_hr, JWT_SECRET
from organization_setup import EmployeeImportItem, review_batch

FIELDS = ('code', 'name', 'email', 'designation', 'department', 'location', 'join_date', 'role', 'work_mode')
REQUIRED = FIELDS[:7]
DEFAULT_MAP = {key: key for key in FIELDS}
ALIASES = {
    'code': ('employee_code', 'staff_code', 'employee id', 'emp id', 'emp_code'),
    'name': ('employee_name', 'official_name', 'full_name', 'full name'),
    'email': ('work_email', 'email_address', 'official_email', 'email id'),
    'designation': ('job_title', 'position', 'job role'),
    'department': ('team', 'business_unit'),
    'location': ('office', 'office_location', 'work_location'),
    'join_date': ('date_of_joining', 'joining_date', 'date of joining', 'doj'),
    'role': ('access_role', 'user_role'),
    'work_mode': ('working_mode', 'work_arrangement'),
}
MAX_BYTES = 10 * 1024 * 1024
MAX_UNCOMPRESSED = 40 * 1024 * 1024


@app.on_event('startup')
def create_quality_import_tables():
    with db() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS hr_data_quality_import_settings (
          id INTEGER PRIMARY KEY,
          mapping_json TEXT NOT NULL,
          duplicate_mode TEXT NOT NULL DEFAULT 'reject',
          date_format TEXT NOT NULL DEFAULT 'YYYY-MM-DD',
          sheet_name TEXT NOT NULL DEFAULT '',
          default_role TEXT NOT NULL DEFAULT 'employee',
          default_work_mode TEXT NOT NULL DEFAULT 'On-site',
          trim_values INTEGER NOT NULL DEFAULT 1,
          skip_blank_rows INTEGER NOT NULL DEFAULT 1,
          max_rows INTEGER NOT NULL DEFAULT 1000,
          updated_by INTEGER NOT NULL REFERENCES employees(id),
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS hr_data_quality_import_history (
          id INTEGER PRIMARY KEY,
          filename TEXT NOT NULL,
          content_sha256 TEXT NOT NULL,
          source_rows INTEGER NOT NULL,
          created_rows INTEGER NOT NULL,
          duplicate_rows INTEGER NOT NULL,
          actor_id INTEGER NOT NULL REFERENCES employees(id),
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_dq_import_history_actor ON hr_data_quality_import_history(actor_id);
        ''')


class ImportSettings(BaseModel):
    mapping: dict[str, str] = Field(default_factory=lambda: DEFAULT_MAP.copy())
    duplicate_mode: Literal['reject', 'skip'] = 'reject'
    date_format: Literal['YYYY-MM-DD', 'DD/MM/YYYY', 'MM/DD/YYYY'] = 'YYYY-MM-DD'
    sheet_name: str = Field(default='', max_length=100)
    default_role: Literal['employee', 'manager'] = 'employee'
    default_work_mode: Literal['On-site', 'Hybrid', 'Remote'] = 'On-site'
    trim_values: bool = True
    skip_blank_rows: bool = True
    max_rows: int = Field(default=1000, ge=1, le=5000)


def validate_settings(s: ImportSettings) -> ImportSettings:
    if set(s.mapping) != set(FIELDS):
        raise HTTPException(422, 'All nine field mappings must be provided.')
    values = [v.strip() for v in s.mapping.values() if v.strip()]
    if any(len(v) > 100 or any(c in v for c in '\r\n\x00') for v in values):
        raise HTTPException(422, 'Column mapping names must be plain text of 100 characters or less.')
    if len({v.casefold() for v in values}) != len(values):
        raise HTTPException(422, 'Two employee fields cannot use the same spreadsheet column.')
    if any(not s.mapping[field].strip() for field in REQUIRED):
        raise HTTPException(422, 'Required employee fields must have a column mapping.')
    if s.sheet_name and ('/' in s.sheet_name or '\\' in s.sheet_name):
        raise HTTPException(422, 'Enter a worksheet name, not a file path.')
    return s


def _get_settings(conn) -> ImportSettings:
    row = conn.execute('SELECT * FROM hr_data_quality_import_settings WHERE id=1').fetchone()
    if not row:
        return ImportSettings()
    try:
        return ImportSettings(mapping=json.loads(row['mapping_json']),
            duplicate_mode=row['duplicate_mode'], date_format=row['date_format'],
            sheet_name=row['sheet_name'], default_role=row['default_role'],
            default_work_mode=row['default_work_mode'], trim_values=bool(row['trim_values']),
            skip_blank_rows=bool(row['skip_blank_rows']), max_rows=int(row['max_rows']))
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(500, 'HR import settings need administrator repair.') from exc


@app.get('/api/admin/data-quality/import/settings')
def get_import_settings(user=Depends(require_hr)):
    with db() as conn:
        return _get_settings(conn).model_dump()


@app.put('/api/admin/data-quality/import/settings')
def save_import_settings(body: ImportSettings, user=Depends(require_hr)):
    settings = validate_settings(body)
    with db() as conn:
        old = _get_settings(conn).model_dump()
        data = settings.model_dump()
        if old != data:
            conn.execute('''INSERT INTO hr_data_quality_import_settings
            (id,mapping_json,duplicate_mode,date_format,sheet_name,default_role,
             default_work_mode,trim_values,skip_blank_rows,max_rows,updated_by,updated_at)
            VALUES (1,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET mapping_json=excluded.mapping_json,
              duplicate_mode=excluded.duplicate_mode,date_format=excluded.date_format,
              sheet_name=excluded.sheet_name,default_role=excluded.default_role,
              default_work_mode=excluded.default_work_mode,trim_values=excluded.trim_values,
              skip_blank_rows=excluded.skip_blank_rows,max_rows=excluded.max_rows,
              updated_by=excluded.updated_by,updated_at=excluded.updated_at''',
            (json.dumps(data['mapping'],sort_keys=True),data['duplicate_mode'],data['date_format'],
             data['sheet_name'],data['default_role'],data['default_work_mode'],
             int(data['trim_values']),int(data['skip_blank_rows']),data['max_rows'],
             user['id'],datetime.now(timezone.utc).isoformat()))
            audit(conn,user['id'],'quality.import.settings_updated','hr-data-import',
                  ','.join(sorted(k for k in data if data[k]!=old[k])))
    return settings.model_dump()


def _filename(request: Request) -> str:
    original = request.headers.get('x-filename', '')
    try:
        from urllib.parse import unquote
        original = unquote(original)
    except Exception:
        pass
    if not original or '/' in original or '\\' in original or '\x00' in original:
        raise HTTPException(422, 'Provide a valid .csv or .xlsx filename.')
    if len(original) > 180 or not original.lower().endswith(('.csv', '.xlsx')):
        raise HTTPException(422, 'Only .csv and .xlsx files are supported (180-character filename limit).')
    return original


async def _upload(request: Request) -> tuple[str, bytes]:
    filename = _filename(request)
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BYTES:
            raise HTTPException(413, 'File is larger than the 10 MB import limit.')
        chunks.append(chunk)
    if size == 0:
        raise HTTPException(422, 'Choose a non-empty CSV or Excel file.')
    return filename, b''.join(chunks)


def _header(value) -> str:
    return str(value or '').strip().casefold()


def _parse_file(filename: str, content: bytes, settings: ImportSettings):
    if filename.lower().endswith('.csv'):
        try:
            raw = content.decode('utf-8-sig',errors='strict')
            reader = csv.reader(io.StringIO(raw, newline=''))
            parsed = iter(reader)
            header = next(parsed, [])
            data = []
            for row in parsed:
                if len(data) >= settings.max_rows:
                    raise HTTPException(413, f'File exceeds the configured {settings.max_rows}-row import limit.')
                data.append(row)
        except (UnicodeDecodeError, csv.Error) as exc:
            raise HTTPException(422, 'CSV must use UTF-8 text and valid CSV formatting.') from exc
    else:
        try:
            if not zipfile.is_zipfile(io.BytesIO(content)):
                raise ValueError('Not a valid XLSX file')
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                if len(z.namelist()) > 2500 or sum(i.file_size for i in z.infolist()) > MAX_UNCOMPRESSED:
                    raise HTTPException(413,'Excel workbook exceeds the safe decompressed-size limit.')
            from openpyxl import load_workbook
            wb = load_workbook(io.BytesIO(content), read_only=True, data_only=False)
            try:
                if settings.sheet_name and settings.sheet_name not in wb.sheetnames:
                    raise HTTPException(422, 'Configured worksheet was not found in this workbook.')
                sheet = wb[settings.sheet_name] if settings.sheet_name else wb.worksheets[0]
                parsed = sheet.iter_rows(values_only=False)
                first = next(parsed, [])
                header = [cell.value for cell in first]
                data = []
                for row in parsed:
                    if len(data) >= settings.max_rows:
                        raise HTTPException(413,f'File exceeds the configured {settings.max_rows}-row import limit.')
                    data.append([('='+str(cell.value) if cell.data_type=='f' else cell.value) for cell in row])
            finally:
                wb.close()
        except HTTPException:
            raise
        except (ImportError, OSError) as exc:
            raise HTTPException(503,'XLSX reading requires the configured openpyxl dependency.') from exc
        except (ValueError, KeyError, EOFError, zipfile.BadZipFile, TypeError, IndexError, ElementTree.ParseError) as exc:
            raise HTTPException(422,'Invalid or unsupported Excel workbook.') from exc
    if not header or len(header) > 100 or not any(str(h or '').strip() for h in header):
        raise HTTPException(422,'Import needs a header row with at most 100 columns.')
    if len({_header(h) for h in header if _header(h)}) != len([h for h in header if _header(h)]):
        raise HTTPException(422,'Spreadsheet contains duplicate column headings.')
    if any(len(str(h or '')) > 100 for h in header):
        raise HTTPException(422,'Column headings must be 100 characters or less.')
    return [str(h or '').strip() for h in header], data


def _date_value(value, mode):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value or '').strip()
    fmt = {'YYYY-MM-DD':'%Y-%m-%d', 'DD/MM/YYYY':'%d/%m/%Y', 'MM/DD/YYYY':'%m/%d/%Y'}[mode]
    try:
        return datetime.strptime(text,fmt).date().isoformat()
    except ValueError:
        return text


def _collect(conn, filename, binary, settings: ImportSettings):
    columns, values = _parse_file(filename,binary,settings)
    names = {_header(v):i for i,v in enumerate(columns)}
    mapping = {}
    for field in FIELDS:
        candidates = [settings.mapping[field]]
        # Default mapping resolves standard aliases automatically; custom mappings are strict.
        if _header(settings.mapping[field]) == field:
            candidates += ALIASES.get(field, ())
        index = next((names[_header(candidate)] for candidate in candidates if _header(candidate) in names),None)
        if index is None and field in REQUIRED:
            raise HTTPException(422, f'Missing required spreadsheet column: {settings.mapping[field]}')
        mapping[field] = index
    known_emails={str(v).casefold() for r in conn.execute('SELECT email,work_email FROM employees') for v in (r['email'],r['work_email']) if v}
    known_codes={str(r['code']).casefold() for r in conn.execute('SELECT code FROM employees')}
    seen_emails=set();seen_codes=set()
    records=[]; errors=[]; duplicates=[]; processed=0
    for row_number,row in enumerate(values,2):
        if len(row) > 100:
            errors.append({'row':row_number,'issues':['Too many columns']});continue
        if settings.skip_blank_rows and not any(v is not None and str(v).strip() for v in row):
            continue
        processed += 1
        payload={}
        invalid_formula=[]
        for field, col in mapping.items():
            value = row[col] if col is not None and col < len(row) else None
            if isinstance(value,str) and value.lstrip().startswith(('=','+','@')):
                invalid_formula.append(field)
            if field=='join_date':
                value = _date_value(value,settings.date_format)
            elif value is not None:
                value = str(value)
                if settings.trim_values:value = value.strip()
            else:
                value = ''
            if field == 'role' and not value:value=settings.default_role
            if field == 'work_mode' and not value:value=settings.default_work_mode
            payload[field]=value
        if invalid_formula:
            errors.append({'row':row_number,'issues':['Spreadsheet formulas are not accepted in: '+', '.join(invalid_formula)]});continue
        try:
            item=EmployeeImportItem.model_validate(payload)
        except ValidationError as exc:
            errors.append({'row':row_number,'issues':[f'{".".join(map(str,e["loc"]))}: {e["msg"]}' for e in exc.errors()][:5]});continue
        code=item.code.casefold(); email=item.email.casefold()
        if code in known_codes or email in known_emails or code in seen_codes or email in seen_emails:
            if settings.duplicate_mode=='skip':
                duplicates.append(row_number)
            else:
                errors.append({'row':row_number,'issues':['Duplicate employee code or work email']})
            continue
        seen_codes.add(code);seen_emails.add(email)
        records.append((row_number,item))
    if processed == 0:
        raise HTTPException(422,'Spreadsheet has no employee rows.')
    # Reuse the canonical HRIS validators: department membership and date constraints.
    for err in review_batch(conn,[item for _,item in records]):
        idx=err['row']-2
        errors.append({'row':records[idx][0],'issues':err['issues']})
    if errors:
        # Validation must be all-or-nothing; never save the valid subset if other rows are invalid.
        records=[]
    return {'columns':columns,'total':processed,'valid':len(records),'skipped':len(duplicates),
            'errors':errors[:100],'error_count':len(errors),'sample':[
              {'row':row_id,'code':x.code,'name':x.name,'department':x.department} for row_id,x in records[:10]]}, records


def _token(uid: int, contents: bytes, settings: ImportSettings) -> str:
    digest=hashlib.sha256(contents).hexdigest()
    config_hash=hashlib.sha256(settings.model_dump_json().encode()).hexdigest()
    expires=int((datetime.now(timezone.utc)+timedelta(minutes=15)).timestamp())
    data=f'{uid}:{digest}:{config_hash}:{expires}'
    encoded=base64.urlsafe_b64encode(data.encode()).decode().rstrip('=')
    mac=hmac.new(JWT_SECRET.encode(),encoded.encode(),hashlib.sha256).hexdigest()
    return encoded+'.'+mac


def _verify_token(token: str, uid: int, contents: bytes, settings: ImportSettings):
    try:
        encoded,signature=token.split('.',1)
        expected=hmac.new(JWT_SECRET.encode(),encoded.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected,signature):raise ValueError()
        data=base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4)).decode().split(':')
        if len(data)!=4 or data[0]!=str(uid):raise ValueError()
        if data[1]!=hashlib.sha256(contents).hexdigest():raise ValueError()
        if data[2]!=hashlib.sha256(settings.model_dump_json().encode()).hexdigest():raise ValueError()
        if int(data[3])<int(datetime.now(timezone.utc).timestamp()):raise ValueError()
    except (ValueError, TypeError, UnicodeDecodeError, binascii.Error) as exc:
        raise HTTPException(409,'Import preview has expired or settings/file changed. Preview the file again.') from exc


@app.post('/api/admin/data-quality/import/columns')
async def inspect_import_columns(request: Request,user=Depends(require_hr)):
    filename,binary=await _upload(request)
    with db() as conn:
        settings=_get_settings(conn)
    columns,rows=_parse_file(filename,binary,settings)
    return {'columns':columns,'file_rows':len(rows),'worksheet':settings.sheet_name or 'First worksheet'}


@app.post('/api/admin/data-quality/import/preview')
async def preview_import(request: Request,user=Depends(require_hr)):
    filename,binary=await _upload(request)
    with db() as conn:
        settings=validate_settings(_get_settings(conn))
        result,_=_collect(conn,filename,binary,settings)
    result['preview_token']=_token(user['id'],binary,settings) if not result['error_count'] and result['valid'] else ''
    return result


@app.post('/api/admin/data-quality/import/commit',status_code=201)
async def commit_import(request: Request,user=Depends(require_hr)):
    if request.headers.get('x-import-confirm')!='IMPORT':
        raise HTTPException(422,'Type IMPORT to confirm employee creation.')
    filename,binary=await _upload(request)
    token=request.headers.get('x-import-preview-token','')
    try:
        with db() as conn:
            settings=validate_settings(_get_settings(conn))
            _verify_token(token,user['id'],binary,settings)
            preview,records=_collect(conn,filename,binary,settings)
            if preview['error_count'] or not records:
                raise HTTPException(409,'Source data changed or validation failed. No employees imported; preview again.')
            for _,item in records:
                password=secrets.token_urlsafe(40)
                conn.execute('''INSERT INTO employees(code,name,email,work_email,role,designation,department,
                  location,work_mode,join_date,manager_id,password_hash,account_active)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                  (item.code.strip(),item.name.strip(),item.email.lower().strip(),item.email.lower().strip(),
                   item.role,item.designation.strip(),item.department.strip(),item.location.strip(),
                   item.work_mode,item.join_date.isoformat(),None,hash_password(password),0))
            stamp=datetime.now(timezone.utc).isoformat()
            conn.execute('''INSERT INTO hr_data_quality_import_history
              (filename,content_sha256,source_rows,created_rows,duplicate_rows,actor_id,created_at)
              VALUES(?,?,?,?,?,?,?)''',
              (filename,hashlib.sha256(binary).hexdigest(),preview['total'],len(records),
               preview['skipped'],user['id'],stamp))
            audit(conn,user['id'],'quality.employee_imported','employees',
                  f'Created {len(records)} inactive employee accounts; duplicate rows skipped {preview["skipped"]}.')
        return {'created':len(records),'skipped':preview['skipped'],'message':'Employees created as inactive accounts. Invite them individually from Account Provisioning.'}
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409,'Employee record changed concurrently. No records imported; preview the file again.') from exc


@app.get('/api/admin/data-quality/import/history')
def import_history(user=Depends(require_hr)):
    with db() as conn:
        return [dict(row) for row in conn.execute('''SELECT id,filename,source_rows,created_rows,
           duplicate_rows,actor_id,created_at FROM hr_data_quality_import_history ORDER BY id DESC LIMIT 50''')]


@app.get('/api/admin/data-quality/import/template.csv')
def import_template(user=Depends(require_hr)):
    with db() as conn:
        settings=_get_settings(conn)
    out=io.StringIO()
    csv.writer(out).writerow([settings.mapping[key] or key for key in FIELDS])
    return Response(out.getvalue(),media_type='text/csv; charset=utf-8',headers={
        'Content-Disposition':'attachment; filename="sass-hrm-employee-import-template.csv"',
        'Cache-Control':'no-store'})
