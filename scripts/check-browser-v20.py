"""Read-only real-browser smoke test: requires a running MySQL-backed SASS HRM server.
Credentials are read ONLY from environment variables; never put passwords in test files.
Requires: pip install playwright && python -m playwright install chromium
"""
import os, sys
from urllib.request import urlopen
import json
try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    raise SystemExit('Install browser tester first: pip install playwright && python -m playwright install chromium') from exc
email=os.getenv('SASS_E2E_EMAIL','').strip()
password=os.getenv('SASS_E2E_PASSWORD','')
if not email or not password:
    raise SystemExit('Set SASS_E2E_EMAIL and SASS_E2E_PASSWORD in your own terminal session. Never store credentials in a ZIP.')
url=os.getenv('SASS_E2E_URL','http://localhost:5173').rstrip('/')
api=os.getenv('SASS_E2E_API','http://localhost:8000/api/health')
try:
    with urlopen(api, timeout=8) as response:
        health=json.load(response)
except Exception as exc:
    raise SystemExit('The API is not responding. Start the backend and MySQL first: '+str(exc))
if health.get('database')!='mysql':
    raise SystemExit('STOP: API is using '+str(health.get('database'))+' instead of MySQL; fix config before browser validation.')
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True)
    page=browser.new_page(viewport={'width':1440,'height':900})
    try:
        page.goto(url,wait_until='domcontentloaded',timeout=30000)
        page.get_by_role('heading',name='Sign in to your workspace').wait_for(timeout=10000)
        page.get_by_label('Work email').fill(email)
        page.get_by_label('Password').fill(password)
        page.get_by_role('button',name='Sign in to SASS HRM').click()
        page.get_by_text('SASS HRM',exact=False).first.wait_for(timeout=15000)
        print('PASS frontend login shell')
        checks=[('Asset management','Asset custody & lifecycle'),
                ('Employee documents','Document verification & expiry'),
                ('Secure document vault','Private employee file vault'),
                ('AI Assistant','Authorized HR data lookup'),
                ('Settings','Personal display preferences')]
        for nav,expected in checks:
            # Sidebar may scroll independently and groups may collapse; use title/role fallback.
            button=page.locator('.sidebar button').filter(has_text=nav).first
            button.scroll_into_view_if_needed(timeout=6000)
            button.click(timeout=6000)
            page.get_by_text(expected,exact=False).first.wait_for(timeout=10000)
            print('PASS browser:',nav)
        # Read-only test: never creates employees, uploads files, or approves requests.
        print('PASS v2.0 read-only browser smoke test. This is not a full compliance or production certification.')
    except Exception as exc:
        page.screenshot(path='sass_hrm_browser_smoke_failure.png',full_page=True)
        print('FAIL browser smoke test; screenshot: sass_hrm_browser_smoke_failure.png')
        raise
    finally:
        browser.close()
