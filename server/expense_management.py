"""SASS HRM expense claim settings, evidence metadata and reimbursement ledger.

Claim records are scoped to owners and HR. Reimbursement recording is *not*
execution of a transfer, bank integration, or certification of a payment.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from main import app, audit, current_user, db, require_hr


def clock():
    return datetime.now(timezone.utc).isoformat()


CATEGORIES = ('Travel', 'Connectivity', 'Meals', 'Equipment', 'Other')


class ExpensePolicy(BaseModel):
    model_config = ConfigDict(extra='forbid')
    allowed_categories: list[Literal['Travel','Connectivity','Meals','Equipment','Other']] = Field(default_factory=lambda: list(CATEGORIES), min_length=1)
    max_claim_amount: int = Field(default=500000, ge=1, le=500000)
    submission_window_days: int = Field(default=180, ge=1, le=1095)
    receipt_required: bool = False
    receipt_threshold: int = Field(default=1000, ge=0, le=500000)
    business_purpose_required: bool = False
    allow_employee_edits: bool = True
    allow_withdrawals: bool = True
    guidance: str = Field(default='Submit only genuine business expenses. HR approval does not initiate reimbursement.', max_length=500)

    @model_validator(mode='after')
    def unique_categories(self):
        if len(set(self.allowed_categories)) != len(self.allowed_categories):
            raise ValueError('Expense categories must be unique')
        return self


DEFAULTS = ExpensePolicy().model_dump()


@app.on_event('startup')
def init_expense_management():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS expense_policy_settings (
            id INTEGER PRIMARY KEY, settings_json TEXT NOT NULL,
            updated_at TEXT NOT NULL, updated_by INTEGER,
            FOREIGN KEY(updated_by) REFERENCES employees(id));
        CREATE TABLE IF NOT EXISTS expense_claim_details (
            expense_id INTEGER PRIMARY KEY, expense_date TEXT NOT NULL,
            merchant TEXT NOT NULL DEFAULT '', business_purpose TEXT NOT NULL DEFAULT '',
            cost_center TEXT NOT NULL DEFAULT '', receipt_reference TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            FOREIGN KEY(expense_id) REFERENCES expenses(id));
        CREATE TABLE IF NOT EXISTS expense_claim_events (
            id INTEGER PRIMARY KEY, expense_id INTEGER NOT NULL, actor_id INTEGER NOT NULL,
            event_type TEXT NOT NULL, event_note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(expense_id) REFERENCES expenses(id),
            FOREIGN KEY(actor_id) REFERENCES employees(id));
        CREATE INDEX IF NOT EXISTS idx_expense_claim_events_expense ON expense_claim_events(expense_id);
        CREATE TABLE IF NOT EXISTS expense_reimbursement_records (
            id INTEGER PRIMARY KEY, expense_id INTEGER NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'Scheduled',
            external_payment_reference TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '', updated_by INTEGER NOT NULL, updated_at TEXT NOT NULL,
            FOREIGN KEY(expense_id) REFERENCES expenses(id),
            FOREIGN KEY(updated_by) REFERENCES employees(id));
        CREATE INDEX IF NOT EXISTS idx_expense_reimbursement_status ON expense_reimbursement_records(status);
        ''')


def read_policy(c):
    row = c.execute('SELECT settings_json,updated_at,updated_by FROM expense_policy_settings WHERE id=1').fetchone()
    if not row:
        return {'settings':DEFAULTS.copy(),'updated_at':None,'updated_by':None,'source':'defaults'}
    saved = json.loads(row['settings_json'])
    policy = ExpensePolicy(**{**DEFAULTS, **saved})
    return {'settings':policy.model_dump(),'updated_at':row['updated_at'],'updated_by':row['updated_by'],'source':'organization'}


@app.get('/api/expenses/policy')
def get_expense_policy(user=Depends(current_user)):
    with db() as c:
        return read_policy(c)


@app.put('/api/expenses/policy')
def put_expense_policy(body:ExpensePolicy, user=Depends(require_hr)):
    with db() as c:
        previous = read_policy(c)['settings']
        values = body.model_dump()
        values['guidance'] = values['guidance'].strip()
        if values == previous:
            return read_policy(c)
        when = clock()
        payload = json.dumps(values, separators=(',',':'))
        existing = c.execute('SELECT id FROM expense_policy_settings WHERE id=1').fetchone()
        if existing:
            c.execute('UPDATE expense_policy_settings SET settings_json=?,updated_at=?,updated_by=? WHERE id=1', (payload,when,user['id']))
        else:
            c.execute('INSERT INTO expense_policy_settings(id,settings_json,updated_at,updated_by) VALUES(1,?,?,?)', (payload,when,user['id']))
        changed = ','.join(sorted(k for k in values if previous[k] != values[k]))
        audit(c,user['id'],'expenses.policy.updated','expense_policy:1',changed)
        return read_policy(c)


class ClaimDetails(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=3,max_length=150)
    amount: float = Field(gt=0,le=500000,allow_inf_nan=False)
    category: Literal['Travel','Connectivity','Meals','Equipment','Other'] = 'Other'
    expense_date: date | None = None
    merchant: str = Field(default='', max_length=150)
    business_purpose: str = Field(default='', max_length=1000)
    cost_center: str = Field(default='', max_length=80)
    receipt_reference: str = Field(default='', max_length=240)


class ClaimEdit(ClaimDetails):
    reason: str = Field(min_length=8,max_length=300)


def validated_claim(body:ClaimDetails, policy:dict):
    day = body.expense_date or date.today()
    if day > date.today():
        raise HTTPException(422,'Expense date cannot be in the future')
    if day < date.today() - timedelta(days=policy['submission_window_days']):
        raise HTTPException(422,'Expense date is outside the configured submission window')
    if body.category not in policy['allowed_categories']:
        raise HTTPException(422,'Expense category is disabled by company policy')
    amount = Decimal(str(body.amount))
    if not amount.is_finite() or amount > Decimal(policy['max_claim_amount']):
        raise HTTPException(422,'Claim amount exceeds the company maximum')
    if amount != amount.quantize(Decimal('0.01')):
        raise HTTPException(422,'Expense amounts may have at most two decimal places')
    if policy['business_purpose_required'] and len(body.business_purpose.strip()) < 8:
        raise HTTPException(422,'Business purpose is required (at least 8 characters)')
    if policy['receipt_required'] and Decimal(str(body.amount)) >= Decimal(policy['receipt_threshold']) and not body.receipt_reference.strip():
        raise HTTPException(422,'Receipt reference is required for this claim amount')
    return day


def event(c, expense_id:int, actor_id:int, name:str, note:str=''):
    c.execute('''INSERT INTO expense_claim_events(expense_id,actor_id,event_type,event_note,created_at)
                 VALUES(?,?,?,?,?)''', (expense_id, actor_id, name, note, clock()))


def create_expense_record(c,user,body:ClaimDetails):
    policy = read_policy(c)['settings']
    when = validated_claim(body,policy)
    stamp=clock()
    result=c.execute('''INSERT INTO expenses(employee_id,title,amount,category,created_at)
                        VALUES(?,?,?,?,?)''',(user['id'],body.title.strip(),body.amount,body.category,stamp))
    expense_id=result.lastrowid
    c.execute('''INSERT INTO expense_claim_details(expense_id,expense_date,merchant,business_purpose,cost_center,receipt_reference,updated_at)
                 VALUES(?,?,?,?,?,?,?)''',(expense_id,when.isoformat(),body.merchant.strip(),body.business_purpose.strip(),body.cost_center.strip(),body.receipt_reference.strip(),stamp))
    event(c,expense_id,user['id'],'Submitted','Claim created for HR review')
    audit(c,user['id'],'expense.submitted',f'expense:{expense_id}')
    return {'id':expense_id,'status':'Pending','notice':'Claim submitted; no reimbursement has been initiated'}


def scoped_claim(c, expense_id:int, user):
    row=c.execute('SELECT * FROM expenses WHERE id=?',(expense_id,)).fetchone()
    if not row:
        raise HTTPException(404,'Expense claim not found')
    if user['role']!='admin' and row['employee_id']!=user['id']:
        raise HTTPException(403,'You can only access your own expense claim')
    return row


@app.put('/api/expenses/{expense_id}/details')
def update_expense(expense_id:int, body:ClaimEdit, user=Depends(current_user)):
    with db() as c:
        existing=scoped_claim(c,expense_id,user)
        policy=read_policy(c)['settings']
        if not policy['allow_employee_edits'] and user['role']!='admin':
            raise HTTPException(403,'Employee edits are disabled')
        if existing['status']!='Pending':
            raise HTTPException(409,'Only pending expense claims can be edited')
        when=validated_claim(body,policy)
        c.execute('''UPDATE expenses SET title=?,amount=?,category=? WHERE id=?''',
                  (body.title.strip(),body.amount,body.category,expense_id))
        stamp=clock()
        detail=c.execute('SELECT expense_id FROM expense_claim_details WHERE expense_id=?',(expense_id,)).fetchone()
        values=(when.isoformat(),body.merchant.strip(),body.business_purpose.strip(),body.cost_center.strip(),body.receipt_reference.strip(),stamp)
        if detail:
            c.execute('''UPDATE expense_claim_details SET expense_date=?,merchant=?,business_purpose=?,cost_center=?,receipt_reference=?,updated_at=? WHERE expense_id=?''',(*values,expense_id))
        else:
            c.execute('''INSERT INTO expense_claim_details(expense_id,expense_date,merchant,business_purpose,cost_center,receipt_reference,updated_at)
                         VALUES(?,?,?,?,?,?,?)''',(expense_id,*values))
        event(c,expense_id,user['id'],'Edited',body.reason.strip())
        audit(c,user['id'],'expense.edited',f'expense:{expense_id}','Reason documented in claim event log')
        return {'id':expense_id,'status':'Pending','notice':'Claim updated and recorded in activity history'}


@app.post('/api/expenses/{expense_id}/withdraw')
def withdraw_expense(expense_id:int,user=Depends(current_user)):
    with db() as c:
        existing=scoped_claim(c,expense_id,user)
        policy=read_policy(c)['settings']
        if not policy['allow_withdrawals'] and user['role']!='admin':
            raise HTTPException(403,'Employee withdrawals are disabled')
        if existing['status']!='Pending':
            raise HTTPException(409,'Only pending claims can be withdrawn')
        c.execute("UPDATE expenses SET status='Withdrawn' WHERE id=? AND status='Pending'",(expense_id,))
        event(c,expense_id,user['id'],'Withdrawn','Claim withdrawn before review')
        audit(c,user['id'],'expense.withdrawn',f'expense:{expense_id}')
        return {'id':expense_id,'status':'Withdrawn'}


@app.get('/api/expenses/{expense_id}/activity')
def expense_activity(expense_id:int,user=Depends(current_user)):
    with db() as c:
        scoped_claim(c,expense_id,user)
        events=c.execute('''SELECT event_type,event_note,created_at FROM expense_claim_events
                            WHERE expense_id=? ORDER BY id DESC LIMIT 100''',(expense_id,)).fetchall()
        reviews=c.execute('''SELECT decision AS event_type,reason AS event_note,reviewed_at AS created_at
                             FROM expense_review_events WHERE expense_id=? ORDER BY id DESC LIMIT 100''',(expense_id,)).fetchall()
        return sorted([dict(r) for r in events]+[dict(r) for r in reviews], key=lambda item:item['created_at'],reverse=True)


class ReimbursementIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal['Scheduled','Paid','Cancelled']
    external_payment_reference: str = Field(default='',max_length=120)
    notes: str = Field(min_length=8,max_length=500)


@app.get('/api/expenses/{expense_id}/reimbursement')
def get_reimbursement(expense_id:int,user=Depends(current_user)):
    with db() as c:
        scoped_claim(c,expense_id,user)
        row=c.execute('''SELECT status,external_payment_reference,notes,updated_at FROM expense_reimbursement_records WHERE expense_id=?''',(expense_id,)).fetchone()
        return dict(row) if row else {'status':'Not recorded','external_payment_reference':'','notes':'','updated_at':None}


@app.put('/api/expenses/{expense_id}/reimbursement')
def update_reimbursement(expense_id:int,body:ReimbursementIn,user=Depends(require_hr)):
    with db() as c:
        row=scoped_claim(c,expense_id,user)
        if row['status']!='Approved':
            raise HTTPException(409,'Only approved expense claims can be recorded for reimbursement')
        previous=c.execute('SELECT * FROM expense_reimbursement_records WHERE expense_id=?',(expense_id,)).fetchone()
        if previous and previous['status']=='Paid':
            raise HTTPException(409,'Paid records cannot be edited; use a separate finance correction process')
        if previous and previous['status']==body.status:
            raise HTTPException(409,'Reimbursement status is unchanged')
        reference=body.external_payment_reference.strip()
        if body.status=='Paid' and len(reference)<4:
            raise HTTPException(422,'Enter an external payment reference before recording a payment')
        stamp=clock()
        if previous:
            c.execute('''UPDATE expense_reimbursement_records SET status=?,external_payment_reference=?,notes=?,updated_by=?,updated_at=? WHERE expense_id=?''',(body.status,reference,body.notes.strip(),user['id'],stamp,expense_id))
        else:
            c.execute('''INSERT INTO expense_reimbursement_records(expense_id,status,external_payment_reference,notes,updated_by,updated_at)
                         VALUES(?,?,?,?,?,?)''',(expense_id,body.status,reference,body.notes.strip(),user['id'],stamp))
        event(c,expense_id,user['id'],'Reimbursement '+body.status,'Finance status recorded by HR; no transfer initiated')
        c.execute('INSERT INTO notifications(employee_id,title,body,created_at) VALUES(?,?,?,?)',
                  (row['employee_id'],'Expense reimbursement update',f'Your expense reimbursement record is {body.status.lower()}. This is a recorded status, not confirmation from the bank.',stamp))
        audit(c,user['id'],'expense.reimbursement.recorded',f'expense:{expense_id}',body.status)
        return {'status':body.status,'notice':'Finance status recorded; no bank transfer was initiated'}
