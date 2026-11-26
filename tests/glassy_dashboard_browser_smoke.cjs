// Run only against a disposable test stack with three synthetic accounts and assigned test equipment.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base='http://127.0.0.1:5173';
if(process.env.SASS_HRM_TESTING!=='1')throw Error('Disposable stack required');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined,args:['--no-sandbox']});
 const errors=[];
 async function login(name,options={}){
  const page=await (await browser.newContext(options)).newPage();
  page.setDefaultTimeout(10000);
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'/workspace/overview');
  await page.locator('#sass-login-email').fill(name+'@test.invalid');
  await page.locator('#sass-login-password').fill('SyntheticBrowser-2026!');
  await page.getByRole('button',{name:'Sign in to SASS HRM'}).click();
  await page.locator('.gd').waitFor();
  return page;
 }
 const nav=p=>p.getByRole('navigation',{name:'Dashboard sections'});
 const tab=(p,label)=>nav(p).getByRole('button',{name:label,exact:true}).click();
 const gd=p=>p.locator('.gd');
 async function opens(page,label,path,section){
  await page.locator('.sass-breadcrumb-link').click();
  await gd(page).waitFor();
  if(section&&section!=='Overview')await tab(page,section);
  else await tab(page,'Overview');
  await gd(page).getByRole('button',{name:label}).click();
  await page.waitForURL('**'+path);
  await gd(page).waitFor({state:'hidden'});
  assert.equal(await page.getByRole('heading',{name:'You cannot open this page'}).count(),0);
 }
 try{
  const hr=await login('reviewer',{viewport:{width:1440,height:1024}});
  await hr.getByRole('button',{name:'Refresh data',exact:true}).isEnabled();
  await gd(hr).getByRole('button',{name:'Apply for leave',exact:true}).click();
  await hr.getByRole('dialog').getByLabel('Leave category').waitFor();
  await hr.keyboard.press('Escape');
  await hr.getByRole('dialog').waitFor({state:'hidden'});
  await tab(hr,'Companies');
  await gd(hr).locator('.gd-list').getByText('Engineering HQ',{exact:true}).waitFor();
  await gd(hr).getByRole('button',{name:'Open organization'}).click();
  await hr.waitForURL('**/people/organization');
  await hr.goBack();
  await gd(hr).waitFor();
  await tab(hr,'Reports');
  await gd(hr).getByLabel('Metric').selectOption('approved_leave');
  await gd(hr).getByLabel('Period').selectOption('3');
  await gd(hr).locator('.gd-trend figcaption>span').last().waitFor();
  assert.equal(await gd(hr).locator('.gd-trend figcaption>span').count(),3);
  const [dl]= await Promise.all([hr.waitForEvent('download'),gd(hr).getByRole('button',{name:'Export department CSV'}).click()]);
  assert.equal(dl.suggestedFilename(),'sass-department-summary.csv');
  if(process.env.GD_SCREENSHOT)await hr.screenshot({path:process.env.GD_SCREENSHOT,animations:'disabled'});
  await tab(hr,'Support');
  await gd(hr).getByText('VPN test',{exact:false}).waitFor();
  assert.ok(Number(await gd(hr).locator('.gd-metric').filter({hasText:'All cases'}).locator('strong').textContent())>=2);
  await gd(hr).getByLabel('Status',{exact:true}).selectOption('completed');
  await gd(hr).getByText('VPN test',{exact:false}).waitFor();
  assert.equal(await gd(hr).getByText('Letter test',{exact:false}).count(),0);
  await gd(hr).getByRole('button',{name:'Open HR Service Center'}).click();
  await hr.waitForURL('**/talent/request-desk');
  await hr.goto(base+'/workspace/overview');
  await tab(hr,'Products');
  await gd(hr).getByText('Synthetic Laptop',{exact:true}).waitFor();
  await gd(hr).getByLabel('Status',{exact:true}).selectOption('Returned');
  await gd(hr).getByText('No assets match that status.').waitFor();
  await gd(hr).getByRole('button',{name:'Open asset register'}).click();
  await hr.waitForURL('**/services/asset-management');
  await hr.getByRole('table').getByText('Synthetic Laptop',{exact:true}).waitFor();

  for(const [label,path,section] of [
   [/^Workforce /,'/people/employee-hris'],
   [/^Present today /,'/compensation/time-attendance'],
   [/^Pending leave /,'/compensation/leave-management'],
   [/^Open jobs /,'/talent/recruitment-ats'],
   ['Announcements','/people/organization'],
   ['My calendar','/workspace/calendar'],
   ['Organization settings','/people/organization-settings','Companies'],
   [/^Directory entries /,'/people/organization-chart','Companies'],
   [/^Headcount /,'/people/employee-hris','Reports'],
   ['Full reports','/people/reports-analytics','Reports'],
   [/^Helpdesk tickets /,'/talent/hr-helpdesk','Support'],
   ['Read HR policies','/people/policies-handbook','Support'],
   ['Open product catalog','/services/products','Products'],
   [/^Total assets /,'/services/asset-management','Products'],
   ['Open project register','/services/projects','Projects'],
   [/^Time entries /,'/compensation/project-timesheets','Projects'],
  ])await opens(hr,label,path,section);
  await hr.goto(base+'/workspace/overview');
  await gd(hr).getByRole('button',{name:'Ask SASS AI'}).click();
  await hr.locator('.sass-ai-floating-window:not(.closed)').waitFor();
  await hr.getByRole('button',{name:'Close AI bot'}).click();
  const employee=await login('other',{viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:1,reducedMotion:'reduce'});
  assert.equal(await nav(employee).getByRole('button',{name:'Reports'}).count(),0);
  await tab(employee,'Support');
  await gd(employee).getByText('No cases match that status.').waitFor();
  assert.equal(await gd(employee).locator('.gd-metric').filter({hasText:'All cases'}).locator('strong').textContent(),'0');
  await tab(employee,'Products');
  await gd(employee).getByText('No assets match that status.').waitFor();
  assert.equal(await gd(employee).getByText('Synthetic Laptop',{exact:true}).count(),0);
  assert.ok(await gd(employee).evaluate(el=>el.scrollWidth<=el.clientWidth+1),'Mobile dashboard should not overflow horizontally');
  if(process.env.GD_MOBILE_SCREENSHOT)await employee.screenshot({path:process.env.GD_MOBILE_SCREENSHOT});

  assert.equal(await gd(employee).getByRole('button',{name:'Open product catalog'}).count(),0);
  await tab(employee,'Projects');
  assert.equal(await gd(employee).getByRole('button',{name:'Open project register'}).count(),0);
  await opens(employee,'Open project timesheets','/compensation/project-timesheets','Projects');
  await opens(employee,/^My profile /,'/workspace/my-profile');
  await opens(employee,/^My learning /,'/culture/learning-training');
  await employee.goto(base+'/people/reports-analytics');
  await employee.getByRole('heading',{name:'You cannot open this page'}).waitFor();
  assert.deepEqual(errors,[]);
  console.log('PASS: glass dashboard, live sections and filters, report download, module navigation, role isolation and mobile layout');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
