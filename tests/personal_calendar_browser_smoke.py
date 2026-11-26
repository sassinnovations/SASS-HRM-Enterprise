"""End-to-end calendar smoke test on a disposable local SQLite/API/browser stack.

Install the project dependencies, Playwright and Chromium before running.
Set CHROMIUM_PATH to your Chromium executable if it isn't Playwright-managed.
"""
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen
from datetime import date, timedelta

from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = 'SyntheticCalendarE2E2026!'
HOLIDAY = 'Browser test holiday'
NEXT_HOLIDAY = 'Range fixture holiday'


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def wait_http(url, process):
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError(f'Server stopped before reaching {url}')
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError(f'Server not reachable at {url}')


def exercise(url):
    def employee_page(browser, account):
        page = browser.new_page()
        page.goto(url + '/sign-in')
        page.locator('#sass-login-email').fill(f'{account}@test.invalid')
        page.locator('#sass-login-password').fill(PASSWORD)
        page.get_by_role('button', name='Sign in to SASS HRM').click()
        page.locator('.gd').wait_for()
        page.goto(url + '/workspace/calendar')
        page.get_by_role('heading', name='My calendar', exact=True).wait_for()
        return page

    with sync_playwright() as p:
        chrome = os.getenv('CHROMIUM_PATH') or (None if Path(p.chromium.executable_path).exists() else shutil.which('chromium'))
        browser = p.chromium.launch(executable_path=chrome, args=['--no-sandbox'])
        try:
            page = employee_page(browser, 'employee-one')
            official = page.locator('.v27-agenda-item').filter(has_text=HOLIDAY)
            expect(official).to_be_visible()
            expect(official.get_by_role('button')).to_have_count(0)
            page.get_by_role('button', name='Calendar settings').click()
            dialog = page.get_by_role('dialog')
            dialog.get_by_label('Week starts on').select_option('sunday')
            dialog.get_by_label('Default personal event time (optional)').fill('08:30')
            dialog.get_by_role('button', name='Save settings').click()
            expect(page.locator('.v27-notice')).to_contain_text('settings saved')
            expect(page.locator('.v27-weekday').first).to_have_text('Sun')

            page.get_by_role('button', name='Manage categories').click()
            expect(dialog.get_by_role('heading', name='Personal event categories')).to_be_visible()
            dialog.get_by_label('Category name').fill('Private color label')
            dialog.get_by_label('Category color').select_option('violet')
            dialog.get_by_role('button', name='Add category', exact=True).click()
            expect(dialog.get_by_role('button', name='Edit category Private color label')).to_be_visible()
            dialog.get_by_role('button', name='Close').click()

            page.get_by_role('button', name='Add personal event', exact=True).first.click()
            expect(dialog.get_by_label('Time (optional)', exact=True)).to_have_value('08:30')
            dialog.get_by_label('Event title').fill('Private browser event')
            dialog.get_by_label('Private notes (optional)').fill('private export test only')
            dialog.get_by_label('Personal category').select_option(label='Private color label')
            dialog.get_by_role('button', name='Save personal event').click()
            entry = page.locator('.v27-agenda-item').filter(has_text='Private browser event')
            expect(entry).to_be_visible()
            expect(entry.locator('.v27-category-badge')).to_have_text('Private color label')
            entry.get_by_role('button', name='Edit', exact=True).click()
            dialog.get_by_label('Event title').fill('Updated private browser event')
            dialog.get_by_role('button', name='Save personal event').click()
            updated = page.locator('.v27-agenda-item').filter(has_text='Updated private browser event')
            expect(updated).to_be_visible()
            updated.get_by_role('button', name='Duplicate').click()
            expect(dialog.get_by_label('Personal category').locator('option:checked')).to_have_text('Private color label')
            dialog.get_by_label('Event title').fill('Duplicated browser event')
            dialog.get_by_role('button', name='Save personal event').click()
            duplicate = page.locator('.v27-agenda-item').filter(has_text='Duplicated browser event')
            expect(duplicate).to_be_visible()

            with page.expect_download() as safe_export:
                page.get_by_role('button', name='Export this month').click()
            text = safe_export.value.path().read_text(encoding='utf-8')
            assert HOLIDAY in text and 'private export test only' not in text and 'Private color label' not in text

            page.get_by_role('button', name='Calendar settings').click()
            dialog.get_by_label('Include private events and notes in calendar exports').check()
            dialog.get_by_role('button', name='Save settings').click()
            expect(page.locator('.v27-notice')).to_contain_text('settings saved')
            with page.expect_download() as opted_in_export:
                page.get_by_role('button', name='Export this month').click()
            private_text = opted_in_export.value.path().read_text(encoding='utf-8')
            assert 'private export test only' in private_text
            assert 'CATEGORIES:Private color label' in private_text

            page.reload()
            expect(page.locator('.v27-weekday').first).to_have_text('Sun')
            expect(updated).to_be_visible()
            page.get_by_label('Category filter').select_option(label='Private color label')
            expect(official).to_have_count(0)
            expect(duplicate).to_be_visible()
            page.get_by_label('Category filter').select_option('none')
            expect(duplicate).to_have_count(0)
            page.get_by_label('Category filter').select_option('all')
            page.get_by_label('Event filter').select_option('personal')
            expect(official).to_have_count(0)
            expect(updated).to_be_visible()
            page.get_by_label('Event filter').select_option('official')
            expect(updated).to_have_count(0)
            expect(official).to_be_visible()
            page.get_by_label('Event filter').select_option('all')

            second = employee_page(browser, 'employee-two')
            expect(second.locator('.v27-weekday').first).to_have_text('Mon')
            expect(second.get_by_text(HOLIDAY, exact=True)).to_be_visible()
            expect(second.get_by_text('Updated private browser event', exact=True)).to_have_count(0)
            expect(second.get_by_label('Category filter').get_by_role('option', name='Private color label')).to_have_count(0)

            page.get_by_role('group',name='Calendar view').get_by_role('button',name='Agenda').click()
            agenda = page.get_by_role('region',name='Agenda')
            expect(agenda).to_be_visible()
            expect(agenda.get_by_label('Show next')).to_have_value('14')
            later = agenda.locator('.v27-agenda-item').filter(has_text=NEXT_HOLIDAY)
            expect(later).to_be_visible()
            expect(later.get_by_role('button')).to_have_count(0)
            agenda.get_by_label('Show next').select_option('7')
            expect(later).to_have_count(0)
            agenda.get_by_role('button',name='Next agenda period').click()
            expect(later).to_be_visible()
            expect(official).to_have_count(0)
            next_fixture_day=(date.today()+timedelta(days=8)).isoformat()
            later.locator('xpath=../..').get_by_role('button',name='Add event on',exact=False).click()
            expect(dialog.get_by_label('Date',exact=True)).to_have_value(next_fixture_day)
            dialog.get_by_label('Event title').fill('Agenda manual appointment')
            dialog.get_by_role('button',name='Save personal event').click()
            agenda_created = agenda.locator('.v27-agenda-item').filter(has_text='Agenda manual appointment')
            expect(agenda_created).to_be_visible()
            expect(page.get_by_label('Agenda start')).to_have_value((date.today()+timedelta(days=7)).isoformat())
            agenda_created.get_by_role('button',name='Edit',exact=True).click()
            dialog.get_by_label('Event title').fill('Updated agenda appointment')
            dialog.get_by_role('button',name='Save personal event').click()
            agenda_edited = agenda.locator('.v27-agenda-item').filter(has_text='Updated agenda appointment')
            expect(agenda_edited).to_be_visible()
            page.once('dialog', lambda confirm: confirm.accept())
            agenda_edited.get_by_role('button',name='Delete',exact=True).click()
            expect(agenda_edited).to_have_count(0)
            agenda.get_by_role('button',name='Previous agenda period').click()
            expect(official).to_be_visible()
            page.get_by_label('Search calendar').fill('not-in-these-fixtures')
            expect(agenda.get_by_text('No events match your filters in this period',exact=True)).to_be_visible()
            agenda.get_by_role('button',name='Clear filters').click()
            expect(updated).to_be_visible()

            page.get_by_role('button',name='Calendar settings').click()
            dialog.get_by_label('Default calendar view').select_option('agenda')
            dialog.get_by_label('Default agenda period').select_option('7')
            dialog.get_by_label('Include private events and notes in calendar exports').uncheck()
            dialog.get_by_role('button',name='Save settings').click()
            expect(page.locator('.v27-notice')).to_contain_text('settings saved')
            page.reload()
            expect(agenda).to_be_visible()
            expect(agenda.get_by_label('Show next')).to_have_value('7')
            expect(official).to_be_visible()
            expect(updated).to_be_visible()
            with page.expect_download() as agenda_export:
                page.get_by_role('button',name='Export this period').click()
            agenda_text=agenda_export.value.path().read_text(encoding='utf-8')
            assert HOLIDAY in agenda_text and NEXT_HOLIDAY not in agenda_text and 'private export test only' not in agenda_text
            second.reload()
            expect(second.get_by_role('group',name='Calendar view').get_by_role('button',name='Month')).to_have_attribute('aria-pressed','true')

            page.get_by_role('button', name='Manage categories').click()
            expect(dialog.get_by_text('2 events', exact=True)).to_be_visible()
            dialog.get_by_role('button', name='Edit category Private color label').click()
            dialog.get_by_label('Category name').fill('Renamed private label')
            dialog.get_by_role('button', name='Save category').click()
            expect(dialog.get_by_role('button', name='Edit category Renamed private label')).to_be_visible()
            page.once('dialog', lambda confirmation: confirmation.accept())
            dialog.get_by_role('button', name='Delete category Renamed private label').click()
            expect(dialog.get_by_text('No personal categories yet.', exact=False)).to_be_visible()
            dialog.get_by_role('button', name='Close').click()
            expect(updated).to_be_visible()
            expect(duplicate).to_be_visible()
            expect(updated.locator('.v27-category-badge')).to_have_count(0)
            for item in (duplicate, updated):
                page.once('dialog', lambda confirm: confirm.accept())
                item.get_by_role('button', name='Delete', exact=True).click()
                expect(item).to_have_count(0)
            expect(official).to_be_visible()
        finally:
            browser.close()


