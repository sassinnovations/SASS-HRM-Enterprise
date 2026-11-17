"""Auditable asset register: required descriptions, condition checks, warranty and maintenance.

No employee monitoring, device tracking, or financial disclosure to non-HR users.
All writes are role-checked, parameterized and committed with the core asset record.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from main import app, db, current_user, require_hr, audit, rows, DB_ENGINE


def timestamp():
    return datetime.now(timezone.utc).isoformat()


@app.on_event('startup')
def initialize_asset_registry():
    # MySQL uses server/mysql_schema.sql. These declarations support isolated SQLite tests.
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS asset_profiles (
          asset_id INTEGER PRIMARY KEY, category TEXT NOT NULL, description TEXT NOT NULL,
          manufacturer TEXT NOT NULL DEFAULT '', model TEXT NOT NULL DEFAULT '',
          asset_tag TEXT UNIQUE, condition_label TEXT NOT NULL, storage_location TEXT NOT NULL,
          purchase_date TEXT, purchase_amount NUMERIC, warranty_expiry TEXT,
          supplier_name TEXT NOT NULL DEFAULT '', invoice_number TEXT NOT NULL DEFAULT '',
          accessories TEXT NOT NULL DEFAULT '', internal_notes TEXT NOT NULL DEFAULT '',
          updated_by INTEGER NOT NULL, updated_at TEXT NOT NULL,
          FOREIGN KEY(asset_id) REFERENCES assets(id), FOREIGN KEY(updated_by) REFERENCES employees(id));
        CREATE INDEX IF NOT EXISTS idx_asset_profiles_category ON asset_profiles(category,condition_label);
        CREATE TABLE IF NOT EXISTS asset_inspections (
          id INTEGER PRIMARY KEY, asset_id INTEGER NOT NULL, inspector_id INTEGER NOT NULL,
          inspected_on TEXT NOT NULL, condition_label TEXT NOT NULL,
          working_ok INTEGER NOT NULL, accessories_ok INTEGER NOT NULL, security_ok INTEGER NOT NULL,
          note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
          FOREIGN KEY(asset_id) REFERENCES assets(id), FOREIGN KEY(inspector_id) REFERENCES employees(id));
        CREATE INDEX IF NOT EXISTS idx_asset_inspections_asset ON asset_inspections(asset_id,inspected_on);
        CREATE TABLE IF NOT EXISTS asset_maintenance_requests (
          id INTEGER PRIMARY KEY, asset_id INTEGER NOT NULL, employee_id INTEGER,
          maintenance_kind TEXT NOT NULL, severity TEXT NOT NULL DEFAULT 'Medium',
          request_status TEXT NOT NULL DEFAULT 'Open', reported_by INTEGER NOT NULL,
          assigned_to INTEGER, completed_at TEXT, created_at TEXT NOT NULL,
          FOREIGN KEY(asset_id) REFERENCES assets(id), FOREIGN KEY(employee_id) REFERENCES employees(id),
          FOREIGN KEY(reported_by) REFERENCES employees(id), FOREIGN KEY(assigned_to) REFERENCES employees(id));
        CREATE INDEX IF NOT EXISTS idx_asset_maintenance_asset ON asset_maintenance_requests(asset_id,created_at);
        CREATE INDEX IF NOT EXISTS idx_asset_maintenance_status ON asset_maintenance_requests(request_status,severity);
        ''')


class AssetProfileIn(BaseModel):
    asset_name: str = Field(min_length=2, max_length=120)
    category: Literal['Laptop','Desktop','Mobile','Monitor','Network equipment','Peripheral','Furniture','Access card','Other']
    description: str = Field(min_length=10, max_length=1500)
    manufacturer: str = Field(default='',max_length=120)
    model: str = Field(default='',max_length=120)
    asset_tag: str | None = Field(default=None,max_length=80)
    condition_label: Literal['New','Good','Fair','Damaged','Needs repair']
    storage_location: str = Field(min_length=2,max_length=191)
    purchase_date: date | None = None
    purchase_amount: Decimal | None = Field(default=None,ge=0,le=9999999999)
    warranty_expiry: date | None = None
    supplier_name: str = Field(default='',max_length=150)
    invoice_number: str = Field(default='',max_length=120)
    accessories: str = Field(default='',max_length=1000)
    internal_notes: str = Field(default='',max_length=1500)

    @model_validator(mode='after')
    def validate_information(self):
        if not self.asset_name.strip() or not self.description.strip() or not self.storage_location.strip():
            raise ValueError('Asset name, detailed description and location are required')
        if self.purchase_date and self.warranty_expiry and self.warranty_expiry < self.purchase_date:
            raise ValueError('Warranty expiry cannot precede the purchase date')
        return self


class AssetRegisterIn(AssetProfileIn):
    employee_id: int = Field(gt=0)
    serial_number: str = Field(min_length=3,max_length=100)

    @model_validator(mode='after')
    def validate_serial(self):
        if len(self.serial_number.strip()) < 3:
            raise ValueError('A real serial number of at least three characters is required')
        return self


class AssetEditIn(AssetProfileIn):
    reason: str = Field(min_length=8,max_length=300)

    @model_validator(mode='after')
    def validate_reason(self):
        if len(self.reason.strip()) < 8:
            raise ValueError('Provide a meaningful reason for changing an asset record')
        return self


class AssetInspectionIn(BaseModel):
    inspected_on: date
    condition_label: Literal['New','Good','Fair','Damaged','Needs repair']
    working_ok: bool
    accessories_ok: bool
    security_ok: bool
    note: str = Field(min_length=5,max_length=1000)

    @model_validator(mode='after')
    def valid_inspection(self):
        if self.inspected_on > date.today():
            raise ValueError('Inspection date cannot be in the future')
        if len(self.note.strip()) < 5:
            raise ValueError('An inspection note is required')
        return self


class AssetMaintenanceIn(BaseModel):
    maintenance_kind: str = Field(min_length=5,max_length=80)
    severity: Literal['Low','Medium','High','Critical'] = 'Medium'

    @model_validator(mode='after')
    def valid_maintenance(self):
        if len(self.maintenance_kind.strip()) < 5:
            raise ValueError('Describe the maintenance issue')
        return self


class AssetMaintenanceStatusIn(BaseModel):
    request_status: Literal['Open','In Progress','Resolved','Cancelled']


PROFILE_COLUMNS = ('category','description','manufacturer','model','asset_tag','condition_label',
                   'storage_location','purchase_date','purchase_amount','warranty_expiry','supplier_name',
                   'invoice_number','accessories','internal_notes')
PRIVATE_COLUMNS = {'purchase_amount','supplier_name','invoice_number','internal_notes'}


def profile_values(body: AssetProfileIn):
    result=[]
    for k in PROFILE_COLUMNS:
        val=getattr(body,k)
        if isinstance(val,date): val=val.isoformat()
        if isinstance(val,Decimal): val=float(val)
        if isinstance(val,str): val=val.strip()
        if k=='asset_tag' and not val: val=None
        result.append(val)
    return result


def asset_for(c, asset_id, user):
    asset=c.execute('SELECT * FROM assets WHERE id=?',(asset_id,)).fetchone()
    if not asset: raise HTTPException(404,'Asset not found')
    if user['role']!='admin' and asset['employee_id']!=user['id']:
        raise HTTPException(403,'This asset is outside your authorized custody')
    return asset


def profile_public(row, user):
    value=dict(row)
    if user['role']!='admin':
        for field in PRIVATE_COLUMNS: value.pop(field,None)
    return value


@app.get('/api/assets/registry')
def asset_registry(user=Depends(current_user)):
    clause,args=('',[]) if user['role']=='admin' else (' WHERE a.employee_id=?',[user['id']])
    with db() as c:
        records=rows(c.execute('''SELECT a.*, e.name AS employee_name, p.*
          FROM assets a JOIN employees e ON e.id=a.employee_id
          LEFT JOIN asset_profiles p ON p.asset_id=a.id'''+clause+' ORDER BY a.id DESC', args))
        return [profile_public(record,user) for record in records]


@app.post('/api/assets/register', status_code=201)
def register_asset(body:AssetRegisterIn,user=Depends(require_hr)):
    with db() as c:
        exists=c.execute('SELECT id FROM employees WHERE id=? AND account_active=1',(body.employee_id,)).fetchone()
        if not exists: raise HTTPException(422,'Choose an active employee')
        if c.execute('SELECT id FROM assets WHERE serial_number=?',(body.serial_number.strip(),)).fetchone():
            raise HTTPException(409,'Serial number already exists')
        if body.asset_tag and c.execute('SELECT asset_id FROM asset_profiles WHERE asset_tag=?',(body.asset_tag.strip(),)).fetchone():
            raise HTTPException(409,'Asset tag already exists')
        try:
            r=c.execute('INSERT INTO assets(employee_id,asset_name,serial_number,assigned_at) VALUES(?,?,?,?)',
                        (body.employee_id,body.asset_name.strip(),body.serial_number.strip(),date.today().isoformat()))
            c.execute('''INSERT INTO asset_profiles (asset_id,'''+','.join(PROFILE_COLUMNS)+''',updated_by,updated_at)
                VALUES ('''+','.join('?' for _ in range(len(PROFILE_COLUMNS)+3))+')',
                (r.lastrowid,*profile_values(body),user['id'],timestamp()))
        except Exception as exc:
            if isinstance(exc,sqlite3.IntegrityError) or 'duplicate entry' in str(exc).lower() or 'unique constraint' in str(exc).lower():
                raise HTTPException(409,'Serial number or asset tag already exists') from exc
            raise
        c.execute('''INSERT INTO asset_lifecycle_events(asset_id,actor_id,event_type,from_employee_id,to_employee_id,note,created_at)
                     VALUES(?,?,?,?,?,?,?)''',(r.lastrowid,user['id'],'Assigned',None,body.employee_id,'Initial assignment',timestamp()))
        audit(c,user['id'],'asset.registered',f'asset:{r.lastrowid}',f'{body.category}; {body.serial_number.strip()}')
        return {'id':r.lastrowid,'status':'Assigned'}


@app.patch('/api/assets/{asset_id}/profile')
def update_asset_profile(asset_id:int,body:AssetEditIn,user=Depends(require_hr)):
    with db() as c:
        asset=asset_for(c,asset_id,user)
        if body.asset_tag and c.execute('SELECT asset_id FROM asset_profiles WHERE asset_tag=? AND asset_id<>?',
                                        (body.asset_tag.strip(),asset_id)).fetchone():
            raise HTTPException(409,'Asset tag already exists')
        c.execute('UPDATE assets SET asset_name=? WHERE id=?',(body.asset_name.strip(),asset_id))
        current=c.execute('SELECT asset_id FROM asset_profiles WHERE asset_id=?',(asset_id,)).fetchone()
        if current:
            c.execute('UPDATE asset_profiles SET '+','.join(f'{k}=?' for k in PROFILE_COLUMNS)+',updated_by=?,updated_at=? WHERE asset_id=?',
                      (*profile_values(body),user['id'],timestamp(),asset_id))
        else:
            c.execute('INSERT INTO asset_profiles (asset_id,'+','.join(PROFILE_COLUMNS)+',updated_by,updated_at) VALUES ('+
                      ','.join('?' for _ in range(len(PROFILE_COLUMNS)+3))+')',
                      (asset_id,*profile_values(body),user['id'],timestamp()))
        c.execute('''INSERT INTO asset_lifecycle_events(asset_id,actor_id,event_type,from_employee_id,to_employee_id,note,created_at)
                     VALUES(?,?,?,?,?,?,?)''',(asset_id,user['id'],'Details updated',asset['employee_id'],asset['employee_id'],body.reason.strip(),timestamp()))
        audit(c,user['id'],'asset.profile.updated',f'asset:{asset_id}',body.reason.strip())
        return {'id':asset_id,'saved':True}


@app.get('/api/assets/{asset_id}/inspections')
def list_asset_inspections(asset_id:int,user=Depends(current_user)):
    with db() as c:
        asset_for(c,asset_id,user)
        result=rows(c.execute('''SELECT id,asset_id,inspected_on,condition_label,working_ok,accessories_ok,security_ok,note,created_at
              FROM asset_inspections WHERE asset_id=? ORDER BY inspected_on DESC,id DESC''',(asset_id,)))
        if user['role']!='admin':
            for item in result: item.pop('note',None)
        return result


@app.post('/api/assets/{asset_id}/inspections',status_code=201)
def inspect_asset(asset_id:int,body:AssetInspectionIn,user=Depends(require_hr)):
    with db() as c:
        asset_for(c,asset_id,user)
        r=c.execute('''INSERT INTO asset_inspections(asset_id,inspector_id,inspected_on,condition_label,
                   working_ok,accessories_ok,security_ok,note,created_at) VALUES(?,?,?,?,?,?,?,?,?)''',
            (asset_id,user['id'],body.inspected_on.isoformat(),body.condition_label,int(body.working_ok),
             int(body.accessories_ok),int(body.security_ok),body.note.strip(),timestamp()))
        c.execute('UPDATE asset_profiles SET condition_label=?,updated_by=?,updated_at=? WHERE asset_id=?',
                  (body.condition_label,user['id'],timestamp(),asset_id))
        audit(c,user['id'],'asset.inspected',f'asset:{asset_id}',f'Inspection {r.lastrowid}: {body.condition_label}')
        return {'id':r.lastrowid,'condition':body.condition_label}


@app.get('/api/assets/{asset_id}/maintenance')
def list_asset_maintenance(asset_id:int,user=Depends(current_user)):
    with db() as c:
        asset_for(c,asset_id,user)
        return rows(c.execute('''SELECT id,asset_id,maintenance_kind,severity,request_status,created_at,completed_at
                                FROM asset_maintenance_requests WHERE asset_id=? ORDER BY id DESC''',(asset_id,)))


@app.post('/api/assets/{asset_id}/maintenance',status_code=201)
def report_asset_maintenance(asset_id:int,body:AssetMaintenanceIn,user=Depends(current_user)):
    with db() as c:
        asset=asset_for(c,asset_id,user)
        if asset['status']=='Returned':raise HTTPException(409,'Returned equipment cannot be reported by the former custodian')
        r=c.execute('''INSERT INTO asset_maintenance_requests(asset_id,employee_id,maintenance_kind,severity,
                      request_status,reported_by,created_at) VALUES(?,?,?,?,?,?,?)''',
                    (asset_id,asset['employee_id'],body.maintenance_kind.strip(),body.severity,'Open',user['id'],timestamp()))
        audit(c,user['id'],'asset.maintenance.requested',f'asset:{asset_id}',f'Maintenance case {r.lastrowid}')
        return {'id':r.lastrowid,'status':'Open'}


@app.patch('/api/assets/maintenance/{request_id}')
def decide_asset_maintenance(request_id:int,body:AssetMaintenanceStatusIn,user=Depends(require_hr)):
    with db() as c:
        request=c.execute('SELECT * FROM asset_maintenance_requests WHERE id=?'+(' FOR UPDATE' if DB_ENGINE=='mysql' else ''),
                          (request_id,)).fetchone()
        if not request:raise HTTPException(404,'Maintenance request not found')
        old=request['request_status']
        if old in ('Resolved','Cancelled') and old!=body.request_status:
            raise HTTPException(409,'Closed requests cannot be reopened')
        allowed={'Open':{'Open','In Progress','Cancelled','Resolved'},'In Progress':{'In Progress','Resolved','Cancelled'},
                 'Resolved':{'Resolved'},'Cancelled':{'Cancelled'}}
        if body.request_status not in allowed.get(old,set()):
            raise HTTPException(409,'Invalid maintenance status transition')
        completed=timestamp() if body.request_status in ('Resolved','Cancelled') else None
        c.execute('UPDATE asset_maintenance_requests SET request_status=?,completed_at=? WHERE id=?',
                  (body.request_status,completed,request_id))
        audit(c,user['id'],'asset.maintenance.updated',f'asset:{request["asset_id"]}',
              f'Maintenance case {request_id}: {old} -> {body.request_status}')
        return {'id':request_id,'status':body.request_status}
