const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base='http://127.0.0.1:5173';
if(process.env.SASS_HRM_TESTING!=='1')throw Error('Disposable stack required');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined,args:['--no-sandbox']});
 const errors=[];
 async function login(username){
  const page=await browser.newPage({viewport:{width:1380,height:990}});
  page.setDefaultTimeout(10000);
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'/sign-in');
  await page.locator('#sass-login-email').fill(username+'@test.invalid');
  await page.locator('#sass-login-password').fill('SyntheticBrowser-2026!');
  await page.getByRole('button',{name:'Sign in to SASS HRM'}).click();
  await page.locator('.gd').waitFor();
  return page;
 }
 try{
  const admin=await login('reviewer');
  for(const kind of ['products','projects']){
   const noun=kind.slice(0,-1);
   const title=noun[0].toUpperCase()+noun.slice(1);
   const category=kind==='products'?'Business tools':'Internal delivery';
   const defaultStatus=kind==='products'?'Inactive':'On Hold';
   const nextStatus=kind==='products'?'Active':'Completed';
   const name='Browser QA '+noun;
   await admin.goto(base+'/services/'+kind);
   await admin.getByRole('button',{name:title+' settings',exact:true}).click();
   await admin.getByLabel('Default status',{exact:true}).selectOption(defaultStatus);
   await admin.getByLabel('Categories (one per line)',{exact:true}).fill(category);
   await admin.getByRole('button',{name:'Save settings',exact:true}).click();
   await admin.getByRole('button',{name:'Add '+noun,exact:true}).click();
   await admin.getByLabel('Code',{exact:true}).fill('QA-'+kind);
   await admin.getByLabel('Name',{exact:true}).fill(name);
   assert.equal(await admin.getByLabel('Status',{exact:true}).inputValue(),defaultStatus);
   await admin.getByLabel('Category',{exact:true}).selectOption({label:category});
   if(kind==='projects'){
    await admin.getByLabel('Project owner',{exact:true}).selectOption({label:'owner'});
    await admin.getByLabel('Start date',{exact:true}).fill('2026-11-25');
    await admin.getByLabel('End date',{exact:true}).fill('2026-12-05');
   }
   await admin.getByRole('button',{name:'Save '+noun,exact:true}).click();
   await admin.getByRole('button',{name:'Edit '+name,exact:true}).waitFor();
   await admin.reload();
   await admin.getByRole('button',{name:'Edit '+name,exact:true}).click();
   await admin.getByLabel('Name',{exact:true}).fill(name+' updated');
   await admin.getByLabel('Status',{exact:true}).selectOption(nextStatus);
   await admin.getByRole('button',{name:'Save '+noun,exact:true}).click();
   await admin.getByRole('button',{name:'Edit '+name+' updated',exact:true}).waitFor();
   const backLink=kind==='products'?'Asset Management':'Project Timesheets';
   await admin.getByRole('navigation',{name:title+' links'}).getByRole('button',{name:backLink,exact:true}).click();
   assert.match(admin.url(),kind==='products'?/asset-management$/:/project-timesheets$/);
   await admin.goBack();
   await admin.getByRole('button',{name:'Delete '+name+' updated',exact:true}).click();
   await admin.getByRole('button',{name:'Keep record',exact:true}).click();
   await admin.getByRole('button',{name:'Delete '+name+' updated',exact:true}).click();
   await admin.getByRole('button',{name:'Confirm delete',exact:true}).click();
   await admin.getByRole('button',{name:'Delete '+name+' updated',exact:true}).waitFor({state:'hidden'});
   await admin.reload();
   await admin.getByRole('button',{name:'Add '+noun,exact:true}).waitFor();
   assert.equal(await admin.getByRole('button',{name:'Edit '+name+' updated',exact:true}).count(),0);
  }
  const emp=await login('owner');
  for(const kind of ['products','projects']){
   await emp.goto(base+'/services/'+kind);
   await emp.getByRole('heading',{name:'You cannot open this page'}).waitFor();
  }
  assert.deepEqual(errors,[]);
  console.log('PASS: both registers, persistent settings and records, add/edit/confirmed delete, linked modules and administrator access');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
