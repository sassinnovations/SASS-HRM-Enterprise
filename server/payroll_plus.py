"""SASS HRM v0.8 payroll workbench. Simulated payslips; never files tax or sends payments."""
from __future__ import annotations
import csv
import calendar
import os
import io
import json
import re
from datetime import datetime,timezone
from typing import Literal
from fastapi import Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from main import app, db, current_user, require_hr, audit, rows
from payroll_engine import estimate_tax,estimate_india_monthly_pay,SOURCES


def now():return datetime.now(timezone.utc).isoformat()

@app.on_event('startup')
def init_payroll_v2():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS salary_packages (
          employee_id INTEGER PRIMARY KEY REFERENCES employees(id),
          country TEXT NOT NULL DEFAULT 'IN' CHECK(country IN ('IN')),
          currency TEXT NOT NULL DEFAULT 'INR', basic REAL NOT NULL CHECK(basic>=0),
          hra REAL NOT NULL CHECK(hra>=0), allowance REAL NOT NULL CHECK(allowance>=0),
          pf_enabled INTEGER NOT NULL DEFAULT 0, esi_enabled INTEGER NOT NULL DEFAULT 0,
          pf_cap REAL NOT NULL DEFAULT 15000, professional_tax REAL NOT NULL DEFAULT 0,
          other_deductions REAL NOT NULL DEFAULT 0, tax_regime TEXT NOT NULL DEFAULT 'new',
          tds_mode TEXT NOT NULL DEFAULT 'estimate', monthly_tds REAL NOT NULL DEFAULT 0,
          updated_by INTEGER NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS pay_adjustments_v2 (
          id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL REFERENCES employees(id),
          month TEXT NOT NULL, bonus REAL NOT NULL DEFAULT 0 CHECK(bonus>=0),
          reimbursements REAL NOT NULL DEFAULT 0 CHECK(reimbursements>=0),
          extra_deductions REAL NOT NULL DEFAULT 0 CHECK(extra_deductions>=0),
          days_worked INTEGER NOT NULL DEFAULT 30 CHECK(days_worked>=0),
          payable_days INTEGER NOT NULL DEFAULT 30 CHECK(payable_days>0),
          tds_override REAL CHECK(tds_override IS NULL OR tds_override>=0),
          notes TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL,
          UNIQUE(employee_id,month));
        CREATE TABLE IF NOT EXISTS pay_runs_v2 (
          id INTEGER PRIMARY KEY, month TEXT NOT NULL UNIQUE, country TEXT NOT NULL DEFAULT 'IN',
          status TEXT NOT NULL DEFAULT 'Draft' CHECK(status IN ('Draft','Reviewed','Published')),
          created_by INTEGER NOT NULL, reviewed_by INTEGER, published_by INTEGER,
          created_at TEXT NOT NULL, reviewed_at TEXT, published_at TEXT,
          ruleset_version TEXT NOT NULL DEFAULT 'INDIA-2026-27-reference');
        CREATE TABLE IF NOT EXISTS pay_items_v2 (
          id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL REFERENCES pay_runs_v2(id),
          employee_id INTEGER NOT NULL REFERENCES employees(id),
          data_json TEXT NOT NULL, UNIQUE(run_id,employee_id));
        CREATE INDEX IF NOT EXISTS idx_v2_employee ON pay_items_v2(employee_id,run_id);
        ''')

class TaxEstimateIn(BaseModel):
    country:Literal['IN','GB','US']='IN'
    annual_gross:float=Field(ge=0,le=100000000)
    regime:str='new'
    deductions:float=Field(default=0,ge=0,le=100000000)
    resident:bool=True

@app.get('/api/payroll-v2/rules')
def rules(user=Depends(current_user)):
    return {'supported_tax_calculators':['IN','GB','US'],
       'implemented_pay_run_countries':['IN'], 'snapshot':'2026-10-13',
       'tax_years':{'IN':'2026-27','GB':'2026-27','US':'2026'},
       'notes':'Reference estimates only. US/UK payroll withholding and statutory filings are NOT implemented.',
       'sources':SOURCES}

@app.post('/api/payroll-v2/tax-estimate')
def tax_preview(body:TaxEstimateIn,user=Depends(current_user)):
    try:return estimate_tax(body.country,body.annual_gross,body.regime,body.deductions,body.resident)
    except ValueError as e: raise HTTPException(422,str(e)) from e

class SalaryIn(BaseModel):
    employee_id:int=Field(gt=0)
    basic:float=Field(ge=0,le=10000000)
    hra:float=Field(ge=0,le=10000000)
    allowance:float=Field(ge=0,le=10000000)
    pf_enabled:bool=False
    esi_enabled:bool=False
    pf_cap:float=Field(default=15000,ge=0,le=1000000)
    professional_tax:float=Field(default=0,ge=0,le=100000)
    other_deductions:float=Field(default=0,ge=0,le=1000000)
    tax_regime:Literal['new','old']='new'
    tds_mode:Literal['estimate','manual']='estimate'
    monthly_tds:float=Field(default=0,ge=0,le=10000000)

@app.get('/api/payroll-v2/salary-packages')
def salary_packages(user=Depends(require_hr)):
    with db() as c:
        return rows(c.execute('''SELECT p.*,e.name employee_name,e.code FROM salary_packages p
          JOIN employees e ON e.id=p.employee_id ORDER BY e.name'''))

@app.put('/api/payroll-v2/salary-packages/{employee_id}')
def save_salary(employee_id:int,body:SalaryIn,user=Depends(require_hr)):
    if employee_id!=body.employee_id:raise HTTPException(422,'Employee ID mismatch')
    with db() as c:
        if not c.execute('SELECT id FROM employees WHERE id=? AND account_active=1',(employee_id,)).fetchone():
            raise HTTPException(404,'Active employee not found')
        # Require positive core salary and explicit payroll administrator setup.
        if body.basic+body.hra+body.allowance<=0:raise HTTPException(422,'Salary package cannot be zero')
        if body.esi_enabled and body.basic+body.hra+body.allowance>21000:
            raise HTTPException(422,'ESI eligibility needs manual specialist review for wages above INR 21,000; toggle off pending assessment')
        data=body.model_dump()
        c.execute('''INSERT INTO salary_packages(employee_id,country,currency,basic,hra,allowance,pf_enabled,esi_enabled,pf_cap,
                     professional_tax,other_deductions,tax_regime,tds_mode,monthly_tds,updated_by,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(employee_id) DO UPDATE SET basic=excluded.basic,hra=excluded.hra,allowance=excluded.allowance,
            pf_enabled=excluded.pf_enabled,esi_enabled=excluded.esi_enabled,pf_cap=excluded.pf_cap,
            professional_tax=excluded.professional_tax,other_deductions=excluded.other_deductions,
            tax_regime=excluded.tax_regime,tds_mode=excluded.tds_mode,monthly_tds=excluded.monthly_tds,
            updated_by=excluded.updated_by,updated_at=excluded.updated_at''',
            (employee_id,'IN','INR',data['basic'],data['hra'],data['allowance'],int(body.pf_enabled),int(body.esi_enabled),
             body.pf_cap,body.professional_tax,body.other_deductions,body.tax_regime,body.tds_mode,body.monthly_tds,user['id'],now()))
        audit(c,user['id'],'payroll.salary_package_updated',f'employee:{employee_id}','No amounts stored in audit details')
        return {'employee_id':employee_id,'message':'Salary package saved. Existing payroll run snapshots do not change.'}

class PayrollAdjustmentIn(BaseModel):
    employee_id:int=Field(gt=0)
    month:str=Field(pattern=r'^\d{4}-(0[1-9]|1[0-2])$')
    bonus:float=Field(default=0,ge=0,le=10000000)
    reimbursements:float=Field(default=0,ge=0,le=10000000)
    extra_deductions:float=Field(default=0,ge=0,le=10000000)
    days_worked:int=Field(default=30,ge=0,le=31)
    payable_days:int=Field(default=30,ge=1,le=31)
    tds_override:float|None=Field(default=None,ge=0,le=10000000)
    notes:str=Field(default='',max_length=300)
    @model_validator(mode='after')
    def check_days(self):
        if self.days_worked>self.payable_days:raise ValueError('Days worked cannot exceed payable days')
        return self

@app.get('/api/payroll-v2/adjustments')
def adjustments(user=Depends(require_hr)):
    with db() as c:
        return rows(c.execute('SELECT a.*,e.name employee_name FROM pay_adjustments_v2 a JOIN employees e ON e.id=a.employee_id ORDER BY month DESC,e.name'))

@app.put('/api/payroll-v2/adjustments/{employee_id}/{month}')
def save_adjustment(employee_id:int,month:str,body:PayrollAdjustmentIn,user=Depends(require_hr)):
    if employee_id!=body.employee_id or month!=body.month:raise HTTPException(422,'Employee or month mismatch')
    if not '2026-04'<=month<='2027-03':raise HTTPException(422,'Unsupported payroll tax year')
    year,mon=map(int,month.split('-'))
    calendar_days=calendar.monthrange(year,mon)[1]
    if body.payable_days>calendar_days or body.days_worked>calendar_days:
        raise HTTPException(422,'Work and payable days cannot exceed days in the selected month')
    with db() as c:
        if not c.execute('SELECT 1 FROM salary_packages WHERE employee_id=?',(employee_id,)).fetchone():
            raise HTTPException(404,'Salary package not found')
        if c.execute('SELECT 1 FROM pay_runs_v2 WHERE month=?',(month,)).fetchone():
            raise HTTPException(409,'This period has been snapshotted and can no longer be adjusted')
        c.execute('''INSERT INTO pay_adjustments_v2(employee_id,month,bonus,reimbursements,extra_deductions,
            days_worked,payable_days,tds_override,notes,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(employee_id,month) DO UPDATE SET bonus=excluded.bonus,
            reimbursements=excluded.reimbursements,extra_deductions=excluded.extra_deductions,
            days_worked=excluded.days_worked,payable_days=excluded.payable_days,
            tds_override=excluded.tds_override,notes=excluded.notes,updated_at=excluded.updated_at''',
            (employee_id,month,body.bonus,body.reimbursements,body.extra_deductions,body.days_worked,
             body.payable_days,body.tds_override,body.notes,now()))
        audit(c,user['id'],'payroll.adjustment_updated',f'employee:{employee_id}',f'period={month}')
        return {'message':'Adjustment saved; apply by generating a new draft pay run','employee_id':employee_id,'month':month}

class PayRunIn(BaseModel):
    month:str=Field(pattern=r'^\d{4}-(0[1-9]|1[0-2])$')

@app.get('/api/payroll-v2/runs')
def run_list(user=Depends(require_hr)):
    with db() as c:
        return rows(c.execute('''SELECT r.*,COUNT(i.id) employee_count
            FROM pay_runs_v2 r LEFT JOIN pay_items_v2 i ON i.run_id=r.id
            GROUP BY r.id ORDER BY r.month DESC'''))

@app.post('/api/payroll-v2/runs',status_code=201)
def create_run(body:PayRunIn,user=Depends(require_hr)):
    if not '2026-04'<=body.month<='2027-03':
        raise HTTPException(422,'This reference tax rule set only supports India tax year 2026-27 (Apr 2026–Mar 2027)')
    with db() as c:
        if c.execute('SELECT id FROM pay_runs_v2 WHERE month=?',(body.month,)).fetchone():
            raise HTTPException(409,'A pay run already exists for that period. Published snapshots are immutable.')
        packages=rows(c.execute('''SELECT p.*,e.name employee_name,e.code FROM salary_packages p
             JOIN employees e ON e.id=p.employee_id WHERE e.account_active=1 ORDER BY e.id'''))
        if not packages:raise HTTPException(409,'Create at least one active salary package before starting a pay run')
        adjustments_by_employee={i['employee_id']:i for i in rows(c.execute(
            'SELECT * FROM pay_adjustments_v2 WHERE month=?',(body.month,)))}
        snapshots=[]
        for p in packages:
            monthly_gross=p['basic']+p['hra']+p['allowance']
            adj=adjustments_by_employee.get(p['employee_id'],{})
            earned_fraction=adj.get('days_worked',30)/adj.get('payable_days',30)
            try:
                tax=estimate_tax('IN',monthly_gross*12,p['tax_regime'])
                tds=p['monthly_tds'] if p['tds_mode']=='manual' else tax['estimated_monthly_tax']
                if adj.get('tds_override') is not None:tds=adj['tds_override']
                statement=estimate_india_monthly_pay(p['basic'],p['hra'],p['allowance'],
                     bonus=adj.get('bonus',0),reimbursements=adj.get('reimbursements',0),
                     earned_fraction=earned_fraction,pf_enabled=bool(p['pf_enabled']),
                     esi_enabled=bool(p['esi_enabled']),pf_wage_cap=p['pf_cap'],
                     professional_tax=p['professional_tax'],
                     other_deductions=p['other_deductions']+adj.get('extra_deductions',0),tds=tds)
            except ValueError as e:raise HTTPException(422,f'Employee {p["code"]}: {e}') from e
            statement.update({'employee_id':p['employee_id'],'employee_name':p['employee_name'],'code':p['code'],
                'month':body.month,'country':'IN','currency':'INR','salary_components':{'basic':p['basic'],'hra':p['hra'],'allowance':p['allowance']},
                'tax_regime':p['tax_regime'],'tds_mode':p['tds_mode'],
                'period_adjustments':{k:adj.get(k) for k in ('bonus','reimbursements','extra_deductions','days_worked','payable_days','tds_override','notes')},
                'tax_reference':tax['sources'],
                'disclaimer':'Illustrative estimate, not validated statutory payroll; no bank transfers or tax filings.'})
            snapshots.append(statement)
        result=c.execute('INSERT INTO pay_runs_v2(month,status,created_by,created_at) VALUES(?,?,?,?)',
                  (body.month,'Draft',user['id'],now()))
        run_id=result.lastrowid
        for item in snapshots:c.execute('INSERT INTO pay_items_v2(run_id,employee_id,data_json) VALUES(?,?,?)',
                    (run_id,item['employee_id'],json.dumps(item)))
        audit(c,user['id'],'payroll.run_created',f'run:{run_id}',f'period={body.month}, staff={len(snapshots)}')
        return {'id':run_id,'month':body.month,'status':'Draft','employee_count':len(snapshots)}

@app.get('/api/payroll-v2/runs/{run_id}')
def run_detail(run_id:int,user=Depends(require_hr)):
    with db() as c:
        run=c.execute('SELECT * FROM pay_runs_v2 WHERE id=?',(run_id,)).fetchone()
        if run is None:raise HTTPException(404,'Pay run not found')
        items=rows(c.execute('SELECT data_json FROM pay_items_v2 WHERE run_id=? ORDER BY employee_id',(run_id,)))
        entries=[json.loads(i['data_json']) for i in items]
        return {'run':dict(run),'items':entries,
                'totals':{k:round(sum(item[k] for item in entries),2) for k in ('gross','deductions','net','employer_total_estimate')}}

class RunDecision(BaseModel):
    action:Literal['review','publish']
    reviewed:bool=True

@app.post('/api/payroll-v2/runs/{run_id}/transition')
def transition(run_id:int,body:RunDecision,user=Depends(require_hr)):
    if not body.reviewed:raise HTTPException(422,'Manual HR review is required')
    with db() as c:
        run=c.execute('SELECT * FROM pay_runs_v2 WHERE id=?',(run_id,)).fetchone()
        if run is None:raise HTTPException(404,'Pay run not found')
        if body.action=='review':
            if run['status']!='Draft':raise HTTPException(409,'Only draft runs can be marked reviewed')
            c.execute('UPDATE pay_runs_v2 SET status=?,reviewed_at=?,reviewed_by=? WHERE id=?',('Reviewed',now(),user['id'],run_id))
        else:
            if os.getenv('PAYROLL_PUBLICATION_ENABLED') != '1':
                raise HTTPException(503,'Payroll publication is disabled until SASS finance validates the local statutory rule set and enables this workflow.')
            if run['status']!='Reviewed':raise HTTPException(409,'Review the pay run before publishing')
            c.execute('UPDATE pay_runs_v2 SET status=?,published_at=?,published_by=? WHERE id=?',('Published',now(),user['id'],run_id))
        audit(c,user['id'],f'payroll.run_{body.action}',f'run:{run_id}')
        return {'id':run_id,'status':'Reviewed' if body.action=='review' else 'Published',
                'message':'Statements are visible to staff only after publication; no payments or tax filings were sent.'}

@app.get('/api/payroll-v2/my-statements')
def my_statements(user=Depends(current_user)):
    with db() as c:
        items=rows(c.execute('''SELECT r.status,i.data_json FROM pay_items_v2 i JOIN pay_runs_v2 r ON r.id=i.run_id
             WHERE i.employee_id=? AND r.status='Published' ORDER BY r.month DESC''',(user['id'],)))
        return [json.loads(i['data_json']) for i in items]

@app.get('/api/payroll-v2/runs/{run_id}/export.csv')
def export_run(run_id:int,user=Depends(require_hr)):
    result=run_detail(run_id,user)
    out=io.StringIO();w=csv.writer(out)
    w.writerow(['Period','Employee code','Employee','Currency','Gross','PF','ESI','Professional tax','TDS estimate','Other deductions','Net'])
    for i in result['items']:
        # Prefix text to avoid spreadsheet formula injection if names/codes are unexpected.
        def safe(v):
            v=str(v)
            return "'"+v if v and v[0] in ('=','+','-','@','\t','\r') else v
        w.writerow([i['month'],safe(i['code']),safe(i['employee_name']),i['currency'],i['gross'],i['employee_pf'],i['employee_esi'],i['professional_tax'],i['income_tax_tds'],i['other_deductions'],i['net']])
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="sass-payroll-{result["run"]["month"]}.csv"'})
