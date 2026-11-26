"""Scalability regression: verifies >2000 rows, bounded previews and safety behavior.

Does not generate/import one million live rows; full capacity must be load-tested on
production-equivalent MySQL before promising throughput/timeouts.
"""
from __future__ import annotations
import hashlib
import io
import os
import tempfile
from pathlib import Path

os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',
                  JWT_SECRET='test-jd-scalability-only-secret-long-012345678901')


def main():
    from fastapi.testclient import TestClient
    from openpyxl import Workbook
    with tempfile.TemporaryDirectory() as root:
        os.environ['DATABASE_PATH']=str(Path(root)/'jd-scale.sqlite')
        import main as m
        import job_descriptions as jd
        assert jd.MAX_IMPORT_ROWS==1_000_000
        assert jd.MAX_UPLOAD>=128*1024*1024
        with TestClient(m.app) as client:
            with m.db() as conn:
                conn.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,
                    join_date,password_hash,account_active) VALUES(?,?,?,?,?,?,?,?,?,1)''',
                    ('AD','Import Administrator','admin@invalid.example','admin','HR admin','HR','India','2026-01-01',
                     m.hash_password('LongImportTestPass123!')))
            token=client.post('/api/auth/login',json={
                'email':'admin@invalid.example','password':'LongImportTestPass123!'}).json()['token']
            h={'Authorization':'Bearer '+token,'x-filename':'3005-jds.csv'}
            parts=['Job Posting Title,Description']
            for n in range(3001):
                parts.append(f'Large JD {n:05d},Senior developer responsibilities at large company {n:05d}.')
            parts.append(parts[1])  # duplicate within the upload
            parts.append(',Missing posting title with otherwise valid text')
            parts.append('Wrong status,"Short"')
            raw=('\n'.join(parts)+'\n').encode()
            sha=hashlib.sha256(raw).hexdigest()
            preview=client.post('/api/job-descriptions/import/preview',headers=h,content=raw)
            assert preview.status_code==200,preview.text
            info=preview.json()
            assert info['total_rows']==3004,info
            assert info['valid_rows']==3002 and info['invalid_rows']==2,info
            assert info['duplicates']==1 and len(info['preview'])==20,info
            wrong=client.post('/api/job-descriptions/import?invalid_mode=reject',
                              headers={**h,'x-confirm-sha256':sha},content=raw)
            assert wrong.status_code==422,wrong.text
            assert client.get('/api/job-descriptions',headers=h).json()['total']==0
            saved=client.post('/api/job-descriptions/import?invalid_mode=skip&duplicate_mode=skip',
                              headers={**h,'x-confirm-sha256':sha},content=raw)
            assert saved.status_code==200,saved.text
            result=saved.json()
            assert result['imported']==3001 and result['skipped']==3 and result['invalid_skipped']==2,result
            assert client.get('/api/job-descriptions',headers=h).json()['total']==3001
            # Re-import same file: no new JDs and all 3002 valid rows are duplicates.
            again=client.post('/api/job-descriptions/import?invalid_mode=skip',
                              headers={**h,'x-confirm-sha256':sha},content=raw)
            assert again.status_code==200 and again.json()['imported']==0 and again.json()['skipped']==3004
            with m.db() as conn:
                assert conn.execute('SELECT COUNT(*) AS n FROM candidates').fetchone()['n']==0
                assert conn.execute('SELECT COUNT(*) AS n FROM jd_import_batches').fetchone()['n']==2
            # Check row-boundary rejection without creating a million-line fixture.
            jd.MAX_IMPORT_ROWS=2
            too_many=client.post('/api/job-descriptions/import/preview',headers=h,content=raw)
            assert too_many.status_code==413 and 'at most 2 rows' in too_many.text
            jd.MAX_IMPORT_ROWS=1_000_000
            # Read-only XLSX export remains valid at >2,000 rows.
            exported=client.get('/api/job-descriptions/export.xlsx',headers=h)
            assert exported.status_code==200,exported.text[:300]
            from openpyxl import load_workbook
            wb=load_workbook(io.BytesIO(exported.content),read_only=True)
            assert sum(1 for _ in wb.active.iter_rows(values_only=True))==3002
            wb.close()
            csv_export=client.get('/api/job-descriptions/export.csv',headers=h)
            assert csv_export.status_code==200 and csv_export.text.count('Large JD')==3001
    print('PASS: 3004-row preview, 3001 JD batch import, duplicate and invalid-row policies, rollback, 1M guard, XLSX/CSV exports, zero candidates')


if __name__=='__main__':main()
