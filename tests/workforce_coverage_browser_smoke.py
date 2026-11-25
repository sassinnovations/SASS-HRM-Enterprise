"""Run the Coverage Planner on a disposable SQLite-backed web stack.

Requires web npm dependencies, the server requirements, Python Playwright, and Chromium.
Run from any directory: python tests/workforce_coverage_browser_smoke.py
"""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack, closing, contextmanager
from datetime import date
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PASSWORD = 'CoverageTest-Only-2026!'


def free_port():
    with closing(socket.socket()) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def wait_for(url, proc):
    for _ in range(150):
        if proc.poll() is not None:
            raise RuntimeError(f'Test server exited before serving {url}')
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except URLError:
            pass
        time.sleep(0.2)
    raise RuntimeError(f'Test server did not respond: {url}')


@contextmanager
def process(args, cwd, env):
    with subprocess.Popen(args, cwd=cwd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as proc:
        try:
            yield proc
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


def run():
    api_port, web_port = free_port(), free_port()
    base = f'http://127.0.0.1:{web_port}'
    api = f'http://127.0.0.1:{api_port}'
    with ExitStack() as stack:
        tmp = stack.enter_context(tempfile.TemporaryDirectory())
        env = {**os.environ, 'SASS_HRM_TESTING': '1', 'DB_ENGINE': 'sqlite',
               'DATABASE_PATH': str(Path(tmp) / 'coverage.sqlite'),
               'JWT_SECRET': 'synthetic-isolated-coverage-ui-tests-no-production-access-2026',
               'CORS_ORIGINS': base, 'VITE_API_URL': api,
               'PYTHONPATH': str(ROOT / 'server')}
        backend = stack.enter_context(process([sys.executable, '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1',
                                               '--port', str(api_port)], ROOT / 'server', env))
        wait_for(api + '/api/live', backend)
        subprocess.run([sys.executable,'-c',"""
from main import db,hash_password
from datetime import date
with db() as c:
    manager=None
    for code,role,dept in [('admin','admin','People'),('manager','manager','Finance'),('analyst','employee','Finance'),
                           ('outsider','employee','Sales')]:
        r=c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,manager_id)
                       VALUES(?,?,?,?,?,?,?,?,?,?)''',(code,code.title(),code+'@test.invalid',role,'Analyst',dept,'Hyderabad',
                              date.today().isoformat(),hash_password('CoverageTest-Only-2026!'),manager if code=='analyst' else None))
        if code=='manager': manager=r.lastrowid
    today=date.today().isoformat()
    c.execute('INSERT INTO holidays(name,day,location) VALUES(?,?,?)',('Coverage browser holiday',today,'All'))
    c.execute('''INSERT INTO leave_requests (employee_id,start_date,end_date,leave_type,reason,days,status,created_at)
                 VALUES(?,?,?,?,?,1,'Approved',?)''',(manager,today,today,'Private type','Sensitive evidence',today))
"""], cwd=ROOT / 'server', env=env, check=True)
        vite = ROOT / 'web' / 'node_modules' / 'vite' / 'bin' / 'vite.js'
        build_dir=str(Path(tmp) / 'web-release')
        subprocess.run(['node',str(vite),'build','--outDir',build_dir,'--emptyOutDir'],
                       cwd=ROOT / 'web',env=env,check=True,stdout=subprocess.DEVNULL)
        frontend = stack.enter_context(process(['node',str(vite),'preview','--outDir',build_dir,
                                               '--host','127.0.0.1','--port',str(web_port),'--strictPort'],
                                               ROOT / 'web', env))
        wait_for(base, frontend)
        pw = stack.enter_context(sync_playwright())
        browser = pw.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH') or shutil.which('chromium'),
                                     args=['--no-sandbox'])
        stack.callback(browser.close)
        errors = []

        def login(who):
            page=browser.new_page()
            page.set_default_timeout(10000)
            page.on('pageerror', lambda exc: errors.append(str(exc)))
            page.goto(base+'/sign-in')
            page.locator('#sass-login-email').fill(who+'@test.invalid')
            page.locator('#sass-login-password').fill(PASSWORD)
            page.get_by_role('button', name='Sign in to SASS HRM').click()
            expect(page.locator('.gd')).to_be_visible()
            page.goto(base+'/workspace/team-leave-planner')
            expect(page.get_by_role('heading',name='Team leave & coverage planner')).to_be_visible()
            return page

        def btn(page,name):
            return page.get_by_role('button',name=name,exact=True)

        admin=login('admin')
        btn(admin,'Coverage settings').click()
        admin.get_by_label('Absence warning threshold').fill('1')
        admin.get_by_label('Warn only Monday–Friday').check()
        btn(admin,'Save settings').click()
        expect(admin.get_by_text('Coverage settings saved.',exact=False)).to_be_visible()
        admin.reload()
        btn(admin,'Coverage settings').click()
        expect(admin.get_by_label('Warn only Monday–Friday')).to_be_checked()
        expect(admin.get_by_label('Absence warning threshold')).to_have_value('1')

        expect(admin.get_by_text('Coverage browser holiday',exact=True)).to_be_visible()
        btn(admin,'My planner settings').click()
        admin.get_by_label('Default department',exact=True).select_option('Finance')
        admin.get_by_label('Show holidays',exact=True).uncheck()
        admin.get_by_label('Plan status filter',exact=True).select_option('Confirmed')
        btn(admin,'Save my planner settings').click()
        expect(admin.get_by_text('Your planner settings were saved.',exact=True)).to_be_visible()
        expect(admin.get_by_text('Coverage browser holiday',exact=True)).to_have_count(0)
        admin.reload()
        btn(admin,'My planner settings').click()
        expect(admin.get_by_label('Default department',exact=True)).to_have_value('Finance')
        expect(admin.get_by_label('Show holidays',exact=True)).not_to_be_checked()
        expect(admin.get_by_label('Plan status filter',exact=True)).to_have_value('Confirmed')

        mgr=login('manager')
        expect(btn(mgr,'Coverage settings')).to_have_count(0)
        expect(mgr.get_by_text('Coverage browser holiday',exact=True)).to_be_visible()
        btn(mgr,'Add coverage plan').click()
        mgr.get_by_label('Plan title').fill('Payroll backup')
        primary=mgr.get_by_label('Primary employee')
        assert 'Outsider' not in primary.inner_text()
        primary.select_option(label='Analyst · Finance')
        mgr.get_by_label('Backup employee').select_option(label='Manager · Finance')
        mgr.get_by_label('Handover notes',exact=False).fill('Managers only')
        btn(mgr,'Save coverage plan').click()
        expect(btn(mgr,'Edit Payroll backup')).to_be_visible()
        expect(mgr.get_by_text('Backup has approved leave during this plan.',exact=True)).to_be_visible()
        expect(mgr.get_by_text('Sensitive evidence',exact=True)).to_have_count(0)
        mgr.reload()
        btn(mgr,'Edit Payroll backup').click()
        mgr.get_by_label('Status',exact=True).select_option('Confirmed')
        btn(mgr,'Save plan changes').click()
        expect(mgr.get_by_text('Confirmed',exact=True)).to_be_visible()

        today=date.today().isoformat()
        btn(mgr,'Review coverage for '+today).click()
        review=mgr.get_by_role('region',name='Daily coverage review')
        expect(review.get_by_role('heading',name='Approved absences (1)')).to_be_visible()
        expect(review.get_by_role('heading',name='Manual backup plans (1)')).to_be_visible()
        expect(review.get_by_text('Backup on approved leave this day',exact=True)).to_be_visible()
        review.get_by_label('Warning days only',exact=True).check()
        expect(review.get_by_label('Review date',exact=True)).to_have_value(today)
        assert review.get_by_label('Review date',exact=True).locator('option').count()==1
        review.get_by_label('Warning days only',exact=True).uncheck()

        btn(review,'Add plan for this day').click()
        expect(mgr.get_by_label('From',exact=True)).to_have_value(today)
        expect(mgr.get_by_label('Through',exact=True)).to_have_value(today)
        mgr.get_by_label('Plan title').fill('Another handover')
        mgr.get_by_label('Primary employee').select_option(label='Analyst · Finance')
        mgr.get_by_label('Backup employee').select_option(label='Manager · Finance')
        btn(mgr,'Save coverage plan').click()
        expect(review.get_by_role('heading',name='Manual backup plans (2)')).to_be_visible()
        expect(review.get_by_text('Backup booked on multiple plans this day',exact=True)).to_have_count(2)
        mgr.once('dialog', lambda dialog: dialog.accept())
        btn(mgr,'Delete Another handover').click()
        expect(review.get_by_text('Backup booked on multiple plans this day',exact=True)).to_have_count(0)

        employee=login('analyst')
        expect(employee.locator('#coverage-plans').get_by_text('Payroll backup',exact=True)).to_be_visible()
        expect(employee.get_by_text('Managers only',exact=True)).to_have_count(0)
        expect(employee.get_by_text('Backup has approved leave during this plan.',exact=True)).to_have_count(0)
        expect(employee.get_by_text('Backup on approved leave this day',exact=True)).to_have_count(0)
        expect(employee.get_by_label('Warning days only',exact=True)).to_have_count(0)
        expect(btn(employee,'Add coverage plan')).to_have_count(0)
        other=login('outsider')
        expect(other.get_by_text('No coverage plans for this month and scope.',exact=True)).to_be_visible()
        expect(other.get_by_text('Payroll backup',exact=True)).to_have_count(0)

        mgr.once('dialog', lambda dialog: dialog.dismiss())
        btn(mgr,'Delete Payroll backup').click()
        expect(btn(mgr,'Edit Payroll backup')).to_be_visible()
        mgr.once('dialog', lambda dialog: dialog.accept())
        btn(mgr,'Delete Payroll backup').click()
        expect(mgr.get_by_text('Coverage plan deleted.',exact=True)).to_be_visible()
        mgr.reload()
        expect(mgr.get_by_text('No coverage plans for this month and scope.',exact=True)).to_be_visible()
        assert not errors, errors
    print('PASS: actual planner route, persisted HR and private preferences, daily review and parallel backup conflict, manager add/edit/confirmed delete, employee and out-of-scope views')


if __name__ == '__main__':
    run()
