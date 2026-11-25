"""Ranged official-calendar reads use stored intervals, office and owner scope."""
from datetime import date, timedelta
import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as tmp:
    os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite',
                      JWT_SECRET='ranged-official-calendar-isolated-test-key-never-production',
                      DATABASE_PATH=str(Path(tmp)/'range.sqlite'))
    import main
    with TestClient(main.app) as client:
        secret='CalendarRangeOnly2026!'
        with main.db() as conn:
            for i, loc in ((1,'Pune'),(2,'Chennai')):
                conn.execute("""INSERT INTO employees(id,code,name,email,work_email,role,designation,department,
                               location,join_date,password_hash,account_active)
                               VALUES(?,?,?,?,?,'employee','QA','Test',?,'2026-01-01',?,1)""",
                             (i,f'QA-{i}',f'Calendar Tester {i}',f'qa{i}@example.invalid',f'qa{i}@example.invalid',
                              loc, main.hash_password(secret)))
            old_start=date(2025,1,1)
            for offset in range(110):
                day=(old_start+timedelta(days=offset)).isoformat()
                conn.execute("INSERT INTO holidays(name,day,location) VALUES('Historical holiday',?,'All')",(day,))
            for name,day,location in [('Public fixture holiday','2026-12-01','All'),
                                      ('Pune fixture holiday','2026-12-02','Pune'),
                                      ('Chennai fixture holiday','2026-12-03','Chennai')]:
                conn.execute('INSERT INTO holidays(name,day,location) VALUES(?,?,?)',(name,day,location))
            for eid, start, end, title, status in [(1,'2026-11-30','2026-12-03','Own annual leave','Approved'),
                       (2,'2026-12-02','2026-12-02','Other employee leave','Approved'),
                       (1,'2026-12-04','2026-12-04','Rejected leave','Rejected')]:
                conn.execute("""INSERT INTO leave_requests(employee_id,start_date,end_date,leave_type,reason,days,status,created_at)
                   VALUES(?,?,?,?, 'Private reason never returned',1,?,'2026-11-10')""",(eid,start,end,title,status))
            conn.execute("INSERT INTO shifts(id,name,start_time,end_time) VALUES(1,'Morning fixture shift','09:00','17:00')")
            conn.execute("INSERT INTO shift_assignments(employee_id,shift_id,work_day) VALUES(1,1,'2026-12-04')")
        login=client.post('/api/auth/login',json={'email':'qa1@example.invalid','password':secret})
        assert login.status_code==200,login.text
        auth={'Authorization':'Bearer '+login.json()['token']}
        base='/api/calendar/me'
        assert client.get(base+'?start=2026-12-01&end=2026-12-04').status_code==401
        for params in ({'start':'2026-12-01'},{'start':'2026-12-04','end':'2026-12-01'},
                       {'start':'2026-01-01','end':'2026-12-01'}):
            assert client.get(base,params=params,headers=auth).status_code==422
        response=client.get(base,params={'start':'2026-12-01','end':'2026-12-04'},headers=auth)
        assert response.status_code==200,response.text
        assert response.headers.get('Cache-Control')=='private, no-store'
        items=response.json()
        assert [row['day'] for row in items if row['kind']=='Leave']==['2026-12-01','2026-12-02','2026-12-03']
        assert {row['title'] for row in items}=={'Own annual leave','Public fixture holiday','Pune fixture holiday','Morning fixture shift'}
        assert all(set(row)=={'day','kind','title','status'} for row in items)
        # Old browsers still get the original point-in-time leave shape and complete response.
        old=client.get(base,headers=auth).json()
        assert any(row['kind']=='Leave' and row['day']=='2026-11-30' for row in old)
        assert not any(row['title']=='Public fixture holiday' for row in old)
print('PASS official calendar: date bounds and spanning leave, recent holidays despite historical rows, owner and office scoping, legacy response.')