def main():
    frontend = f'http://127.0.0.1:{free_port()}'
    api = f'http://127.0.0.1:{free_port()}'
    while api == frontend:
        api = f'http://127.0.0.1:{free_port()}'
    with tempfile.TemporaryDirectory(prefix='sass-calendar-') as temp:
        os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite', DATABASE_PATH=str(Path(temp) / 'test.sqlite'),
                          JWT_SECRET=secrets.token_urlsafe(48), CORS_ORIGINS=frontend, VITE_API_URL=api)
        sys.path.insert(0, str(ROOT / 'server'))
        import main as hrm
        with TestClient(hrm.app):
            with hrm.db() as conn:
                for i, owner in enumerate(('employee-one', 'employee-two'), 1):
                    conn.execute('''INSERT INTO employees(code,name,email,work_email,role,designation,department,
                      location,work_mode,join_date,password_hash,account_active) VALUES(?,?,?,?,?,?,?,?,?,?,?,1)''',
                      (f'CAL-{i}', owner, f'{owner}@test.invalid', f'{owner}@test.invalid', 'employee', 'Engineer',
                       'Engineering', 'HQ', 'On-site', date.today().isoformat(), hrm.hash_password(PASSWORD)))
                for days_back in range(120, 230):
                    conn.execute('INSERT INTO holidays(name,day) VALUES(?,?)',
                                 (f'Old holiday {days_back}', (date.today()-timedelta(days=days_back)).isoformat()))
                conn.execute('INSERT INTO holidays(name,day) VALUES(?,?)', (HOLIDAY, date.today().isoformat()))
                conn.execute('INSERT INTO holidays(name,day) VALUES(?,?)',
                             (NEXT_HOLIDAY, (date.today()+timedelta(days=8)).isoformat()))
        processes = []
        try:
            processes.append(subprocess.Popen([sys.executable, '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1',
                                               '--port', api.rsplit(':', 1)[1]], cwd=ROOT / 'server', stdout=subprocess.DEVNULL))
            processes.append(subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1',
                                               '--port', frontend.rsplit(':', 1)[1]],
                                               cwd=ROOT / 'web', stdout=subprocess.DEVNULL))
            wait_http(api + '/api/health', processes[0])
            wait_http(frontend, processes[1])
            exercise(frontend)
        finally:
            for process in reversed(processes):
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    print('PASS calendar browser Month and Agenda, bounded official dates, CRUD, persisted settings, private export and account isolation')


if __name__ == '__main__':
    main()
