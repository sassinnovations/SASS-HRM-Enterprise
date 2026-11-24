"""v4.4 profile image lifecycle, opt-in sharing, editing and SQL persistence."""
import os
import tempfile
from io import BytesIO
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient
os.environ['SASS_HRM_TESTING']='1'
os.environ['DB_ENGINE']='sqlite'
os.environ['JWT_SECRET']='V44-TEST-SECRET-ONLY-DO-NOT-USE-IN-REAL-APPLICATION-123'
with tempfile.TemporaryDirectory() as tmp:
    os.environ['DATABASE_PATH']=str(Path(tmp)/'test.db')
    import main
    from main import db,hash_password
    with TestClient(main.app) as client:
        with db() as conn:
            for code,name,email,role in [('ADMIN-1','Admin','administrator@example.test','admin'),('EMP-1','First','first@example.test','employee'),('EMP-2','Second','second@example.test','employee')]:
                conn.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,work_mode,join_date,manager_id,password_hash,account_active)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?,1)''',(code,name,email,role,'Engineer','Engineering','Hyderabad','On-site','2026-09-01',None,hash_password('SecurePassword1234!')))
        def header(email):
            login=client.post('/api/auth/login',json={'email':email,'password':'SecurePassword1234!'})
            assert login.status_code==200,login.text
            return {'Authorization':'Bearer '+login.json()['token']}
        first=header('first@example.test');second=header('second@example.test');admin=header('administrator@example.test')
        picture=Image.new('RGB',(1000,680),'purple');stream=BytesIO();picture.save(stream,format='PNG');valid=stream.getvalue()
        assert client.put('/api/profile/me/photo',content=valid,headers={'Content-Type':'image/png'}).status_code==401
        assert client.put('/api/profile/me/photo',content=b'<svg></svg>',headers={**first,'Content-Type':'image/svg+xml'}).status_code==415
        assert client.put('/api/profile/me/photo',content=b'not a png',headers={**first,'Content-Type':'image/png'}).status_code==422
        assert client.put('/api/profile/me/photo',content=b'x'*(2*1024*1024+1),headers={**first,'Content-Type':'image/png'}).status_code==413
        uploaded=client.put('/api/profile/me/photo',content=valid,headers={**first,'Content-Type':'image/png'})
        assert uploaded.status_code==200,uploaded.text
        me=client.get('/api/profile/me',headers=first).json()
        assert bool(me['has_photo']) is True and 'password_hash' not in me
        photo=client.get('/api/profile/me/photo',headers=first)
        assert photo.status_code==200 and photo.headers['content-type']=='image/jpeg' and photo.content[:3]==b'\xff\xd8\xff'
        assert photo.headers['cache-control']=='private, no-store'
        with Image.open(BytesIO(photo.content)) as image:
            assert max(image.size)<=512
            assert not image.info.get('exif')
        with db() as conn:
            assert conn.execute('SELECT length(photo_bytes) AS length FROM profile_photos WHERE employee_id=?',(me['id'],)).fetchone()['length']>100
        # Other employees can only view opted-in directory portraits.
        assert client.get(f'/api/profile/directory/{me["id"]}/photo',headers=second).status_code==200
        assert client.put('/api/profile/me',json={'preferred_name':'First Initial','headline':'Tester','directory_visible':False},headers=first).status_code==200
        assert client.get(f'/api/profile/directory/{me["id"]}/photo',headers=second).status_code==404
        assert client.get(f'/api/profile/directory/{me["id"]}/photo',headers=admin).status_code==404
        assert client.get('/api/profile/me/photo',headers=first).status_code==200
        # Account and HR identity untouched when deleting self-service fields.
        cleared=client.delete('/api/profile/me/optional',headers=first)
        assert cleared.status_code==200 and cleared.json()['headline']=='' and not cleared.json()['has_photo']
        assert cleared.json()['email']=='first@example.test'
        assert client.get('/api/profile/me/photo',headers=first).status_code==404
        assert client.post('/api/auth/login',json={'email':'first@example.test','password':'SecurePassword1234!'}).status_code==200
        assert client.put('/api/profile/me/photo',content=valid,headers={**first,'Content-Type':'image/png'}).status_code==200
        assert client.delete('/api/profile/me/photo',headers=first).json()['has_photo'] is False
        assert client.delete('/api/profile/me/photo',headers=first).status_code==200
        with db() as conn:
            entries=[r['action'] for r in conn.execute("SELECT action FROM audit_events WHERE action LIKE 'profile.%'").fetchall()]
            for action in ('profile.photo.updated','profile.photo.deleted','profile.optional_cleared'):
                assert action in entries,entries
        print('PASS: sanitized binary photo upload, session checks, directory privacy, removal, optional reset, password preserved, auditing')
