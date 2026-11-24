"""v2.0 employee services: auditable equipment custody, HR document metadata review,
and employee-owned workspace preferences. No demo data or implicit approvals.
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from typing import Literal
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from main import app, db, current_user, require_hr, audit, rows, DB_ENGINE


def utcnow():
    return datetime.now(timezone.utc).isoformat()


@app.on_event('startup')
def initialize_employee_services():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS asset_lifecycle_events (
          id INTEGER PRIMARY KEY, asset_id INTEGER NOT NULL, actor_id INTEGER NOT NULL,
          event_type TEXT NOT NULL, from_employee_id INTEGER, to_employee_id INTEGER,
          note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
          FOREIGN KEY(asset_id) REFERENCES assets(id), FOREIGN KEY(actor_id) REFERENCES employees(id));
        CREATE INDEX IF NOT EXISTS idx_asset_lifecycle_asset ON asset_lifecycle_events(asset_id);
        CREATE TABLE IF NOT EXISTS document_review_events (
          id INTEGER PRIMARY KEY, document_id INTEGER NOT NULL, reviewer_id INTEGER NOT NULL,
          decision TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', expires_on TEXT,
          reviewed_at TEXT NOT NULL,
          FOREIGN KEY(document_id) REFERENCES documents(id),
          FOREIGN KEY(reviewer_id) REFERENCES employees(id));
        CREATE INDEX IF NOT EXISTS idx_document_review_doc ON document_review_events(document_id);
        CREATE TABLE IF NOT EXISTS employee_preferences (
          employee_id INTEGER PRIMARY KEY, date_format TEXT NOT NULL DEFAULT 'DD MMM YYYY',
          density TEXT NOT NULL DEFAULT 'Comfortable', reduce_motion INTEGER NOT NULL DEFAULT 0,
          updated_at TEXT NOT NULL, FOREIGN KEY(employee_id) REFERENCES employees(id));
        ''')


class AssetAction(BaseModel):
    action: Literal['Return', 'Transfer', 'Send for repair', 'Restore to service', 'Reassign']
    new_employee_id: int | None = None
    note: str = Field(default='', max_length=350)


@app.post('/api/assets/{asset_id}/lifecycle')
def asset_lifecycle(asset_id: int, body: AssetAction, user=Depends(require_hr)):
    with db() as c:
        a = c.execute('SELECT * FROM assets WHERE id=?'+(' FOR UPDATE' if DB_ENGINE=='mysql' else ''), (asset_id,)).fetchone()
        if not a:
            raise HTTPException(404, 'Asset not found')
        state = a['status']
        to_id = a['employee_id']
        action = body.action
        if action == 'Return':
            if state not in ('Assigned', 'Maintenance'):
                raise HTTPException(409, 'Only issued or serviced assets can be returned')
            new_state = 'Returned'
        elif action == 'Send for repair':
            if state != 'Assigned':
                raise HTTPException(409, 'Only assigned assets can be sent for repair')
            new_state = 'Maintenance'
        elif action == 'Restore to service':
            if state != 'Maintenance':
                raise HTTPException(409, 'Asset is not in maintenance')
            new_state = 'Assigned'
        elif action in ('Transfer', 'Reassign'):
            if (action == 'Transfer' and state != 'Assigned') or (action == 'Reassign' and state != 'Returned'):
                raise HTTPException(409, 'Asset must be in the correct state to change custodian')
            if body.new_employee_id is None or body.new_employee_id == a['employee_id']:
                raise HTTPException(422, 'Select a different employee')
            target = c.execute('SELECT id FROM employees WHERE id=? AND account_active=1', (body.new_employee_id,)).fetchone()
            if not target:
                raise HTTPException(422, 'Select an active employee')
            to_id = body.new_employee_id
            new_state = 'Assigned'
        else:
            raise HTTPException(422, 'Invalid asset transition')
        c.execute('UPDATE assets SET employee_id=?,status=? WHERE id=?', (to_id, new_state, asset_id))
        c.execute('''INSERT INTO asset_lifecycle_events(asset_id,actor_id,event_type,from_employee_id,to_employee_id,note,created_at)
                     VALUES(?,?,?,?,?,?,?)''', (asset_id,user['id'],action,a['employee_id'],to_id,body.note.strip(),utcnow()))
        audit(c, user['id'], 'asset.lifecycle', f'asset:{asset_id}', f'{action}: {state} -> {new_state}')
        return {'asset_id':asset_id,'status':new_state,'employee_id':to_id}


@app.get('/api/assets/{asset_id}/lifecycle')
def asset_history(asset_id: int, user=Depends(current_user)):
    with db() as c:
        a = c.execute('SELECT * FROM assets WHERE id=?',(asset_id,)).fetchone()
        if not a:
            raise HTTPException(404,'Asset not found')
        if user['role'] != 'admin' and a['employee_id'] != user['id']:
            raise HTTPException(403,'Asset history is restricted to the current custodian or HR')
        events = rows(c.execute('''SELECT event_type,created_at,actor_id,from_employee_id,to_employee_id,note
                                  FROM asset_lifecycle_events WHERE asset_id=? ORDER BY id DESC''',(asset_id,)))
        if user['role'] != 'admin':
            # Do not disclose prior employees or HR-only maintenance comments.
            return [{'event_type':e['event_type'],'created_at':e['created_at']} for e in events]
        return events


class DocumentReview(BaseModel):
    decision: Literal['Verified','Rejected','Expired']
    note: str = Field(default='',max_length=500)
    expires_on: date | None = None


@app.post('/api/documents/{document_id}/review')
def review_document(document_id: int, body: DocumentReview, user=Depends(require_hr)):
    if body.decision == 'Verified' and body.expires_on and body.expires_on < date.today():
        raise HTTPException(422,'A verified document cannot already be expired')
    if body.decision == 'Rejected' and len(body.note.strip()) < 5:
        raise HTTPException(422,'Provide a reason when rejecting a document')
    with db() as c:
        doc = c.execute('SELECT * FROM documents WHERE id=?',(document_id,)).fetchone()
        if not doc:
            raise HTTPException(404,'Document record not found')
        c.execute('UPDATE documents SET status=? WHERE id=?',(body.decision,document_id))
        c.execute('''INSERT INTO document_review_events(document_id,reviewer_id,decision,note,expires_on,reviewed_at)
                     VALUES(?,?,?,?,?,?)''', (document_id,user['id'],body.decision,body.note.strip(),body.expires_on.isoformat() if body.expires_on else None,utcnow()))
        audit(c,user['id'],'document.reviewed',f'document:{document_id}',body.decision)
        return {'document_id':document_id,'status':body.decision}


@app.get('/api/documents/{document_id}/reviews')
def get_document_reviews(document_id: int, user=Depends(current_user)):
    with db() as c:
        doc = c.execute('SELECT employee_id FROM documents WHERE id=?',(document_id,)).fetchone()
        if not doc:
            raise HTTPException(404,'Document record not found')
        if user['role']!='admin' and doc['employee_id']!=user['id']:
            raise HTTPException(403,'Document reviews are private')
        events=rows(c.execute('''SELECT decision,expires_on,reviewed_at,reviewer_id,note FROM document_review_events
                                 WHERE document_id=? ORDER BY id DESC''',(document_id,)))
        if user['role']=='admin':
            return events
        return [{'decision':x['decision'],'expires_on':x['expires_on'],'reviewed_at':x['reviewed_at']} for x in events]


class Preferences(BaseModel):
    date_format: Literal['DD MMM YYYY','YYYY-MM-DD','MM/DD/YYYY']='DD MMM YYYY'
    density: Literal['Comfortable','Compact']='Comfortable'
    reduce_motion: bool=False


@app.get('/api/me/preferences')
def my_preferences(user=Depends(current_user)):
    with db() as c:
        r=c.execute('SELECT date_format,density,reduce_motion FROM employee_preferences WHERE employee_id=?',(user['id'],)).fetchone()
        if not r:
            return Preferences().model_dump()
        return {'date_format':r['date_format'],'density':r['density'],'reduce_motion':bool(r['reduce_motion'])}


@app.put('/api/me/preferences')
def save_preferences(body: Preferences, user=Depends(current_user)):
    with db() as c:
        c.execute('''INSERT INTO employee_preferences(employee_id,date_format,density,reduce_motion,updated_at)
                     VALUES(?,?,?,?,?) ON CONFLICT(employee_id) DO UPDATE SET
                     date_format=excluded.date_format,density=excluded.density,
                     reduce_motion=excluded.reduce_motion,updated_at=excluded.updated_at''',
                  (user['id'],body.date_format,body.density,int(body.reduce_motion),utcnow()))
        audit(c,user['id'],'preferences.updated',f'employee:{user["id"]}', 'Display preferences updated')
    return body.model_dump()


@app.get('/api/ai/capabilities')
def ai_capabilities(user=Depends(current_user)):
    # Capability status does not imply an external LLM is connected.
    import os
    provider_ready=bool(os.getenv('AI_API_KEY'))
    return {'account_lookup':True,'policy_lookup':True,'llm_configured':provider_ready,
            'write_actions':False,'message_storage':'Browser session only',
            'privacy_note':'Never submit passwords, government identifiers, or private case information to the assistant.'}


@app.get('/api/admin/employee-services/summary')
def employee_services_summary(user=Depends(require_hr)):
    with db() as c:
        def count(sql): return c.execute(sql).fetchone()[0]
        return {'issued_assets':count("SELECT COUNT(*) FROM assets WHERE status='Assigned'"),
                'returned_assets':count("SELECT COUNT(*) FROM assets WHERE status='Returned'"),
                'maintenance_assets':count("SELECT COUNT(*) FROM assets WHERE status='Maintenance'"),
                'documents_pending':count("SELECT COUNT(*) FROM documents WHERE status='Pending'"),
                'documents_rejected':count("SELECT COUNT(*) FROM documents WHERE status='Rejected'")}
