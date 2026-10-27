"""Restricted read-only diagnostics. Does not expose environment secrets or employee data."""
import os
from datetime import datetime, timezone
from fastapi import Depends, HTTPException
from main import app, db, DB_ENGINE, current_user

def require_developer(user=Depends(current_user)):
    if user['role'] != 'admin':
        raise HTTPException(403,'HR administrator role required for developer diagnostics')
    with db() as c:
        grant=c.execute('SELECT enabled FROM developer_grants WHERE employee_id=?',(user['id'],)).fetchone()
    if not grant or not grant['enabled']:
        raise HTTPException(403,'Developer access required')
    return user

@app.get('/api/developer/status')
def developer_status(user=Depends(require_developer)):
    with db() as c:
        c.execute('SELECT 1').fetchone()
        if DB_ENGINE == 'mysql':
            count=c.execute("SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_schema=DATABASE() AND table_type='BASE TABLE'").fetchone()['n']
        else:
            count=c.execute("SELECT COUNT(*) AS n FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()['n']
        company = c.execute('SELECT 1 FROM organization_profile WHERE id=1').fetchone()
        active_offices = c.execute('SELECT COUNT(*) AS n FROM organization_offices WHERE is_active=1').fetchone()['n']
        c.execute('SELECT 1 FROM personal_calendar_events LIMIT 1').fetchall()
    smtp_ready = bool(os.getenv('SMTP_HOST') and os.getenv('SMTP_FROM'))
    checks = [
        {'key':'database','label':'Database connection','ready':True,'hint':'Connected to configured database'},
        {'key':'company','label':'Company identity','ready':bool(company),'hint':'Complete Company setup & import' if not company else 'Company profile saved'},
        {'key':'offices','label':'Active office directory','ready':active_offices>0,'hint':'Add an active office in Organization settings' if not active_offices else 'Office directory configured'},
        {'key':'smtp','label':'Invitation email configuration','ready':smtp_ready,'hint':'Configure SMTP_HOST and SMTP_FROM in the private server environment' if not smtp_ready else 'SMTP settings present (delivery not tested)'},
        {'key':'calendar','label':'Personal calendar storage','ready':True,'hint':'Private calendar table available'}
    ]
    return {
        'service':'SASS HRM Enterprise',
        'app_version':app.version,
        'api_status':'healthy',
        'database_engine':DB_ENGINE,
        'database_status':'connected',
        'schema_table_count':count,
        'checked_at':datetime.now(timezone.utc).isoformat(),
        'capabilities':['read-only system diagnostics','configured-service readiness'],
        'checks':checks,
        'note':'No database credentials, secrets, employee details or payroll amounts are exposed.'
    }
