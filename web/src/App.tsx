import {AccountSecurityCenter} from './AccountSecurityCenter';
import {hrmFetch,HRM_CONNECTION_LOST,HRM_CONNECTION_RESTORED,HRM_SESSION_EXPIRED} from './apiTransport';
import {PerformanceJournal} from './PerformanceJournal';
import {PerformanceFollowups} from './PerformanceFollowups';
import {PerformanceGrowth} from './PerformanceGrowth';
import {PerformanceSuite} from './PerformanceSuite';
import {GlobalSearch} from './GlobalSearch';
import {DataQualityCenter} from './DataQualityCenter';
import {REFRESH_DATA_EVENT,useRefreshData} from './useRefreshData';
import {LeaveCoveragePlanner,HRTaskTemplates} from './WorkforcePlanning';
import {WorkflowReminders} from './WorkflowReminders';
import {WorkspaceControl} from './WorkspaceControl';
import {SelfServiceHub} from './SelfServiceHub';
import {PAGE_ROUTES,pageUrl,pageFromPath} from './pageRoutes';
import {EmployeeServiceOperations,WorkspacePreferences,AICapabilities} from './EmployeeServicesV20';
import React, {useCallback, useEffect, useRef, useState} from 'react';
import {
  Activity, ArrowDownLeft, ArrowDownRight, ArrowRight, ArrowUpRight, BarChart3, Bell,
  BookOpen, Bot, BriefcaseBusiness, CalendarDays, CalendarCheck2, Check, CheckCircle2,
  ChevronDown, ChevronRight, CircleHelp, ClipboardCheck, Clock3,
  Download, FileBadge2, FileText, GraduationCap, HandCoins, Home, Inbox, Laptop2,
  LayoutDashboard, LockKeyhole, LogOut, Menu, Megaphone,
  MessageCircle, Plus, Search, Send, Settings2, ShieldCheck, Sparkles, Building2, UploadCloud,
  Target, UserRoundCheck, UsersRound, WalletCards, X, Timer, Award, HeartHandshake, ClipboardList, ListTodo, CalendarRange, BadgeCheck, Video, KeyRound, Lock,
  Network, UserCog, MessagesSquare, Fingerprint, UserRoundPlus, BookMarked, ContactRound, NotebookPen, House, FileDown, CalendarClock, FolderLock, Flag, GitBranch, Eye, EyeOff
} from 'lucide-react';
import './style.css';
import {PayrollWorkbench, TaxCalculator} from './PayrollExtra';
import {AttendanceCorrections, DocumentVault, ReadinessCenter} from './OperationsExtra';
import {CultureModule} from './CultureSuite';
import {AdminSetupCenter} from './AdminSetup';
import {OrganizationSettings} from './OrganizationSettings';
import {PersonalCalendar} from './PersonalCalendar';
import {SetupProgress} from './SetupProgress';
import {TalentTools} from './TalentTools';
import {MyProfile,ProfileManagement} from './ProfileCenter';
import {CompensationTools} from './CompensationTools';
import {CompensationSettings} from './CompensationSettings';
import {AdminSettingsCenter} from './AdminSettingsCenter';
import {CultureEnhancements} from './CultureEnhancements';

