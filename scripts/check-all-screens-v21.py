"""Read-only browser audit across SASS HRM v2.1 navigation screens.

Requires installed Playwright, a running frontend, real MySQL-backed API, and
credentials in environment variables. Does NOT create employees or change HR data.
Screenshots are disabled by default to avoid saving personal information.
"""
import json
import os
import sys
from urllib.request import urlopen

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    raise SystemExit('Install Playwright: pip install playwright && python -m playwright install chromium')

email = os.getenv('SASS_E2E_EMAIL', '').strip()
password = os.getenv('SASS_E2E_PASSWORD', '')
frontend = os.getenv('SASS_E2E_URL', 'http://localhost:5173').rstrip('/')
api = os.getenv('SASS_E2E_API', 'http://localhost:8000/api/health')
if not email or not password:
    raise SystemExit('Set SASS_E2E_EMAIL and SASS_E2E_PASSWORD as environment variables. Do not add secrets to the source.')

try:
    with urlopen(api, timeout=10) as response:
        health = json.load(response)
except Exception as exc:
    raise SystemExit(f'Backend health endpoint is unreachable: {exc}')
if health.get('database') != 'mysql':
    raise SystemExit(f'Requires live MySQL integration; backend reports {health.get("database")!r}.')

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    visited = []
    failed = []
    try:
        page.goto(frontend, wait_until='domcontentloaded', timeout=30000)
        page.get_by_role('heading', name='Sign in to your workspace').wait_for(timeout=15000)
        page.get_by_label('Work email').fill(email)
        page.get_by_label('Password').fill(password)
        page.locator('.login-submit').click()
        page.locator('.sidebar .nav-list a').first.wait_for(timeout=25000)

        # Read only the menus the authenticated user is authorized to see.
        # Expand each group, then navigate. Do not rely on fixed admin data.
        groups = page.locator('.sidebar .nav-group')
        titles = [groups.nth(i).locator('.nav-group-toggle').inner_text() for i in range(groups.count())]
        for title in titles:
            group = page.locator('.sidebar .nav-group').filter(has=page.locator('.nav-group-toggle', has_text=title)).first
            toggle = group.locator('.nav-group-toggle')
            if toggle.get_attribute('aria-expanded') != 'true':
                toggle.click()
            menu = group.locator('.nav-list a')
            labels = [menu.nth(i).locator('span').first.inner_text() for i in range(menu.count())]
            for label in labels:
                try:
                    group = page.locator('.sidebar .nav-group').filter(has=page.locator('.nav-group-toggle', has_text=title)).first
                    item = group.locator('.nav-list a').filter(has=page.locator('span', has_text=label)).first
                    item.scroll_into_view_if_needed(timeout=10000)
                    item.click(timeout=10000)
                    assert page.url.startswith(frontend + '/'), 'Missing page-specific browser route'
                    page.locator('.breadcrumb strong').filter(has_text=label).first.wait_for(timeout=8000)
                    if page.locator('.sass-boot-failure').count():
                        raise AssertionError('React error boundary was displayed')
                    if page.locator('.data-error-banner').count():
                        raise AssertionError('API data source failed for this screen')
                    visited.append(label)
                    print('PASS', label)
                except Exception as exc:
                    failed.append(f'{label}: {exc}')
                    print('FAIL', label, str(exc)[:180])
        for label in ('AI Assistant', 'Settings'):
            try:
                item = page.locator('.sidebar .nav-list a').filter(has_text=label).last
                item.click(timeout=10000)
                if page.locator('.sass-boot-failure').count():
                    raise AssertionError('React error boundary shown')
                visited.append(label)
                print('PASS', label)
            except Exception as exc:
                failed.append(f'{label}: {exc}')
        # Deep-link reload smoke check without modifying any employee records.
        try:
            for route in ('/workspace/my-profile', '/settings/my-workspace'):
                page.goto(frontend + route, wait_until='domcontentloaded', timeout=30000)
                page.locator('.sidebar .nav-list a').first.wait_for(timeout=25000)
                if page.url.split('?', 1)[0] != frontend + route:
                    raise AssertionError(f'Page refresh unexpectedly lost {route}')
            print('PASS direct URL refresh on profile and workspace settings.')
        except Exception as exc:
            failed.append(f'Direct URL refresh: {exc}')
        if errors:
            failed.extend(['JavaScript error: ' + e for e in errors])
        print(f'Visited {len(visited)} authorized screens. Failures: {len(failed)}.')
        for f in failed:
            print(' -', f)
        if failed:
            sys.exit(1)
        print('PASS read-only browser navigation. Interactive form submission, mobile layouts and statutory compliance are separate checks.')
    finally:
        browser.close()
