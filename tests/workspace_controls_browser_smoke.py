"""Run against local dev servers on a disposable synthetic database only.

Create test accounts workspace-1@example.invalid (admin), workspace-3 (employee)
and workspace-4 (second employee); the admin must have permission to select
employee IDs 3 and 4. Set SASS_WORKSPACE_SMOKE_PASSWORD in the test environment.
Requires Python Playwright and installed Chromium (or CHROMIUM_PATH).
"""
import os

from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

BASE = 'http://127.0.0.1:5173'
if os.environ.get('SASS_HRM_TESTING') != '1' or os.environ.get('DB_ENGINE') != 'sqlite':
    raise RuntimeError('Use only the disposable SQLite test stack with SASS_HRM_TESTING=1.')
PASSWORD = os.environ['SASS_WORKSPACE_SMOKE_PASSWORD']


def run(browser):
    context = browser.new_context(viewport={'width': 1440, 'height': 950})
    page = context.new_page()
    issues = []
    page.on('pageerror', lambda error: issues.append(str(error)))
    page.on('response', lambda response: issues.append(f'{response.status} {urlsplit(response.url).path}')
            if response.status >= 500 and '/api/' in response.url else None)
    page.on('dialog', lambda dialog: dialog.accept())

    def login(user):
        page.goto(BASE)
        page.locator('input[name=email]').fill(f'workspace-{user}@example.invalid')
        page.locator('input[name=password]').fill(PASSWORD)
        page.get_by_role('button', name='Sign in to SASS HRM').click()
        page.wait_for_function("Boolean(sessionStorage.getItem('sass_token'))")

    def go(path, title):
        page.goto(BASE + path)
        expect(page.get_by_role('heading', name=title, exact=True)).to_be_visible()

    def button(name, locator=page):
        return locator.get_by_role('button', name=name, exact=True)

    login(1)
    setup='/people/company-setup-import'
    go(setup, 'Company setup & HRIS import')
    expect(page.get_by_text('MySQL backend not verified',exact=False).first).to_be_visible()
    expect(button('Save company profile')).to_be_disabled()
    expect(page.get_by_role('heading',name='Employee HRIS import & settings')).to_have_count(0)
    setup_api='**/api/admin/setup/overview'
    page.route(setup_api,lambda route:route.fulfill(json={
        'database_engine':'mysql','backend_version':'4.8.0','completed':0,'total':0,'checks':[],'counts':{}
    }))
    go(setup, 'Company setup & HRIS import')
    expect(page.get_by_role('heading',name='Employee HRIS import & settings')).to_be_visible()
    page.unroute(setup_api)
    print('PASS Company setup importer blocked until MySQL and API release verified', flush=True)
    go('/workspace/team-leave-planner', 'Team leave & coverage planner')
    button('Coverage settings').click()
    page.get_by_label('Absence warning threshold').fill('3')
    button('Save settings').click()
    expect(page.get_by_text('Warning threshold: 3', exact=False)).to_be_visible()
    button('Add coverage plan').click()
    page.get_by_label('Plan title').fill('Workspace smoke coverage')
    page.get_by_label('Primary employee').select_option('3')
    page.get_by_label('Backup employee').select_option('4')
    button('Save coverage plan').click()
    button('Edit Workspace smoke coverage').click()
    page.get_by_label('Plan title').fill('Workspace smoke updated coverage')
    button('Save plan changes').click()
    button('Delete Workspace smoke updated coverage').click()
    expect(button('Edit Workspace smoke updated coverage')).to_have_count(0)
    print('PASS coverage settings and manual add/edit/delete', flush=True)

    page.evaluate("sessionStorage.clear()")
    login(3)
    settings_path='/settings/my-workspace'
    links=(
        ('Team leave & coverage planner','/workspace/team-leave-planner'),
        ('My requests & shortcuts','/workspace/my-requests'),
        ('Notification inbox','/workspace/notifications'),
        ('My calendar','/workspace/calendar'),
        ('My Account Security','/settings/account-security'),
    )
    directory=page.locator('.ws-settings-directory')
    for title, url in links:
        go(settings_path,'My workspace')
        entry=directory.get_by_role('link',name=title,exact=True)
        expect(entry).to_have_attribute('href',url)
        entry.click()
        expect(page).to_have_url(BASE+url)
        expect(page.get_by_role('heading',name=title,exact=True)).to_be_visible()
    page.set_viewport_size({'width':390,'height':850})
    go(settings_path,'My workspace')
    expect(directory.get_by_role('link',name='My Account Security',exact=True)).to_be_visible()
    assert directory.evaluate('(el) => el.scrollWidth <= el.clientWidth + 1'), 'Directory overflowing on mobile'
    page.set_viewport_size({'width':1440,'height':950})
    print('PASS settings directory links and mobile layout', flush=True)

    go('/workspace/team-leave-planner', 'Team leave & coverage planner')
    expect(page.get_by_role('heading', name='My coverage assignments')).to_be_visible()
    expect(button('Add coverage plan')).to_have_count(0)

    go('/workspace/my-requests', 'My requests & shortcuts')
    button('New draft').click()
    page.get_by_label('Draft title').fill('Workspace smoke draft')
    button('Save draft').click()
    button('Edit draft: Workspace smoke draft').click()
    page.get_by_label('Draft title').fill('Workspace smoke updated draft')
    button('Save draft').click()
    button('Delete draft: Workspace smoke updated draft').click()
    button('Delete draft').click()
    expect(button('Edit draft: Workspace smoke updated draft')).to_have_count(0)
    button('History settings').click()
    expect(page.get_by_role('heading', name='History settings', exact=True)).to_be_visible()
    print('PASS request draft add/edit/delete and settings panel', flush=True)

    go('/workspace/notifications', 'Notification inbox')
    page.get_by_text('Inbox settings', exact=True).click()
    page.get_by_label('Default to unread-only inbox').click()
    expect(page.get_by_label('Default to unread-only inbox')).to_be_checked()
    button('Add reminder').click()
    page.get_by_label('Title', exact=True).fill('Workspace smoke reminder')
    button('Save reminder').click()
    row = page.locator('article').filter(has_text='Workspace smoke reminder')
    button('Edit', row).click()
    page.get_by_label('Title', exact=True).fill('Workspace smoke updated reminder')
    button('Save reminder').click()
    row = page.locator('article').filter(has_text='Workspace smoke updated reminder')
    button('Complete', row).click()
    expect(row).to_have_count(0)
    button('Completed').click()
    button('Delete', row).click()
    button('Confirm deletion', row).click()
    expect(row).to_have_count(0)
    print('PASS inbox settings and private reminder add/edit/complete/delete', flush=True)

    go('/workspace/calendar', 'My calendar')
    button('Calendar settings').click()
    page.get_by_label('Week starts on').select_option('sunday')
    page.get_by_label('Default personal event time', exact=False).fill('10:30')
    button('Save settings').click()
    expect(page.locator('.v27-weekday').first).to_have_text('Sun')
    button('Add personal event').first.click()
    expect(page.get_by_label('Time (optional)')).to_have_value('10:30')
    page.get_by_label('Event title').fill('Workspace smoke event')
    button('Save personal event').click()
    card = page.locator('.v27-agenda-item').filter(has_text='Workspace smoke event')
    button('Edit', card).click()
    page.get_by_label('Event title').fill('Workspace smoke updated event')
    button('Save personal event').click()
    card = page.locator('.v27-agenda-item').filter(has_text='Workspace smoke updated event')
    button('Delete', card).click()
    expect(card).to_have_count(0)
    print('PASS calendar settings and private event add/edit/delete', flush=True)

    go('/settings/account-security', 'My Account Security')
    page.get_by_label('Time zone').select_option('utc')
    button('Save display settings').click()
    expect(page.get_by_text('Display settings saved.', exact=True)).to_be_visible()
    page.get_by_label('Checklist item', exact=True).fill('Workspace smoke security review')
    button('Add checklist item').click()
    button('Edit Workspace smoke security review').click()
    page.get_by_label('Checklist item', exact=True).fill('Workspace smoke updated security review')
    button('Save checklist item').click()
    button('Delete Workspace smoke updated security review').click()
    expect(button('Edit Workspace smoke updated security review')).to_have_count(0)
    print('PASS security settings and private checklist add/edit/delete', flush=True)
    assert not issues, issues
    context.close()


if __name__ == '__main__':
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.environ.get('CHROMIUM_PATH') or None,
            headless=True, args=['--no-sandbox'],
        )
        try:
            run(browser)
        finally:
            browser.close()
