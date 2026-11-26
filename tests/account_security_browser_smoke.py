"""Browser smoke against a disposable SASS HRM stack.

Requires Playwright + Chromium, a seeded employee account with no checklist data,
and SASS_HRM_TESTING=1. Exercises the actual account-security page (not mocked).
"""
import csv
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright

base = os.environ.get('SASS_HRM_BROWSER_TEST_URL', 'http://127.0.0.1:5173')
email = os.environ.get('SASS_HRM_BROWSER_TEST_EMPLOYEE', 'security-browser@example.test')
password = 'SyntheticBrowser-2026!'
if os.environ.get('SASS_HRM_TESTING') != '1' or urlparse(base).hostname not in ('127.0.0.1', 'localhost'):
    raise RuntimeError('Use a disposable local stack with SASS_HRM_TESTING=1')
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH') or None, args=['--no-sandbox'])
    try:
        page = browser.new_page()
        page.set_default_timeout(10000)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('dialog', lambda d: d.accept())
        def login(pwrd):
            page.goto(base + '/sign-in')
            page.locator('#sass-login-email').fill(email)
            page.locator('#sass-login-password').fill(pwrd)
            page.get_by_role('button', name='Sign in to SASS HRM').click()
            page.wait_for_url(lambda url: not url.endswith('/sign-in'))
        login(password)
        page.goto(base + '/settings/account-security')
        expect(page.get_by_role('heading', name='My Account Security')).to_be_visible()
        page.get_by_label('Number of sign-ins').select_option('10')
        page.get_by_label('Time zone').select_option('utc')
        page.get_by_role('button', name='Save display settings').click()
        expect(page.get_by_text('Display settings saved.', exact=True)).to_be_visible()
        page.reload()
        expect(page.get_by_label('Number of sign-ins')).to_have_value('10')
        expect(page.get_by_label('Time zone')).to_have_value('utc')
        expect(page.get_by_text('Showing up to 10 recent successful sign-ins in UTC.')).to_be_visible()
        page.get_by_role('button', name='Export my sign-ins').click()
        utc_today=datetime.now(timezone.utc).date().isoformat()
        page.get_by_label('Report start date (UTC)').fill(utc_today)
        page.get_by_label('Report end date (UTC)').fill('2001-01-01')
        page.get_by_role('button', name='Download sign-ins CSV').click()
        expect(page.get_by_text('The start date cannot be after the end date.')).to_be_visible()
        page.get_by_label('Report end date (UTC)').fill(utc_today)
        with page.expect_download() as pending:
            page.get_by_role('button', name='Download sign-ins CSV').click()
        download=pending.value
        assert download.suggested_filename=='sass-my-sign-ins.csv'
        with Path(download.path()).open(newline='') as stream:
            rows=list(csv.reader(stream))
        assert rows[0]==['signed_in_at_utc'] and len(rows)==2, rows
        assert rows[1][0].startswith(utc_today+'T') and rows[1][0].endswith('+00:00'), rows
        page.get_by_role('button', name='Hide report options').click()
        page.get_by_label('Default checklist view').select_option('due')
        page.get_by_label('Default sort order').select_option('title')
        page.get_by_label('Default due date').select_option('week')
        page.get_by_role('button', name='Save checklist settings').click()
        expect(page.get_by_text('Checklist settings saved.', exact=True)).to_be_visible()
        page.reload()
        expect(page.get_by_label('Checklist status')).to_have_value('due')
        expect(page.get_by_label('Sort checklist')).to_have_value('title')
        expect(page.get_by_label('Due date (optional)')).to_have_value((date.today()+timedelta(days=7)).isoformat())
        page.get_by_label('Checklist item', exact=True).fill('Review recent sign-ins')
        page.get_by_label('Due date (optional)').fill('2020-12-02')
        page.get_by_role('button', name='Add checklist item').click()
        expect(page.get_by_text('Overdue', exact=True)).to_be_visible()
        page.get_by_role('button', name='Complete Review recent sign-ins', exact=True).click()
        expect(page.get_by_text('No checklist items match these filters.')).to_be_visible()
        page.get_by_label('Checklist status').select_option('completed')
        page.get_by_role('button', name='Reopen Review recent sign-ins', exact=True).click()
        expect(page.get_by_text('No checklist items match these filters.')).to_be_visible()
        page.get_by_label('Checklist status').select_option('all')
        page.get_by_label('Find checklist items').fill('does not match')
        expect(page.get_by_text('No checklist items match these filters.')).to_be_visible()
        page.get_by_label('Find checklist items').fill('recent')
        page.get_by_role('button', name='Edit Review recent sign-ins').click()
        page.get_by_label('Checklist item', exact=True).fill('Review recent sign-ins and sessions')
        page.get_by_label('Completed', exact=True).check()
        page.get_by_role('button', name='Save checklist item').click()
        expect(page.get_by_text('Completed · Due 2020-12-02')).to_be_visible()
        page.reload()
        expect(page.get_by_label('Checklist status')).to_have_value('due')
        page.get_by_label('Checklist status').select_option('completed')
        page.get_by_role('button', name='Delete Review recent sign-ins and sessions').click()
        expect(page.get_by_text('No checklist items yet.')).to_be_visible()
        new_password = 'NewSyntheticBrowser-2026!'
        page.get_by_role('button', name='Change password', exact=True).click()
        page.get_by_label('Current password', exact=True).fill(password)
        page.get_by_label('New password', exact=True).fill(new_password)
        page.get_by_label('Confirm new password', exact=True).fill('DifferentPassword-123')
        page.get_by_role('button', name='Update password').click()
        expect(page.get_by_text('The new passwords do not match.')).to_be_visible()
        page.get_by_label('Confirm new password', exact=True).fill(new_password)
        page.get_by_role('button', name='Update password').click()
        expect(page.get_by_role('button', name='Sign in to SASS HRM')).to_be_visible()
        login(new_password)
        assert not errors, errors
    finally:
        browser.close()
print('PASS browser account security: settings persistence, authorized sign-in CSV, checklist lifecycle, and password change + sign-in')
