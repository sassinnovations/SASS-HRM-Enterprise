"""Large local JD imports without HTTP/proxy timeouts.

Run on the trusted backend host with valid MySQL credentials configured:
  python server/jd_bulk_import_cli.py /path/to/jds.xlsx --admin-id 1
  python server/jd_bulk_import_cli.py /path/to/jds.xlsx --admin-id 1 --apply --confirm-sha256 HASH

No candidate, payroll, attendance, or other business records are written.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys
from pathlib import Path
from urllib.parse import quote

from starlette.requests import Request


def local_request(path: Path, checksum='') -> Request:
    file=path.open('rb')
    more=True

    async def receive():
        nonlocal more
        if not more:
            return {'type':'http.request','body':b'','more_body':False}
        block=file.read(1024*1024)
        if block:
            return {'type':'http.request','body':block,'more_body':True}
        more=False
        file.close()
        return {'type':'http.request','body':b'','more_body':False}

    headers=[(b'x-filename',quote(path.name).encode('ascii'))]
    if checksum:
        headers.append((b'x-confirm-sha256',checksum.encode('ascii')))
    return Request({'type':'http','http_version':'1.1','method':'POST',
                    'path':'/api/job-descriptions/import','headers':headers},receive)


async def main():
    parser=argparse.ArgumentParser(description='Preview/import up to 1,000,000 JDs using local disk and MySQL')
    parser.add_argument('file',type=Path,help='CSV or XLSX job descriptions')
    parser.add_argument('--admin-id',type=int,required=True,help='Active HR admin employee ID for the audit trail')
    parser.add_argument('--apply',action='store_true',help='Actually import; without it only preview')
    parser.add_argument('--confirm-sha256',default='',help='SHA-256 from previous preview, mandatory for --apply')
    parser.add_argument('--duplicate-mode',choices=('skip','reject'),default='skip')
    parser.add_argument('--invalid-mode',choices=('reject','skip'),default='reject')
    args=parser.parse_args()

    if not args.file.is_file() or args.file.suffix.lower() not in ('.xlsx','.csv'):
        parser.error('Existing .xlsx or .csv file required')
    from main import db
    from job_descriptions import MAX_UPLOAD, preview_jd_import, import_jds
    if args.file.stat().st_size>MAX_UPLOAD:
        parser.error('File exceeds the 512 MB upload cap; split the workbook')
    with db() as conn:
        actor=conn.execute('SELECT id,role,account_active FROM employees WHERE id=?',(args.admin_id,)).fetchone()
        if not actor or actor['role']!='admin' or not actor['account_active']:
            parser.error('Selected employee is not an active HR administrator')
    user={'id':args.admin_id,'role':'admin'}
    if args.apply:
        if len(args.confirm_sha256)!=64 or not all(c in '0123456789abcdef' for c in args.confirm_sha256.lower()):
            parser.error('--apply requires the 64-character SHA-256 checksum from a prior preview')
        result=await import_jds(local_request(args.file,args.confirm_sha256),
                                duplicate_mode=args.duplicate_mode,
                                invalid_mode=args.invalid_mode,user=user)
        print('COMMITTED',result)
    else:
        result=await preview_jd_import(local_request(args.file),user=user)
        print('PREVIEW', {k:v for k,v in result.items() if k not in ('preview','issues')})
        if result['issues']:
            print('FIRST ISSUES:',result['issues'][:10])
        print('Run with --apply --confirm-sha256',result['sha256'],
              'to import. Default behavior rejects invalid rows.')


if __name__=='__main__':
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f'JD import failed: {exc}',file=sys.stderr)
        raise SystemExit(1) from exc
