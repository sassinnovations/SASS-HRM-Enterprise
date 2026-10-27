"""Real-organization setup, company details and transactional HRIS employee import.

No demonstration records, default credentials or external side effects are created.
"""
from __future__ import annotations

import os
import re
import secrets
import sqlite3
from datetime import date, datetime, timezone, timedelta
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from main import app, db, audit, hash_password, require_hr, DB_ENGINE


@app.on_event('startup')
def create_organization_profile_table():
    with db() as conn:
        conn.executescript('''CREATE TABLE IF NOT EXISTS organization_profile (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, legal_name TEXT NOT NULL,
            country TEXT NOT NULL, timezone TEXT NOT NULL, contact_email TEXT NOT NULL,
            website TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL,
            updated_by INTEGER NOT NULL);
        ''')


class CompanyProfile(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    legal_name: str = Field(min_length=2, max_length=180)
    country: str = Field(min_length=2, max_length=80)
    timezone: str = Field(min_length=3, max_length=80)
    contact_email: str = Field(min_length=6, max_length=180)
    website: str = Field(default='', max_length=250)


EMAIL = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
CODE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{1,39}$')


def validate_company(body: CompanyProfile):
    if not EMAIL.fullmatch(body.contact_email.strip()):
        raise HTTPException(422, 'A valid organization contact email is required')
    if body.website and not (body.website.startswith('https://') and '.' in body.website[8:]):
        raise HTTPException(422, 'Website must use an https:// URL')
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo(body.timezone)
    except Exception:
        raise HTTPException(422, 'Use a recognized IANA timezone, such as Asia/Kolkata')


@app.get('/api/admin/organization-profile')
def get_company_profile(user=Depends(require_hr)):
    with db() as conn:
        record=conn.execute('SELECT name, legal_name, country, timezone, contact_email, website, updated_at FROM organization_profile WHERE id=1').fetchone()
    return dict(record) if record else None


@app.put('/api/admin/organization-profile')
def save_company_profile(body:CompanyProfile,user=Depends(require_hr)):
    validate_company(body)
    now=datetime.now(timezone.utc).isoformat()
    values=(body.name.strip(),body.legal_name.strip(),body.country.strip(),body.timezone.strip(),body.contact_email.strip().lower(),body.website.strip(),now,user['id'])
    with db() as conn:
        record=conn.execute('SELECT 1 FROM organization_profile WHERE id=1').fetchone()
        if record:
            conn.execute('UPDATE organization_profile SET name=?,legal_name=?,country=?,timezone=?,contact_email=?,website=?,updated_at=?,updated_by=? WHERE id=1',values)
        else:
            conn.execute('INSERT INTO organization_profile(id,name,legal_name,country,timezone,contact_email,website,updated_at,updated_by) VALUES(1,?,?,?,?,?,?,?,?)',values)
        audit(conn,user['id'],'organization.profile.updated','organization:1')
    return {'message':'Organization details saved'}


@app.get('/api/admin/setup/overview')
def setup_overview(user=Depends(require_hr)):
    with db() as conn:
        counts={}
        for name,table in (('employees','employees'),('active_accounts','employees'),('departments','departments'),('leave_types','leave_entitlements'),('policies','policies'),('holidays','holidays'),('skills','skill_catalog')):
            try:
                if name == 'active_accounts':
                    counts[name]=int(conn.execute('SELECT COUNT(*) FROM employees WHERE account_active=1').fetchone()[0])
                else:
                    counts[name]=int(conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0])
            except Exception:
                counts[name]=0
        profile=bool(conn.execute('SELECT 1 FROM organization_profile WHERE id=1').fetchone())
        office_count=int(conn.execute('SELECT COUNT(*) FROM organization_offices WHERE is_active=1').fetchone()[0])
        preferences=bool(conn.execute('SELECT 1 FROM organization_preferences WHERE id=1').fetchone())
    smtp_ready=all(os.getenv(key) for key in ('SMTP_HOST','SMTP_FROM'))
    checks=[
        {'key':'company','label':'Company profile','ready':profile,'hint':'Enter the legal company details and timezone'},
        {'key':'offices','label':'Active office directory','ready':office_count>0,'hint':'Create at least one official office location'},
        {'key':'preferences','label':'Workspace preferences','ready':preferences,'hint':'Set reporting defaults and the financial year'},
        {'key':'departments','label':'Departments','ready':counts['departments']>0,'hint':'Create your actual business units'},
        {'key':'employees','label':'Workforce records','ready':counts['employees']>1,'hint':'Add staff individually or import a reviewed CSV'},
        {'key':'leave','label':'Leave entitlements','ready':counts['leave_types']>0,'hint':'Configure applicable leave categories'},
        {'key':'policies','label':'Published HR policies','ready':counts['policies']>0,'hint':'Publish your approved policies'},
        {'key':'smtp','label':'Employee invitation emails','ready':smtp_ready,'hint':'Configure your SMTP delivery service and test it'},
        {'key':'mysql','label':'MySQL connection','ready':DB_ENGINE=='mysql','hint':'Real SASS HRM must connect to MySQL, never a testing SQLite file'},
    ]
    return {'database_engine':DB_ENGINE,'backend_version':app.version,'checks':checks,'counts':counts,'completed':sum(1 for c in checks if c['ready']), 'total':len(checks)}


