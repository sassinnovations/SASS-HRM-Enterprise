"""File-settings/vault integration regression with a local simulated ClamAV socket.

Does not require MySQL, Docker, or network downloads. Does NOT test an actual
antivirus engine, production database, or browser file picker.
"""
from __future__ import annotations

import base64
import hashlib
import os
import socketserver
import struct
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite',
                  JWT_SECRET='vault-regression-only-secret-long-enough-0123456789')


class ClamDHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = bytearray()
        while not data.endswith(b'\x00'):
            chunk = self.request.recv(1)
            if not chunk:
                return
            data.extend(chunk)
            if len(data) > 100:
                return
        if data == b'zPING\x00':
            self.request.sendall(b'PONG\x00')
            return
        if data != b'zINSTREAM\x00':
            return
        document = bytearray()
        while True:
            count = self._read_exact(4)
            if len(count) != 4:
                return
            length = struct.unpack('!I', count)[0]
            if not length:
                break
            if length > 16384:
                return
            document.extend(self._read_exact(length))
        if b'SIMULATED_VIRUS' in document:
            self.request.sendall(b'stream: Mock.Signature FOUND\x00')
        else:
            self.request.sendall(b'stream: OK\x00')

    def _read_exact(self, count):
        result = bytearray()
        while len(result) < count:
            chunk = self.request.recv(count - len(result))
            if not chunk:
                break
            result.extend(chunk)
        return bytes(result)


