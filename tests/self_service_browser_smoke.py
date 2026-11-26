"""Exercise the self-service UI through real Chromium, FastAPI and disposable SQLite.

Requires installed web packages, Playwright, and Chromium (or CHROMIUM_PATH).
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

from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = 'SyntheticSelfService2026!'
ROUTE = '/workspace/my-requests'


def free_port():
    with socket.socket() as handle:
        handle.bind(('127.0.0.1', 0))
        return handle.getsockname()[1]


def wait_http(url, proc):
    for _ in range(100):
        if proc.poll() is not None:
            raise RuntimeError(f'Server terminated before serving {url}')
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError(f'Server not reachable at {url}')


def exercise(frontend):
    def login(browser, account):
        page = browser.new_page()
        page.goto(frontend + '/sign-in')
        page.locator('#sass-login-email').fill(f'{account}@test.invalid')
        page.locator('#sass-login-password').fill(PASSWORD)
        page.get_by_role('button', name='Sign in to SASS HRM').click()
        page.locator('.gd').wait_for()
        page.goto(frontend + ROUTE)
        page.get_by_role('heading', name='My requests & shortcuts').wait_for()
        return page

    with sync_playwright() as playwright:
        chrome = os.getenv('CHROMIUM_PATH') or shutil.which('chromium')
        browser = playwright.chromium.launch(executable_path=chrome, args=['--no-sandbox'])
        try:
            page = login(browser, 'employee-one')
            page.get_by_role('button', name='History settings').click()
            page.get_by_label('Default category').select_option('leave')
            page.get_by_label('Default status').select_option('active')
            page.get_by_label('Rows per page').select_option('10')
            page.get_by_role('button', name='Save settings').click()
            expect(page.get_by_text('History settings saved.', exact=True)).to_be_visible()
            expect(page.get_by_role('combobox', name='Category', exact=True)).to_have_value('leave')

            page.get_by_role('button', name='New draft').click()
            draft = page.get_by_role('form', name='New request draft')
            draft.get_by_label('Draft title').fill('Private vacation draft')
            draft.get_by_label('Notes').fill('Draft note for the browser test')
            draft.get_by_role('button', name='Save draft').click()
            expect(page.get_by_text('Private vacation draft', exact=True)).to_be_visible()
            page.get_by_role('button', name='Edit draft: Private vacation draft').click()
            draft = page.get_by_role('form', name='Edit request draft')
            draft.get_by_label('Draft title').fill('Updated vacation draft')
            draft.get_by_role('button', name='Save draft').click()
            expect(page.get_by_text('Updated vacation draft', exact=True)).to_be_visible()

            page.get_by_role('button', name='New draft').click()
            draft = page.get_by_role('form', name='New request draft')
            draft.get_by_label('Request module').select_option('expenses')
            draft.get_by_label('Draft title').fill('Another newer draft')
            draft.get_by_role('button', name='Save draft').click()
            expect(page.get_by_text('Another newer draft', exact=True)).to_be_visible()
            draft_titles = page.locator('.ssh-list article strong')
            expect(draft_titles.first).to_have_text('Another newer draft')
            page.get_by_role('button', name='Pin draft: Updated vacation draft', exact=True).click()
            expect(page.get_by_text('Draft pinned.', exact=True)).to_be_visible()
            expect(draft_titles.first).to_have_text('Updated vacation draft')
            page.get_by_role('combobox', name='Draft stage: Updated vacation draft', exact=True).select_option('ready')
            expect(page.get_by_text('Draft marked ready. Nothing was submitted.', exact=True)).to_be_visible()
            expect(page.get_by_text('1 ready · 1 pinned', exact=False)).to_be_visible()
            page.get_by_role('combobox', name='Draft view').select_option('ready')
            expect(page.get_by_text('Another newer draft', exact=True)).to_have_count(0)
            page.get_by_role('button', name='Reset draft filters').click()
            page.get_by_role('searchbox', name='Search drafts').fill('browser test')
            expect(draft_titles).to_have_count(1)
            expect(draft_titles.first).to_have_text('Updated vacation draft')
            page.get_by_role('combobox', name='Draft module').select_option('expenses')
            expect(page.get_by_text('No drafts match these filters.', exact=True)).to_be_visible()
            page.get_by_role('button', name='Reset draft filters').click()

            page.get_by_role('combobox', name='Draft view').select_option('pinned')
            page.get_by_role('combobox', name='Draft module').select_option('leave')
            page.get_by_role('combobox', name='Sort drafts').select_option('title')
            page.get_by_role('searchbox', name='Search drafts').fill('vacation')
            page.get_by_role('button', name='Save view as default').click()
            expect(page.get_by_text('Default draft view saved.', exact=True)).to_be_visible()
            page.get_by_role('button', name='Reset draft filters').click()
            expect(page.get_by_text('Another newer draft', exact=True)).to_be_visible()
            page.get_by_role('button', name='Use saved view').click()
            expect(page.get_by_text('Another newer draft', exact=True)).to_have_count(0)

            for page_key in ('calendar', 'leave'):
                page.get_by_label('Module to pin').select_option(page_key)
                page.get_by_role('button', name='Add shortcut').click()
            page.get_by_role('button', name='Move Leave up').click()
            page.get_by_role('button', name='Save shortcuts').click()
            expect(page.get_by_text('Shortcuts saved to your account.', exact=True)).to_be_visible()
            expect(page.locator('.ssh-shortcuts-selected a').first).to_have_text('Leave')

            page.reload()
            expect(page.get_by_role('combobox', name='Category', exact=True)).to_have_value('leave')
            expect(page.get_by_text('Updated vacation draft', exact=True)).to_be_visible()
            expect(page.locator('.ssh-shortcuts-selected a').first).to_have_text('Leave')
            expect(page.get_by_role('combobox', name='Draft view')).to_have_value('pinned')
            expect(page.get_by_role('combobox', name='Draft module')).to_have_value('leave')
            expect(page.get_by_role('combobox', name='Sort drafts')).to_have_value('title')
            expect(page.get_by_role('searchbox', name='Search drafts')).to_have_value('')
            expect(page.get_by_text('Another newer draft', exact=True)).to_have_count(0)
            page.get_by_role('button', name='Duplicate draft: Updated vacation draft').click()
            expect(page.get_by_text('Updated vacation draft (copy)', exact=True)).to_be_visible()
            expect(page.get_by_role('combobox', name='Draft stage: Updated vacation draft (copy)',exact=True)).to_have_value('drafting')
            expect(page.get_by_role('button', name='Pin draft: Updated vacation draft (copy)',exact=True)).to_be_visible()
            expect(page.get_by_text('Another newer draft', exact=True)).to_be_visible()
            page.get_by_role('button', name='Use saved view').click()
            expect(page.get_by_text('Updated vacation draft (copy)', exact=True)).to_have_count(0)
            page.get_by_role('button', name='Reset saved draft view').click()
            expect(page.get_by_text('Saved draft view reset.', exact=True)).to_be_visible()
            expect(page.get_by_text('Updated vacation draft (copy)', exact=True)).to_be_visible()
            page.get_by_role('button', name='Delete draft: Updated vacation draft (copy)',exact=True).click()
            page.get_by_role('button', name='Delete draft', exact=True).click()
            expect(page.get_by_text('Updated vacation draft (copy)', exact=True)).to_have_count(0)
            expect(draft_titles.first).to_have_text('Updated vacation draft')
            expect(page.get_by_role('combobox', name='Draft stage: Updated vacation draft', exact=True)).to_have_value('ready')
            expect(page.get_by_role('button', name='Unpin draft: Updated vacation draft')).to_be_visible()
            page.get_by_role('combobox', name='Sort drafts').select_option('title')
            expect(draft_titles.first).to_have_text('Updated vacation draft')
            page.get_by_text('Show draft notes').click()
            expect(page.get_by_text('Draft note for the browser test')).to_be_visible()
            page.locator('.ssh-list article').filter(has_text='Updated vacation draft').get_by_role('link', name='Open module').click()
            expect(page).not_to_have_url(frontend + ROUTE)
            page.goto(frontend + ROUTE)
            expect(page.get_by_text('Updated vacation draft', exact=True)).to_be_visible()

            other = login(browser, 'employee-two')
            expect(other.get_by_text('No drafts yet.', exact=False)).to_be_visible()
            expect(other.get_by_text('Nothing pinned yet.', exact=True)).to_be_visible()
            expect(other.get_by_role('combobox', name='Category', exact=True)).to_have_value('all')

            page.get_by_role('button', name='Delete draft: Updated vacation draft').click()
            page.get_by_role('button', name='Keep draft').click()
            expect(page.get_by_text('Updated vacation draft', exact=True)).to_be_visible()
            page.get_by_role('button', name='Delete draft: Updated vacation draft').click()
            page.get_by_role('button', name='Delete draft', exact=True).click()
            expect(page.get_by_text('Updated vacation draft', exact=True)).to_have_count(0)
            page.get_by_role('button', name='Delete draft: Another newer draft').click()
            page.get_by_role('button', name='Delete draft', exact=True).click()
            expect(page.get_by_text('No drafts yet.', exact=False)).to_be_visible()
            page.get_by_role('button', name='Remove Leave shortcut').click()
            page.get_by_role('button', name='Save shortcuts').click()
            expect(page.locator('.ssh-shortcuts-selected a')).to_have_count(1)
            expect(page.locator('.ssh-shortcuts-selected a').first).to_have_text('My calendar')
            page.get_by_role('combobox', name='Replace My calendar shortcut').select_option('profile')
            page.get_by_role('button', name='Save shortcuts').click()
            expect(page.locator('.ssh-shortcuts-selected a').first).to_have_text('My profile')
            page.get_by_role('button', name='History settings').click()
            page.get_by_role('button', name='Restore defaults').click()
            expect(page.get_by_text('History settings reset.', exact=True)).to_be_visible()
            expect(page.get_by_role('combobox', name='Category', exact=True)).to_have_value('all')
        finally:
            browser.close()


def main():
    frontend = f'http://127.0.0.1:{free_port()}'
    api = f'http://127.0.0.1:{free_port()}'
    with tempfile.TemporaryDirectory(prefix='sass-self-service-') as temp:
        os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite', DATABASE_PATH=str(Path(temp) / 'test.sqlite'),
                          JWT_SECRET=secrets.token_urlsafe(48), CORS_ORIGINS=frontend, VITE_API_URL=api)
        sys.path.insert(0, str(ROOT / 'server'))
        import main as hrm
        with TestClient(hrm.app):
            with hrm.db() as conn:
                for i, owner in enumerate(('employee-one', 'employee-two'), 1):
                    conn.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,
                      work_mode,join_date,password_hash,account_active) VALUES(?,?,?,?,?,?,?,?,?,?,1)''',
                      (f'SS-{i}', owner, f'{owner}@test.invalid', 'employee', 'Engineer',
                       'Engineering', 'HQ', 'On-site', '2026-01-01', hrm.hash_password(PASSWORD)))
        processes = []
        try:
            processes.append(subprocess.Popen([sys.executable, '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1',
                                               '--port', api.rsplit(':', 1)[1]], cwd=ROOT / 'server', stdout=subprocess.DEVNULL))
            npm = shutil.which('npm') or 'npm'
            processes.append(subprocess.Popen([npm, 'run', 'dev', '--', '--port', frontend.rsplit(':', 1)[1]],
                                               cwd=ROOT / 'web', stdout=subprocess.DEVNULL))
            wait_http(api + '/api/health', processes[0])
            wait_http(frontend, processes[1])
            exercise(frontend)
        finally:
            for proc in reversed(processes):
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
    print('PASS self-service Chromium CRUD, draft duplication and saved view, pin/stage/search/filter, settings and shortcut persistence, source link and second-account isolation')


if __name__ == '__main__':
    main()