class EmployeeImportItem(BaseModel):
    code: str = Field(min_length=2,max_length=40)
    name: str = Field(min_length=2,max_length=100)
    email: str = Field(min_length=6,max_length=200)
    designation: str = Field(min_length=2,max_length=120)
    department: str = Field(min_length=2,max_length=100)
    location: str = Field(min_length=2,max_length=100)
    work_mode: Literal['Remote','Hybrid','On-site'] = 'On-site'
    role: Literal['employee','manager'] = 'employee'
    join_date: date


class EmployeeImportBatch(BaseModel):
    records: list[EmployeeImportItem] = Field(min_length=1,max_length=250)


class EmployeeCommitBatch(EmployeeImportBatch):
    confirm: Literal['IMPORT']


def review_batch(conn,items):
    errors=[]
    known_emails={str(value).lower() for row in conn.execute('SELECT email,work_email FROM employees').fetchall() for value in (row['email'],row['work_email']) if value}
    known_codes={str(x['code']).lower() for x in conn.execute('SELECT code FROM employees').fetchall()}
    departments={str(x['name']).lower() for x in conn.execute('SELECT name FROM departments').fetchall()}
    seen_emails=set()
    seen_codes=set()
    upper_bound=date.today()+timedelta(days=730)
    for number,item in enumerate(items,start=2):
        row_errors=[]
        email=item.email.strip().lower()
        code=item.code.strip()
        if not EMAIL.fullmatch(email):row_errors.append('Invalid email')
        if not CODE.fullmatch(code):row_errors.append('Employee code must use 2-40 letters, digits, dots, hyphens or underscores')
        if email in known_emails or email in seen_emails:row_errors.append('Duplicate employee email')
        if code.lower() in known_codes or code.lower() in seen_codes:row_errors.append('Duplicate employee code')
        if item.department.strip().lower() not in departments:row_errors.append('Department must exist in Organization first')
        if item.join_date < date(1950,1,1) or item.join_date>upper_bound:row_errors.append('Join date outside supported range')
        if row_errors:errors.append({'row':number,'code':code,'issues':row_errors})
        seen_emails.add(email)
        seen_codes.add(code.lower())
    return errors


@app.post('/api/admin/employees/import/preview')
def preview_employee_import(batch:EmployeeImportBatch,user=Depends(require_hr)):
    with db() as conn:
        errors=review_batch(conn,batch.records)
    return {'total':len(batch.records),'valid':len(batch.records)-len(errors),'errors':errors,'can_import':not errors}


@app.post('/api/admin/employees/import/commit',status_code=201)
def commit_employee_import(batch:EmployeeCommitBatch,user=Depends(require_hr)):
    # Entire import is committed as one transaction. There is no partial/unsafe import mode.
    try:
        with db() as conn:
            errors=review_batch(conn,batch.records)
            if errors:
                raise HTTPException(422,detail={'message':'Import validation failed; no rows were saved','errors':errors})
            for item in batch.records:
                raw_password=secrets.token_urlsafe(40)  # Unusable until HR sends a one-time activation invitation.
                conn.execute('''INSERT INTO employees(code,name,email,work_email,role,designation,department,location,work_mode,join_date,manager_id,password_hash,account_active)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                            (item.code.strip(),item.name.strip(),item.email.strip().lower(),item.email.strip().lower(),item.role,item.designation.strip(),item.department.strip(),item.location.strip(),item.work_mode,item.join_date.isoformat(),None,hash_password(raw_password),0))
            audit(conn,user['id'],'employee.imported','employees',f'{len(batch.records)} inactive employee account(s) created via validated import')
    except sqlite3.IntegrityError:
        # A concurrent writer may insert an employee between preview and commit.
        # The context manager rolls back the whole import; no partial staff record remains.
        raise HTTPException(409,'An email or employee code was created concurrently. Reload and validate the CSV again.')
    return {'created':len(batch.records),'message':'Imported staff are inactive until individually invited and activated through Account provisioning.'}