class Scanner(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def run():
    with tempfile.TemporaryDirectory() as folder, Scanner(('127.0.0.1', 0), ClamDHandler) as scanner:
        os.environ['DATABASE_PATH'] = str(Path(folder) / 'vault_regression.sqlite')
        os.environ['VAULT_FERNET_KEY'] = Fernet.generate_key().decode('ascii')
        os.environ['VAULT_AV_HOST'] = '127.0.0.1'
        os.environ['VAULT_AV_PORT'] = str(scanner.server_address[1])
        worker = threading.Thread(target=scanner.serve_forever, daemon=True)
        worker.start()
        try:
            import main
            import operations_v09
            with TestClient(main.app) as client:
                with main.db() as conn:
                    for code, name, email, role in (
                        ('ADMIN', 'Admin', 'vault-admin@example.test', 'admin'),
                        ('USER1', 'Employee One', 'vault-1@example.test', 'employee'),
                        ('USER2', 'Employee Two', 'vault-2@example.test', 'employee')):
                        conn.execute('''INSERT INTO employees
                            (code,name,email,role,designation,department,location,work_mode,
                            join_date,manager_id,password_hash,account_active)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,1)''',
                            (code, name, email, role, 'Engineer', 'IT', 'Hyderabad',
                             'On-site', '2026-01-01', None, main.hash_password('VaultOnlyPassword!123')))
                def session(email):
                    r = client.post('/api/auth/login',json={'email': email,'password':'VaultOnlyPassword!123'})
                    assert r.status_code == 200, r.text
                    return {'Authorization': 'Bearer ' + r.json()['token']}
                admin=session('vault-admin@example.test')
                owner=session('vault-1@example.test')
                other=session('vault-2@example.test')
                with main.db() as c:
                    owner_id=c.execute("SELECT id FROM employees WHERE code='USER1'").fetchone()['id']
                    other_id=c.execute("SELECT id FROM employees WHERE code='USER2'").fetchone()['id']
                assert client.get('/api/vault/status',headers=owner).json()['enabled'] is True
                assert client.get('/api/vault/status').status_code == 401

                content=b'A small legitimate employee test document\n'
                def document(employee=owner_id,content=content,name='employment.txt',mime='text/plain'):
                    return {'employee_id':employee,'filename':name,'mime_type':mime,
                            'category':'Employment','data_base64':base64.b64encode(content).decode('ascii')}
                assert client.post('/api/vault/files',json=document()).status_code==401
                # Attempts to scan a different employee's content must be rejected first.
                with patch.object(operations_v09,'scan_file') as scan:
                    denied=client.post('/api/vault/files',headers=owner,json=document(employee=other_id))
                    assert denied.status_code==403, denied.text
                    scan.assert_not_called()
                assert client.post('/api/vault/files',headers=owner,json=document(name='../bad.txt')).status_code==422
                assert client.post('/api/vault/files',headers=owner,json=document(name='bad.pdf',mime='application/pdf')).status_code==422
                assert client.post('/api/vault/files',headers=owner,json=document(content=b'\x00',name='bad.txt')).status_code==422
                assert client.post('/api/vault/files',headers=owner,json=document(content=b'a'*(2*1024*1024+1))).status_code in (413,422)
                assert client.post('/api/vault/files',headers=owner,json=document(content=b'SIMULATED_VIRUS')).status_code==422

                r=client.post('/api/vault/files',headers=owner,json=document())
                assert r.status_code==201, r.text
                file_id=r.json()['id']
                assert r.json()['sha256']==hashlib.sha256(content).hexdigest()
                with main.db() as c:
                    ciphertext=bytes(c.execute('SELECT contents FROM document_vault WHERE id=?',(file_id,)).fetchone()['contents'])
                    assert ciphertext.startswith(operations_v09.VAULT_PREFIX)
                    assert content not in ciphertext
                assert len(client.get('/api/vault/files',headers=owner).json())==1
                assert client.get('/api/vault/files',headers=other).json()==[]
                assert len(client.get('/api/vault/files',headers=admin).json())==1
                assert client.get(f'/api/vault/files/{file_id}/download',headers=other).status_code==403
                assert client.delete(f'/api/vault/files/{file_id}',headers=other).status_code==403
                for headers in (owner, admin):
                    download=client.get(f'/api/vault/files/{file_id}/download',headers=headers)
                    assert download.status_code==200 and download.content==content
                    assert download.headers['x-content-type-options']=='nosniff'
                    assert 'no-store' in download.headers['cache-control']
                # Key loss or scanner unavailability block reading without returning plaintext.
                with patch.dict(os.environ,{'VAULT_FERNET_KEY':''}):
                    assert client.get('/api/vault/status',headers=owner).json()['enabled'] is False
                    assert client.get(f'/api/vault/files/{file_id}/download',headers=owner).status_code==503
                with patch.dict(os.environ,{'VAULT_FERNET_KEY':'!!invalid-base64!!'}):
                    assert client.get('/api/vault/status',headers=owner).json()['enabled'] is False
                    assert client.get(f'/api/vault/files/{file_id}/download',headers=owner).status_code==503
                with patch.dict(os.environ,{'VAULT_AV_PORT':'not-a-number'}):
                    assert client.get('/api/vault/status',headers=owner).json()['enabled'] is False
                    assert client.get(f'/api/vault/files/{file_id}/download',headers=owner).status_code==503
                with patch.dict(os.environ,{'VAULT_AV_PORT':'1'}):
                    assert client.get('/api/vault/status',headers=owner).json()['enabled'] is False
                    assert client.get(f'/api/vault/files/{file_id}/download',headers=owner).status_code==503
                    # Authorized deletion must continue to work during outages.
                    deleted=client.delete(f'/api/vault/files/{file_id}',headers=owner)
                    assert deleted.status_code==200 and deleted.json()['deleted'] is True
                assert client.get(f'/api/vault/files/{file_id}/download',headers=owner).status_code==404
                with main.db() as c:
                    events=[r['action'] for r in c.execute("SELECT action FROM audit_events WHERE action LIKE 'vault.%'").fetchall()]
                    assert {'vault.file_uploaded','vault.file_downloaded','vault.file_deleted'} <= set(events)
            print('PASS: real-socket scanner simulation, vault status, encrypted upload, input validation, infection blocking, owner/admin restrictions, download/delete, fail-closed key/scanner, audits')
        finally:
            scanner.shutdown()
            worker.join(timeout=5)


if __name__=='__main__':
    run()
