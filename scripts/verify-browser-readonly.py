"""Read-only browser smoke test for a running local SASS HRM deployment.

Requires: pip install playwright; python -m playwright install chromium
Use an authorized test account. NEVER writes payroll, candidate or employee data.
Does not save credentials, screenshots, traces, or HTTP response bodies.
"""
from __future__ import annotations

import getpass
import os
import sys
from urllib.parse import urlsplit


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('BLOCKED: Install Playwright: python -m pip install playwright')
        print('Then run: python -m playwright install chromium')
        return 2

    base = os.getenv('SASS_HRM_TEST_URL', 'http://127.0.0.1:5173').rstrip('/')
    hostname = (urlsplit(base).hostname or '').lower()
    if hostname not in {'localhost', '127.0.0.1'}:
        print('BLOCKED: This safe checker is limited to the local HRM deployment.')
        return 2
    email = input('Authorized test-account email: ').strip()
    if not email:
        print('SKIP: No test account supplied.')
        return 2
    password = getpass.getpass('Password (hidden, never logged): ')
    if not password:
        print('SKIP: No password supplied.')
        return 2

    checks = []
    http_errors = []
    js_errors = []
    def result(name: str, passed: bool, detail: str = ''):
        checks.append((name, passed, detail))
        print(f"{'PASS' if passed else 'FAIL'}: {name}" + (f' - {detail}' if detail else ''))

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:
            print('BLOCKED: Chromium is unavailable. Run: python -m playwright install chromium')
            print(type(exc).__name__)
            return 2
        context = browser.new_context(viewport={'width': 1440, 'height': 900})
        page = context.new_page()
        page.on('pageerror', lambda err: js_errors.append(type(err).__name__))
        page.on('response', lambda resp: http_errors.append((resp.status, urlsplit(resp.url).path)) if resp.status >= 500 and '/api/' in resp.url else None)
        try:
            response = page.goto(base + '/', wait_until='domcontentloaded', timeout=25000)
            result('Frontend served in Chromium', bool(response and response.status == 200))
            page.locator('input[name="email"]').fill(email, timeout=20000)
            page.locator('input[name="password"]').fill(password)
            page.locator('button[type="submit"]').filter(has_text='Sign in to SASS HRM').click()
            try:
                page.wait_for_function("Boolean(sessionStorage.getItem('sass_token'))", timeout=20000)
                result('Interactive browser login', True)
            except Exception:
                result('Interactive browser login', False, 'Check test credentials, API, and sign-in error in browser.')
                return 1
            # Only read/navigate; never click edit, save, publish, delete or import.
            routes = [
                ('Overview', '/workspace/overview', '.page-content'),
                ('Employee HRIS', '/people/employee-hris', '.page-content'),
                ('Payroll workbench', '/compensation/payroll-workbench', '.pay-heading h1'),
                ('Candidate Search', '/talent/candidate-search-database', '.page-content'),
                ('Workspace settings', '/settings/my-workspace', '.page-content'),
            ]
            for name, path, selector in routes:
                try:
                    response = page.goto(base + path, wait_until='domcontentloaded', timeout=25000)
                    page.locator(selector).first.wait_for(state='visible', timeout=20000)
                    body_text = page.locator('body').inner_text(timeout=10000).lower()
                    forbidden = 'you do not have permission to open this feature' in body_text or 'page not found' in body_text
                    result(name + ' screen', bool(response and response.ok and not forbidden))
                except Exception as exc:
                    result(name + ' screen', False, type(exc).__name__)
            try:
                page.goto(base + '/compensation/payroll-workbench', wait_until='domcontentloaded', timeout=25000)
                page.get_by_role('button', name='Recheck readiness').click(timeout=12000)
                page.wait_for_timeout(1400)
                result('Read-only payroll readiness button', True)
            except Exception as exc:
                result('Read-only payroll readiness button', False, type(exc).__name__)
            result('No JavaScript page errors', not js_errors, f'{len(js_errors)} errors')
            result('No HTTP API 5xx responses', not http_errors, f'{len(http_errors)} errors')
        finally:
            # The browser/session is kept in memory only and closed on completion.
            context.close()
            browser.close()
            del password
    total = len(checks)
    failed = sum(not passed for _, passed, _ in checks)
    print(f'\nBrowser smoke test: {total - failed}/{total} passed. No writes performed.')
    print('These checks do not validate statutory payroll accuracy or every UI control.')
    if http_errors:
        print('API 5xx routes:', sorted(set(http_errors))[:10])
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
