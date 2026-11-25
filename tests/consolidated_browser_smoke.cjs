// Requires Playwright and a disposable, already running test-only instance.
// The test creates synthetic records; do not point it at a real HRM instance.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const base = 'http://127.0.0.1:5173';
if (process.env.SASS_HRM_TESTING !== '1') throw Error('Only run with a disposable SASS_HRM_TESTING instance');
(async () => {
  const browser = await chromium.launch({executablePath:process.env.CHROMIUM_PATH || undefined, args:['--no-sandbox']});
  const marker = Date.now();
  const ticket = 'VPN test '+marker;
  const request = 'Letter test '+marker;
  const errors = [];
  async function signIn(name, route) {
    const context = await browser.newContext();
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(base + route);
    await page.locator('#sass-login-email').fill(name+'@test.invalid');
    await page.locator('#sass-login-password').fill('SyntheticBrowser-2026!');
    await page.getByRole('button',{name:'Sign in to SASS HRM'}).click();
    await page.locator('.page-content').waitFor();
    return page;
  }
  try {
    const owner = await signIn('owner','/talent/request-desk');
    const queue = owner.getByRole('region',{name:'HR Service Center'});
    await queue.getByRole('button',{name:'New service request',exact:true}).click();
    await owner.getByLabel('Request type').selectOption({label:'Documents'});
    await owner.getByLabel('Subject',{exact:true}).fill(request);
    await owner.getByLabel('Details',{exact:true}).fill('Please create a sample letter for this test.');
    await owner.getByRole('button',{name:'Submit request',exact:true}).click();
    await queue.getByRole('button',{name:new RegExp('Open Request.*'+request)}).waitFor();

    await queue.getByRole('button',{name:'New support ticket',exact:true}).click();
    const dialog = owner.getByRole('dialog');
    await dialog.getByLabel('Subject',{exact:true}).fill(ticket);
    await dialog.getByLabel('Describe your request').fill('Please check the synthetic VPN issue.');
    await dialog.locator('button[type=submit]').click();
    await dialog.waitFor({state:'hidden'});
    await queue.getByRole('button',{name:new RegExp('Open Ticket.*'+ticket)}).click();
    const details = owner.getByRole('region',{name:'Case details'});
    await details.getByText('Please check the synthetic VPN issue.').waitFor();
    await details.getByLabel('Reply visible to the employee').fill('Synthetic test reply.');
    await details.getByRole('button',{name:'Send reply'}).click();
    await details.getByText('Synthetic test reply.',{exact:true}).waitFor();
    assert.equal(await details.getByLabel('Change case status').count(),0);
    await details.getByRole('button',{name:'Close details'}).click();
    await queue.getByLabel('Case type').selectOption('request');
    await queue.getByRole('button',{name:new RegExp('Open Request.*'+request)}).waitFor();
    assert.equal(await queue.getByRole('button',{name:new RegExp('Open Ticket.*'+ticket)}).count(),0);
    await owner.reload();
    await queue.getByRole('button',{name:new RegExp('Open Ticket.*'+ticket)}).waitFor();
    await queue.getByRole('button',{name:new RegExp('Open Request.*'+request)}).waitFor();

    const other = await signIn('other','/talent/hr-helpdesk');
    await other.getByText('No cases found.',{exact:true}).waitFor();
    const reviewer = await signIn('reviewer','/talent/request-desk');
    const review = reviewer.getByRole('region',{name:'Case details'});
    await reviewer.getByRole('button',{name:new RegExp('Open Ticket.*'+ticket)}).click();
    await review.getByText('Synthetic test reply.',{exact:true}).waitFor();
    await review.getByLabel('HR owner').selectOption({label:'reviewer'});
    await review.getByLabel('Response due date').fill('2099-12-01');
    await review.getByRole('button',{name:'Save assignment'}).click();
    await review.getByText('reviewer · Due 2099-12-01',{exact:false}).waitFor();
    await review.getByLabel('Change case status').selectOption('Resolved');
    await review.getByRole('button',{name:'Save status'}).click();
    await review.getByText(/Ticket #.+Resolved/).waitFor();
    await review.getByRole('button',{name:'Close details'}).click();
    await reviewer.getByRole('button',{name:new RegExp('Open Request.*'+request)}).click();
    await review.getByLabel('Change case status').selectOption('In Progress');
    await review.getByRole('button',{name:'Save status'}).click();
    await review.getByText(/Request #.+In Progress/).waitFor();
    await review.getByRole('button',{name:'Close details'}).click();
    await reviewer.getByLabel('Case status').selectOption('completed');
    await reviewer.getByRole('button',{name:new RegExp('Open Ticket.*'+ticket)}).waitFor();
    assert.equal(await reviewer.getByRole('button',{name:new RegExp('Open Request.*'+request)}).count(),0);
    const recruitment = reviewer.getByRole('link',{name:'Recruitment Workspace',exact:true});
    if (!(await recruitment.isVisible())) await reviewer.getByRole('button',{name:'Talent Management',exact:true}).click();
    await recruitment.click();
    const workflows = reviewer.getByRole('navigation',{name:'Recruitment workflows'});
    await workflows.getByRole('button',{name:'Candidate Search & Database',exact:true}).click();
    await reviewer.waitForURL('**/talent/candidate-search-database');
    await workflows.getByRole('button',{name:'Interviews',exact:true}).click();
    await reviewer.getByRole('heading',{name:'Interview scheduling',exact:true}).waitFor();
    await reviewer.goBack();
    await reviewer.waitForURL('**/talent/candidate-search-database');
    await workflows.waitFor();
    assert.deepEqual(errors, []);
    console.log('PASS: browser sign-in, both case forms, replies, HR assignment and status changes, case filters, reload, privacy, and recruitment routing');
  } finally {
    await browser.close();
  }
})().catch(error => {console.error(error);process.exitCode=1;});
