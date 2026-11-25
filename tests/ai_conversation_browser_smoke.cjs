const {chromium}=require('playwright');
const assert=require('node:assert/strict');
if(process.env.SASS_HRM_TESTING!=='1')throw Error('Disposable browser stack only');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined,args:['--no-sandbox']});
 try{
  const page=await browser.newPage();
  page.setDefaultTimeout(10000);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:5173/sign-in');
  await page.locator('#sass-login-email').fill('owner@test.invalid');
  await page.locator('#sass-login-password').fill('SyntheticBrowser-2026!');
  await page.getByRole('button',{name:'Sign in to SASS HRM'}).click();
  await page.getByRole('button',{name:'Open AI bot'}).click();
  const ai=page.locator('#sass-ai-floating-window');
  await ai.getByRole('textbox',{name:'Ask SASS AI'}).fill('What is my leave balance?');
  await ai.getByRole('button',{name:'Send question'}).click();
  const follow=ai.getByRole('group',{name:'Follow-up questions'});
  await follow.getByRole('button',{name:'Check again'}).click();
  await ai.getByText(/Your configured annual-leave allowance/).nth(1).waitFor();
  await follow.getByRole('button',{name:'Open the source'}).click();
  await ai.getByText(/Use the source or module link/).waitFor();
  await ai.locator('.sass-ai-msg.bot').last().getByRole('button',{name:'Open',exact:true}).click();
  await page.waitForURL('**/compensation/leave-management');
  assert.ok(await ai.isVisible());
  page.once('dialog',d=>d.accept());
  await ai.getByRole('button',{name:'New chat'}).click();
  await follow.waitFor({state:'hidden'});
  assert.equal(await ai.getByText(/configured annual-leave allowance/).count(),0);
  assert.deepEqual(errors,[]);
  console.log('PASS: conversational follow-ups, authorized source navigation, floating chat continuity, and New chat reset');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
