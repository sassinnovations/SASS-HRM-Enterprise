"""Offline regression tests for manual, photo and external-device attendance."""
import hashlib
import hmac
import json
import os
import secrets
import tempfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from PIL import Image

DEVICE_SECRET='device-secret-'+secrets.token_hex(25)
os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',
                  JWT_SECRET='attendance-integration-secret-12345678901234567890',
                  ATTENDANCE_TIMEZONE='Asia/Kolkata',
                  ATTENDANCE_PHOTO_FERNET_KEY=Fernet.generate_key().decode(),
                  ATTENDANCE_PHOTO_ENABLED='1',ATTENDANCE_DEVICE_ENABLED='1',
                  ATTENDANCE_DEVICE_SECRETS_JSON=json.dumps({'office-scanner-1':DEVICE_SECRET}))

with tempfile.TemporaryDirectory() as root:
    os.environ['DATABASE_PATH']=str(Path(root)/'attendance.db')
    import main
    today=datetime.now(ZoneInfo('Asia/Kolkata')).date().isoformat()
    with TestClient(main.app) as client:
        with main.db() as c:
            for code,email,role in [('HR1','hr@invalid.test','admin'),('STAFF1','staff@invalid.test','employee'),('STAFF2','other@invalid.test','employee')]:
                c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,account_active)
                    VALUES(?,?,?,?,?,?,?,?,?,1)''',(code,code,email,role,'Specialist','HR','Hyderabad','2026-01-01',main.hash_password('StrongPass433!')))
        keys={}
        for role,email in [('hr','hr@invalid.test'),('staff','staff@invalid.test'),('other','other@invalid.test')]:
            resp=client.post('/api/auth/login',json={'email':email,'password':'StrongPass433!'})
            assert resp.status_code==200,resp.text
            keys[role]={'Authorization':'Bearer '+resp.json()['token']}
        def call(role,method,path,payload=None):
            return client.request(method,'/api'+path,headers=keys[role],json=payload)
        with main.db() as c:
            people={r['code']:r['id'] for r in c.execute('SELECT code,id FROM employees')}
        methods=call('staff','GET','/attendance/methods')
        assert methods.status_code==200 and methods.json()['photo_enabled'] and methods.json()['fingerprint_enabled']
        assert call('staff','POST','/attendance/manual',{'employee_id':people['STAFF2'],'work_day':today,'check_in':'09:00','reason':'On-site attendance'}).status_code==403
        assert call('hr','POST','/attendance/manual',{'employee_id':people['STAFF2'],'work_day':today,'check_in':'09:00','reason':'         '}).status_code==422
        invalid=call('hr','POST','/attendance/manual',{'employee_id':people['STAFF2'],'work_day':today,'check_in':'19:00','check_out':'09:00','reason':'Corrected shift'})
        assert invalid.status_code==422,invalid.text
        manual=call('hr','POST','/attendance/manual',{'employee_id':people['STAFF2'],'work_day':today,'check_in':'09:00','check_out':'18:00','reason':'Scanner was under maintenance'})
        assert manual.status_code==201,manual.text
        assert call('hr','POST','/attendance/manual',{'employee_id':people['STAFF2'],'work_day':today,'check_in':'10:00','reason':'Not intended to overwrite'}).status_code==409
        assert any(x['method']=='Manual' for x in call('hr','GET','/attendance/capture-events').json())
        assert all(x['employee_id']!=people['STAFF2'] for x in call('staff','GET','/attendance/capture-events').json())
        image=Image.new('RGB',(180,160),(120,80,55));buffer=BytesIO();image.save(buffer,'JPEG');photo=buffer.getvalue()
        assert client.post('/api/attendance/photo?action=check-in&consent=true',content=photo,headers={'Content-Type':'image/jpeg'}).status_code==401
        assert client.post('/api/attendance/photo?action=check-in&consent=false',content=photo,headers={**keys['staff'],'Content-Type':'image/jpeg'}).status_code==422
        assert client.post('/api/attendance/photo?action=check-in&consent=true',content=b'not an image',headers={**keys['staff'],'Content-Type':'image/jpeg'}).status_code==422
        checkin=client.post('/api/attendance/photo?action=check-in&consent=true',content=photo,headers={**keys['staff'],'Content-Type':'image/jpeg'})
        assert checkin.status_code==201,checkin.text
        event_id=checkin.json()['id']
        with main.db() as c:
            stored=c.execute('SELECT ciphertext FROM attendance_photo_evidence WHERE event_id=?',(event_id,)).fetchone()['ciphertext']
            assert photo not in stored and bytes(stored)!=photo
        assert call('other','GET',f'/attendance/photo-evidence/{event_id}').status_code==403
        proof=call('hr','GET',f'/attendance/photo-evidence/{event_id}')
        assert proof.status_code==200 and proof.content.startswith(b'\xff\xd8\xff') and proof.headers['cache-control']=='private, no-store'
        assert call('staff','GET',f'/attendance/photo-evidence/{event_id}').status_code==200
        assert client.post('/api/attendance/photo?action=check-in&consent=true',content=photo,headers={**keys['staff'],'Content-Type':'image/jpeg'}).status_code==409
        out=client.post('/api/attendance/photo?action=check-out&consent=true',content=photo,headers={**keys['staff'],'Content-Type':'image/jpeg'})
        assert out.status_code==201,out.text
        assert call('other','DELETE',f'/attendance/photo-evidence/{event_id}').status_code==403
        assert call('staff','DELETE',f'/attendance/photo-evidence/{event_id}').status_code==200
        assert call('staff','GET',f'/attendance/photo-evidence/{event_id}').status_code==404
        assert any(x['method']=='Photo' for x in call('staff','GET','/attendance/capture-events').json())
        # New employee used for signed device test; manual and photo records remain untouched.
        with main.db() as c:
            c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,account_active)
              VALUES(?,?,?,?,?,?,?,?,?,1)''',('DEVICE1','Device staff','device@invalid.test','employee','Worker','HR','Hyderabad','2026-01-01',main.hash_password('StrongPass433!')))
        def device_send(modality,action,nonce,signature_override=None,code='DEVICE1'):
            body={'device_id':'office-scanner-1','employee_code':code,'modality':modality,'action':action,
                  'matched':True,'observed_at':datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(),'nonce':nonce}
            raw=json.dumps(body,separators=(',',':')).encode()
            sig=signature_override or hmac.new(DEVICE_SECRET.encode(),raw,hashlib.sha256).hexdigest()
            return client.post('/api/attendance/biometric/device-event',content=raw,
                               headers={'Content-Type':'application/json','X-SASS-Device-Signature':sig})
        assert device_send('fingerprint','check-in',secrets.token_hex(16),signature_override='0'*64).status_code==401
        nonce=secrets.token_hex(16)
        punch=device_send('fingerprint','check-in',nonce)
        assert punch.status_code==201,punch.text
        assert device_send('fingerprint','check-in',nonce).status_code==409
        assert device_send('iris','check-out',secrets.token_hex(16)).status_code==201
        with main.db() as c:
            stored_events=[dict(x) for x in c.execute("SELECT * FROM attendance_capture_events WHERE device_id='office-scanner-1'")]
            assert {x['method'] for x in stored_events}=={'Fingerprint','Iris'}
            assert not any('template' in k or 'raw_image' in k for e in stored_events for k in e)
            assert c.execute('SELECT COUNT(*) FROM attendance_device_nonces').fetchone()[0]==2
        assert call('hr','GET','/attendance/capture-events').status_code==200
        # Disable both optional modalities; manual remains available even with no hardware/keys.
        os.environ['ATTENDANCE_PHOTO_ENABLED']='0'; os.environ['ATTENDANCE_DEVICE_ENABLED']='0'
        assert call('staff','GET','/attendance/methods').json()['photo_enabled'] is False
        assert client.post('/api/attendance/photo?action=check-in&consent=true',content=photo,headers={**keys['other'],'Content-Type':'image/jpeg'}).status_code==503
        assert device_send('iris','check-in',secrets.token_hex(16)).status_code==503
        assert call('staff','POST','/attendance/manual',{'employee_id':people['STAFF1'],'work_day':today,'check_in':'09:00','reason':'Not authorized'}).status_code==403
        print('PASS attendance modalities: manual HR controls, photo consent/encryption/privacy, device signature/replay, capture history, disabled-mode behavior')
