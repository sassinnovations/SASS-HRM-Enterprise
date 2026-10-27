"""Backend identity regression checks; isolated test DB only."""
import os, tempfile
from pathlib import Path
os.environ['SASS_HRM_TESTING']='1'
os.environ['DB_ENGINE']='sqlite'
os.environ['JWT_SECRET']='read-only-runtime-test-secret-at-least-forty-characters-abcdef'
from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory() as tmp:
 os.environ['DATABASE_PATH']=str(Path(tmp)/'isolation.db')
 import main
 with TestClient(main.app) as client:
  status=client.get('/api/health').json()
  assert status['status']=='ok' and status['database']=='sqlite'
  assert status['version']==main.app.version=='4.5.0'
  assert client.get('/api/admin/setup/overview').status_code==401
  print('PASS: backend version visible through health; protected setup endpoint; isolated SQLite test only')
