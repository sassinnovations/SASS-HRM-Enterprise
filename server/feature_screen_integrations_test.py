"""Source contracts, auth, isolated SQLite and simulated missing MySQL objects."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',
                  JWT_SECRET='isolated-feature-screen-contracts-test-secret-only-12345678')
from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory() as root:
    os.environ['DATABASE_PATH']=str(Path(root)/'test.sqlite')
    import main
    from feature_screen_integrations import screen_contracts, inspect_feature_screens
    from schema_audit import get_required_schema
    registry=screen_contracts()
    assert len(registry)==73 and len({r['feature_key'] for r in registry})==73
    expected=get_required_schema()
    routes={(m,route.path) for route in main.app.routes for m in getattr(route,'methods',())}
    assert all(('GET',r['representative_get_route']) in routes for r in registry)
    assert all(set(filter(None,r['key_tables'].split(';'))) <= set(expected) for r in registry)
    assert any(not r['key_tables'] for r in registry), 'Non-storage features should remain unverified'
    with TestClient(main.app) as client:
        assert client.get('/api/admin/database/screen-integrations').status_code==401
        with main.db() as c:
            c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,account_active)
                         VALUES(?,?,?,?,?,?,?,?,?,1)''',('A100','Administrator','admin@example.invalid','admin','HR','HR','Office','2026-01-01',main.hash_password('StrongExampleAdminPassword123!')))
            c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,account_active)
                         VALUES(?,?,?,?,?,?,?,?,?,1)''',('E100','Employee','staff@example.invalid','employee','Engineer','IT','Office','2026-01-01',main.hash_password('StrongExampleEmployeePassword123!')))
        def token(email,password):
            r=client.post('/api/auth/login',json={'email':email,'password':password})
            assert r.status_code==200,r.text
            return {'Authorization':'Bearer '+r.json()['token']}
        admin=token('admin@example.invalid','StrongExampleAdminPassword123!')
        staff=token('staff@example.invalid','StrongExampleEmployeePassword123!')
        assert client.get('/api/admin/database/screen-integrations',headers=staff).status_code==403
        response=client.get('/api/admin/database/screen-integrations',headers=admin)
        assert response.status_code==200,response.text
        payload=response.json()
        assert payload['screen_count']==73 and payload['api_routes_registered']==73
        assert not payload['live_mysql_inspected'] and payload['structural_matches']==0
        assert payload['end_to_end_verified_count']==0
        assert all(x['state']=='not_live_verified' for x in payload['screens'])
        assert client.get('/api/admin/database/screen-integrations?probe_tables=true',headers=admin).status_code==200
    fake={'engine':'mysql','database_reachable':True,'schema_complete':False,
          'tables':['employees','hr_task_templates'], 'table_access_probed':True,
          'table_access_failures':['hr_task_templates']}
    sample=inspect_feature_screens(fake,routes)
    emp=next(x for x in sample['screens'] if x['feature_key']=='employees')
    template=next(x for x in sample['screens'] if x['feature_key']=='tasktemplates')
    assert emp['state']=='structural_match' and template['state']=='missing_tables'
    fake['tables'].append('hr_task_template_assignments')
    sample=inspect_feature_screens(fake,routes)
    template=next(x for x in sample['screens'] if x['feature_key']=='tasktemplates')
    assert template['state']=='table_access_failed'
    assert sample['structural_matches']>0 and sample['end_to_end_verified_count']==0
    print('PASS: 73 source contracts, 73 API routes, schema names, auth, SQLite disclaimer, MySQL simulations')
