"""One-time bootstrap of the first SASS HRM administrator into an empty database."""
from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).with_name('.env'))
from main import db, hash_password, audit


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--email',required=True,help='Administrator work email')
    parser.add_argument('--developer',action='store_true',help='Grant read-only developer diagnostics access to this same administrator account')
    parser.add_argument('--name',required=True,help='Full display name')
    parser.add_argument('--code',required=True,help='Unique employee code')
    parser.add_argument('--department',default='Human Resources')
    parser.add_argument('--location',required=True,help='Primary office location')
    args=parser.parse_args()
    if os.getenv('DB_ENGINE', 'mysql') != 'mysql' and os.getenv('SASS_HRM_TESTING') != '1':
        raise SystemExit('Administrator setup requires MySQL')
    if not __import__('re').fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', args.email.strip()):
        raise SystemExit('Supply a valid work email address')
    password=getpass.getpass('Choose a NEW unique admin password (at least 12 characters): ')
    password2=getpass.getpass('Repeat the password: ')
    if password!=password2 or len(password)<12 or not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise SystemExit('Passwords must match and contain at least 12 characters, letters and digits.')
    with db() as c:
        if c.execute('SELECT COUNT(*) FROM employees').fetchone()[0] != 0:
            raise SystemExit('Initial bootstrap is allowed only when employees is empty. Use HR account management afterwards.')
        if c.execute('SELECT 1 FROM employees WHERE lower(email)=lower(?) OR code=?',(args.email.strip(),args.code)).fetchone():
            raise SystemExit('Email or employee code already exists. Nothing changed.')
        c.execute('''INSERT INTO employees(code,name,email,work_email,role,designation,department,location,work_mode,
                     join_date,manager_id,password_hash,avatar_color,account_active,session_version)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                  (args.code,args.name.strip(),args.email.strip().lower(),args.email.strip().lower(),'admin','HR Administrator',
                   args.department.strip(),args.location.strip(),'On-site',__import__('datetime').date.today().isoformat(),
                   None,hash_password(password),'#496AE6',1,0))
        if args.developer:
            created=c.execute('SELECT id FROM employees WHERE email=?',(args.email.strip().lower(),)).fetchone()
            c.execute('INSERT INTO developer_grants(employee_id,enabled,granted_at) VALUES(?,?,?)',
                      (created['id'],1,__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()))
        bootstrap=c.execute('SELECT id FROM employees WHERE email=?',(args.email.strip().lower(),)).fetchone()
        audit(c,bootstrap['id'],'admin.bootstrap','organization:1','Initial SASS HRM administrator created')
    print('Administrator created successfully'+(' with developer diagnostics access' if args.developer else '')+'. Sign in with the supplied work email.')

if __name__=='__main__':main()
