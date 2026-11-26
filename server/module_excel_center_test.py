"""Isolated read/write coverage of approved module Excel operations (no production MySQL)."""
import base64
import io
import json
import os
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

os.environ['SASS_HRM_TESTING'] = '1'
os.environ['DB_ENGINE'] = 'sqlite'
os.environ['JWT_SECRET'] = 'SASS-HRM-EXCEL-TEST-ONLY-NOT-A-PRODUCTION-SECRET-123456789'
from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as directory:
    os.environ['DATABASE_PATH'] = str(Path(directory) / 'test.db')
    import main
    from module_excel_center import DATASETS, build_xlsx
    with TestClient(main.app) as client:
        with main.db() as conn:
            for code, email, role in [('AEX','admin@example.org','admin'), ('TEX','staff@example.org','employee'), ('BEX','otheradmin@example.org','admin')]:
                conn.execute('''INSERT INTO employees(code,name,email,work_email,role,designation,department,location,work_mode,join_date,password_hash,account_active)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,1)''', (code, code, email, email, role, 'Staff', 'Operations', 'Hyderabad', 'Hybrid', '2026-01-01', main.hash_password('StrongPassword123!')))
        def head(email):
            response = client.post('/api/auth/login', json={'email':email,'password':'StrongPassword123!'})
            assert response.status_code == 200, response.text
            return {'Authorization': 'Bearer ' + response.json()['token']}
        admin, staff, other = [head(x) for x in ['admin@example.org','staff@example.org','otheradmin@example.org']]
        path='/api/admin/excel/catalog'
        assert client.get(path).status_code == 401
        assert client.get(path,headers=staff).status_code == 403
        catalog = client.get(path,headers=admin)
        assert catalog.status_code == 200, catalog.text
        assert len(catalog.json()['features']) == 73
        assert len(catalog.json()['datasets']) == len(DATASETS) == 26
        assert sorted(x['key'] for x in catalog.json()['datasets'] if x['importable']) == ['hr_task_templates', 'office_locations', 'service_categories']
        assert client.get('/api/admin/excel/export/employees.xlsx',headers=admin).status_code == 404
        assert client.get('/api/admin/excel/export/employee_directory.xlsx',headers=staff).status_code == 403
        response=client.get('/api/admin/excel/export/employee_directory.xlsx',headers=admin)
        assert response.status_code==200,response.text
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            assert 'xl/worksheets/sheet1.xml' in z.namelist()
            data=z.read('xl/worksheets/sheet1.xml').decode()
            assert 'admin@example.org' in data and 'password_hash' not in data and 'StrongPassword123!' not in data
            ET.fromstring(data)
        with main.db() as conn:
            conn.execute("UPDATE employees SET designation=? WHERE code='TEX'", ('=HYPERLINK("evil")',))
        response=client.get('/api/admin/excel/export/employee_directory.xlsx',headers=admin)
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            data=z.read('xl/worksheets/sheet1.xml').decode()
            assert "'=HYPERLINK" in data, 'Injection-leading formula must be escaped as plain Excel text'
        assert client.get('/api/admin/excel/template/employee_directory.xlsx',headers=admin).status_code==404
        assert client.get('/api/admin/excel/database.xlsx?limit=2',headers=staff).status_code==403
        workbook=client.get('/api/admin/excel/database.xlsx?limit=2',headers=admin)
        assert workbook.status_code==200,workbook.text
        with zipfile.ZipFile(io.BytesIO(workbook.content)) as z:
            assert len([s for s in z.namelist() if s.startswith('xl/worksheets/sheet') and s.endswith('.xml')])==27
            assert b'not a' in z.read('xl/worksheets/sheet1.xml').lower() or b'NOT a' in z.read('xl/worksheets/sheet1.xml')

        def payload(key,headers,values):
            b=build_xlsx([('Import',list(headers),values)])
            return {'filename':key+'.xlsx','file_base64':base64.b64encode(b).decode()}
        cases=[('office_locations', ('code','name','city','country','address','timezone','is_active'), [['HYD01','Hyderabad Office','Hyderabad','India','Hi-tech City','Asia/Kolkata','true']]),
          ('service_categories',('name','description'),[['Hardware Requests','Laptops and office hardware']]),
          ('hr_task_templates',('title','guidance','priority','due_offset_days'),[['New Joiner Basics','Set up access','Normal',3]])]
        for key,cols,values in cases:
            content=payload(key,cols,values)
            assert client.post(f'/api/admin/excel/import/{key}/preview',headers=staff,json=content).status_code==403
            assert client.post(f'/api/admin/excel/import/{key}/commit',headers=admin,json=content).status_code==409
            response=client.post(f'/api/admin/excel/import/{key}/preview',headers=admin,json=content)
            assert response.status_code==200,response.text
            preview=response.json()
            assert preview['valid_rows']==1 and not preview['errors'],preview
            assert client.post(f'/api/admin/excel/import/{key}/commit',headers=other,json={**content,'preview_token':preview['preview_token']}).status_code==409
            tampered=client.post(f'/api/admin/excel/import/{key}/commit',headers=admin,json={**content,'file_base64':'ZZZZ'+content['file_base64'][4:],'preview_token':preview['preview_token']});assert tampered.status_code in (409,422),(tampered.status_code,tampered.text)
            confirmed=client.post(f'/api/admin/excel/import/{key}/commit',headers=admin,json={**content,'preview_token':preview['preview_token']})
            assert confirmed.status_code==201,confirmed.text
            assert confirmed.json()['created']==1
            assert client.post(f'/api/admin/excel/import/{key}/commit',headers=admin,json={**content,'preview_token':preview['preview_token']}).status_code==409
            assert client.post(f'/api/admin/excel/import/{key}/preview',headers=admin,json=content).json()['errors']
        # Existing CRUD continues to operate on newly imported records.
        offices=client.get('/api/admin/organization/offices',headers=admin).json()
        assert offices[0]['code']=='HYD01'
        assert client.put(f"/api/admin/organization/offices/{offices[0]['id']}",headers=admin,json={
          'code':'HYD01','name':'Hyderabad Office Updated','city':'Hyderabad','country':'India',
          'address':'Hi-tech City','timezone':'Asia/Kolkata','is_active':True}).status_code==200
        tasks=client.get('/api/workforce/task-templates',headers=admin).json()
        assert len(tasks)==1 and tasks[0]['title']=='New Joiner Basics'
        assert client.put(f"/api/workforce/task-templates/{tasks[0]['id']}",headers=admin,json={
          'title':'New Joiner Basics Updated','guidance':'Set up access','priority':'Normal','due_offset_days':3}).status_code==200
        # A malformed second row prevents the first row being saved (transactional no partial import).
        invalid=payload('office_locations',cases[0][1],[['MUM01','Mumbai Office','Mumbai','India','','Asia/Kolkata',1], ['BADD','Bad Zone','Delhi','India','','Invalid/Timezone',1]])
        preview=client.post('/api/admin/excel/import/office_locations/preview',headers=admin,json=invalid)
        assert preview.status_code==200,preview.text
        assert preview.json()['errors'] and preview.json()['preview_token'] is None
        assert not any(x['code']=='MUM01' for x in client.get('/api/admin/organization/offices',headers=admin).json())
        # Duplicate entries in the same worksheet are rejected.
        duplicate=payload('service_categories',cases[1][1],[['Repeat Name','one'],['Repeat Name','two']])
        r=client.post('/api/admin/excel/import/service_categories/preview',headers=admin,json=duplicate)
        assert r.status_code==200,r.text
        assert r.json()['valid_rows']==0 and r.json()['errors']
        with main.db() as conn:
            events=[x['action'] for x in conn.execute('SELECT action FROM audit_events ORDER BY id')]
            assert events.count('excel.import_create') == 3 and 'excel.export_workbook' in events
        print('PASS: 73 feature links, 26 curated Excel sheets, roles, formula safety, 3 create-only imports, preview signature, duplicate/atomic validation, existing editor compatibility and audit')
