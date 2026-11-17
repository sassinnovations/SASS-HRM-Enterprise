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
from main import app, db, current_user, require_hr, audit, rows, DB_ENGINE
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
        CREATE TABLE IF NOT EXISTS payroll_run_events_v2 (
          id INTEGER PRIMARY KEY,
          run_id INTEGER NOT NULL REFERENCES pay_runs_v2(id),
          action TEXT NOT NULL,
          note TEXT NOT NULL DEFAULT '',
          checklist_json TEXT NOT NULL DEFAULT '{}',
          actor_id INTEGER NOT NULL,
          created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_payroll_events_run ON payroll_run_events_v2(run_id,id);
        ''')

class TaxEstimateIn(BaseModel):
    country:Literal['IN','GB','US','AU','AE']='IN'
    annual_gross:float=Field(ge=0,le=100000000,allow_inf_nan=False)
    regime:str='new'
    deductions:float=Field(default=0,ge=0,le=100000000,allow_inf_nan=False)
    resident:bool=True

@app.get('/api/payroll-v2/rules')
def rules(user=Depends(current_user)):
    return {'supported_tax_calculators':['IN','GB','US','AU','AE'],
       'implemented_pay_run_countries':['IN'], 'snapshot':'2026-11-16',
       'tax_years':{'IN':'2026-27','GB':'2026-27','US':'2026','AU':'2026-27','AE':'2026'},
       'country_options': {
           'IN':{'name':'India','currency':'INR','regimes':['new','old']},
           'GB':{'name':'United Kingdom','currency':'GBP','regimes':['standard','scotland']},
           'US':{'name':'United States','currency':'USD','regimes':['single','married_joint','head_household','married_separate']},
           'AU':{'name':'Australia','currency':'AUD','regimes':['resident']},
           'AE':{'name':'United Arab Emirates','currency':'AED','regimes':['salary']},
       },
       'notes':'Reference salary income tax estimates only. Statutory withholding, payroll payments and filings are NOT implemented.',
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
            raise HTTPException(422,'ESI eligibility for wages above INR 21,000 requires specialist review. Existing insured employees may remain covered to the end of the contribution period (and a higher threshold can apply to persons with disabilities). If ESI should be off pending assessment, uncheck ESI and save the salary package.')
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

class PayrollDeleteRequest(BaseModel):
    """A deliberately explicit confirmation for destructive payroll actions."""
    confirm: Literal['DELETE']
    reason: str = Field(min_length=8, max_length=300)

    @model_validator(mode='after')
    def meaningful_reason(self):
        self.reason = self.reason.strip()
        if len(self.reason) < 8:
            raise ValueError('Provide a deletion reason with at least eight characters')
        return self


@app.delete('/api/payroll-v2/salary-packages/{employee_id}')
def delete_salary_package(employee_id: int, body: PayrollDeleteRequest, user=Depends(require_hr)):
    """Delete an active salary configuration, never any historical snapshots."""
    with db() as c:
        package = c.execute('SELECT employee_id FROM salary_packages WHERE employee_id=?',
                            (employee_id,)).fetchone()
        if package is None:
            raise HTTPException(404, 'Salary package not found')
        if c.execute('SELECT 1 FROM pay_adjustments_v2 WHERE employee_id=? LIMIT 1',
                     (employee_id,)).fetchone():
            raise HTTPException(409, 'Delete this employee\'s monthly adjustments before removing the salary package. Existing payroll snapshots remain protected.')
        c.execute('DELETE FROM salary_packages WHERE employee_id=?', (employee_id,))
        audit(c, user['id'], 'payroll.salary_package_deleted', f'employee:{employee_id}',
              f'Administrator deletion; reason={body.reason}; historical payroll snapshots retained')
    return {'deleted': True, 'employee_id': employee_id,
            'message': 'Salary package removed. Previous payroll snapshots and employee records remain unchanged.'}


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
        existing=c.execute('SELECT status FROM pay_runs_v2 WHERE month=?',(month,)).fetchone()
        if existing and existing['status'] != 'Draft':
            raise HTTPException(409,'A reviewed or published payroll run must not be adjusted. Reopen reviewed runs first.')
        c.execute('''INSERT INTO pay_adjustments_v2(employee_id,month,bonus,reimbursements,extra_deductions,
            days_worked,payable_days,tds_override,notes,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(employee_id,month) DO UPDATE SET bonus=excluded.bonus,
            reimbursements=excluded.reimbursements,extra_deductions=excluded.extra_deductions,
            days_worked=excluded.days_worked,payable_days=excluded.payable_days,
            tds_override=excluded.tds_override,notes=excluded.notes,updated_at=excluded.updated_at''',
            (employee_id,month,body.bonus,body.reimbursements,body.extra_deductions,body.days_worked,
             body.payable_days,body.tds_override,body.notes,now()))
        audit(c,user['id'],'payroll.adjustment_updated',f'employee:{employee_id}',f'period={month}')
        return {'message':'Adjustment saved. If a Draft payroll run already exists, recalculate it before review.','employee_id':employee_id,'month':month}

@app.delete('/api/payroll-v2/adjustments/{employee_id}/{month}')
def delete_adjustment(employee_id: int, month: str, body: PayrollDeleteRequest,
                      user=Depends(require_hr)):
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', month):
        raise HTTPException(422, 'Invalid payroll month')
    with db() as c:
        record = c.execute('SELECT id FROM pay_adjustments_v2 WHERE employee_id=? AND month=?',
                           (employee_id, month)).fetchone()
        if record is None:
            raise HTTPException(404, 'Monthly adjustment not found')
        existing=c.execute('SELECT status FROM pay_runs_v2 WHERE month=? LIMIT 1',(month,)).fetchone()
        if existing and existing['status'] != 'Draft':
            raise HTTPException(409,'Reopen reviewed payroll before deleting its adjustment. Published payroll runs are protected.')
        c.execute('DELETE FROM pay_adjustments_v2 WHERE employee_id=? AND month=?',
                  (employee_id, month))
        audit(c, user['id'], 'payroll.adjustment_deleted', f'employee:{employee_id}',
              f'period={month}; reason={body.reason}; no historical snapshot deleted')
    return {'deleted': True, 'employee_id': employee_id, 'month': month,
            'message': 'Monthly adjustment removed; other employee records remain unchanged.'}


def _record_run_event(c, run_id: int, actor_id: int, action: str, note: str, checks: dict):
    c.execute('''INSERT INTO payroll_run_events_v2(run_id,action,note,checklist_json,actor_id,created_at)
        VALUES(?,?,?,?,?,?)''', (run_id,action,note,json.dumps(checks),actor_id,now()))


class PayrollRunCorrection(BaseModel):
    confirm: Literal['RECALCULATE']
    reason: str = Field(min_length=8,max_length=300)

    @model_validator(mode='after')
    def valid_reason(self):
        self.reason=self.reason.strip()
        if len(self.reason)<8:raise ValueError('Explain why recalculation is required')
        return self


class PayrollReopen(BaseModel):
    confirm: Literal['REOPEN']
    reason: str = Field(min_length=8,max_length=300)

    @model_validator(mode='after')
    def valid_reason(self):
        self.reason=self.reason.strip()
        if len(self.reason)<8:raise ValueError('Explain why the review must be reopened')
        return self


@app.get('/api/payroll-v2/preflight')
def payroll_preflight(month: str,user=Depends(require_hr)):
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',month):
        raise HTTPException(422,'Invalid payroll month')
    if not '2026-04'<=month<='2027-03':
        raise HTTPException(422,'Only the configured 2026–27 India reference period is supported')
    with db() as c:
        missing=rows(c.execute('''SELECT e.id,e.code FROM employees e LEFT JOIN salary_packages p
                  ON e.id=p.employee_id WHERE e.account_active=1 AND p.employee_id IS NULL ORDER BY e.code'''))
        packages=rows(c.execute('''SELECT p.employee_id,p.basic,p.hra,p.allowance,p.esi_enabled,p.tds_mode,e.code
                  FROM salary_packages p JOIN employees e ON e.id=p.employee_id
                  WHERE e.account_active=1 ORDER BY e.code'''))
        adjustments=rows(c.execute('SELECT employee_id,days_worked,payable_days FROM pay_adjustments_v2 WHERE month=?',(month,)))
        old=c.execute('SELECT id,status FROM pay_runs_v2 WHERE month=?',(month,)).fetchone()
        issues=[]
        if not packages:issues.append({'level':'blocker','code':'no_salary_packages','message':'No active salary packages are configured.'})
        if missing:issues.append({'level':'warning','code':'missing_packages','message':f'{len(missing)} active employee(s) have no salary package and will be excluded.','employee_codes':[x['code'] for x in missing]})
        for p in packages:
            if p['esi_enabled'] and p['basic']+p['hra']+p['allowance']>21000:
                issues.append({'level':'warning','code':'esi_review','message':f'ESI wage review required for employee {p["code"]}.'})
            if p['tds_mode']=='estimate':
                issues.append({'level':'info','code':'estimated_tds','message':f'Employee {p["code"]} uses estimated, not final, TDS.'})
        if old:
            issues.append({'level':'info','code':'period_exists','message':f'A {old["status"].lower()} pay run already exists for this month.'})
        if packages:
            try:
                snapshots=_snapshot_for_period(c,month)
            except (HTTPException,ValueError) as exc:
                issues.append({'level':'blocker','code':'calculation_failed','message':str(getattr(exc,'detail',exc))})
                snapshots=[]
        else:snapshots=[]
        totals={k:round(sum(i[k] for i in snapshots),2) for k in ('gross','deductions','net','employer_total_estimate')}
        return {'month':month,'active_employee_count':len(packages)+len(missing),'configured_employee_count':len(packages),
                'missing_salary_package_count':len(missing),'adjustment_count':len(adjustments),
                'calculated_employee_count':len(snapshots),'issues':issues,'totals':totals,
                'can_create_draft':bool(snapshots) and old is None and not any(x['level']=='blocker' for x in issues),
                'existing_run':dict(old) if old else None,
                'publication_enabled':os.getenv('PAYROLL_PUBLICATION_ENABLED')=='1',
                'notice':'Estimates are not final payroll, tax declarations or payment instructions.'}


class PayRunIn(BaseModel):
    month:str=Field(pattern=r'^\d{4}-(0[1-9]|1[0-2])$')

@app.get('/api/payroll-v2/runs')
def run_list(user=Depends(require_hr)):
    with db() as c:
        return rows(c.execute('''SELECT r.*,COUNT(i.id) employee_count
            FROM pay_runs_v2 r LEFT JOIN pay_items_v2 i ON i.run_id=r.id
            GROUP BY r.id ORDER BY r.month DESC'''))


def _snapshot_for_period(c, month: str) -> list[dict]:
    """Compute a new simulated snapshot without writing anything to the database."""
    packages=rows(c.execute('''SELECT p.*,e.name employee_name,e.code FROM salary_packages p
         JOIN employees e ON e.id=p.employee_id WHERE e.account_active=1 ORDER BY e.id'''))
    if not packages:raise HTTPException(409,'Create at least one active salary package before starting a pay run')
    adjustments_by_employee={i['employee_id']:i for i in rows(c.execute(
        'SELECT * FROM pay_adjustments_v2 WHERE month=?',(month,)))}
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
            'month':month,'country':'IN','currency':'INR','salary_components':{'basic':p['basic'],'hra':p['hra'],'allowance':p['allowance']},
            'tax_regime':p['tax_regime'],'tds_mode':p['tds_mode'],
            'period_adjustments':{k:adj.get(k) for k in ('bonus','reimbursements','extra_deductions','days_worked','payable_days','tds_override','notes')},
            'tax_reference':tax['sources'],
            'disclaimer':'Illustrative estimate, not validated statutory payroll; no bank transfers or tax filings.'})
        snapshots.append(statement)
    return snapshots

def _draft_has_changes(c, run_id: int, month: str) -> bool:
    """Detect if saved salary packages or adjustments changed since the last snapshot."""
    try:
        expected=_snapshot_for_period(c,month)
    except (ValueError,HTTPException):
        return True
    stored=rows(c.execute('SELECT employee_id,data_json FROM pay_items_v2 WHERE run_id=?',(run_id,)))
    old={i['employee_id']:json.loads(i['data_json']) for i in stored}
    expected_by_id={i['employee_id']:i for i in expected}
    return old != expected_by_id


@app.post('/api/payroll-v2/runs',status_code=201)
def create_run(body:PayRunIn,user=Depends(require_hr)):
    if not '2026-04'<=body.month<='2027-03':
        raise HTTPException(422,'This reference tax rule set only supports India tax year 2026-27 (Apr 2026–Mar 2027)')
    with db() as c:
        if c.execute('SELECT id FROM pay_runs_v2 WHERE month=?',(body.month,)).fetchone():
            raise HTTPException(409,'A pay run already exists for that period. Published snapshots are immutable.')
        snapshots=_snapshot_for_period(c,body.month)
        result=c.execute('INSERT INTO pay_runs_v2(month,status,created_by,created_at) VALUES(?,?,?,?)',
                  (body.month,'Draft',user['id'],now()))
        run_id=result.lastrowid
        for item in snapshots:c.execute('INSERT INTO pay_items_v2(run_id,employee_id,data_json) VALUES(?,?,?)',
                    (run_id,item['employee_id'],json.dumps(item)))
        _record_run_event(c,run_id,user['id'],'created','Initial draft created',{})
        audit(c,user['id'],'payroll.run_created',f'run:{run_id}',f'period={body.month}, staff={len(snapshots)}')
        return {'id':run_id,'month':body.month,'status':'Draft','employee_count':len(snapshots)}

@app.post('/api/payroll-v2/runs/{run_id}/recalculate')
def recalculate_draft(run_id:int,body:PayrollRunCorrection,user=Depends(require_hr)):
    with db() as c:
        run=c.execute('SELECT id,month,status FROM pay_runs_v2 WHERE id=?'+(' FOR UPDATE' if DB_ENGINE=='mysql' else ''),(run_id,)).fetchone()
        if not run:raise HTTPException(404,'Payroll run not found')
        if run['status']!='Draft':raise HTTPException(409,'Only Draft payroll runs may be recalculated. Reopen reviewed runs first; published runs are immutable.')
        snapshots=_snapshot_for_period(c,run['month'])
        # An empty set or calculation error must not erase the previous draft.
        if not snapshots:raise HTTPException(409,'No salary packages are available to recalculate')
        previous=c.execute('SELECT COUNT(*) AS n FROM pay_items_v2 WHERE run_id=?',(run_id,)).fetchone()['n']
        c.execute('DELETE FROM pay_items_v2 WHERE run_id=?',(run_id,))
        for item in snapshots:c.execute('INSERT INTO pay_items_v2(run_id,employee_id,data_json) VALUES(?,?,?)',
                  (run_id,item['employee_id'],json.dumps(item)))
        _record_run_event(c,run_id,user['id'],'recalculated',body.reason,{})
        audit(c,user['id'],'payroll.run_recalculated',f'run:{run_id}',f'period={run["month"]}; staff_previous={previous}; staff_new={len(snapshots)}')
        return {'id':run_id,'status':'Draft','previous_employee_count':previous,'employee_count':len(snapshots),
                'message':'Draft updated from current salary and adjustment records; no statements were published.'}


@app.post('/api/payroll-v2/runs/{run_id}/reopen')
def reopen_review(run_id:int,body:PayrollReopen,user=Depends(require_hr)):
    with db() as c:
        run=c.execute('SELECT id,month,status FROM pay_runs_v2 WHERE id=?'+(' FOR UPDATE' if DB_ENGINE=='mysql' else ''),(run_id,)).fetchone()
        if not run:raise HTTPException(404,'Payroll run not found')
        if run['status']!='Reviewed':raise HTTPException(409,'Only Reviewed runs may be reopened. Published statements cannot be changed.')
        c.execute("UPDATE pay_runs_v2 SET status='Draft',reviewed_by=NULL,reviewed_at=NULL WHERE id=?",(run_id,))
        _record_run_event(c,run_id,user['id'],'reopened',body.reason,{})
        audit(c,user['id'],'payroll.run_reopened',f'run:{run_id}',f'period={run["month"]}')
        return {'id':run_id,'status':'Draft','message':'Reviewed run returned to Draft for correction.'}


@app.get('/api/payroll-v2/runs/{run_id}/history')
def run_history(run_id:int,user=Depends(require_hr)):
    with db() as c:
        if not c.execute('SELECT 1 FROM pay_runs_v2 WHERE id=?',(run_id,)).fetchone():
            raise HTTPException(404,'Payroll run not found')
        return rows(c.execute('''SELECT r.id,r.action,r.note,r.checklist_json,r.actor_id,r.created_at,e.name actor_name
                  FROM payroll_run_events_v2 r LEFT JOIN employees e ON r.actor_id=e.id
                  WHERE r.run_id=? ORDER BY r.id DESC''',(run_id,)))


@app.delete('/api/payroll-v2/runs/{run_id}')
def delete_pay_run(run_id: int, body: PayrollDeleteRequest, user=Depends(require_hr)):
    """Delete only unpublished simulations. Remove children explicitly for MySQL FKs."""
    with db() as c:
        record = c.execute('SELECT id,month,status FROM pay_runs_v2 WHERE id=?' + (' FOR UPDATE' if DB_ENGINE == 'mysql' else ''),
                           (run_id,)).fetchone()
        if record is None:
            raise HTTPException(404, 'Payroll run not found')
        if record['status'] == 'Published':
            raise HTTPException(409, 'Published payroll statements cannot be deleted. Use the finance correction process.')
        if record['status'] not in ('Draft', 'Reviewed'):
            raise HTTPException(409, 'Only draft or reviewed payroll runs can be removed')
        n = c.execute('SELECT COUNT(*) AS n FROM pay_items_v2 WHERE run_id=?', (run_id,)).fetchone()['n']
        c.execute('DELETE FROM payroll_run_events_v2 WHERE run_id=?', (run_id,))
        c.execute('DELETE FROM pay_items_v2 WHERE run_id=?', (run_id,))
        c.execute('DELETE FROM pay_runs_v2 WHERE id=?', (run_id,))
        audit(c, user['id'], 'payroll.unpublished_run_deleted', f'run:{run_id}',
              f'period={record["month"]}; status={record["status"]}; count={n}; reason={body.reason}')
    return {'deleted': True, 'id': run_id, 'month': record['month'],
            'removed_items': n,
            'message': 'Unpublished payroll run and its snapshot items removed. Salary packages and monthly adjustments are retained.'}


@app.get('/api/payroll-v2/runs/{run_id}')
def run_detail(run_id:int,user=Depends(require_hr)):
    with db() as c:
        run=c.execute('SELECT * FROM pay_runs_v2 WHERE id=?',(run_id,)).fetchone()
        if run is None:raise HTTPException(404,'Pay run not found')
        items=rows(c.execute('SELECT data_json FROM pay_items_v2 WHERE run_id=? ORDER BY employee_id',(run_id,)))
        entries=[json.loads(i['data_json']) for i in items]
        previous=c.execute("SELECT id,month FROM pay_runs_v2 WHERE month<? AND status='Published' ORDER BY month DESC LIMIT 1",(run['month'],)).fetchone()
        variance=[]
        if previous:
            prior=rows(c.execute('SELECT employee_id,data_json FROM pay_items_v2 WHERE run_id=?',(previous['id'],)))
            old_net={r['employee_id']:json.loads(r['data_json'])['net'] for r in prior}
            for item in entries:
                before=old_net.get(item['employee_id'])
                if before is None:
                    variance.append({'employee_id':item['employee_id'],'code':item['code'],'employee_name':item['employee_name'],
                                     'prior_net':None,'current_net':item['net'],'difference':None,'change_percent':None,'flag':True,'reason':'New payroll employee'})
                    continue
                delta=round(item['net']-before,2)
                change_percent=round(delta/before*100,2) if before else None
                flag=abs(delta)>1000 and (before==0 or abs(change_percent)>20)
                variance.append({'employee_id':item['employee_id'],'code':item['code'],'employee_name':item['employee_name'],
                                 'prior_net':before,'current_net':item['net'],'difference':delta,
                                 'change_percent':change_percent,'flag':flag,'reason':'Change exceeds 20% and ₹1,000' if flag else ''})
        return {'run':dict(run),'items':entries,'draft_out_of_date':_draft_has_changes(c,run_id,run['month']) if run['status']!='Published' else False,'comparison_period':previous['month'] if previous else None,
                'variance':variance,'flagged_variance_count':sum(1 for item in variance if item['flag']),
                'totals':{k:round(sum(item[k] for item in entries),2) for k in ('gross','deductions','net','employer_total_estimate')}}

class RunDecision(BaseModel):
    action:Literal['review','publish']
    reviewed:bool=True
    note:str=Field(default='',max_length=500)
    checklist:dict[str,bool]=Field(default_factory=dict)

    @model_validator(mode='after')
    def valid_review(self):
        self.note=self.note.strip()
        if self.action=='review':
            if len(self.note)<8:
                raise ValueError('Provide a review note of at least 8 characters')
            if not all(self.checklist.get(k) is True for k in ('roster','adjustments','statutory')):
                raise ValueError('Complete all payroll review checklist items')
        return self

@app.post('/api/payroll-v2/runs/{run_id}/transition')
def transition(run_id:int,body:RunDecision,user=Depends(require_hr)):
    if not body.reviewed:raise HTTPException(422,'Manual HR review is required')
    with db() as c:
        run=c.execute('SELECT * FROM pay_runs_v2 WHERE id=?'+(' FOR UPDATE' if DB_ENGINE=='mysql' else ''),(run_id,)).fetchone()
        if run is None:raise HTTPException(404,'Pay run not found')
        if body.action=='review':
            if run['status']!='Draft':raise HTTPException(409,'Only draft runs can be marked reviewed')
            if _draft_has_changes(c,run_id,run['month']):
                raise HTTPException(409,'Draft salary or attendance inputs have changed. Recalculate the draft before review.')
            c.execute('UPDATE pay_runs_v2 SET status=?,reviewed_at=?,reviewed_by=? WHERE id=?',('Reviewed',now(),user['id'],run_id))
        else:
            if os.getenv('PAYROLL_PUBLICATION_ENABLED') != '1':
                raise HTTPException(503,'Payroll publication is disabled until SASS finance validates the local statutory rule set and enables this workflow.')
            if run['status']!='Reviewed':raise HTTPException(409,'Review the pay run before publishing')
            if _draft_has_changes(c,run_id,run['month']):
                raise HTTPException(409,'Payroll inputs changed after review. Reopen and recalculate before publishing.')
            if os.getenv('PAYROLL_DUAL_APPROVAL_ENABLED')=='1' and run['reviewed_by']==user['id']:
                raise HTTPException(409,'Independent payroll approval is enabled: the reviewer cannot publish the same payroll run')
            c.execute('UPDATE pay_runs_v2 SET status=?,published_at=?,published_by=? WHERE id=?',('Published',now(),user['id'],run_id))
        _record_run_event(c,run_id,user['id'],body.action,body.note.strip(),body.checklist)
        audit(c,user['id'],f'payroll.run_{body.action}',f'run:{run_id}')
        return {'id':run_id,'status':'Reviewed' if body.action=='review' else 'Published',
                'message':'Statements are visible to staff only after publication; no payments or tax filings were sent.'}

@app.get('/api/payroll-v2/my-statements')
def my_statements(user=Depends(current_user)):
    with db() as c:
        items=rows(c.execute('''SELECT r.status,i.data_json FROM pay_items_v2 i JOIN pay_runs_v2 r ON r.id=i.run_id
             WHERE i.employee_id=? AND r.status='Published' ORDER BY r.month DESC''',(user['id'],)))
        return [json.loads(i['data_json']) for i in items]

@app.get('/api/payroll-v2/my-statements/{month}/export.csv')
def export_my_statement(month:str,user=Depends(current_user)):
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',month):raise HTTPException(422,'Invalid payroll month')
    with db() as c:
        statement=c.execute("""SELECT i.data_json FROM pay_items_v2 i
               JOIN pay_runs_v2 r ON r.id=i.run_id
               WHERE i.employee_id=? AND r.month=? AND r.status='Published'""",(user['id'],month)).fetchone()
        if not statement:raise HTTPException(404,'No published statement for this month')
        payload=json.loads(statement['data_json'])
    out=io.StringIO();writer=csv.writer(out)
    writer.writerow(['SASS HRM — SIMULATED PAY STATEMENT','Not proof of bank payment or statutory filing'])
    for name,key in [('Month','month'),('Employee code','code'),('Employee name','employee_name'),('Currency','currency'),
                     ('Gross','gross'),('Reimbursements','reimbursements'),('Employee PF','employee_pf'),('Employee ESI','employee_esi'),
                     ('Professional tax','professional_tax'),('Estimated TDS','income_tax_tds'),('Other deductions','other_deductions'),
                     ('Total deductions','deductions'),('Net simulated salary','net')]:
        value=payload.get(key,'')
        if isinstance(value,str) and value.startswith(('=','+','-','@','\t','\r')):value="'"+value
        writer.writerow([name,value])
    return StreamingResponse(iter([out.getvalue()]),media_type='text/csv',
          headers={'Content-Disposition':f'attachment; filename="sass-own-pay-statement-{month}.csv"'})


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