type Rec = Record<string, any>;
type Field={key:string;label:string;type?:'text'|'date'|'datetime-local'|'password'|'number'|'email'|'textarea'|'select';required?:boolean;options?:(string|{value:string;label:string})[];value?:string|number; min?:number|string; max?:number|string};
type Dialog={title:string;description?:string;fields:Field[];path:string;method?:string;success?:string; fixed?:Rec};
type Column={key:string;label:string;render?:(item:Rec)=>React.ReactNode};
type MenuItem={key:string;label:string;icon:React.ElementType;only?:'admin'|'management'};
// Use Vite's /api proxy for local development. Production can provide VITE_API_URL.
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
// Calendar dates must be local dates, not UTC or browser-locale dependent strings.
const localDate=(d:Date)=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
const today=()=>localDate(new Date());
const nextMonth=()=>{const d=new Date();d.setMonth(d.getMonth()+1);return localDate(d)};
const currency=(n:number)=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(n||0);
const fmt=(s:string)=>{if(!s)return '—';let d=new Date(s.length===10?s+'T12:00:00':s);if(isNaN(d.getTime()))return s;const style=document.documentElement.dataset.hrDateFormat;return style==='YYYY-MM-DD'?d.toLocaleDateString('sv-SE'):style==='MM/DD/YYYY'?d.toLocaleDateString('en-US',{month:'2-digit',day:'2-digit',year:'numeric'}):d.toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'})};
const nameCaps=(s:string)=>s.split(' ').map(n=>n[0]||'').slice(0,2).join('').toUpperCase();
const titleCase=(v:string)=>v.replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
const menus:MenuItem[]=[
 {key:'dashboard',label:'Overview',icon:LayoutDashboard},
 {key:'workcenter',label:'Action center',icon:ClipboardCheck},
 {key:'globalsearch',label:'Global HR search',icon:Search},
 {key:'dataquality',label:'HR data quality center',icon:ClipboardCheck,only:'admin'},
 {key:'reminders',label:'Workflow reminders',icon:Bell},
 {key:'coverage',label:'Team leave planner',icon:CalendarDays},
 {key:'selfservice',label:'My requests & shortcuts',icon:Inbox},
 {key:'inbox',label:'Notification inbox',icon:Bell},
 {key:'workflowsettings',label:'Workflow settings',icon:Settings2,only:'admin'},
 {key:'employees',label:'Employee HRIS',icon:UsersRound},
 {key:'orgchart',label:'Organization chart',icon:Network},
 {key:'skills',label:'Skills & competencies',icon:BookMarked},
 {key:'privateprofile',label:'Private contact profile',icon:ContactRound},
 {key:'profile',label:'My profile',icon:UserRoundCheck},
 {key:'profilemgmt',label:'Profile management',icon:UserCog,only:'admin'},
 {key:'workmode',label:'Work arrangement requests',icon:House},
 {key:'compliance',label:'Policy acknowledgements',icon:NotebookPen},
 {key:'accounts',label:'Account provisioning',icon:UserCog,only:'admin'},
 {key:'companysetup',label:'Company setup & import',icon:Building2,only:'admin'},
 {key:'orgsettings',label:'Organization settings',icon:Settings2,only:'admin'},
 {key:'settingscenter',label:'Administration settings center',icon:Settings2,only:'admin'},
 {key:'talentsettings',label:'Talent & service settings',icon:Settings2,only:'admin'},
 {key:'attendance',label:'Time & attendance',icon:Clock3},
 {key:'corrections',label:'Attendance corrections',icon:CalendarClock},
 {key:'shifts',label:'Shifts & schedules',icon:CalendarCheck2},
 {key:'timesheets',label:'Project timesheets',icon:Timer},
 {key:'leave',label:'Leave management',icon:CalendarDays},
 {key:'recruitment',label:'Recruitment ATS',icon:BriefcaseBusiness,only:'management'},
 {key:'onboarding',label:'Onboarding',icon:UserRoundCheck},
 {key:'payrollengine',label:'Payroll workbench',icon:WalletCards},
 {key:'compensationsettings',label:'Compensation settings',icon:Settings2,only:'admin'},
 {key:'payroll',label:'Payslip archive',icon:FileText},
 {key:'taxcalculator',label:'Tax calculator · Global',icon:HandCoins},
 {key:'performance',label:'Performance & goals',icon:Target},
 {key:'performancecycles',label:'Performance review cycles',icon:CalendarRange},
 {key:'appraisals',label:'Employee appraisals',icon:ClipboardList},
 {key:'checkins',label:'1:1 check-ins',icon:MessagesSquare},
 {key:'growthplans',label:'Individual development plans',icon:BookMarked},
 {key:'feedbackrequests',label:'Manager feedback requests',icon:MessageCircle},
 {key:'followups',label:'Performance action tracker',icon:ClipboardCheck},
 {key:'reviewprogress',label:'Review cycle progress',icon:BarChart3},
 {key:'evidence',label:'Performance evidence portfolio',icon:BookMarked},
 {key:'goaljournal',label:'Goal check-in journal',icon:NotebookPen},
 {key:'training',label:'Learning & training',icon:GraduationCap},
 {key:'career',label:'Career development',icon:GitBranch},
 {key:'voice',label:'Employee Voice',icon:HeartHandshake},
 {key:'discipline',label:'Discipline & conduct',icon:Flag},
 {key:'requestdesk',label:'Request Desk',icon:Inbox},
 {key:'helpdesk',label:'HR helpdesk',icon:CircleHelp},
 {key:'expenses',label:'Expenses & claims',icon:HandCoins},
 {key:'assets',label:'Asset management',icon:Laptop2},
 {key:'documents',label:'Employee documents',icon:FileBadge2},
 {key:'vault',label:'Secure document vault',icon:FolderLock},
 {key:'offboarding',label:'Offboarding',icon:ClipboardCheck},
 {key:'organization',label:'Organization',icon:Home},
 {key:'policies',label:'Policies & handbook',icon:BookOpen},
 {key:'benefits',label:'Benefits & programs',icon:HeartHandshake},
 {key:'recognition',label:'Recognition wall',icon:Award},
 {key:'surveys',label:'Employee pulse',icon:ClipboardList},
 {key:'interviews',label:'Interview scheduling',icon:Video,only:'management'},
 {key:'tasks',label:'HR tasks',icon:ListTodo},
 {key:'tasktemplates',label:'HR task templates',icon:ClipboardList,only:'management'},
 {key:'approvals',label:'Approval inbox',icon:BadgeCheck,only:'management'},
 {key:'calendar',label:'My calendar',icon:CalendarRange},
 {key:'reports',label:'Reports & analytics',icon:BarChart3,only:'management'},
 {key:'audit',label:'Audit trail',icon:ShieldCheck,only:'admin'},
 {key:'readiness',label:'HR operations center',icon:ClipboardCheck,only:'admin'},
 {key:'developer',label:'Developer console',icon:LockKeyhole},
 {key:'assistant',label:'SASS AI Assistant',icon:Bot},
 {key:'settings',label:'My settings',icon:Settings2},
 {key:'mysecurity',label:'My account security',icon:ShieldCheck},
 {key:'securityaudit',label:'Account sign-in review',icon:LockKeyhole,only:'admin'}
];

const menuGroups:{title:string;keys:string[]}[]=[
 {title:'Workspace',keys:['dashboard','workcenter','globalsearch','reminders','coverage','selfservice','inbox','calendar','profile','mysecurity']},
 {title:'People Management',keys:['employees','orgchart','privateprofile','skills','profilemgmt','accounts','securityaudit','companysetup','settingscenter','orgsettings','talentsettings','workflowsettings','organization','policies','compliance','reports','audit','readiness','dataquality','developer']},
 {title:'Talent Management',keys:['recruitment','interviews','onboarding','requestdesk','helpdesk','tasks','tasktemplates','offboarding']},
 {title:'Compensation',keys:['leave','attendance','corrections','shifts','timesheets','payrollengine','payroll','taxcalculator','benefits','expenses','compensationsettings']},
 {title:'Culture',keys:['performance','performancecycles','appraisals','checkins','growthplans','feedbackrequests','followups','reviewprogress','evidence','goaljournal','career','training','surveys','voice','discipline','recognition','workmode']},
 {title:'Employee Services',keys:['approvals','assets','documents','vault']}
];
const entities:Record<string,string>={
 privateProfile:'/private-profile/me', workModeRequests:'/work-mode/requests', policyCompliance:'/policy-compliance/me', policyComplianceSummary:'/policy-compliance/summary', employees:'/employees', orgChart:'/organization/chart', accounts:'/admin/accounts', skillsCatalog:'/skills/catalog', skillsAssignments:'/skills/assignments', entitlements:'/leave/entitlements', trends:'/reports/trends', attendance:'/attendance',shifts:'/shifts',schedule:'/schedule',timesheets:'/timesheets',leave:'/leave',payroll:'/payroll',candidates:'/candidates',jobs:'/recruitment/jobs',
 onboarding:'/onboarding',goals:'/performance/goals',reviews:'/performance/reviews',courses:'/training/courses',
 enrollments:'/training/enrollments',tickets:'/helpdesk/tickets',expenses:'/expenses',assets:'/assets',documents:'/documents',
 offboarding:'/offboarding',departments:'/organization/departments',holidays:'/organization/holidays',
 announcements:'/organization/announcements',policies:'/policies',notifications:'/notifications',audit:'/audit',
 balances:'/leave/balances/me',reports:'/reports/overview',
 benefitPlans:'/benefits/plans',benefitEnrollments:'/benefits/enrollments',recognitions:'/recognitions',
 surveys:'/surveys',interviews:'/recruitment/interviews',tasks:'/tasks',approvals:'/approvals/inbox',calendar:'/calendar/me'
};
async function req<T=Rec>(path:string,method='GET',body?:unknown):Promise<T>{
 const token=sessionStorage.getItem('sass_token');
 let res:Response;
 try {
  res=await hrmFetch(API+path,{method,headers:{'Content-Type':'application/json',...(token?{'Authorization':`Bearer ${token}`}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{})});
 } catch (error) {
  throw error instanceof Error ? error : new Error('Cannot contact the HRM API. Check Docker and the backend health.');
 }
 let output:Rec|null=null;try{output=await res.json()}catch{}
 if(!res.ok){
  if(!output && [500,502,503,504].includes(res.status)){
   throw new Error(`The HRM API is unavailable (HTTP ${res.status}). Check the backend terminal or run CHECK_CONNECTION.bat.`);
  }
  throw new Error(typeof output?.detail==='string'?output.detail:`Request failed (${res.status})`);
 }
 return output as T;
}
function Badge({value}:{value:string|number|undefined}){
 let text=String(value??'—');const norm=text.toLowerCase();
 const level=['approved','completed','present','resolved','open','hired'].includes(norm)?'success':
 ['rejected','absent','closed'].includes(norm)?'danger':
 ['pending','in progress','requested','under review','screening','interview','applied','enrolled'].includes(norm)?'warning':'neutral';
 return <span className={`badge status-${level}`}><span className="badge-dot"/>{text}</span>;
}
function Avatar({name,color,size}:{name:string;color?:string;size?:string}){
 return <span className={`avatar ${size||''}`} style={{backgroundColor:color||'#5061ad'}}>{nameCaps(name||'SA')}</span>;
}
/** Authenticated, no-store account portrait; never places JWT tokens in image URLs. */
function AccountAvatar({name,color,size}:{name:string;color?:string;size?:string}){
 const [url,setUrl]=useState('');
 useEffect(()=>{
  let current='';let active=true;
  async function loadPhoto(){
   try{
    const token=sessionStorage.getItem('sass_token');
    if(!token){if(active)setUrl('');return}
    const response=await hrmFetch('/api/profile/me/photo',{headers:{Authorization:`Bearer ${token}`}});
    if(!response.ok){if(current){URL.revokeObjectURL(current);current=''}if(active)setUrl('');return}
    const next=URL.createObjectURL(await response.blob());
    if(!active){URL.revokeObjectURL(next);return}
    if(current)URL.revokeObjectURL(current);
    current=next;setUrl(next);
   }catch{if(current){URL.revokeObjectURL(current);current=''}if(active)setUrl('')}
  }
  void loadPhoto();
  window.addEventListener('sass-hrm:profile-photo-changed',loadPhoto);
  window.addEventListener(REFRESH_DATA_EVENT,loadPhoto);
  return ()=>{active=false;window.removeEventListener('sass-hrm:profile-photo-changed',loadPhoto);window.removeEventListener(REFRESH_DATA_EVENT,loadPhoto);if(current)URL.revokeObjectURL(current)};
 },[name]);
 return <span className={`avatar ${size||''}`} style={{backgroundColor:color||'#5061ad',overflow:'hidden'}}>{url?<img src={url} alt="Your profile photo" style={{width:'100%',height:'100%',objectFit:'cover'}}/>:nameCaps(name||'SA')}</span>;
}
function Empty({label='No records yet',icon:Icon=Inbox,description='Records and updates will appear here.'}:{label?:string;icon?:React.ElementType;description?:string}){return <div className="empty"><Icon size={25}/><strong>{label}</strong><span>{description}</span></div>}
// Shared original-demo table styling with reusable operational controls on every HR screen.
// Sorting and paging happen only on already-authorized rows returned by the API.
function Table({rows,cols,actions,emptyLabel,allCount,onClearSearch}:{rows:Rec[];cols:Column[];actions?:(r:Rec)=>React.ReactNode;emptyLabel?:string;allCount?:number;onClearSearch?:()=>void}){
 const [order,setOrder]=useState<{key:string;descending:boolean}|null>(null);
 const [limit,setLimit]=useState(10);
 const [pageIndex,setPageIndex]=useState(0);
 useEffect(()=>setPageIndex(0),[rows,limit,order]);
 const sorted=React.useMemo(()=>{
  if(!order)return rows;
  const normalize=(item:Rec)=>{
   const v=item[order.key];
   if(v===null||v===undefined)return '';
   if(typeof v==='number')return v;
   const str=String(v);
   if(/^\d{4}-\d{2}-\d{2}/.test(str))return str;
   return str.toLocaleLowerCase();
  };
  return [...rows].sort((a,b)=>{
   const aa=normalize(a),bb=normalize(b);
   const diff=typeof aa==='number'&&typeof bb==='number'?aa-bb:String(aa).localeCompare(String(bb),undefined,{numeric:true,sensitivity:'base'});
   return order.descending?-diff:diff;
  });
 },[rows,order]);
 const pageCount=Math.max(1,Math.ceil(sorted.length/limit));
 const current=Math.min(pageIndex,pageCount-1);
 const slice=sorted.slice(current*limit,(current+1)*limit);
 return <div className="sass-table-container">
  {rows.length>0&&<div className="sass-table-controls"><span>{sorted.length} record{sorted.length===1?'':'s'}{typeof allCount==='number'&&allCount>rows.length?` · filtered from ${allCount}`:''}</span><label>Rows per page <select aria-label="Rows per page" value={limit} onChange={e=>setLimit(Number(e.target.value))}><option value={10}>10</option><option value={25}>25</option><option value={50}>50</option></select></label></div>}
  <div className="table-scroll"><table><thead><tr>{cols.map(c=><th key={c.key} aria-sort={order?.key===c.key?(order.descending?'descending':'ascending'):'none'}><button className="sass-column-sort" type="button" title={`Sort by ${c.label}`} onClick={()=>setOrder(old=>old?.key===c.key?{key:c.key,descending:!old.descending}:{key:c.key,descending:false})}>{c.label}<span aria-hidden="true">{order?.key===c.key?(order.descending?' ↓':' ↑'):' ↕'}</span></button></th>)}{actions&&<th>Actions</th>}</tr></thead><tbody>
  {slice.map((r,i)=><tr key={`${r.id??i}-${current*limit+i}`}>{cols.map(c=><td key={c.key}>{c.render?c.render(r):<span>{r[c.key]??'—'}</span>}</td>)}{actions&&<td className="table-actions">{actions(r)}</td>}</tr>)}
  </tbody></table>{!rows.length&&<div><Empty label={allCount&&allCount>0?'No matching records':emptyLabel} description={allCount&&allCount>0?'Try another search term or clear the page filter.':'No organization records are loaded for this section yet.'}/>{allCount&&allCount>0&&onClearSearch&&<button className="sass-clear-search" type="button" onClick={onClearSearch}>Clear search</button>}</div>}</div>
  {pageCount>1&&<div className="sass-table-pagination"><span>Showing {current*limit+1}–{Math.min((current+1)*limit,sorted.length)} of {sorted.length}</span><div><button type="button" disabled={current===0} onClick={()=>setPageIndex(current-1)}>Previous</button><span>Page {current+1} of {pageCount}</span><button type="button" disabled={current>=pageCount-1} onClick={()=>setPageIndex(current+1)}>Next</button></div></div>}
 </div>;
}
function Section({title,subtitle,actions,children,flush=false}:{title:string;subtitle?:string;actions?:React.ReactNode;children:React.ReactNode;flush?:boolean}){
 return <section className={`section-card ${flush?'flush':''}`}><div className="section-heading"><div><h3>{title}</h3>{subtitle&&<p>{subtitle}</p>}</div><div className="section-actions">{actions}</div></div>{children}</section>
}
function Button({children,onClick,variant='primary',disabled=false}:{children:React.ReactNode;onClick?:()=>void;variant?:'primary'|'outline'|'subtle'|'danger';disabled?:boolean}){
 return <button className={`btn ${variant}`} type="button" onClick={onClick} disabled={disabled}>{children}</button>
}
function Header({eyebrow,title,desc,right}:{eyebrow:string;title:string;desc:string;right?:React.ReactNode}){
 return <div className="page-header"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{desc}</p></div>{right&&<div className="header-right">{right}</div>}</div>
}
function Login({onLogin,notice}:{onLogin:(p:Rec)=>void;notice?:string}){
 const [email,setEmail]=useState('');const[password,setPassword]=useState('');
 const [loading,setLoading]=useState(false);const[err,setErr]=useState('');const [showPassword,setShowPassword]=useState(false);
 const [activating,setActivating]=useState(false);const[activationToken,setActivationToken]=useState('');const[newPassword,setNewPassword]=useState('');const[activationResult,setActivationResult]=useState('');
 const [recovering,setRecovering]=useState(false);const[resetEmail,setResetEmail]=useState('');
 const [resetToken,setResetToken]=useState('');const[resetPassword,setResetPassword]=useState('');
 const [resetNotice,setResetNotice]=useState('');const[resetBusy,setResetBusy]=useState(false);
 const [savedAccounts,setSavedAccounts]=useState<string[]>(()=>{try{const result=JSON.parse(localStorage.getItem('sass_known_accounts_v33')||'[]');return Array.isArray(result)?result.filter((v:unknown)=>typeof v==='string'&&v.includes('@')).slice(0,10):[]}catch{return []}});
 const [rememberAccount,setRememberAccount]=useState(false);
 const forgetAccount=(address:string)=>{const next=savedAccounts.filter(x=>x!==address);setSavedAccounts(next);localStorage.setItem('sass_known_accounts_v33',JSON.stringify(next));if(email===address){setEmail('');setPassword('')}};

 async function submit(e:React.FormEvent){e.preventDefault();setLoading(true);setErr('');try{const data=await req<{token:string;user:Rec}>('/auth/login','POST',{email,password});sessionStorage.setItem('sass_token',data.token);if(rememberAccount){const next=[email.trim().toLowerCase(),...savedAccounts.filter(x=>x!==email.trim().toLowerCase())].slice(0,10);setSavedAccounts(next);localStorage.setItem('sass_known_accounts_v33',JSON.stringify(next))}setPassword('');onLogin(data.user)}catch(e){setErr((e as Error).message)}finally{setLoading(false)}}
 return (
  <div className="login-shell">
   <aside className="login-intro" aria-label="About SASS HRM">
    <div className="login-brand"><span className="brand-icon"><Sparkles size={25}/></span><span>SASS <b>HRM</b><small>ENTERPRISE</small></span></div>
    <div className="login-statement">
     <div className="pill inverse"><span className="pulse-dot"/> THE INTELLIGENT PEOPLE PLATFORM</div>
     <h1>People first.<br/><span>Everything connected.</span></h1>
     <p>One beautifully connected workspace for your people, workflows, payroll, and AI-powered employee experience.</p>
     <div className="login-features">
      <span><CheckCircle2 size={17}/> All-in-one HRMS &amp; HRIS</span>
      <span><CheckCircle2 size={17}/> Role-secured workflows</span>
      <span><CheckCircle2 size={17}/> AI-assisted self service</span>
     </div>
    </div>
    <div className="login-end">SASS INNOVATIONS <span>Technology · Transformation · Talent</span></div>
   </aside>
   <main className="login-main">
    <div className="login-panel">
     <div className="mobile-brand"><span className="brand-icon"><Sparkles size={20}/></span><span>SASS <b>HRM</b><small>ENTERPRISE</small></span></div>
     <form className="login-card" onSubmit={submit}>
      <div className="overline">WELCOME BACK</div>
      <h2>Sign in to your workspace</h2>
      {notice&&<p role="status" className="sass-session-message">{notice}</p>}
      <p>Manage your day, your team and your people in one place.</p>
      {savedAccounts.length>0&&<div className="saved-login-accounts"><label htmlFor="sass-account-select">Choose a previously used account</label><div className="saved-account-list"><select id="sass-account-select" value={savedAccounts.includes(email)?email:''} onChange={e=>{setEmail(e.target.value);setPassword('');setErr('')}}><option value="">Use another account</option>{savedAccounts.map(x=><option key={x} value={x}>{x}</option>)}</select>{savedAccounts.includes(email)&&<button type="button" onClick={()=>forgetAccount(email)} title="Forget this email on this device">Remove</button>}</div><small>Only account emails are saved here, never passwords or tokens.</small></div>}
      <label htmlFor="sass-login-email">Sign-in email or work email</label>
      <input id="sass-login-email" name="email" type="email" autoComplete="username" placeholder="you@company.com" value={email} onChange={e=>setEmail(e.target.value)} required/>
      <div className="login-password-heading"><label htmlFor="sass-login-password">Password</label>
       <button className="login-text-action" type="button" aria-controls="sass-login-reset" aria-expanded={recovering} onClick={()=>{setRecovering(v=>!v);setActivating(false)}}>Forgot password?</button>
      </div>
      <div className="login-password-field">
       <input id="sass-login-password" name="password" type={showPassword?'text':'password'} autoComplete="current-password" placeholder="Enter your password" value={password} onChange={e=>setPassword(e.target.value)} required/>
       <button type="button" className="login-password-visibility" onClick={()=>setShowPassword(v=>!v)} aria-label={showPassword?'Hide password':'Show password'} aria-pressed={showPassword} title={showPassword?'Hide password':'Show password'}>{showPassword?<EyeOff size={18}/>:<Eye size={18}/>}</button>
      </div>
      <label className="remember-account"><input type="checkbox" checked={rememberAccount} onChange={e=>setRememberAccount(e.target.checked)}/><span>Remember this account email on this device (not the password)</span></label>
      {err&&<div className="alert error login-error" role="alert">{err}</div>}
      <button className="btn primary login-submit" disabled={loading} type="submit"><span>{loading?'Signing in…':'Sign in to SASS HRM'}</span><ArrowRight size={18}/></button>
     </form>
     <div className="login-secondary">
      <div className="activation-card">
       <button className="activation-toggle" type="button" aria-controls="sass-login-activate" aria-expanded={activating} onClick={()=>{setActivating(v=>!v);setRecovering(false)}}><Fingerprint size={18}/><span>{activating?'Hide employee activation':'Have an invitation token? Activate your account'}</span><ChevronDown size={17} className={activating?'login-rotated':''}/></button>
       {activating&&<form id="sass-login-activate" className="activation-form" onSubmit={async e=>{e.preventDefault();setActivationResult('');try{const result=await req<{message:string}>('/auth/activate','POST',{token:activationToken,new_password:newPassword});setActivationResult(result.message);setActivationToken('');setNewPassword('')}catch(e){setActivationResult((e as Error).message)}}}>
        <label>Invitation token<input value={activationToken} onChange={e=>setActivationToken(e.target.value)} autoComplete="off" required minLength={20}/></label>
        <label>Create password (12+ characters)<input type="password" value={newPassword} onChange={e=>setNewPassword(e.target.value)} autoComplete="new-password" required minLength={12}/></label>
        <button type="submit" className="btn primary">Activate account</button>{activationResult&&<p className="helper-note" role="status">{activationResult}</p>}
       </form>}
      </div>
      {recovering&&<div className="activation-card login-recovery" id="sass-login-reset">
       <div className="login-recovery-heading"><KeyRound size={17}/><strong>Reset your password</strong><button type="button" aria-label="Close password reset" onClick={()=>setRecovering(false)}><X size={17}/></button></div>
       <div className="activation-form">
        <form onSubmit={async e=>{e.preventDefault();setResetBusy(true);setResetNotice('');try{const result=await req<{message:string}>('/auth/password-reset/request','POST',{email:resetEmail});setResetNotice(result.message)}catch(err){setResetNotice((err as Error).message)}finally{setResetBusy(false)}}}>
         <label>Work email<input type="email" required autoComplete="email" value={resetEmail} onChange={e=>setResetEmail(e.target.value)}/></label>
         <button type="submit" className="btn primary" disabled={resetBusy}>Email a one-time reset token</button>
        </form>
        <form onSubmit={async e=>{e.preventDefault();setResetBusy(true);setResetNotice('');try{const result=await req<{message:string}>('/auth/password-reset/confirm','POST',{token:resetToken,new_password:resetPassword});setResetNotice(result.message);setResetToken('');setResetPassword('')}catch(err){setResetNotice((err as Error).message)}finally{setResetBusy(false)}}}>
         <label>Reset token from email<input required minLength={24} autoComplete="off" value={resetToken} onChange={e=>setResetToken(e.target.value)}/></label>
         <label>New password (12+ characters, letters and numbers)<input required type="password" minLength={12} autoComplete="new-password" value={resetPassword} onChange={e=>setResetPassword(e.target.value)}/></label>
         <button type="submit" className="btn primary" disabled={resetBusy}>Save new password</button>
        </form>
        {resetNotice&&<p className="helper-note" role="status">{resetNotice}</p>}
       </div>
      </div>}
     </div>
    </div>
    <div className="login-disclaimer"><LockKeyhole size={14}/> Authorized SASS personnel only</div>
   </main>
  </div>
 );
}
function DialogBox({dialog,close,submit,busy}:{dialog:Dialog;close:()=>void;submit:(body:Rec)=>Promise<void>;busy:boolean}){
 const initial:Rec={};for(const f of dialog.fields)initial[f.key]=dialog.fixed?.[f.key]??f.value??'';
 const [form,setForm]=useState<Rec>(initial);
 const [error,setError]=useState('');
 const firstField=useRef<HTMLInputElement|HTMLTextAreaElement|HTMLSelectElement|null>(null);
 useEffect(()=>{
  firstField.current?.focus();
  const esc=(e:KeyboardEvent)=>{if(e.key==='Escape'&&!busy)close()};
  document.addEventListener('keydown',esc);
  return ()=>document.removeEventListener('keydown',esc);
 },[close,busy]);
 const save=async(e:React.FormEvent)=>{
  e.preventDefault();setError('');
  for(const f of dialog.fields){
   const val=String(form[f.key]??'');
   if(f.required!==false&&!val.trim()){setError(`${f.label} is required.`);return;}
   if(f.type==='number'&&val.trim()){
    const n=Number(val);
    if(!Number.isFinite(n)||f.min!==undefined&&n<Number(f.min)||f.max!==undefined&&n>Number(f.max)){setError(`Enter a valid value for ${f.label}.`);return;}
   }
  }
  if(('confirm_password' in form) && String(form.confirm_password||'')!==String(form.initial_password||form.new_password||'')){
   setError('The two passwords must match.');return;
  }
  const start=form.start_date??form.start_day,end=form.end_date??form.end_day;
  if(start&&end&&String(start)>String(end)){setError('End date must not be before start date.');return;}
  const body:Rec={...dialog.fixed};for(const f of dialog.fields){const val=form[f.key];body[f.key]=f.type==='number'&&String(val??'').trim()!==''?Number(val):val;}
  delete body.confirm_password;
  await submit(body);
 };
 return <div className="modal-overlay" onMouseDown={e=>{if(e.currentTarget===e.target&&!busy)close()}}><div className="modal-box" role="dialog" aria-modal="true" aria-labelledby="sass-dialog-title"><div className="modal-header"><div><span className="eyebrow">SASS HRM / WORKFLOW</span><h2 id="sass-dialog-title">{dialog.title}</h2>{dialog.description&&<p>{dialog.description}</p>}</div><button onClick={close} disabled={busy} className="icon-button" aria-label="Close form"><X size={19}/></button></div><form onSubmit={save}>{error&&<p role="alert" className="sass-form-error">{error}</p>}<div className="form-content">{dialog.fields.map((f,i)=><label className={`field ${f.type==='textarea'?'wide':''}`} key={f.key}>{f.label}{f.type==='textarea'?<textarea ref={i===0?firstField as React.Ref<HTMLTextAreaElement>:undefined} rows={3} value={form[f.key]??''} onChange={e=>setForm(x=>({...x,[f.key]:e.target.value}))} required={f.required!==false}/>:f.type==='select'?<select ref={i===0?firstField as React.Ref<HTMLSelectElement>:undefined} value={form[f.key]??''} required={f.required!==false} onChange={e=>setForm(x=>({...x,[f.key]:e.target.value}))}><option value="">Select option</option>{(f.options||[]).map(a=><option key={typeof a==='string'?a:a.value} value={typeof a==='string'?a:a.value}>{typeof a==='string'?a:a.label}</option>)}</select>:<input ref={i===0?firstField as React.Ref<HTMLInputElement>:undefined} value={form[f.key]??''} type={f.type||'text'} autoComplete={f.type==='password'?'new-password':undefined} min={f.min} max={f.max} step={f.type==='number'?'any':undefined} required={f.required!==false} onChange={e=>setForm(x=>({...x,[f.key]:e.target.value}))}/>}</label>)}</div><div className="modal-footer"><Button onClick={close} variant="outline" disabled={busy}>Cancel</Button><button disabled={busy} className="btn primary" type="submit">{busy?'Saving…':dialog.title.startsWith('Acknowledge:')?'I have read this policy — Acknowledge':'Save changes'} <ArrowRight size={15}/></button></div></form></div></div>;
}
function AI({user}:{user:Rec}){
 const [messages,setMessages]=useState<{who:'ai'|'me';text:string;mode?:string}[]>([{who:'ai',text:`Hi ${user.name?.split(' ')[0]}! I'm SASS AI, your HR assistant. I can help with your leave balance, attendance, HR policies and workspace navigation. What would you like to know?`}]);
 const [draft,setDraft]=useState('');const[busy,setBusy]=useState(false);
 const questions=['How many leave days do I have?','What are my assigned tasks?','Show my benefits','Show my logged hours','What are my skills?','Who is my manager?','What recognition have I received?','What is my work arrangement request status?','What is my attendance correction status?','How many files are in my file vault?','Which policies need my acknowledgement?','Explain the remote work policy','Show my career plan','What is my service request status?','How do I submit an Employee Voice concern?'];
 const send=async(q?:string)=>{const msg=(q||draft).trim();if(!msg||busy)return;setMessages(a=>[...a,{who:'me',text:msg}]);setDraft('');setBusy(true);try{const data=await req<{answer:string;mode:string}>('/ai/chat','POST',{message:msg});setMessages(a=>[...a,{who:'ai',text:data.answer,mode:data.mode}])}catch(e){setMessages(a=>[...a,{who:'ai',text:(e as Error).message}])}finally{setBusy(false)}};
 return <><Header eyebrow="SASS INTELLIGENCE" title="SASS AI Assistant" desc="Your privacy-aware HR copilot, grounded in approved policies and your authorized data." right={<span className="status-online"><span/> HR data lookup available</span>}/><AICapabilities/><div className="ai-grid"><section className="section-card chat-workspace"><div className="chat-top"><span className="ai-symbol"><Sparkles size={24}/></span><div><strong>SASS AI Copilot</strong><small>Role-aware · Read-only · Authorized HR context</small></div><button type="button" className="btn subtle" onClick={()=>setMessages([])}>Clear conversation</button></div><div className="chat-messages" aria-live="polite">{messages.map((m,i)=><div className={`bubble-row ${m.who}`} key={i}>{m.who==='ai'&&<span className="mini-ai"><Sparkles size={17}/></span>}<div className={`bubble ${m.who}`}>{m.text}{m.mode&&<small className="ai-source">{m.mode==='llm'?'AI-generated answer · Verify with HR':'Based on your authorized HR data'}</small>}</div></div>)}{busy&&<div className="bubble-row ai"><span className="mini-ai"><Sparkles size={17}/></span><div className="bubble ai">Thinking…</div></div>}</div><form className="chat-compose" onSubmit={e=>{e.preventDefault();send()}}><input aria-label="Ask SASS AI" placeholder="Ask SASS AI about your HR workspace..." value={draft} onChange={e=>setDraft(e.target.value)} maxLength={1000}/><button disabled={!draft.trim()||busy} type="submit"><Send size={17}/></button></form></section><aside className="ai-side"><section className="section-card pad"><div className="eyebrow">GET STARTED</div><h3>Suggested questions</h3><p className="muted">Try a question to see how SASS AI can help.</p><div className="question-list">{questions.map(q=><button key={q} onClick={()=>send(q)}>{q}<ArrowUpRight size={15}/></button>)}</div></section><section className="ai-privacy"><ShieldCheck size={23}/><strong>Designed for responsible HR AI</strong><p>Chat is read-only. Sensitive employee records are permission restricted. This assistant doesn't approve requests, change salaries or make hiring decisions.</p></section></aside></div></>
}
function DeveloperConsole(){
 const [status,setStatus]=useState<Rec|null>(null);
 const [error,setError]=useState('');
 const [loading,setLoading]=useState(false);
 const reload=async()=>{setLoading(true);setError('');try{setStatus(await req<Rec>('/developer/status'))}catch(e){setError((e as Error).message)}finally{setLoading(false)}};
 useEffect(()=>{void reload()},[]);
 useRefreshData(reload);
 return <><Header eyebrow="SYSTEM / RESTRICTED" title="Developer console" desc="Read-only system status and setup checks. No employee details, passwords or JWT secrets are exposed." />
 {error&&<div className="data-error-banner" role="alert">{error}</div>}
 {status&&status.app_version!=='4.5.0'&&<div className="data-error-banner" role="alert"><CircleHelp size={20}/><span>This browser expects SASS HRM API v4.5.0, but the connected server reports {status.app_version}. Restart the current Docker stack before changing HR data. Do not reset MySQL volumes.</span></div>}
 <Section title="System status" subtitle="Diagnostic results from the connected API">
  {status?<><div className="metric-line"><div><span>API</span><b>{status.api_status}</b></div><div><span>Database</span><b>{status.database_status}</b></div><div><span>Engine</span><b>{status.database_engine}</b></div><div><span>Tables</span><b>{status.schema_table_count}</b></div></div><p className="muted">Backend {status.app_version} · Checked {fmt(status.checked_at)} · {status.checked_at?.slice(11,19)} UTC</p></>:<p className="muted">{loading?'Checking API and database status…':'Unable to load diagnostics'}</p>}
 </Section>
 {status?.checks&&<Section title="Configuration readiness" subtitle="These checks inspect configuration and record presence—not production security or SMTP delivery"><div className="v27-checks">{status.checks.map((check:Rec)=><div key={check.key} className="v27-check-row"><span className={check.ready?'v27-check-pass':'v27-check-attention'}>{check.ready?<CheckCircle2 size={18}/>:<CircleHelp size={18}/>}</span><div><strong>{check.label}</strong><small>{check.hint}</small></div><Badge value={check.ready?'Configured':'Action needed'}/></div>)}</div><p className="helper-note">SMTP must be tested separately with a real invitation. JWT configuration is never displayed. Only authorized administrators may use this console.</p></Section>}
 <div className="privacy-banner"><ShieldCheck size={20}/> Developer diagnostics are read-only. Use Company setup, Organization settings and Account administration for approved changes.</div>
 </>;
}

function App(){
 const [user,setUser]=useState<Rec|null>(null);const [checking,setChecking]=useState(true);
 const [page,setPage]=useState(()=>pageFromPath(window.location.pathname)||'dashboard');const[mobileMenu,setMobileMenu]=useState(false);
 const [routeError,setRouteError]=useState<{kind:'not-found'|'forbidden';path:string;label:string}|null>(null);
 const [data,setData]=useState<Record<string,Rec[]>>({});const [privateProfile,setPrivateProfile]=useState<Rec>({});const[report,setReport]=useState<Rec|null>(null);
 const [dialog,setDialog]=useState<Dialog|null>(null);const[busy,setBusy]=useState(false);
 const [surveyView,setSurveyView]=useState<Rec|null>(null);

 const [selectedTicket,setSelectedTicket]=useState<Rec|null>(null);const [ticketThread,setTicketThread]=useState<Rec[]>([]);
 const[toast,setToast]=useState<{type:'success'|'error';text:string}|null>(null);const[search,setSearch]=useState('');
 const[notificationsOpen,setNotificationsOpen]=useState(false);const [loadingData,setLoadingData]=useState(false);const [navFilter,setNavFilter]=useState('');
 const [loadFailures,setLoadFailures]=useState<string[]>([]);
 const [lastSync,setLastSync]=useState<string>('');
 const [connectionIssue,setConnectionIssue]=useState(false);
 const [sessionNotice,setSessionNotice]=useState('');
 const [collapsedGroups,setCollapsedGroups]=useState<Record<string,boolean>>({});
 const [workspaceOpen,setWorkspaceOpen]=useState(false);
 const [organizationName,setOrganizationName]=useState('SASS Innovations');
 const isHR=user?.role==='admin';const management=!!user&&user.role!=='employee';
 const reloadOrganization=useCallback(async()=>{
  if(!user)return;
  try{const profile=await req<{name:string}>('/organization/identity');setOrganizationName(profile?.name||'SASS Innovations')}catch{setOrganizationName('SASS Innovations')}
 },[user]);
 useEffect(()=>{void reloadOrganization()},[reloadOrganization]);
 const logout=useCallback(()=>{setWorkspaceOpen(false);setOrganizationName('SASS Innovations');sessionStorage.removeItem('sass_token');setUser(null);setData({});setPrivateProfile({});setLoadFailures([]);setReport(null);setSelectedTicket(null);setTicketThread([]);setPage('dashboard');setRouteError(null);window.history.replaceState(null,'','/sign-in')},[]);
 const signOut=useCallback(async()=>{try{await req('/auth/logout','POST')}catch{}finally{logout()}},[logout]);
 useEffect(()=>{
   const expired=()=>{logout();setSessionNotice('Your session expired or was revoked. Sign in again to continue securely.');};
   const lost=()=>setConnectionIssue(true);
   const restored=()=>setConnectionIssue(false);
   const offline=()=>setConnectionIssue(true);
   const online=()=>{setConnectionIssue(false);};
   window.addEventListener(HRM_SESSION_EXPIRED,expired);
   window.addEventListener(HRM_CONNECTION_LOST,lost);
   window.addEventListener(HRM_CONNECTION_RESTORED,restored);
   window.addEventListener('offline',offline);
   window.addEventListener('online',online);
   return ()=>{window.removeEventListener(HRM_SESSION_EXPIRED,expired);window.removeEventListener(HRM_CONNECTION_LOST,lost);window.removeEventListener(HRM_CONNECTION_RESTORED,restored);window.removeEventListener('offline',offline);window.removeEventListener('online',online)};
 },[logout]);
 useEffect(()=>{if(!sessionStorage.getItem('sass_token')){setChecking(false);return;}req<Rec>('/auth/me').then(setUser).catch(logout).finally(()=>setChecking(false))},[logout]);
 const refresh=useCallback(async()=>{
  if(!user)return;
  setLoadingData(true);
  const entry=Object.entries(entities).filter(([k])=>{
    if(['candidates','jobs','reports','approvals','interviews','trends'].includes(k))return user.role!=='employee';
    if(['audit','accounts','policyComplianceSummary'].includes(k))return user.role==='admin';return true;
  });
  const values=await Promise.allSettled(entry.map(([_,url])=>req(url)));
  const next:Record<string,Rec[]>={};const failed:string[]=[];entry.forEach(([key],i)=>{
   const item=values[i];if(item.status==='fulfilled'){
    if(key==='reports')setReport(item.value as Rec);else if(key==='privateProfile')setPrivateProfile(item.value as Rec);else next[key]=Array.isArray(item.value)?item.value as Rec[]:[];
   } else failed.push(key);
  });setLoadFailures(failed);setData(previous=>({...previous,...next}));if(failed.length<entry.length)setLastSync(new Date().toLocaleTimeString());setLoadingData(false);
 },[user]);
 useEffect(()=>{refresh()},[refresh]);
 const rowsFor=(key:string)=>data[key]||[];
 const scoped=(arr:Rec[])=>!search?arr:arr.filter(r=>Object.values(r).some(v=>String(v??'').toLowerCase().includes(search.toLowerCase())));
 const notify=(text:string,type:'success'|'error'='success')=>setToast({type,text});
 const action=async(path:string,method='POST',body?:unknown,success='Changes saved successfully')=>{
  setBusy(true);try{await req(path,method,body);notify(success);setDialog(null);if(path==='/auth/change-password'||path===`/admin/accounts/${user?.id}/profile`){logout();return;}await refresh();if(selectedTicket&&path===`/helpdesk/tickets/${selectedTicket.id}/messages`){setTicketThread(await req<Rec[]>(`/helpdesk/tickets/${selectedTicket.id}/messages`))}}catch(e){notify((e as Error).message,'error')}finally{setBusy(false)}
 };
 const open=(title:string,path:string,fields:Field[],description='',method='POST',fixed?:Rec)=>setDialog({title,path,fields,description,method,fixed});
 const askUpdate=(path:string,key:string,value:string|number,msg='Updated successfully')=>action(path,'PATCH',{[key]:value},msg);
 const col=(key:string,label?:string,render?:Column['render']):Column=>({key,label:label||titleCase(key),render});
 const nameCol=col('name','Name',r=><div className="table-person"><Avatar name={r.name} color={r.avatar_color}/><div><strong>{r.name}</strong><small>{r.code||r.email||r.designation||''}</small></div></div>);
 const employeeOptions=rowsFor('employees').map(e=>({label:`${e.name} (${e.code})`,value:String(e.id)}));
 const interviewTime=()=>{const t=new Date(Date.now()+86400000);return new Date(t.getTime()-t.getTimezoneOffset()*60000).toISOString().slice(0,16)};
 const employeeField:Field={key:'employee_id',label:'Employee',type:'select',options:employeeOptions};
 const canOpenPage=useCallback((key:string)=>{
  const entry=menus.find(m=>m.key===key);
  if(!entry||!user||!PAGE_ROUTES[key])return false;
  if(entry.only==='admin'&&user.role!=='admin')return false;
  if(entry.only==='management'&&user.role==='employee')return false;
  if(key==='developer'&&!user.developer_access)return false;
  return true;
 },[user]);
 const applyPage=(key:string)=>{
  setRouteError(null);setPage(key);setSearch('');setNavFilter('');setMobileMenu(false);
  setDialog(null);setSelectedTicket(null);setNotificationsOpen(false);setWorkspaceOpen(false);
  window.scrollTo(0,0);
 };
 // All module buttons and cards navigate through the same address-bar router.
 const setActive=(key:string)=>{
  if(!canOpenPage(key)){notify('You do not have permission to open this feature.','error');return;}
  const href=pageUrl(key);
  if(window.location.pathname!==href)window.history.pushState({sassPage:key},'',href);
  applyPage(key);
 };
 // Refresh, direct links, browser Back/Forward and new tabs resolve the same URL.
 useEffect(()=>{
  if(!user)return;
  const syncRoute=()=>{
    const requested=pageFromPath(window.location.pathname);
    if(!requested && window.location.pathname!=='/sign-in'){
      // Do not silently show Overview at an invalid deep link.
      setRouteError({kind:'not-found',path:window.location.pathname,label:'Unknown feature'});
      setPage('__unavailable__');setMobileMenu(false);setDialog(null);
      return;
    }
    if(requested && !canOpenPage(requested)){
      // Frontend only provides an explanation; the API remains the authority.
      setRouteError({kind:'forbidden',path:window.location.pathname,label:menus.find(m=>m.key===requested)?.label||'Restricted feature'});
      setPage('__unavailable__');setMobileMenu(false);setDialog(null);
      return;
    }
    const safe=requested||'dashboard';
    if(window.location.pathname!==pageUrl(safe))window.history.replaceState({sassPage:safe},'',pageUrl(safe));
    applyPage(safe);
  };
  syncRoute();
  window.addEventListener('popstate',syncRoute);
  return()=>window.removeEventListener('popstate',syncRoute);
 },[user,canOpenPage]);
 // Ctrl+K opens role-scoped record search from any feature page.
 useEffect(()=>{
  if(!user)return;
  const onSearch=(event:KeyboardEvent)=>{
   if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){
    event.preventDefault();setActive('globalsearch');
   }
  };
  window.addEventListener('keydown',onSearch);
  return ()=>window.removeEventListener('keydown',onSearch);
 },[user,canOpenPage]);
 // Document title distinguishes each feature even when browser tabs are duplicated.
 useEffect(()=>{
  document.title=`${page==='__unavailable__'?'Page unavailable':menus.find(m=>m.key===page)?.label||'Overview'} | SASS HRM Enterprise`;
 },[page]);
 const readable=menus.filter(m=>m.only!=='admin'||isHR).filter(m=>m.only!=='management'||management).filter(m=>m.key!=='developer'||!!user?.developer_access);
 const title=page==='__unavailable__'?'Page unavailable':menus.find(m=>m.key===page)?.label||'Overview';
 const stats=report?.stats||{};
 const todayAttend=rowsFor('attendance').filter(x=>x.day===today());
 const totalPeople=rowsFor('employees').length;
 const pendingLeaves=rowsFor('leave').filter(x=>x.status==='Pending');
 const unread=rowsFor('notifications').filter(x=>!x.is_read).length;
 const person=user||{};
 function boxTable(key:string,cols:Column[],actions?:(r:Rec)=>React.ReactNode,empty?:string){return <Table rows={scoped(rowsFor(key))} cols={cols} actions={actions} emptyLabel={empty} allCount={rowsFor(key).length} onClearSearch={()=>setSearch('')}/>}
 async function downloadProtectedCSV(path:string,filename:string){
  try{
   const token=sessionStorage.getItem('sass_token');
   if(!token)throw Error('Sign in to download your records');
   const response=await hrmFetch(API+path,{headers:{Authorization:`Bearer ${token}`},cache:'no-store'});
   if(!response.ok){let detail='Export failed';try{const error=await response.json();if(typeof error.detail==='string')detail=error.detail}catch{}throw Error(detail)}
   const blob=await response.blob();const url=URL.createObjectURL(blob);
   try{const link=document.createElement('a');link.href=url;link.download=filename;link.click()}
   finally{window.setTimeout(()=>URL.revokeObjectURL(url),1000)}
   notify('CSV export downloaded');
  }catch(e){notify((e as Error).message,'error')}
 }
 function exportCSV(){const token=sessionStorage.getItem('sass_token');hrmFetch(API+'/reports/departments.csv',{headers:token?{Authorization:`Bearer ${token}`}:{}}).then(async response=>{if(!response.ok)throw Error('Export failed');return response.blob()}).then(blob=>{const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='sass-department-summary.csv';a.click();URL.revokeObjectURL(url)}).catch(e=>notify((e as Error).message,'error'))}
 const exportMyRecords=async()=>{
  try{const data=await req<Rec>('/privacy/export-me');const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});
   const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`sass-my-hr-records-${person.code}.json`;a.click();URL.revokeObjectURL(url);notify('Personal records exported locally');}
  catch(e){notify((e as Error).message,'error')}
 };
 const makeManagedAccount=()=>open('Create sign-in account','/admin/accounts/create',[
  {key:'name',label:'Full name'},{key:'email',label:'Sign-in email',type:'email'},
  {key:'work_email',label:'Work email (optional; defaults to sign-in email)',type:'email',required:false},
  {key:'designation',label:'Designation'},{key:'department',label:'Department'},
  {key:'location',label:'Office location'},
  {key:'work_mode',label:'Work mode',type:'select',options:['Remote','Hybrid','On-site'],value:'Hybrid'},
  {key:'role',label:'Access role',type:'select',options:[{value:'employee',label:'Employee — personal HR'}, {value:'hr_subadmin',label:'HR Sub-Admin — team workflows, no full HR administration'}, {value:'manager',label:'Manager — team approvals'}, {value:'admin',label:'HR Administrator — HR administration'}, {value:'developer_admin',label:'Developer Administrator — administrator + restricted diagnostics'}],value:'employee'},
  {key:'initial_password',label:'Set initial password (12+ characters, letters and numbers)',type:'password'},
  {key:'confirm_password',label:'Confirm initial password',type:'password'}
 ],'Only existing administrators may create accounts. New users can sign in immediately with the initial password. Share it privately and ask them to change it. Passwords are hashed and cannot be viewed later.');
 const editManagedAccount=(employee:Rec)=>open(`Edit account: ${employee.name}`,`/admin/accounts/${employee.id}/profile`,[
  {key:'name',label:'Full name',value:employee.name},
  {key:'email',label:'Sign-in email',type:'email',value:employee.email},
  {key:'work_email',label:'Work email',type:'email',value:employee.work_email||employee.email},
  {key:'designation',label:'Designation',value:employee.designation},
  {key:'department',label:'Department',value:employee.department},
  {key:'location',label:'Office location',value:employee.location},
  {key:'work_mode',label:'Work mode',type:'select',options:['Remote','Hybrid','On-site'],value:employee.work_mode||'Hybrid'}
 ],`Database ID ${employee.id} / Staff code ${employee.code}. Identity changes are audited. Sign-in or work email changes sign out this account's earlier sessions. No password is ever revealed.`, 'PATCH');
 const updateAccountRole=(employee:Rec)=>open(`Change role: ${employee.name}`,`/admin/accounts/${employee.id}/role`,[
  {key:'role',label:'New access role',type:'select',options:[{value:'employee',label:'Employee'}, {value:'hr_subadmin',label:'HR Sub-Admin — limited team permissions'}, {value:'manager',label:'Manager'}, {value:'admin',label:'HR Administrator'}, {value:'developer_admin',label:'Developer Administrator'}],value:employee.access_tier||employee.role}
 ],'Changing a role will revoke all existing JWT sessions.','PATCH');
 const setAccountPassword=(employee:Rec)=>open(`Set password: ${employee.name}`,`/admin/accounts/${employee.id}/set-password`,[
   {key:'new_password',label:'New password (12+ characters, letters and numbers)',type:'password'},
   {key:'confirm_password',label:'Confirm new password',type:'password'}
 ],'This securely changes the account password, activates the account and revokes all previous sessions. Only use for authorized password recovery.');
 const revokeAccountSessions=(employee:Rec)=>{if(window.confirm(`Sign out all sessions for ${employee.name}?`))action(`/admin/accounts/${employee.id}/revoke-sessions`,'POST',{},'All previous sessions revoked')};
 const setDeveloperGrant=(employee:Rec)=>{const enabled=!Boolean(employee.developer_access);if(window.confirm(`${enabled?'Enable':'Disable'} read-only developer diagnostics for ${employee.name}?`))action(`/admin/accounts/${employee.id}/developer`,'PATCH',{enabled},'Developer access updated; sessions revoked')};
 const createInvite=async(employee:Rec)=>{
  if(!window.confirm(`Send a one-time activation email to ${employee.email}?`))return;
  try{const result=await req<{message:string}>('/admin/invitations','POST',{employee_id:employee.id});notify(result.message);await refresh()}
  catch(e){notify((e as Error).message,'error')}
 };
 const showTicket=async(ticket:Rec)=>{
  try{setSelectedTicket(ticket);setTicketThread(await req<Rec[]>(`/helpdesk/tickets/${ticket.id}/messages`))}
  catch(e){notify((e as Error).message,'error')}
 };
 const refreshCurrentPage=async()=>{
  // Shared tables and current module records stay in sync without discarding forms.
  await refresh();
  window.dispatchEvent(new Event(REFRESH_DATA_EVENT));
  if(selectedTicket)await showTicket(selectedTicket);
 };
 const ticketReply=()=>{if(selectedTicket)open('Reply to support request',`/helpdesk/tickets/${selectedTicket.id}/messages`,[{key:'message',label:'Message',type:'textarea'}],`Conversation for ticket #${selectedTicket.id}`)};
 const makeEmployee=()=>open('Add employee','/employees',[
  {key:'name',label:'Full name'}, {key:'email',label:'Work email',type:'email'},
  {key:'designation',label:'Designation'},{key:'department',label:'Department',type:'select',options:rowsFor('departments').map(x=>x.name)},
  {key:'location',label:'Office location'},{key:'work_mode',label:'Working arrangement',type:'select',options:['On-site','Hybrid','Remote'],value:'Hybrid'},
  {key:'role',label:'Access role',type:'select',options:['employee','manager'],value:'employee'}
 ],'New accounts require separate secure credential provisioning.');
 const makeLeave=()=>open('Apply for leave','/leave',[
  {key:'leave_type',label:'Leave category',type:'select',options:rowsFor('entitlements').map(e=>e.leave_type)},
  {key:'start_date',label:'Start date',type:'date',value:today()},{key:'end_date',label:'End date',type:'date',value:today()},
  {key:'reason',label:'Reason',type:'textarea'}
 ],'Your manager or HR can review the submitted request.');
 const makeTicket=()=>open('Create HR support ticket','/helpdesk/tickets',[
  {key:'subject',label:'Subject'}, {key:'category',label:'Category',type:'select',options:['General','IT Support','Payroll','Facilities','Leave','Other'],value:'General'},
  {key:'priority',label:'Priority',type:'select',options:['Low','Normal','High'],value:'Normal'},{key:'description',label:'Describe your request',type:'textarea'}
 ]);
 const makeExpense=()=>open('Submit expense claim','/expenses',[
  {key:'title',label:'Expense description'}, {key:'amount',label:'Amount (INR)',type:'number',min:1},
  {key:'category',label:'Category',type:'select',options:['Travel','Connectivity','Meals','Equipment','Other'],value:'Other'}
 ],'Approval records do not initiate bank reimbursements.');
 const makeGoal=()=>open('Add performance goal','/performance/goals',[
  {key:'employee_id',label:'Employee ID',type:'select',options:management?employeeOptions:[{value:String(person.id),label:person.name}],value:String(person.id)},
  {key:'title',label:'Goal title'},{key:'due_date',label:'Target date',type:'date',value:nextMonth()},
  {key:'description',label:'Success criteria',type:'textarea'}
 ],'Goal owners and reporting managers can track progress.');
 if(checking)return <div className="loading-screen"><span className="spinner"/> Loading your workspace…</div>;
 if(!user)return <Login notice={sessionNotice} onLogin={u=>{setSessionNotice('');setConnectionIssue(false);setUser(u)}}/>;
 return <div className="shell">
 <aside className={`sidebar ${mobileMenu?'visible':''}`}>
  <div className="brand"><div className="brand-icon"><Sparkles size={22}/></div><div className="brand-words">SASS <b>HRM</b><small>ENTERPRISE</small></div></div>
  <div className="workspace-selector"><button type="button" className="workspace workspace-button" aria-expanded={workspaceOpen} aria-controls="sass-workspace-menu" onClick={()=>setWorkspaceOpen(open=>!open)}><div className="workspace-mark">S</div><div><strong>{organizationName}</strong><small>Organization workspace</small></div><ChevronDown size={14} className={`workspace-chevron ${workspaceOpen?'open':''}`}/></button>
  {workspaceOpen&&<nav id="sass-workspace-menu" className="workspace-menu" aria-label="Organization workspace menu"><div className="workspace-menu-label">Workspace</div><button type="button" onClick={()=>setActive('organization')}><Building2 size={16}/> View organization</button>{isHR&&<><button type="button" onClick={()=>setActive('orgsettings')}><Settings2 size={16}/> Set up the SASS organization</button><button type="button" onClick={()=>setActive('accounts')}><UserCog size={16}/> Account administration</button><button type="button" onClick={()=>setActive('companysetup')}><UploadCloud size={16}/> HRIS import & readiness</button></>}</nav>}</div>
  <div className="sidebar-scroll"><div className="sidebar-nav-search"><Search size={16}/><input aria-label="Find HR modules" placeholder="Find a module..." value={navFilter} onChange={e=>setNavFilter(e.target.value)}/>{navFilter&&<button aria-label="Clear module search" onClick={()=>setNavFilter('')}><X size={13}/></button>}</div>{menuGroups.map(group=>{
   const matches=readable.filter(m=>group.keys.includes(m.key)&&m.label.toLowerCase().includes(navFilter.trim().toLowerCase()));
   return matches.length?<div className="nav-group" key={group.title}><button type="button" className="menu-label nav-group-toggle" aria-expanded={!!navFilter||!collapsedGroups[group.title]} onClick={()=>setCollapsedGroups(old=>({...old,[group.title]:!old[group.title]}))}><span>{group.title}</span><ChevronDown size={13} className={collapsedGroups[group.title]&&!navFilter?'rotated':''}/></button>{(!collapsedGroups[group.title]||!!navFilter)&&<nav className="nav-list" aria-label={group.title}>{matches.map(m=><a href={pageUrl(m.key)} title={m.label} aria-current={page===m.key?'page':undefined} className={page===m.key?'active':''} key={m.key} onClick={e=>{if(e.button!==0||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;e.preventDefault();setActive(m.key)}}><m.icon size={18}/><span>{m.label}</span>{m.key==='leave'&&pendingLeaves.length>0&&management&&<small className="nav-count">{pendingLeaves.length}</small>}</a>)}</nav>}</div>:null;
  })}
  <div className="menu-label second">AI & PREFERENCES</div><nav className="nav-list"><a href={pageUrl('assistant')} className={`ai-nav ${page==='assistant'?'active':''}`} onClick={e=>{if(e.button!==0||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;e.preventDefault();setActive('assistant')}}><Sparkles size={18}/> <span>AI Assistant</span><span className="new-pill">AI</span></a><a href={pageUrl('settings')} className={page==='settings'?'active':''} onClick={e=>{if(e.button!==0||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;e.preventDefault();setActive('settings')}}><Settings2 size={18}/><span>Settings</span></a></nav></div>
  <div className="side-bottom"><div className="sidebar-ai"><div className="sidebar-ai-icon"><Bot size={19}/></div><strong>Need HR guidance?</strong><p>Your SASS AI copilot is available around the clock.</p><button onClick={()=>setActive('assistant')}>Ask SASS AI <ArrowRight size={15}/></button></div><div className="side-profile"><AccountAvatar name={person.name} color={person.avatar_color}/><div><strong>{person.name}</strong><small>{person.role==='admin'?'HR Administrator':titleCase(person.role)}</small></div><button aria-label="Sign out" title="Sign out" onClick={signOut}><LogOut size={17}/></button></div></div>
 </aside>
 {mobileMenu&&<button aria-label="Close navigation" className="mobile-backdrop" onClick={()=>setMobileMenu(false)}/>}
 <div className="main-area"><header className="topbar"><div className="breadcrumb"><button className="mobile-toggle" aria-label="Open menu" onClick={()=>setMobileMenu(true)}><Menu size={21}/></button><a href={pageUrl('dashboard')} className="sass-breadcrumb-link" onClick={e=>{if(e.button!==0||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;e.preventDefault();setActive('dashboard')}}>Workspace</a><ChevronRight size={15}/><strong>{title}</strong></div><div className="top-actions"><button type="button" className="sass-search-top-link" title="Find HR records" onClick={()=>setActive('globalsearch')}><Search size={16}/><span>Find records</span></button><button type="button" className="sass-refresh-workspace" aria-label="Refresh data" aria-busy={loadingData} title="Refresh data for this page and the workspace" onClick={()=>void refreshCurrentPage()} disabled={loadingData}><Activity size={16}/><span>Refresh data</span></button><span className="top-date"><CalendarDays size={16}/>{new Date().toLocaleDateString('en-IN',{month:'short',day:'numeric',year:'numeric'})}</span><div className="notifications-wrap"><button className="icon-button notification-button" aria-label="Notifications" onClick={()=>setNotificationsOpen(v=>!v)}><Bell size={19}/>{unread>0&&<span className="notification-indicator"/>}</button>{notificationsOpen&&<div className="notification-popover"><h3>Notifications</h3><button type="button" onClick={()=>setActive('inbox')}><span><strong>Open notification inbox →</strong><small>Manage all, unread and archived alerts</small></span></button>{rowsFor('notifications').length?rowsFor('notifications').map(n=><button key={n.id} onClick={()=>action(`/notifications/${n.id}/read`,'PATCH',undefined,'Notification marked read')}><span className={`notification-dot ${n.is_read?'read':''}`}/><span><strong>{n.title}</strong><small>{n.body}</small></span></button>):<p>You're all caught up.</p>}</div>}</div><div className="top-divider"/><button type="button" className="profile-top-button" title="Open my profile" aria-label="Open my profile" onClick={()=>setActive('profile')}><AccountAvatar name={person.name} color={person.avatar_color}/></button></div></header>
 <main className="content"><div className="page-content">
 {connectionIssue&&<div className="data-error-banner sass-connectivity-warning" role="alert"><CircleHelp size={18}/><span>Cannot reach the API reliably. Saved records may be out of date. Verify Docker and MySQL are running; use the single Refresh data button when the connection returns. Do not re-submit a form until its previous result is confirmed.</span></div>}
 {lastSync&&<div className="sass-sync-note" role="status">Workspace last checked at {lastSync}{loadFailures.length>0?' · Some sources need attention':''}</div>}
 {loadFailures.length>0&&<div className="data-error-banner" role="alert"><CircleHelp size={18}/><span>{loadFailures.length} workspace data source(s) could not load: {loadFailures.slice(0,4).join(', ')}. Some tables may be incomplete. Use Refresh data above to retry.</span></div>}
 {toast&&<div className={`toast ${toast.type}`} role="status">{toast.type==='success'?<CheckCircle2 size={17}/>:<CircleHelp size={17}/>}<span>{toast.text}</span><button onClick={()=>setToast(null)} aria-label="Dismiss"><X size={15}/></button></div>}
 {page==='__unavailable__'&&routeError&&<section className="sass-route-panel" role="alert"><ShieldCheck size={30}/><div><span className="eyebrow">{routeError.kind==='forbidden'?'ACCESS RESTRICTED':'PAGE NOT FOUND'}</span><h1>{routeError.kind==='forbidden'?'You cannot open this page':'This feature URL does not exist'}</h1><p>{routeError.kind==='forbidden'?`${routeError.label} is not available to your account. Ask your HR administrator if access is required.`:'Check the address or choose an existing module from the sidebar.'}</p><code>{routeError.path}</code><div className="button-pair"><Button onClick={()=>setActive('dashboard')}>Open Overview</Button><Button variant="outline" onClick={()=>setActive('settings')}>My settings</Button></div></div></section>}
 {page!=='__unavailable__'&&page!=='dashboard'&&page!=='assistant'&&page!=='settings'&&!['profile','profilemgmt','workcenter','inbox','workflowsettings','selfservice','globalsearch','dataquality','coverage','tasktemplates','career','voice','discipline','requestdesk','calendar','developer','companysetup','orgsettings','readiness'].includes(page)&&<div className="global-search"><Search size={17}/><input placeholder={`Search ${title.toLowerCase()}...`} value={search} onChange={e=>setSearch(e.target.value)}/>{loadingData&&<span className="tiny-spinner"/>}</div>}
 {page==='dashboard'&&<>
 {isHR&&<SetupProgress navigate={setActive}/>}
 <div className="welcome-banner"><div><span className="eyebrow">YOUR INTELLIGENT HR WORKSPACE</span><h1>Good {new Date().getHours()<12?'morning':new Date().getHours()<17?'afternoon':'evening'}, {person.name?.split(' ')[0]} <span>✦</span></h1><p>Here’s what’s happening {isHR?'across your organization':management?'with your team':'in your workspace'} today. Stay connected, stay productive.</p><div className="hero-buttons"><Button onClick={()=>setActive('assistant')}><Sparkles size={17}/> Ask SASS AI <ArrowRight size={15}/></Button><Button onClick={()=>setActive('leave')} variant="outline"><CalendarDays size={16}/> Manage leave</Button></div></div><div className="hero-orb orb1"/><div className="hero-orb orb2"/><div className="hero-decoration"><span>✳</span><span>✳</span></div></div>
 <section className="sass-pillars" aria-label="HRM solution areas">
 {[
  {title:'People Management',desc:'Employee HRIS, people analytics and HR administration',page:'employees',Icon:UsersRound},
  {title:'Talent Management',desc:'Recruitment, onboarding and service requests',page:'requestdesk',Icon:BriefcaseBusiness},
  {title:'Compensation',desc:'Leave, attendance, rosters and pay',page:'leave',Icon:WalletCards},
  {title:'Culture',desc:'Career growth, employee voice and fair process',page:'career',Icon:HeartHandshake}
 ].map(item=><button key={item.title} className="sass-pillar" onClick={()=>setActive(item.page)}><span className="sass-pillar-symbol"><item.Icon size={21}/></span><span><b>{item.title}</b><small>{item.desc}</small></span><ArrowRight size={18}/></button>)}
 </section>
 <div className="kpi-grid">{[
  {label:management?'Team / workforce':'My profile',value:management?isHR?totalPeople:stats.employees||1:'Active',icon:UsersRound,delta:'People overview',kind:'violet'},
  {label:'Present today',value:todayAttend.filter(x=>x.status==='Present').length,icon:Clock3,delta:'Attendance recorded',kind:'mint'},
  {label:'Pending leave',value:pendingLeaves.length,icon:CalendarDays,delta:'Awaiting approval',kind:'peach'},
  {label:management?'Active candidates':'My learning',value:management?rowsFor('candidates').length:rowsFor('enrollments').filter(e=>e.status!=='Completed').length,icon:management?BriefcaseBusiness:GraduationCap,delta:management?'Hiring pipeline':'Active enrollments',kind:'blue'},
 ].map((k,i)=><div className="kpi" key={k.label}><div className="kpi-label">{k.label}<span className={`kpi-icon ${k.kind}`}><k.icon size={20}/></span></div><div className="kpi-value">{k.value}</div><div className="kpi-footer"><span className="kpi-trend"><ArrowUpRight size={14}/> CURRENT</span> {k.delta}</div><div className="kpi-index">0{i+1}</div></div>)}</div>
 <div className="dashboard-grid"><Section title="Announcements" subtitle="Updates from your people team" actions={<span className="section-tag">SASS NEWS</span>}><div className="news-list">{rowsFor('announcements').slice(0,3).map(a=><div className="news-item" key={a.id}><span className="news-icon"><Megaphone size={18}/></span><div><strong>{a.title}</strong><p>{a.body}</p><small>{fmt(a.created_at)}</small></div></div>)}{rowsFor('announcements').length===0&&<div className="v27-empty-dashboard"><Megaphone size={24}/><strong>No announcements published yet</strong><p>Approved organization updates will appear here.</p>{isHR&&<Button variant="outline" onClick={()=>setActive('organization')}>Publish an announcement</Button>}</div>}</div></Section>
 <Section title="Quick actions" subtitle="Jump back into your everyday work"><div className="quick-actions">{[
  {label:'Apply for leave',desc:'Plan your time off',icon:CalendarCheck2,run:makeLeave},
  {label:'Check attendance',desc:'Your attendance history',icon:Clock3,run:()=>setActive('attendance')},
  {label:'HR support',desc:'Open a request',icon:MessageCircle,run:makeTicket},
  {label:'Learning hub',desc:'Explore new skills',icon:GraduationCap,run:()=>setActive('training')}
 ].map(a=><button key={a.label} className="quick-action" onClick={a.run}><span><a.icon size={19}/></span><div><strong>{a.label}</strong><small>{a.desc}</small></div><ArrowUpRight size={17}/></button>)}</div></Section></div>
 <div className="dashboard-grid bottom"><Section title="Upcoming holidays" subtitle="Plan around the next important dates" actions={<Button variant="subtle" onClick={()=>setActive('organization')}>View calendar <ArrowRight size={15}/></Button>}><div className="holidays-preview">{rowsFor('holidays').slice(0,3).map(h=><div key={h.id} className="holiday-row"><span className="holiday-day"><b>{h.day.slice(8,10)}</b><small>{new Date(h.day+'T12:00:00').toLocaleDateString('en-IN',{month:'short'})}</small></span><span><strong>{h.name}</strong><small>{h.location} locations</small></span><CalendarDays size={18}/></div>)}{rowsFor('holidays').length===0&&<div className="v27-empty-dashboard"><CalendarDays size={24}/><strong>No published holidays</strong><p>Organization holidays will show here once HR adds them.</p><Button variant="outline" onClick={()=>setActive(isHR?'organization':'calendar')}>{isHR?'Manage holidays':'Open my calendar'}</Button></div>}</div></Section><Section title="Your activity" subtitle="Recent requests and progress"><div className="activity-list">{rowsFor('leave').slice(0,2).map(r=><div className="activity-item" key={r.id}><span className="activity-icon"><CalendarDays size={17}/></span><div><strong>{r.employee_name} · {r.leave_type}</strong><small>{fmt(r.start_date)} – {fmt(r.end_date)}</small></div><Badge value={r.status}/></div>)}{rowsFor('tickets').slice(0,2).map(r=><div className="activity-item" key={`t${r.id}`}><span className="activity-icon"><MessageCircle size={17}/></span><div><strong>{r.subject}</strong><small>HR Helpdesk</small></div><Badge value={r.status}/></div>)}{rowsFor('leave').length===0&&rowsFor('tickets').length===0&&<Empty/>}</div></Section></div>
 </>}
 {page==='employees'&&<><Header eyebrow="CORE HR / PERSONNEL INFORMATION" title="Employee directory" desc="A unified view of your workforce, reporting lines and work arrangements." right={isHR&&<div className="button-pair"><Button variant="outline" onClick={()=>setActive('companysetup')}><UploadCloud size={16}/> Import staff CSV</Button><Button onClick={makeEmployee}><Plus size={16}/> Add employee</Button></div>}/><div className="metric-line"><div><span>People</span><b>{totalPeople}</b></div><div><span>Departments</span><b>{new Set(rowsFor('employees').map(r=>r.department)).size}</b></div><div><span>Locations</span><b>{new Set(rowsFor('employees').map(r=>r.location)).size}</b></div><div><span>Remote employees</span><b>{rowsFor('employees').filter(r=>r.work_mode==='Remote').length}</b></div></div><Section title="All employees" subtitle="Work contact data only · Payroll information is separate">{boxTable('employees',[nameCol,col('designation'),col('department'),col('location'),col('work_mode','Work mode',r=><Badge value={r.work_mode}/>),col('join_date','Joined',r=>fmt(r.join_date))],isHR?r=><Button variant="subtle" onClick={()=>open('Update '+r.name,`/employees/${r.id}`,[{key:'designation',label:'Designation',value:r.designation},{key:'department',label:'Department',value:r.department},{key:'location',label:'Location',value:r.location},{key:'work_mode',label:'Work mode',type:'select',options:['Remote','Hybrid','On-site'],value:r.work_mode},{key:'manager_id',label:'Reporting manager',type:'select',options:employeeOptions.filter(x=>x.value!==String(r.id)),value:r.manager_id??''}],'Update job and working information.','PATCH')}>Edit</Button>:undefined)}</Section>{isHR&&<Section title="Account access" subtitle="Send one-time activation emails or suspend and restore employee access.">{boxTable('accounts',[col('name','Employee',r=><strong>{r.name}</strong>),col('email','Work email'),col('role','Role'),col('account_active','Account',r=><Badge value={r.account_active?'Active':r.session_version===0?'Pending activation':'Suspended'}/>)],r=><div className="button-pair"><Button variant="subtle" disabled={!r.account_active&&r.session_version>0} onClick={()=>createInvite(r)}><UserRoundPlus size={15}/> Invite</Button><Button variant="outline" disabled={r.id===person.id} onClick={()=>action(`/admin/accounts/${r.id}`,'PATCH',{active:!r.account_active},r.account_active?'Account suspended':'Account reactivated')}>{r.account_active?'Suspend':'Reactivate'}</Button></div>)}</Section>}</>}
 {page==='corrections'&&<AttendanceCorrections role={person.role} employeeId={person.id} onChanged={refresh}/>}
 {page==='vault'&&<DocumentVault role={person.role} employeeId={person.id} employees={rowsFor('employees')}/>}
 {page==='selfservice'&&<SelfServiceHub navigate={setActive}/>}
 {page==='reminders'&&<WorkflowReminders isHR={isHR} navigate={setActive}/>}
 {page==='coverage'&&<LeaveCoveragePlanner isHR={isHR}/>}
 {page==='tasktemplates'&&management&&<HRTaskTemplates isHR={isHR} userId={Number(person.id)} employees={rowsFor('employees').map(e=>({id:Number(e.id),name:String(e.name),department:String(e.department||''),manager_id:e.manager_id?Number(e.manager_id):undefined,account_active:e.account_active}))}/>} 
 {(['workcenter','inbox','workflowsettings'] as const).includes(page as any)&&<WorkspaceControl key={page} mode={page as 'workcenter'|'inbox'|'workflowsettings'} isHR={isHR} navigate={setActive}/>}
 {(['growthplans','feedbackrequests'] as const).includes(page as any)&&<PerformanceGrowth page={page as 'growthplans'|'feedbackrequests'} userId={Number(person.id)} role={String(person.role)} employees={rowsFor('employees').map(e=>({id:Number(e.id),name:String(e.name),manager_id:e.manager_id?Number(e.manager_id):undefined,account_active:e.account_active}))} navigate={setActive}/>}
 {(['evidence','goaljournal'] as const).includes(page as any)&&<PerformanceJournal page={page as 'evidence'|'goaljournal'} userId={Number(person.id)} role={String(person.role)} navigate={setActive}/>}
 {(['followups','reviewprogress'] as const).includes(page as any)&&<PerformanceFollowups page={page as 'followups'|'reviewprogress'} userId={Number(person.id)} role={String(person.role)} employees={rowsFor('employees').map(e=>({id:Number(e.id),name:String(e.name),manager_id:e.manager_id?Number(e.manager_id):undefined,account_active:e.account_active}))} navigate={setActive}/>}
 {(['performancecycles','appraisals','checkins'] as const).includes(page as any)&&<PerformanceSuite page={page as 'performancecycles'|'appraisals'|'checkins'} userId={Number(person.id)} role={String(person.role)} employees={rowsFor('employees').map(e=>({id:Number(e.id),name:String(e.name),manager_id:e.manager_id?Number(e.manager_id):undefined,account_active:e.account_active}))} navigate={setActive}/>}
 {page==='profile'&&<MyProfile navigate={setActive} onSaved={async()=>{setUser(await req<Rec>('/auth/me'))}}/>}
 {page==='profilemgmt'&&isHR&&<ProfileManagement navigate={setActive}/>}
 {page==='compensationsettings'&&isHR&&<CompensationSettings isHR={isHR}/>}
 {page==='orgsettings'&&isHR&&<OrganizationSettings navigate={setActive} onOrganizationSaved={()=>void reloadOrganization()}/>}
 {page==='companysetup'&&isHR&&<AdminSetupCenter navigate={setActive} onChanged={refresh}/>}
 {page==='developer'&&user?.developer_access&&<DeveloperConsole/>}
 {page==='readiness'&&isHR&&<ReadinessCenter navigate={setActive}/>}
 {page==='attendance' &&<><Header eyebrow="TIME / WORKFORCE" title="Time & attendance" desc="Your real-time attendance, check-in and check-out history." right={<div className="button-pair"><Button variant="outline" onClick={()=>downloadProtectedCSV('/attendance/export-me.csv','sass-my-attendance.csv')}><Download size={16}/> Download my attendance CSV</Button><Button variant="outline" disabled={busy} onClick={()=>action('/attendance/check-out','POST',undefined,'Checked out successfully')}><ArrowDownRight size={16}/> Check out</Button><Button disabled={busy} onClick={()=>action('/attendance/check-in','POST',undefined,'Checked in successfully')}><ArrowDownLeft size={16}/> Check in</Button></div>}/><Section title="Attendance records" subtitle="Today's check-ins and recent time logs">{boxTable('attendance',[col('employee_name','Employee',r=><strong>{r.employee_name}</strong>),col('day','Date',r=>fmt(r.day)),col('check_in','Check-in'),col('check_out','Check-out'),col('status','Status',r=><Badge value={r.status}/>),])}</Section></>}
 {page==='shifts'&&<><Header eyebrow="WORKFORCE SCHEDULING" title="Shifts & schedules" desc="View your assigned shifts, their timing and the upcoming work roster." right={<div className="button-pair">{isHR&&<Button variant="outline" onClick={()=>open('Create shift template','/shifts',[{key:'name',label:'Shift name'},{key:'start_time',label:'Start time (HH:MM)',value:'09:30'},{key:'end_time',label:'End time (HH:MM)',value:'18:30'},{key:'location',label:'Work location',value:'Office'}])}><Plus size={15}/> Shift template</Button>}{management&&<Button onClick={()=>open('Assign work shift','/schedule',[employeeField,{key:'shift_id',label:'Shift',type:'select',options:rowsFor('shifts').map(r=>({value:String(r.id),label:`${r.name} (${r.start_time}–${r.end_time})`}))},{key:'work_day',label:'Work date',type:'date',value:nextMonth()}])}><Plus size={16}/> Assign shift</Button>}</div>}/><Section title="Shift templates" subtitle="Standardized work-time configurations">{boxTable('shifts',[col('name','Shift',r=><strong>{r.name}</strong>),col('start_time','Start'),col('end_time','End'),col('location','Workplace')])}</Section><Section title="Scheduled work" subtitle="Upcoming shift allocations, scoped to your team or profile">{boxTable('schedule',[col('employee_name','Employee',r=><strong>{r.employee_name}</strong>),col('work_day','Work date',r=>fmt(r.work_day)),col('shift_name','Shift'),col('start_time','Start'),col('end_time','End'),col('location')])}</Section></>}
 {page==='leave'&&<><Header eyebrow="TIME OFF / APPROVAL WORKFLOWS" title="Leave management" desc="Request time off, review balances and track manager approvals." right={<Button onClick={makeLeave}><Plus size={16}/> Request leave</Button>}/><div className="metric-line">{rowsFor('balances').map(b=><div key={b.type}><span>{b.type} remaining*</span><b>{b.remaining} <small>days</small></b></div>)}<div><span>Requests pending</span><b>{pendingLeaves.length}</b></div></div><p className="helper-note">*Balances use HR-configured annual allowances; accrual and carryover may require separate verification.</p><Section title="Leave requests" subtitle="Status, dates, employee and approvals">{boxTable('leave',[col('employee_name','Employee',r=><strong>{r.employee_name}</strong>),col('leave_type','Type'),col('start_date','From',r=>fmt(r.start_date)),col('end_date','To',r=>fmt(r.end_date)),col('days','Days'),col('status','Status',r=><Badge value={r.status}/>)],r=>r.status==='Pending'&&r.employee_id===person.id?<Button variant="outline" onClick={()=>action(`/leave/${r.id}/cancel`,'POST',undefined,'Leave request cancelled')}>Cancel request</Button>:management&&r.status==='Pending'&&r.employee_id!==person.id&&(isHR||rowsFor('employees').some(e=>e.id===r.employee_id&&e.manager_id===person.id))?<div className="button-pair"><Button variant="subtle" onClick={()=>action(`/leave/${r.id}/decision`,'POST',{decision:'Approved'},'Leave approved')}><Check size={15}/> Approve</Button><Button variant="danger" onClick={()=>action(`/leave/${r.id}/decision`,'POST',{decision:'Rejected'},'Leave rejected')}>Reject</Button></div>:null)}</Section>{isHR&&<Section title="Organization leave entitlements" subtitle="Configured annual leave allocations (HR-managed)." actions={<Button variant="subtle" onClick={()=>open('Add leave category','/leave/entitlements',[{key:'leave_type',label:'Leave category name'},{key:'days',label:'Annual allowance (days)',type:'number',min:0,max:365}])}><Plus size={15}/> Add leave type</Button>}>{boxTable('entitlements',[col('leave_type','Leave category'),col('days','Annual allocation',r=>`${r.days} days`),col('updated_at','Changed',r=>fmt(r.updated_at))],r=><Button variant="outline" onClick={()=>open('Set '+r.leave_type+' allowance',`/leave/entitlements/${encodeURIComponent(r.leave_type)}`,[{key:'days',label:'Days per year',type:'number',value:r.days,min:0,max:365}],'Changes should follow your approved HR leave policy.','PATCH')}>Configure</Button>)}</Section>}</>}
 {page==='recruitment' &&management&&<><Header eyebrow="TALENT / APPLICANT TRACKING" title="Recruitment ATS" desc="Manage open positions and progress applicants through your hiring pipeline." right={<Button onClick={()=>open('Add candidate','/candidates',[{key:'name',label:'Candidate name'},{key:'job_title',label:'Role applied for'},{key:'source',label:'Candidate source',type:'select',options:['Careers Portal','LinkedIn','Referral','Naukri','Other'],value:'Careers Portal'}])}><Plus size={16}/> Add candidate</Button>}/><div className="metric-line"><div><span>Total candidates</span><b>{rowsFor('candidates').length}</b></div><div><span>Open positions</span><b>{rowsFor('jobs').filter(x=>x.status==='Open').length}</b></div><div><span>At interview stage</span><b>{rowsFor('candidates').filter(x=>x.stage==='Interview').length}</b></div><div><span>Offers</span><b>{rowsFor('candidates').filter(x=>x.stage==='Offer').length}</b></div></div><Section title="Job openings" subtitle="Vacancies and requisitions" actions={isHR&&<Button variant="outline" onClick={()=>open('Publish vacancy','/recruitment/jobs',[{key:'title',label:'Position title'},{key:'department',label:'Department'},{key:'location',label:'Location'},{key:'employment_type',label:'Employment type',type:'select',options:['Full-time','Part-time','Internship','Contract'],value:'Full-time'},{key:'openings',label:'Openings',type:'number',value:1}])}><Plus size={15}/> Add vacancy</Button>}>{boxTable('jobs',[col('title','Job title',r=><strong>{r.title}</strong>),col('department'),col('location'),col('employment_type','Employment'),col('openings'),col('status','Status',r=><Badge value={r.status}/>)],isHR?r=><select className="inline-select" value={r.status} onChange={e=>askUpdate(`/recruitment/jobs/${r.id}`,'status',e.target.value)}>{['Open','Paused','Closed'].map(x=><option key={x}>{x}</option>)}</select>:undefined)}</Section><Section title="Candidate pipeline" subtitle="Status changes are tracked in the audit trail">{boxTable('candidates',[col('name','Candidate',r=><strong>{r.name}</strong>),col('job_title','Position'),col('source'),col('applied_at','Applied',r=>fmt(r.applied_at)),col('stage','Stage',r=><Badge value={r.stage}/>)],r=><select className="inline-select" value={r.stage} onChange={e=>askUpdate(`/candidates/${r.id}/stage`,'stage',e.target.value,'Candidate stage updated')}>{['Applied','Screening','Assessment','Interview','Offer','Hired','Rejected'].map(x=><option key={x}>{x}</option>)}</select>)}</Section></>}
 {page==='onboarding'&&<><Header eyebrow="EMPLOYEE LIFECYCLE" title="Onboarding hub" desc="Track joining tasks, handbook acknowledgments, and first-week readiness." right={isHR&&<Button onClick={()=>open('Assign onboarding task','/onboarding',[employeeField,{key:'title',label:'Task description'},{key:'due_date',label:'Due date',type:'date',value:nextMonth()}])}><Plus size={16}/> Assign task</Button>}/><div className="metric-line"><div><span>Assigned tasks</span><b>{rowsFor('onboarding').length}</b></div><div><span>Completed</span><b>{rowsFor('onboarding').filter(r=>r.status==='Completed').length}</b></div><div><span>Pending</span><b>{rowsFor('onboarding').filter(r=>r.status==='Pending').length}</b></div></div><Section title="Joining checklist" subtitle="Track actions and complete your own assigned items">{boxTable('onboarding',[col('employee_name','Employee',r=><strong>{r.employee_name}</strong>),col('title','Task'),col('due_date','Due date',r=>fmt(r.due_date)),col('status','Status',r=><Badge value={r.status}/>)],r=>isHR||r.employee_id===person.id?<Button variant="subtle" onClick={()=>askUpdate(`/onboarding/${r.id}`,'status',r.status==='Completed'?'Pending':'Completed')}>{r.status==='Completed'?'Reopen':'Mark done'}</Button>:null)}</Section></>}
 {page==='payrollengine'&&<PayrollWorkbench isHR={isHR}/>}
 {page==='payroll'&&<><Header eyebrow="PAYROLL / RECORDS" title="Payslip archive" desc="Historic payroll records in your authorized view. New pay-run statements are managed in Payroll workbench." right={<Button variant="outline" onClick={()=>setActive('payrollengine')}><WalletCards size={16}/> Open payroll workbench</Button>}/><div className="privacy-panel"><ShieldCheck size={20}/><div><strong>Confidential pay information</strong><p>Employees only see their own historical records. Only authorized HR administrators can view organization-wide records. Manual payslip creation has been retired.</p></div></div><Section title="Historical payslips" subtitle="Existing legacy records; no sample data is preloaded">{boxTable('payroll',[col('employee_name','Employee'),col('month','Pay period'),col('gross','Gross pay',r=>currency(Number(r.gross))),col('deductions','Deductions',r=>currency(Number(r.deductions))),col('net','Net pay',r=>currency(Number(r.net)))])}</Section></>}
 {page==='taxcalculator'&&<TaxCalculator/>}
 {page==='performance'&&<><Header eyebrow="PEOPLE DEVELOPMENT" title="Performance & goals" desc="Track objectives, continuous progress and manager feedback." right={<div className="button-pair"><Button variant="outline" onClick={()=>setActive('appraisals')}><ClipboardList size={16}/> Appraisal center</Button><Button onClick={makeGoal}><Plus size={16}/> Add goal</Button></div>}/><div className="metric-line"><div><span>Tracked goals</span><b>{rowsFor('goals').length}</b></div><div><span>Goals completed</span><b>{rowsFor('goals').filter(x=>x.progress===100).length}</b></div><div><span>Performance reviews</span><b>{rowsFor('reviews').length}</b></div></div><Section title="Performance goals" subtitle="Update goal progress when milestones are reached">{boxTable('goals',[col('employee_name','Employee',r=><strong>{r.employee_name}</strong>),col('title','Goal'),col('due_date','Due date',r=>fmt(r.due_date)),col('progress','Progress',r=><div className="progress-cell"><div className="progress-bar"><span style={{width:`${r.progress}%`}}/></div><small>{r.progress}%</small></div>),col('status','Status',r=><Badge value={r.status}/>)],r=><select className="inline-select" value={r.progress} onChange={e=>askUpdate(`/performance/goals/${r.id}`,'progress',Number(e.target.value))}>{[0,25,50,75,100,r.progress].filter((v,i,a)=>a.indexOf(v)===i).sort((a,b)=>a-b).map(v=><option key={v} value={v}>{v}%</option>)}</select>)}</Section><Section title="Performance reviews" subtitle="Manager-authored feedback" actions={management&&<Button variant="outline" onClick={()=>open('New performance review','/performance/reviews',[{...employeeField,options:employeeOptions.filter(o=>Number(o.value)!==person.id)},{key:'cycle',label:'Review cycle'},{key:'rating',label:'Rating (1–5)',type:'number',min:1,max:5,value:4},{key:'feedback',label:'Written feedback',type:'textarea'}])}><Plus size={15}/> Add review</Button>}>{boxTable('reviews',[col('employee_name','Employee',r=><strong>{r.employee_name}</strong>),col('cycle','Cycle'),col('rating','Rating',r=><span className="rating">★ {r.rating}/5</span>),col('feedback','Feedback'),col('reviewer_name','Reviewer')])}</Section></>}
 {page==='training'&&<><Header eyebrow="TALENT / SKILLS" title="Learning & development" desc="Discover training programs, enroll in courses and track skill development." right={isHR&&<Button onClick={()=>open('Create training course','/training/courses',[{key:'title',label:'Course title'},{key:'category',label:'Category'},{key:'duration_hours',label:'Duration (hours)',type:'number',min:1},{key:'description',label:'Description',type:'textarea'}])}><Plus size={16}/> New course</Button>}/><div className="course-grid">{scoped(rowsFor('courses')).map((r,i)=>{const enrolled=rowsFor('enrollments').find(e=>e.course_id===r.id&&e.employee_id===person.id);return <div className="course-card" key={r.id}><div className={`course-top course-${i%4}`}><span><BookOpen size={19}/></span><span>{r.category}</span></div><h3>{r.title}</h3><p>{r.description}</p><div className="course-bottom"><span><Clock3 size={15}/>{r.duration_hours} hours</span>{enrolled?<Badge value={enrolled.status}/>:<Button variant="outline" onClick={()=>action('/training/enrollments','POST',{course_id:r.id},'Course enrolled')}>Enroll <ArrowRight size={14}/></Button>}</div></div>})}</div><Section title="My and team enrollments" subtitle="Track courses through enrollment and completion">{boxTable('enrollments',[col('employee_name','Employee',r=><strong>{r.employee_name}</strong>),col('course_title','Course'),col('status','Progress',r=><Badge value={r.status}/>),col('enrolled_at','Enrolled',r=>fmt(r.enrolled_at))],r=>r.employee_id===person.id||isHR?<select className="inline-select" value={r.status} onChange={e=>askUpdate(`/training/enrollments/${r.id}`,'status',e.target.value)}>{['Enrolled','In Progress','Completed'].map(x=><option key={x}>{x}</option>)}</select>:null)}</Section></>}
 {page==='helpdesk'&&<><Header eyebrow="EMPLOYEE EXPERIENCE" title="HR helpdesk" desc="Raise an HR, payroll, IT or workplace request and follow it to resolution." right={<Button onClick={makeTicket}><Plus size={16}/> New ticket</Button>}/><div className="metric-line"><div><span>Total tickets</span><b>{rowsFor('tickets').length}</b></div><div><span>Open</span><b>{rowsFor('tickets').filter(x=>x.status==='Open').length}</b></div><div><span>In progress</span><b>{rowsFor('tickets').filter(x=>x.status==='In Progress').length}</b></div><div><span>Resolved</span><b>{rowsFor('tickets').filter(x=>x.status==='Resolved').length}</b></div></div><Section title="Support requests" subtitle="HR administrators can triage and resolve cases">{boxTable('tickets',[col('subject','Ticket',r=><div><strong>{r.subject}</strong><small className="cell-sub">{r.employee_name}</small></div>),col('category'),col('priority','Priority',r=><Badge value={r.priority}/>),col('status','Status',r=><Badge value={r.status}/>),col('created_at','Opened',r=>fmt(r.created_at))],r=><div className="button-pair"><Button variant="outline" onClick={()=>showTicket(r)}><MessagesSquare size={15}/> Conversation</Button>{isHR&&<select className="inline-select" value={r.status} onChange={e=>askUpdate(`/helpdesk/tickets/${r.id}`,'status',e.target.value)}>{['Open','In Progress','Resolved','Closed'].map(x=><option key={x}>{x}</option>)}</select>}</div>)}</Section>{selectedTicket&&<Section title={`Conversation · ${selectedTicket.subject}`} subtitle="Ticket messages are visible to the owner and HR only" actions={<div className="button-pair"><Button variant="outline" onClick={()=>setSelectedTicket(null)}>Close</Button><Button onClick={ticketReply}><Plus size={15}/> Reply</Button></div>}><div className="thread-list">{ticketThread.length?ticketThread.map(m=><div className="thread-item" key={m.id}><strong>{m.author_name}</strong><small>{fmt(m.created_at)}</small><p>{m.message}</p></div>):<Empty label="No replies yet"/>}</div></Section>}</>}
 {page==='expenses'&&<><Header eyebrow="FINANCE / SELF SERVICE" title="Expenses & claims" desc="Submit reimbursable expenses and see each approval decision." right={<Button onClick={makeExpense}><Plus size={16}/> Submit claim</Button>}/><div className="metric-line"><div><span>Submitted claims</span><b>{rowsFor('expenses').length}</b></div><div><span>Pending review</span><b>{rowsFor('expenses').filter(x=>x.status==='Pending').length}</b></div><div><span>Approved total</span><b>{currency(rowsFor('expenses').filter(x=>x.status==='Approved').reduce((a,b)=>a+b.amount,0))}</b></div></div><Section title="Expense register" subtitle="HR reviews require an explanation in the Compensation Operations panel below; payments are not processed">{boxTable('expenses',[col('employee_name','Employee',r=><strong>{r.employee_name}</strong>),col('title','Description'),col('category'),col('amount','Amount',r=>currency(r.amount)),col('status','Status',r=><Badge value={r.status}/>),col('created_at','Submitted',r=>fmt(r.created_at))],undefined)}</Section></>}
 {page==='assets'&&<><Header eyebrow="OPERATIONS / RESOURCE TRACKING" title="Asset management" desc="Maintain an auditable inventory of equipment assigned to employees." right={isHR&&<Button onClick={()=>open('Assign equipment','/assets',[employeeField,{key:'asset_name',label:'Asset description'},{key:'serial_number',label:'Serial / asset code'}])}><Plus size={16}/> Assign asset</Button>}/><Section title="Assigned assets" subtitle="IT asset register; no tracking or monitoring software is installed">{boxTable('assets',[col('asset_name','Asset',r=><div className="asset-name"><Laptop2 size={19}/><strong>{r.asset_name}</strong></div>),col('serial_number','Asset ID'),col('employee_name','Assigned to'),col('assigned_at','Assigned',r=>fmt(r.assigned_at)),col('status','Status',r=><Badge value={r.status}/>)])}</Section></>}
 {page==='documents'&&<><Header eyebrow="HRIS / FILE REGISTER" title="Employee documents" desc="Track contracts and compliance document metadata. Secure file uploads remain disabled pending a compliance review." right={isHR&&<Button onClick={()=>open('Register document','/documents',[employeeField,{key:'title',label:'Document title'},{key:'document_type',label:'Document type',type:'select',options:['Contract','HR Form','Compliance','Certificate','Other'],value:'HR Form'}],'This workflow registers document metadata only, and does not store actual files.')}><Plus size={16}/> Register document</Button>}/><div className="privacy-panel"><ShieldCheck size={20}/><div><strong>Employee document metadata</strong><p>This page tracks document metadata. Secure file uploads are disabled pending encrypted storage, malware scanning, and retention controls.</p></div></div><Section title="Document register" subtitle="Records visible only to their owner and HR administrators">{boxTable('documents',[col('title','Document',r=><div className="asset-name"><FileText size={19}/><strong>{r.title}</strong></div>),col('document_type','Type'),col('employee_name','Employee'),col('created_at','Created',r=>fmt(r.created_at)),col('status','Status',r=><Badge value={r.status}/>)])}</Section></>}
 {page==='offboarding'&&<><Header eyebrow="EMPLOYEE LIFECYCLE" title="Offboarding" desc="Request an exit and follow the HR review and clearance process." right={<Button onClick={()=>open('Request offboarding','/offboarding',[{key:'last_working_day',label:'Proposed final working day',type:'date',value:nextMonth()},{key:'reason',label:'Reason for request',type:'textarea'}],'This request does not automatically terminate employment.')}><Plus size={16}/> New request</Button>}/><Section title="Exit requests" subtitle="HR-led approval workflow with tracked outcomes">{boxTable('offboarding',[col('employee_name','Employee',r=><strong>{r.employee_name}</strong>),col('last_working_day','Last working day',r=>fmt(r.last_working_day)),col('reason'),col('status','Status',r=><Badge value={r.status}/>),col('created_at','Requested',r=>fmt(r.created_at))],isHR?r=><select className="inline-select" value={r.status} onChange={e=>askUpdate(`/offboarding/${r.id}`,'status',e.target.value)}>{['Requested','Under Review','Approved','Closed'].map(x=><option key={x}>{x}</option>)}</select>:undefined)}</Section></>}
 {page==='organization'&&<><Header eyebrow="COMPANY / ADMINISTRATION" title="Our organization" desc="Discover departments, upcoming holidays and company-wide announcements."/>{isHR&&rowsFor('departments').length===0&&<div className="privacy-panel"><Building2 size={22}/><div><strong>Build your actual department structure</strong><p>Create your business units using Add below, then visit Company setup & import to onboard employees. This workspace intentionally contains no demo departments.</p><Button variant="outline" onClick={()=>setActive('companysetup')}>Company setup</Button></div></div>}<div className="dashboard-grid"><Section title="Departments" subtitle="Business units and primary locations" actions={isHR&&<Button variant="subtle" onClick={()=>open('Create department','/organization/departments',[{key:'name',label:'Department name'},{key:'location',label:'Primary location'}])}><Plus size={15}/> Add</Button>}><div className="dept-list">{rowsFor('departments').filter(r=>!search||r.name.toLowerCase().includes(search.toLowerCase())).map(r=><div key={r.id}><span className="dept-icon"><UsersRound size={17}/></span><div><strong>{r.name}</strong><small>{r.location}</small></div><span className="dept-count">{rowsFor('employees').filter(e=>e.department===r.name).length} people</span></div>)}{rowsFor('departments').length===0&&<div className="v27-empty-dashboard"><Building2 size={22}/><strong>No departments yet</strong><p>Set up the first business unit to organize staff.</p>{isHR&&<Button variant="outline" onClick={()=>setActive('orgsettings')}>Organization settings</Button>}</div>}</div></Section><Section title="Upcoming holidays" subtitle="Shared HR calendar" actions={isHR&&<Button variant="subtle" onClick={()=>open('Add holiday','/organization/holidays',[{key:'name',label:'Holiday name'},{key:'day',label:'Date',type:'date',value:nextMonth()},{key:'location',label:'Location',value:'All'}])}><Plus size={15}/> Add</Button>}><div className="holidays-preview">{rowsFor('holidays').map(h=><div className="holiday-row" key={h.id}><span className="holiday-day"><b>{h.day.slice(8,10)}</b><small>{new Date(h.day+'T12:00:00').toLocaleDateString('en-IN',{month:'short'})}</small></span><span><strong>{h.name}</strong><small>{h.location}</small></span><CalendarDays size={17}/></div>)}</div></Section></div><Section title="Company announcements" subtitle="Important HR notices and internal updates" actions={isHR&&<Button variant="outline" onClick={()=>open('Post announcement','/organization/announcements',[{key:'title',label:'Announcement title'},{key:'body',label:'Announcement text',type:'textarea'}])}><Plus size={16}/> Publish</Button>}><div className="announcements-full">{scoped(rowsFor('announcements')).map(n=><div className="announcement-item" key={n.id}><span><Megaphone size={19}/></span><div><strong>{n.title}</strong><p>{n.body}</p><small>By {n.author_name} · {fmt(n.created_at)}</small></div></div>)}</div></Section></>}
 {page==='policies'&&<><Header eyebrow="KNOWLEDGE / EMPLOYEE SELF SERVICE" title="HR policies & handbook" desc="Understand your organization's guidelines with searchable policy information." right={<div className="button-pair"><Button variant="outline" onClick={()=>setActive('assistant')}><Sparkles size={16}/> Ask SASS AI</Button>{isHR&&<Button onClick={()=>open('Publish HR policy','/policies',[{key:'title',label:'Policy title'},{key:'category',label:'Policy category'},{key:'content',label:'Approved policy text',type:'textarea'}])}><Plus size={16}/> New policy</Button>}</div>}/>{rowsFor('policies').length===0&&<div className="privacy-panel"><BookOpen size={22}/><div><strong>No approved HR policies published yet</strong><p>Employees cannot acknowledge a policy until HR publishes its approved content. Draft your organization policies, confirm legal requirements, and then publish them using New policy.</p>{isHR&&<Button variant="outline" onClick={()=>setActive('companysetup')}>Open company setup</Button>}</div></div>}<div className="policy-grid">{scoped(rowsFor('policies')).map(p=><div key={p.id} className="policy-card"><div className="policy-icon"><FileText size={22}/></div><span className="policy-category">{p.category}</span><h3>{p.title}</h3><p>{p.content}</p><small>Updated {fmt(p.last_updated)}</small>{isHR&&<div className="policy-edit"><Button variant="subtle" onClick={()=>open('Edit HR policy',`/policies/${p.id}`,[{key:'title',label:'Policy title',value:p.title},{key:'category',label:'Category',value:p.category},{key:'content',label:'Policy text',type:'textarea',value:p.content}],'Use only officially approved policies.','PATCH')}>Edit policy</Button></div>}</div>)}</div><p className="helper-note">Only HR-published policies are shown. Confirm legal requirements with HR.</p></>}
 {page==='reports'&&management&&<><Header eyebrow="PEOPLE INSIGHTS" title="Reports & analytics" desc="Aggregated and role-scoped workforce reporting to support HR decisions." right={<Button onClick={exportCSV}><Download size={17}/> Export department CSV</Button>}/><div className="metric-line">{Object.entries(stats).slice(0,5).map(([k,v])=><div key={k}><span>{titleCase(k)}</span><b>{String(v)}</b></div>)}</div><div className="dashboard-grid"><Section title="Headcount by department" subtitle="Workforce distribution, scoped to your permission level"><div className="chart-bars">{((report?.departments||[]) as Rec[]).map((r:Rec)=>{const max=Math.max(1,...(report?.departments||[]).map((x:Rec)=>x.value));return <div className="chart-line" key={r.name}><span>{r.name}</span><div><div style={{width:(r.value/max*100)+'%'}}/></div><strong>{r.value}</strong></div>})}</div></Section><Section title="Analytics integrity" subtitle="Data visibility and scope"><div className="insight-list"><div><ShieldCheck size={19}/><span>Managers only see summary data for their reporting team.</span></div><div><LockKeyhole size={19}/><span>CSV export contains aggregated department counts, not salaries or identities.</span></div><div><Activity size={19}/><span>Reports read current records from your organizational database.</span></div></div></Section></div></>}
 {page==='orgchart'&&<><Header eyebrow="STRUCTURE / REPORTING LINES" title="Organization chart" desc="Reporting relationships, teams and departments from the active staff directory."/><div className="metric-line"><div><span>Active employees</span><b>{rowsFor('orgChart').length}</b></div><div><span>Reporting managers</span><b>{new Set(rowsFor('orgChart').map(x=>x.manager_id).filter(Boolean)).size}</b></div><div><span>Departments</span><b>{new Set(rowsFor('orgChart').map(x=>x.department)).size}</b></div></div><div className="org-cards">{scoped(rowsFor('orgChart')).map(p=><article className="org-person" key={p.id}><Avatar name={p.name} color={p.avatar_color} size="large"/><div><strong>{p.name}</strong><small>{p.designation} · {p.department}</small><span>{p.manager_id?`Reports to ${rowsFor('orgChart').find(x=>x.id===p.manager_id)?.name||'Not assigned'}`:'Executive / no manager assigned'}</span></div></article>)}</div><p className="helper-note">HR may update reporting managers from Employee HRIS. Circular reporting structures are rejected.</p>{isHR&&rowsFor('orgChart').length===1&&<div className="privacy-panel"><Network size={21}/><div><strong>Reporting lines will grow with your team</strong><p>Create employee records, then assign their reporting managers using the Employee HRIS Edit action. The organization chart uses those real reporting relationships.</p><Button variant="outline" onClick={()=>setActive('employees')}>Manage employees and managers</Button></div></div>}</>}
 {page==='skills'&&<><Header eyebrow="TALENT / CAPABILITIES" title="Skills & competencies" desc="A searchable employee skills catalog and self-assessed proficiency levels." right={<div className="button-pair">{isHR&&<Button variant="outline" onClick={()=>open('Create skill','/skills/catalog',[{key:'name',label:'Skill name'},{key:'category',label:'Category'}])}><Plus size={15}/> Add catalog skill</Button>}<Button disabled={rowsFor('skillsCatalog').length===0} onClick={()=>open('Update my skill','/skills/assignments',[{key:'skill_id',label:'Skill',type:'select',options:rowsFor('skillsCatalog').map(x=>({value:String(x.id),label:`${x.name} · ${x.category}`}))},{key:'level',label:'Proficiency',type:'select',options:['Beginner','Intermediate','Advanced'],value:'Intermediate'}])}><Plus size={16}/> Update my skills</Button></div>}/><Section title="Talent skills inventory" subtitle="Managers can review direct-report skills; employees can see their own entries.">{boxTable('skillsAssignments',[col('employee_name','Employee',r=><strong>{r.employee_name}</strong>),col('skill_name','Skill'),col('category'),col('level','Proficiency',r=><Badge value={r.level}/>),col('updated_at','Updated',r=>fmt(r.updated_at))])}</Section><Section title="Skills catalog" subtitle="Available skills and competency areas">{boxTable('skillsCatalog',[col('name','Skill'),col('category')])}</Section>{rowsFor('skillsCatalog').length===0&&<div className="privacy-panel"><BookMarked size={20}/><div><strong>Skills catalog not configured yet</strong><p>HR should add the approved skills catalog first. Employees can then select a skill and record their own proficiency level.</p>{isHR&&<Button variant="outline" onClick={()=>open('Create skill','/skills/catalog',[{key:'name',label:'Skill name'},{key:'category',label:'Category'}])}>Create the first skill</Button>}</div></div>}<p className="helper-note">Proficiency is self-reported; this is not a validated assessment or automated employment decision.</p></>}
 {page==='accounts'&&isHR&&<><Header eyebrow="SECURITY / IDENTITY" title="Account administration" desc="Create reusable sign-in accounts, choose access tiers, update passwords and manage JWT sessions." right={<Button onClick={makeManagedAccount}><UserRoundPlus size={16}/> Create account with password</Button>}/><div className="privacy-panel"><ShieldCheck size={22}/><div><strong>Administrator-managed account security</strong><p>Administrators create and edit database-backed accounts with sign-in email, work email, location, and access tiers. The internal MySQL ID is assigned automatically. Password hashes, not readable passwords, are saved in MySQL and are never returned by the API or saved in the browser. HR Sub-Admins have limited team-management permissions (effective manager role), not full HR admin access. Use one-time invitations for separate employee-controlled activation.</p></div></div><Section title="Sign-in accounts and access" subtitle="Saved MySQL records · Edit contact details, permissions and credentials independently">{boxTable('accounts',[col('code','Staff ID',r=><span title={`MySQL ID: ${r.id}`}>{r.code} (#{r.id})</span>),col('name','Employee',r=><strong>{r.name}</strong>),col('email','Sign-in email'),col('work_email','Work email'),col('location','Location'),col('access_tier','Access tier',r=><Badge value={r.access_tier==='developer_admin'?'Developer Admin':r.access_tier==='hr_subadmin'?'HR Sub-Admin':r.role==='admin'?'HR Administrator':r.role==='manager'?'Manager':'Employee'}/>),col('account_active','Account status',r=><Badge value={r.account_active?'Active':r.session_version===0?'Pending invitation':'Suspended'}/>)],r=><div className="button-pair"><Button variant="outline" onClick={()=>editManagedAccount(r)}>Edit details</Button><Button variant="outline" disabled={r.id===person.id} onClick={()=>setAccountPassword(r)}><KeyRound size={14}/> Set password</Button><Button variant="outline" onClick={()=>createInvite(r)}>Email invitation</Button><Button variant="outline" disabled={r.id===person.id} onClick={()=>updateAccountRole(r)}>Change role</Button><Button variant="subtle" disabled={r.id===person.id} onClick={()=>action(`/admin/accounts/${r.id}`,'PATCH',{active:!r.account_active})}>{r.account_active?'Suspend':'Reactivate'}</Button><Button variant="subtle" disabled={r.id===person.id} onClick={()=>revokeAccountSessions(r)}>Revoke sessions</Button>{r.role==='admin'&&<Button variant="subtle" disabled={r.id===person.id} onClick={()=>setDeveloperGrant(r)}>{r.developer_access?'Remove developer access':'Grant developer access'}</Button>}</div>)}</Section></>}

 {page==='reports'&&management&&<Section title="Six-month workforce trends" subtitle="Scope-limited headcount, approved leave requests and approved expense claims"><div className="trend-rows">{rowsFor('trends').map(row=><div className="trend-row" key={row.month}><strong>{row.month}</strong><div className="trend-meter"><span style={{width:`${Math.max(3,Math.min(100,row.headcount/Math.max(1,...rowsFor('trends').map(x=>x.headcount))*100))}%`}}/></div><span>{row.headcount} people · {row.approved_leave} approved leave · {row.approved_claims} approved claims</span></div>)}</div></Section>}
 {page==='audit'&&isHR&&<><Header eyebrow="COMPLIANCE / GOVERNANCE" title="Audit trail" desc="Trace changes to HR records and approval workflows." right={<Button variant="outline" onClick={()=>downloadProtectedCSV('/audit/export.csv','sass-hrm-audit-activity.csv')}><Download size={16}/> Export audit CSV</Button>}/><Section title="Recent activity events" subtitle="Actions and timestamps; detailed audit retention is not configured">{boxTable('audit',[col('action','Event',r=><strong>{titleCase(r.action.replaceAll('.',' '))}</strong>),col('target','Record'),col('actor_id','Actor ID'),col('details','Details'),col('created_at','Time',r=>fmt(r.created_at))])}</Section></>}

 {page==='timesheets'&&<><Header eyebrow="TIME / PROJECT TRACKING" title="Project timesheets" desc="Record work hours, submit entries, and follow manager approval decisions." right={<Button onClick={()=>open('Add time entry','/timesheets',[{key:'work_day',label:'Work date',type:'date',value:today()},{key:'project',label:'Project / workstream'},{key:'hours',label:'Hours (0.25 increments)',type:'number',value:8,min:0.25,max:12},{key:'notes',label:'Work summary',type:'textarea',required:false}],'Use 0.25-hour increments. Submitted entries require manager review.')}><Plus size={16}/> Log hours</Button>}/>
 <div className="metric-line">{['Draft','Submitted','Approved','Rejected'].map(status=><div key={status}><span>{status}</span><b>{rowsFor('timesheets').filter(x=>x.status===status).length}</b></div>)}</div>
 <Section title="Work log" subtitle="Employees record their own time; reporting managers approve direct reports">{boxTable('timesheets',[col('employee_name','Employee'),col('work_day','Date',r=>fmt(r.work_day)),col('project','Project',r=><strong>{r.project}</strong>),col('hours','Hours',r=>`${r.hours} h`),col('notes','Summary'),col('status','Status',r=><Badge value={r.status}/>)],r=>r.status==='Draft'&&r.employee_id===person.id?<Button variant="subtle" onClick={()=>action(`/timesheets/${r.id}/submit`,'POST',undefined,'Submitted for review')}>Submit</Button>:r.status==='Submitted'&&management&&r.employee_id!==person.id&&(isHR||r.manager_id===person.id)?<div className="button-pair"><Button variant="subtle" onClick={()=>action(`/timesheets/${r.id}/decision`,'POST',{decision:'Approved'},'Hours approved')}>Approve</Button><Button variant="outline" onClick={()=>action(`/timesheets/${r.id}/decision`,'POST',{decision:'Rejected'},'Hours rejected')}>Reject</Button></div>:null)}</Section></>}
 {page==='benefits'&&<><Header eyebrow="EMPLOYEE EXPERIENCE / BENEFITS" title="Benefits & programs" desc="Explore HR-managed programs, request enrollment, and track recorded status." right={isHR&&<Button onClick={()=>open('Create benefit program','/benefits/plans',[{key:'name',label:'Program name'},{key:'category',label:'Category'},{key:'description',label:'Program overview',type:'textarea'}])}><Plus size={16}/> New program</Button>}/>
 <div className="privacy-panel"><ShieldCheck size={20}/><div><strong>HR-managed programs</strong><p>Enrollment requests are not proof of insurance coverage or payment. HR must verify eligibility.</p></div></div>
 <div className="advanced-card-grid">{scoped(rowsFor('benefitPlans')).map(plan=>{const existing=rowsFor('benefitEnrollments').find(e=>e.plan_id===plan.id&&e.employee_id===person.id&&e.status==='Active');return <article className="feature-card" key={plan.id}><span className="feature-icon"><HeartHandshake size={22}/></span><small>{plan.category}</small><h3>{plan.name}</h3><p>{plan.description}</p><div className="feature-card-bottom">{existing?<Badge value="Requested"/>:<Badge value="Available"/>}{existing?<Button variant="outline" onClick={()=>action(`/benefits/enrollments/${existing.id}/cancel`,'POST',undefined,'Enrollment cancelled')}>Cancel enrollment</Button>:<Button onClick={()=>action('/benefits/enrollments','POST',{plan_id:plan.id},'Enrollment requested')}>Enroll</Button>}</div></article>})}</div>
 <Section title="Benefit enrollments" subtitle={isHR?'Organization enrollments':'Your benefit enrollments'}>{boxTable('benefitEnrollments',[col('plan_name','Program'),col('employee_name','Employee'),col('category'),col('status','Status',r=><Badge value={r.status==='Active'?'Requested':r.status}/>),col('enrolled_at','Enrolled',r=>fmt(r.enrolled_at))])}</Section></>}
 {page==='recognition'&&<><Header eyebrow="CULTURE / APPRECIATION" title="Recognition wall" desc="Celebrate teammates who show teamwork, innovation, ownership and customer focus." right={<Button onClick={()=>open('Recognize a colleague','/recognitions',[{key:'recipient_id',label:'Colleague',type:'select',options:employeeOptions.filter(x=>x.value!==String(person.id))},{key:'value',label:'Value',type:'select',options:['Teamwork','Innovation','Ownership','Customer Focus','Leadership'],value:'Teamwork'},{key:'message',label:'Appreciation message',type:'textarea'}])}><Award size={16}/> Give recognition</Button>}/>
 <div className="advanced-card-grid">{scoped(rowsFor('recognitions')).map(r=><article className="feature-card recognition-card" key={r.id}><span className="feature-icon"><Award size={22}/></span><Badge value={r.value}/><h3>{r.recipient_name}</h3><p>“{r.message}”</p><div className="feature-card-bottom"><span>From {r.sender_name}</span><small>{fmt(r.created_at)}</small></div></article>)}</div></>}
 {page==='surveys'&&<><Header eyebrow="EMPLOYEE VOICE / PULSE" title="Employee pulse surveys" desc="Share your feedback in short multiple-choice surveys. Aggregates are shown only after three responses." right={isHR&&<Button onClick={()=>open('Create pulse survey','/surveys',[{key:'title',label:'Survey name'},{key:'question',label:'Survey question'},{key:'choices',label:'Answer options (comma separated)',type:'textarea'}],'Individual employee answers are not visible through the application.')}><Plus size={16}/> New survey</Button>}/>
 <div className="privacy-panel"><Lock size={20}/><div><strong>Privacy threshold</strong><p>HR can view grouped results only after at least three responses. This workspace is not a certified anonymous survey platform.</p></div></div>
 <div className="advanced-card-grid">{scoped(rowsFor('surveys')).map(s=><article className="feature-card" key={s.id}><span className="feature-icon"><ClipboardList size={22}/></span><div className="feature-card-bottom"><Badge value={s.status}/>{s.my_answer_index!==null&&s.my_answer_index!==undefined&&<Badge value="Submitted"/>}</div><h3>{s.title}</h3><p>{s.question}</p><div className="survey-options">{s.choices?.map((choice:string,i:number)=><button key={i} type="button" disabled={s.status!=='Open'||s.my_answer_index!==null&&s.my_answer_index!==undefined} className={s.my_answer_index===i?'selected':''} onClick={()=>action(`/surveys/${s.id}/responses`,'POST',{answer_index:i},'Thank you for responding')}>{choice}{s.my_answer_index===i&&<Check size={14}/>}</button>)}</div>{isHR&&<div className="feature-card-bottom"><Button variant="outline" onClick={async()=>{try{setSurveyView(await req(`/surveys/${s.id}/results`))}catch(e){notify((e as Error).message,'error')}}}>View results</Button><Button variant="subtle" onClick={()=>askUpdate(`/surveys/${s.id}`,'status',s.status==='Open'?'Closed':'Open')}>{s.status==='Open'?'Close':'Reopen'}</Button></div>}</article>)}</div>
 {surveyView&&isHR&&<Section title="Survey response summary" subtitle="Results are grouped and cannot identify individual answers" actions={<Button variant="subtle" onClick={()=>setSurveyView(null)}>Close</Button>}><div className="result-panel"><strong>{surveyView.participants} participants</strong>{surveyView.threshold_met?(surveyView.results||[]).map((r:Rec)=><div className="result-row" key={r.choice}><span>{r.choice}</span><strong>{r.count}</strong></div>):<p>At least three participants are required before grouped results are available.</p>}</div></Section>}</>}
 {page==='interviews'&&management&&<><Header eyebrow="RECRUITMENT / INTERVIEWS" title="Interview scheduling" desc="Schedule candidate interviews and track appointment status with role checks." right={<Button onClick={()=>open('Schedule interview','/recruitment/interviews',[{key:'candidate_id',label:'Candidate',type:'select',options:rowsFor('candidates').map(x=>({value:String(x.id),label:`${x.name} (${x.job_title})`}))},{key:'interviewer_id',label:'Interviewer',type:'select',options:isHR?employeeOptions.filter(x=>rowsFor('employees').some(e=>e.id===Number(x.value)&&e.role!=='employee')):[{value:String(person.id),label:person.name}],value:String(person.id)},{key:'scheduled_at',label:'Date & time',type:'datetime-local',value:interviewTime()},{key:'duration_minutes',label:'Duration (minutes)',type:'number',value:45,min:15,max:180},{key:'mode',label:'Meeting mode',type:'select',options:['Video','On-site','Phone'],value:'Video'},{key:'notes',label:'Preparation notes',type:'textarea',required:false}],'Only appointment metadata is recorded; meeting invitations require an integrated calendar service.')}><Plus size={16}/> Schedule interview</Button>}/>
 <Section title="Candidate appointments" subtitle="Only HR and management can access recruitment data">{boxTable('interviews',[col('candidate_name','Candidate',r=><strong>{r.candidate_name}</strong>),col('job_title','Position'),col('interviewer_name','Interviewer'),col('scheduled_at','Interview time',r=>new Date(r.scheduled_at).toLocaleString('en-IN')),col('mode','Mode'),col('status','Status',r=><Badge value={r.status}/>)],r=>r.status==='Scheduled'&&(isHR||r.interviewer_id===person.id)?<div className="button-pair"><Button variant="subtle" onClick={()=>askUpdate(`/recruitment/interviews/${r.id}`,'status','Completed')}>Complete</Button><Button variant="outline" onClick={()=>askUpdate(`/recruitment/interviews/${r.id}`,'status','Cancelled')}>Cancel</Button></div>:<span className="muted">—</span>)}</Section></>}
 {page==='tasks'&&<><Header eyebrow="WORKFLOW / TASK MANAGER" title="HR tasks & follow-ups" desc="Assign, complete and track HR-related work with clear ownership and due dates." right={management&&<Button onClick={()=>open('Assign HR task','/tasks',[{key:'title',label:'Task title'},{key:'assignee_id',label:'Owner',type:'select',options:employeeOptions},{key:'due_date',label:'Due date',type:'date',value:nextMonth()},{key:'priority',label:'Priority',type:'select',options:['Low','Normal','High'],value:'Normal'}])}><Plus size={16}/> Assign task</Button>}/>
 <div className="metric-line">{['Open','In Progress','Completed'].map(state=><div key={state}><span>{state}</span><b>{rowsFor('tasks').filter(x=>x.status===state).length}</b></div>)}</div>
 <Section title="Assigned tasks" subtitle="Manage your own tasks; managers may assign work to direct reports">{boxTable('tasks',[col('title','Task',r=><strong>{r.title}</strong>),col('assignee_name','Owner'),col('due_date','Due date',r=>fmt(r.due_date)),col('priority','Priority',r=><Badge value={r.priority}/>),col('status','Progress',r=><Badge value={r.status}/>)],r=><select className="inline-select" value={r.status} onChange={e=>askUpdate(`/tasks/${r.id}`,'status',e.target.value)}>{['Open','In Progress','Completed'].map(x=><option key={x}>{x}</option>)}</select>)}</Section></>}
 {['assets','documents'].includes(page)&&<EmployeeServiceOperations key={page} page={page as 'assets'|'documents'} role={person.role} userId={person.id} assets={rowsFor('assets')} documents={rowsFor('documents')} employees={rowsFor('employees')} refreshCore={refresh}/>}
 {page==='approvals'&&management&&<><Header eyebrow="WORKFLOWS / MANAGEMENT" title="Approval inbox" desc="Review leave, expenses, attendance, work arrangements and offboarding in one place."/><div className="metric-line">{['Leave','Expense','Offboarding','Work mode','Attendance'].map(kind=><div key={kind}><span>{kind} requests</span><b>{rowsFor('approvals').filter(x=>x.kind===kind).length}</b></div>)}</div>
 <Section title="Awaiting decisions" subtitle="Manager approvals are limited to direct reports; HR can process wider requests">{boxTable('approvals',[col('kind','Request type',r=><Badge value={r.kind}/>),col('employee_name','Employee',r=><strong>{r.employee_name}</strong>),col('label','Details'),col('start_date','Date',r=>fmt(r.start_date))],r=><div className="button-pair">{r.kind==='Leave'?<><Button variant="subtle" onClick={()=>action(r.path,'POST',{decision:'Approved'},'Leave approved')}>Approve</Button><Button variant="outline" onClick={()=>action(r.path,'POST',{decision:'Rejected'},'Leave rejected')}>Reject</Button></>:r.kind==='Expense'?<><Button variant="subtle" onClick={()=>askUpdate(r.path,'status','Approved')}>Approve</Button><Button variant="outline" onClick={()=>askUpdate(r.path,'status','Rejected')}>Reject</Button></>:r.kind==='Attendance'?<><Button variant="subtle" onClick={()=>action(r.path,'POST',{decision:'Approved'},'Attendance corrected')}>Approve</Button><Button variant="outline" onClick={()=>action(r.path,'POST',{decision:'Rejected'},'Attendance rejected')}>Reject</Button></>:r.kind==='Work mode'?<><Button variant="subtle" onClick={()=>action(r.path,'POST',{decision:'Approved'},'Work arrangement approved')}>Approve</Button><Button variant="outline" onClick={()=>action(r.path,'POST',{decision:'Rejected'},'Work arrangement rejected')}>Reject</Button></>:<><Button variant="subtle" onClick={()=>askUpdate(r.path,'status','Under Review')}>Review</Button><Button variant="outline" onClick={()=>askUpdate(r.path,'status','Approved')}>Approve</Button></>}</div>)}</Section></>}
 {page==='calendar'&&<PersonalCalendar official={rowsFor('calendar') as {day:string;kind:string;title:string;status:string}[]}/>}

 {page==='privateprofile'&&<><Header eyebrow="PERSONAL / PRIVACY" title="My private contact profile" desc="This information is visible only to you and authorized HR administrators. Your manager and colleagues cannot access it." right={<Button onClick={()=>open('Update private contact information','/private-profile/me',[
  {key:'contact_phone',label:'Contact phone',required:false,value:privateProfile.contact_phone||''},
  {key:'emergency_contact_name',label:'Emergency contact name',required:false,value:privateProfile.emergency_contact_name||''},
  {key:'emergency_contact_phone',label:'Emergency contact number',required:false,value:privateProfile.emergency_contact_phone||''},
  {key:'mailing_address',label:'Mailing address',type:'textarea',required:false,value:privateProfile.mailing_address||''}
 ],'Private fields are excluded from the employee directory and audits.','PATCH')}><Plus size={16}/> Edit my profile</Button>}/><Section title="Your personal contact details" subtitle="Only your own profile is loaded into this page"><div className="account-facts">{[['Contact number',privateProfile.contact_phone],['Emergency contact',privateProfile.emergency_contact_name],['Emergency phone',privateProfile.emergency_contact_phone],['Mailing address',privateProfile.mailing_address]].map(([k,v])=><div key={k}><span>{k}</span><strong>{v||'Not provided'}</strong></div>)}</div></Section><div className="privacy-banner"><ShieldCheck size={21}/> Data entered here is for this workspace. Complete a formal security and data protection review before storing sensitive information.</div></>}
 {page==='workmode'&&<><Header eyebrow="WORKPLACE / FLEXIBILITY" title="Work arrangement requests" desc="Request Remote, Hybrid or On-site work, then track manager and HR decisions." right={<Button onClick={()=>open('Request a work arrangement','/work-mode/requests',[
  {key:'requested_mode',label:'New work mode',type:'select',options:['Remote','Hybrid','On-site'].filter(m=>m!==person.work_mode)},
  {key:'effective_date',label:'Effective date',type:'date',value:today(),min:today()},
  {key:'reason',label:'Business reason',type:'textarea'}
 ],'The request must be approved before your working arrangement is changed.')}><Plus size={16}/> New request</Button>}/><div className="metric-line"><div><span>Current work mode</span><b>{rowsFor('employees').find(x=>x.id===person.id)?.work_mode||person.work_mode}</b></div><div><span>Pending requests</span><b>{rowsFor('workModeRequests').filter(x=>x.status==='Pending').length}</b></div></div><Section title="Work arrangement workflow" subtitle="Employees manage their requests; managers approve only direct reports">{boxTable('workModeRequests',[
  col('employee_name','Employee'),col('current_mode','Current mode'),col('requested_mode','Requested'),col('effective_date','Effective from',r=>fmt(r.effective_date)),col('status','Status',r=><Badge value={r.status}/>),col('reason','Reason')
 ],r=>r.status==='Pending'?<div className="button-pair">{r.employee_id===person.id&&<Button variant="outline" onClick={()=>action(`/work-mode/requests/${r.id}/cancel`,'POST',undefined,'Request cancelled')}>Cancel</Button>}{management&&r.employee_id!==person.id&&<><Button variant="subtle" onClick={()=>action(`/work-mode/requests/${r.id}/decision`,'POST',{decision:'Approved'},'Request approved')}>Approve</Button><Button variant="outline" onClick={()=>action(`/work-mode/requests/${r.id}/decision`,'POST',{decision:'Rejected'},'Request rejected')}>Reject</Button></>}</div>:<span className="muted">—</span>)}</Section>{isHR&&<div className="inline-toolbar"><Button variant="outline" onClick={()=>action('/work-mode/activate-due','POST',undefined,'Due approved changes activated')}><CalendarCheck2 size={16}/> Apply scheduled approvals due today</Button></div>}</>}
 {page==='compliance'&&<><Header eyebrow="COMPLIANCE / POLICY RECEIPTS" title="Policy acknowledgements" desc="Read company policies and acknowledge their current versions; updates require a fresh acknowledgement."/><div className="metric-line"><div><span>Current policies</span><b>{rowsFor('policyCompliance').length}</b></div><div><span>Need acknowledgement</span><b>{rowsFor('policyCompliance').filter(x=>!x.acknowledged_at).length}</b></div></div><Section title="My policy receipts" subtitle="Acknowledgements are tracked against each policy revision">{boxTable('policyCompliance',[
 col('title','Policy'),col('category'),col('revision','Revision'),col('last_updated','Updated',r=>fmt(r.last_updated)),col('acknowledged_at','Acknowledgement',r=>r.acknowledged_at?<Badge value="Acknowledged"/>:<Badge value="Pending"/>)
 ],r=><Button variant="outline" disabled={!!r.acknowledged_at} onClick={()=>{const p=rowsFor('policies').find(p=>p.id===r.policy_id);if(p)open(`Acknowledge: ${p.title}`,`/policy-compliance/${r.policy_id}/acknowledge`,[],p.content);else notify('Unable to open the policy','error')}}>{r.acknowledged_at?'Recorded':'Read & acknowledge'}</Button>)}</Section>{isHR&&<Section title="Organization acknowledgement coverage" subtitle="Summary counts for the current revision only">{boxTable('policyComplianceSummary',[col('title'),col('revision'),col('acknowledged','Acknowledged'),col('active_employees','Active workforce')])}</Section>}</>}
 {(['career','voice','discipline','requestdesk'] as const).includes(page as any)&&<CultureModule key={page} kind={page as 'career'|'voice'|'discipline'|'requestdesk'} user={person as any}/>}
 {page==='globalsearch'&&<GlobalSearch navigate={setActive} role={person.role}/>}
 {page==='dataquality'&&isHR&&<DataQualityCenter navigate={setActive}/>}
 {page==='assistant'&&<AI user={person}/>}
 {page==='settingscenter'&&isHR&&<AdminSettingsCenter mode="center" navigate={setActive}/>}
 {page==='talentsettings'&&isHR&&<AdminSettingsCenter mode="talent" navigate={setActive}/>}
 {page==='settings'&&<><Header eyebrow="ACCOUNT / PREFERENCES" title="My workspace" desc="View your profile and security settings."/><div className="dashboard-grid"><Section title="Account information" subtitle="Your active session"><div className="account-block"><AccountAvatar name={person.name} color={person.avatar_color} size="large"/><div><h2>{person.name}</h2><p>{person.designation}</p></div></div><div className="account-facts">{[['Employee ID',person.code],['Email',person.email],['Access role',titleCase(person.role)],['Department',person.department],['Location',person.location],['Work arrangement',person.work_mode]].map(([k,v])=><div key={k}><span>{k}</span><strong>{v}</strong></div>)}</div></Section><Section title="Platform security" subtitle="Account security"><div className="security-list"><div><CheckCircle2 size={18}/> Password-protected, scoped session tokens</div><div><CheckCircle2 size={18}/> Manager, HR and employee permissions</div><div><CheckCircle2 size={18}/> Audit trail for sensitive workflows</div><div><CircleHelp size={18}/> Enterprise SSO / MFA requires production integration</div><div><CircleHelp size={18}/> Security review and organization policies are required before handling sensitive employee records.</div></div><div className="button-pair"><Button variant="outline" onClick={()=>open('Change account password','/auth/change-password',[{key:'current_password',label:'Current password',type:'password'},{key:'new_password',label:'New password (12+ characters, letters and numbers)',type:'password'}],'All signed-in sessions will be revoked after changing your password.')}><KeyRound size={16}/> Change password</Button><Button variant="outline" onClick={()=>setActive('mysecurity')}><ShieldCheck size={16}/> Account security & sign-ins</Button><Button variant="outline" onClick={exportMyRecords}><FileDown size={16}/> Export my HR records (JSON)</Button><Button variant="outline" onClick={signOut}><LogOut size={16}/> Sign out</Button></div></Section></div></>}
 {page==='settings'&&<div className="inline-toolbar"><Button variant="outline" onClick={()=>setActive('profile')}><UserRoundCheck size={16}/> Manage my professional profile</Button>{isHR&&<Button variant="outline" onClick={()=>setActive('profilemgmt')}><UsersRound size={16}/> Open profile management</Button>}</div>}
 {page==='settings'&&<WorkspacePreferences/>}
 {page==='mysecurity'&&<AccountSecurityCenter mode="me" navigate={setActive} onRevoke={logout}/>}
 {page==='securityaudit'&&isHR&&<AccountSecurityCenter mode="admin" navigate={setActive} onRevoke={logout}/>}
 {page==='settings'&&<div className="inline-toolbar"><Button variant="outline" onClick={()=>setActive('inbox')}><Bell size={16}/> Manage notifications</Button><Button variant="outline" onClick={()=>setActive('workcenter')}><ClipboardCheck size={16}/> Open action center</Button>{isHR&&<><Button variant="outline" onClick={()=>setActive('settingscenter')}><Settings2 size={16}/> Administration settings center</Button><Button variant="outline" onClick={()=>setActive('workflowsettings')}><Settings2 size={16}/> Workflow configuration</Button></>}</div>}
 {page==='approvals'&&isHR&&<EmployeeServiceOperations page="approvals" role={person.role} userId={person.id} assets={rowsFor('assets')} documents={rowsFor('documents')} employees={rowsFor('employees')} refreshCore={refresh}/>}
 {(['performance','training','recognition'] as const).includes(page as any)&&<CultureEnhancements key={'culture-'+page} page={page as 'performance'|'training'|'recognition'} userId={Number(person.id)} isHR={isHR} goals={rowsFor('goals')} enrollments={rowsFor('enrollments')} recognitions={rowsFor('recognitions')}/>}
 <CompensationTools key={'comp-'+page} page={page} isHR={isHR} userId={Number(person.id||0)} expenses={rowsFor('expenses')} benefits={rowsFor('benefitEnrollments')} refreshCore={refresh}/>
 <TalentTools key={page} page={page} isHR={isHR} management={management} userId={Number(person.id||0)} candidates={rowsFor('candidates')} employees={rowsFor('employees')} tickets={rowsFor('tickets')} offboarding={rowsFor('offboarding')} tasks={rowsFor('tasks')} jobs={rowsFor('jobs')} onboarding={rowsFor('onboarding')} interviews={rowsFor('interviews')} refreshCore={refresh}/>
 </div></main><footer className="footer">© 2026 SASS Innovations <span>Technology · Transformation · Talent</span><span className="footer-right">SASS HRM Enterprise · Enterprise Workspace</span></footer></div>
 {dialog&&<DialogBox key={dialog.title+dialog.path} dialog={dialog} close={()=>setDialog(null)} busy={busy} submit={async body=>action(dialog.path,dialog.method||'POST',dialog.path==='/surveys'?{...body,choices:String(body.choices).split(',').map((x:string)=>x.trim()).filter(Boolean)}:dialog.path==='/recruitment/interviews'?{...body,scheduled_at:new Date(body.scheduled_at).toISOString()}:body,dialog.success||'Changes saved successfully')}/>}
 </div>
}
export default App;
