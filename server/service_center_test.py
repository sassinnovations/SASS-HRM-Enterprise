"""Role and database persistence regression for the consolidated support queue."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

with TemporaryDirectory() as temp:
    os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite',
                      DATABASE_PATH=str(Path(temp) / 'isolated.db'),
                      JWT_SECRET='isolated-service-center-regression-tests-never-production')
    import main

    with TestClient(main.app) as client:
        password = 'SyntheticTest-2026!'
        hashed = main.hash_password(password)
        with main.db() as conn:
            for name, role in [('hr', 'admin'), ('staff', 'employee'), ('manager', 'manager')]:
                conn.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,
                                join_date,password_hash,account_active) VALUES(?,?,?,?,?,?,?,?,?,1)''',
                             (name, name, name+'@test.invalid', role, 'QA', 'IT', 'Hyderabad', '2026-01-01', hashed))

        def log_in(name):
            result = client.post('/api/auth/login', json={'email': name+'@test.invalid', 'password': password})
            assert result.status_code == 200, result.text
            return {'Authorization': 'Bearer '+result.json()['token']}

        hr, staff, manager = map(log_in, ['hr', 'staff', 'manager'])

        def send(method, path, auth, body=None, expect=200):
            response = client.request(method, '/api'+path, headers=auth, json=body)
            assert response.status_code == expect, response.text
            return response.json()

        ticket = send('POST','/helpdesk/tickets',staff, {'subject':'VPN access', 'description':'Need help restoring access'},201)['id']
        send('POST',f'/helpdesk/tickets/{ticket}/messages',staff,{'message':'Still unable to connect.'},201)
        category = send('POST','/request-desk/categories',hr,{'name':'Employment letter','description':'HR documents'},201)['id']
        request = send('POST','/request-desk/requests',staff,{'category_id':category,'subject':'Bank letter','details':'Need the current proof of employment'},201)['id']
        assert ticket == request, 'Test must exercise independent records with matching numeric IDs'
        send('POST',f'/talent/request-desk/{request}/messages',staff,{'message':'Please include my title.'},201)
        manager_ticket = send('POST','/helpdesk/tickets',manager,{'subject':'Separate case','description':'Manager-only support record'},201)['id']

        path = '/service-center/cases'
        send('GET',path,{},expect=401)
        items = send('GET',path,staff)['items']
        assert {(r['kind'],r['id']) for r in items} == {('ticket',ticket),('request',request)}
        assert all('details' not in r and 'description' not in r for r in items)
        assert [r['id'] for r in send('GET',path,manager)['items']] == [manager_ticket]
        all_cases = send('GET',path,hr)['items']
        assert len(all_cases) == 3
        assert [r['kind'] for r in send('GET',path+'?kind=request',hr)['items']] == ['request']
        assert send('GET',path+'?limit=1',hr)['has_more']
        assert send('GET',path+'?limit=1&offset=2',hr) == {'items':all_cases[2:], 'has_more':False}
        assert send('GET',path+'?limit=1&offset=1',hr)['items'] == all_cases[1:2]
        send('GET',path+'?kind=unknown',hr,expect=422)
        send('GET',path+'?limit=101',hr,expect=422)
        send('GET',path+'?offset=-1',hr,expect=422)
        send('PATCH',f'/helpdesk/tickets/{ticket}',staff,{'status':'Closed'},403)
        send('PATCH',f'/helpdesk/tickets/{ticket}',hr,{'status':'Resolved'})
        send('POST',f'/request-desk/requests/{request}/decision',hr,{'status':'In Progress'})
        send('POST',f'/request-desk/requests/{request}/decision',hr,{'status':'Fulfilled','hr_response':'Letter issued.'})
        assert {r['kind']:r['status'] for r in send('GET',path,staff)['items']} == {'ticket':'Resolved','request':'Fulfilled'}
        assert len(send('GET',f'/helpdesk/tickets/{ticket}/messages',staff)) == 1
        assert len(send('GET',f'/talent/request-desk/{request}/messages',staff)) == 1
        assert send('GET',path+'?q=VPN',staff)['items'][0]['kind'] == 'ticket'
        assert not send('GET',path+'?q=%25',staff)['items'], 'Search wildcards must be literal'
        assert len(send('GET',path+'?q=manager',hr)['items']) == 1
        assert not send('GET',path+'?q=manager',staff)['items']
        assert len(send('GET',path+'?state=completed',staff)['items']) == 2
        assert not send('GET',path+'?state=active',staff)['items']
        assert send('GET',path+'?include_summary=true&state=active&limit=1',staff) == {
            'items':[], 'has_more':False, 'summary':{'total':2,'completed':2,'tickets':1}}
        assert send('GET',path+'?include_summary=true',hr)['summary'] == {'total':3,'completed':2,'tickets':2}
        assert send('GET',path+'?include_summary=true',manager)['summary'] == {'total':1,'completed':0,'tickets':1}
        send('GET',path+'?include_summary=true',{},expect=401)
        case_ticket = f'{path}/ticket/{ticket}'
        case_request = f'{path}/request/{request}'
        t = send('GET',case_ticket,staff)
        assert t['messages'][0]['message'] == 'Still unable to connect.'
        assert t['subject'] == 'VPN access' and t['details'] == 'Need help restoring access'
        assert t['assignment'] is None and not t['can_assign'] and not t['allowed_statuses']
        assert send('GET',case_ticket,hr)['can_assign']
        assert [owner['name'] for owner in send('GET',case_ticket,hr)['owners']] == ['hr']
        assert t['owners'] == []
        r = send('GET',case_request,staff)
        assert r['messages'][0]['message'] == 'Please include my title.'
        assert r['hr_response'] == 'Letter issued.' and not r['can_reply']
        assert not send('GET',case_request,hr)['allowed_statuses']
        send('GET',case_request,manager,expect=404)
        send('GET',case_ticket,manager,expect=404)
        send('GET',case_ticket,{},expect=401)
        with main.db() as conn:
            reviewer = conn.execute("SELECT id FROM employees WHERE code='hr'").fetchone()[0]
        send('POST',f'/talent/helpdesk/{ticket}/triage',hr,{'assignee_id':reviewer,'due_date':'2099-12-01'})
        assert send('GET',case_ticket,hr)['assignment']['assignee_name'] == 'hr'
        assert send('GET',case_ticket,staff)['assignment'] is None
        with main.db() as conn:
            for table, expected in [('tickets',2), ('service_requests',1), ('ticket_messages',1), ('service_messages',1)]:
                assert conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == expected
        with main.db() as conn:
            author = conn.execute("SELECT id FROM employees WHERE code='staff'").fetchone()[0]
            conn.executemany('INSERT INTO ticket_messages(ticket_id,author_id,message,created_at) VALUES (?,?,?,?)',
                             [(ticket,author,f'History {i}','2026-11-25T00:00:00Z') for i in range(55)])
        latest = send('GET',case_ticket,staff)
        older = send('GET',case_ticket+'?message_offset=50',staff)
        assert len(latest['messages']) == 50 and latest['has_older_messages']
        assert len(older['messages']) == 6 and not older['has_older_messages']
        assert latest['messages'][0]['message'] == 'History 5'
        assert older['messages'][0]['message'] == 'Still unable to connect.'
        assert not set(x['id'] for x in latest['messages']) & set(x['id'] for x in older['messages'])
    print('PASS: unified queue boundaries, independent IDs, filters, pagination, role checks, state and history persistence')
