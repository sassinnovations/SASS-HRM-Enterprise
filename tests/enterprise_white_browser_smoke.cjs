// This check reads all registered routes in a disposable, seeded local stack.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
if(process.env.SASS_HRM_TESTING!=='1')throw Error('Disposable stack required');
const base='http://127.0.0.1:5173';
const routes=[...fs.readFileSync(path.join(__dirname,'../web/src/pageRoutes.ts'),'utf8').matchAll(/^\s+(\w+): '(\/[^']+)'/gm)].map(m=>[m[1],m[2]]);
const white='rgb(255, 255, 255)';
const blue='rgb(90, 95, 233)';
const blueWash='rgb(238, 240, 255)';
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined,args:['--no-sandbox']});
 try{
  const desktop=await browser.newPage({viewport:{width:1440,height:1024},reducedMotion:'reduce'});
  const mobile=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:1,reducedMotion:'reduce'});
  const errors=[];
  for(const page of [desktop,mobile]){
   page.setDefaultTimeout(8000);
   page.on('pageerror',error=>errors.push(error.message));
  }
  const bg=(page,selector)=>page.locator(selector).evaluate(el=>getComputedStyle(el).backgroundColor);
  for(const page of [desktop,mobile]){
   await page.goto(base+'/sign-in');
   await page.locator('.login-card').waitFor();
   assert.equal(await bg(page,'.login-submit'),blue);
   for(const selector of ['.login-card','.login-panel']){
    const frame=await page.locator(selector).evaluate(el=>[getComputedStyle(el).borderTopWidth,getComputedStyle(el).boxShadow]);
    assert.deepEqual(frame,['0px','none']);
   }
   for(const selector of ['.login-shell','.login-main'])assert.equal(await bg(page,selector),white,selector);
   if(await page.locator('.login-intro').isVisible())assert.match(await page.locator('.login-intro').evaluate(el=>getComputedStyle(el).backgroundImage),/linear-gradient.*36, 42, 114/);
   assert.match(await page.locator('.login-main').evaluate(el=>getComputedStyle(el).backgroundImage),/porcelain-botanical|data:image\/svg\+xml/);
   if(process.env.BOTANICAL_CAPTURE)await page.screenshot({path:process.env.BOTANICAL_CAPTURE+(page===desktop?'-desktop.png':'-mobile.png'),animations:'disabled'});
   await page.getByRole('button',{name:'Create Employee / HR / Admin account'}).click();
   await page.locator('.signup-card').waitFor();
   assert.equal(await bg(page,'.signup-card'),white);
   await page.getByRole('button',{name:'Back to sign in'}).click();
   await page.locator('#sass-login-email').fill((page===desktop?'reviewer':'owner')+'@test.invalid');
   await page.locator('#sass-login-password').fill('SyntheticBrowser-2026!');
   await page.getByRole('button',{name:'Sign in to SASS HRM'}).click();
   await page.locator('.gd').waitFor();
   assert.equal(await bg(page,'.gd'),white);
   assert.equal(await bg(page,'.gd-primary'),blue);
   assert.equal(await bg(page,'.gd-tabs [aria-pressed=true]'),blueWash);
  }
  let visited=0;
  for(const [key,route] of routes){
   await desktop.evaluate(url=>{
    window.history.pushState(null,'',url);
    window.dispatchEvent(new PopStateEvent('popstate'));
   },route);
   if(key==='assistant'){
    await desktop.locator('.sass-ai-floating-window:not(.closed) .sass-ai-hero').waitFor();
    assert.equal(await bg(desktop,'.sass-ai-hero'),white);
    assert.equal(await bg(desktop,'.sass-ai-floating-window'),white);
    assert.equal(await bg(desktop,'.sass-ai-tabs [aria-selected=true]'),blueWash);
    await desktop.getByRole('button',{name:'Close AI bot'}).click();
   }else{
    await desktop.waitForURL('**'+route);
    const current=await desktop.locator('.page-content').innerText();
    assert.ok(!/You cannot open this page|This feature URL does not exist|could not display this screen/.test(current),route);
    assert.ok(current.trim().length>35,'Content should render: '+route);
    for(const selector of ['.shell','.content','.topbar'])assert.equal(await bg(desktop,selector),white,route+' '+selector);
    if(await desktop.locator('.page-header').count()){
     const colors=await desktop.locator('.page-header').evaluateAll(items=>items.map(el=>getComputedStyle(el).backgroundColor));
     assert.ok(colors.every(value=>value===white),route+' header');
    }
   }
   visited++;
  }
  for(const route of ['/people/employee-hris','/services/asset-management','/talent/request-desk']){
   await mobile.evaluate(url=>{history.pushState(null,'',url);dispatchEvent(new PopStateEvent('popstate'))},route);
   await mobile.waitForURL('**'+route);
   assert.equal(await bg(mobile,'.content'),white,route);
   assert.ok(await mobile.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),route+' mobile overflow');
  }
  await mobile.getByRole('button',{name:'Open AI bot'}).click();
  await mobile.locator('.sass-ai-hero').waitFor();
  assert.equal(await bg(mobile,'.sass-ai-hero'),white);
  assert.deepEqual(errors,[]);
  console.log('PASS: '+visited+' registered white routes, sign-in, sign-up, floating AI and representative mobile pages');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
