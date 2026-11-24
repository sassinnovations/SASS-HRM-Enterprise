import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import {useEffect, useState} from 'react';
import {AlertTriangle, BadgeCheck, CalendarDays, ClipboardCheck, Clock3, ShieldCheck, Wallet} from 'lucide-react';
import './compensation-tools.css';
import {pageUrl} from './pageRoutes';

type Row=Record<string,any>;
type Props={page:string;isHR:boolean;userId:number;expenses:Row[];benefits?:Row[];refreshCore:()=>Promise<void>};
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
const activePages=new Set(['attendance','corrections','shifts','timesheets','leave','payrollengine','payroll','taxcalculator','expenses','benefits']);
const monday=()=>{const d=new Date(),dow=(d.getDay()+6)%7;d.setDate(d.getDate()-dow);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`};
async function api(path:string,method='GET',body?:unknown):Promise<any>{
  const token=sessionStorage.getItem('sass_token');
  const res=await hrmFetch(API+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});
  const json=await res.json().catch(()=>({}));
  if(!res.ok)throw Error(typeof json.detail==='string'?json.detail:`HTTP ${res.status}: unable to complete request`);
  return json;
}

export function CompensationTools(props: Props){
  const {page,isHR,userId,expenses,refreshCore}=props;
  const [overview,setOverview]=useState<Row|null>(null);
  const [readiness,setReadiness]=useState<Row|null>(null);
  const [weekly,setWeekly]=useState<Row|null>(null);
  const [verifications,setVerifications]=useState<Row[]>([]);
  const [expenseId,setExpenseId]=useState('');
  const [benefitId,setBenefitId]=useState('');
  const [decision,setDecision]=useState('Approved');
  const [benefitDecision,setBenefitDecision]=useState('Verified');
  const [reason,setReason]=useState('');
  const [week,setWeek]=useState(monday());
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const [busy,setBusy]=useState(false);
  const [history,setHistory]=useState<Row[]>([]);
  const [config,setConfig]=useState<Row|null>(null);
  const load=async()=>{
    if(!activePages.has(page))return;
    try{
      setError('');
      const requests:[Promise<any>,Promise<any>|null,Promise<any>|null,Promise<any>|null,Promise<any>]=[
        api('/compensation/overview'),
        page==='payrollengine'&&isHR?api('/compensation/payroll-readiness'):null,
        page==='timesheets'?api('/compensation/timesheets/weekly?week_start='+encodeURIComponent(week)):null,
        page==='benefits'?api('/compensation/benefits/verification'):null,
        api('/compensation/settings')
      ];
      const r=await Promise.all(requests.map(p=>p??Promise.resolve(null)));
      setOverview(r[0]);setReadiness(r[1]);setWeekly(r[2]);setVerifications(Array.isArray(r[3])?r[3]:[]);setConfig(r[4]?.settings||null);
    }catch(e){setError((e as Error).message)}
  };
  useEffect(()=>{setHistory([]);setNotice('');setExpenseId('');setBenefitId('');void load()},[page,isHR,userId,week]);
  useRefreshData(load);
  const mutate=async(url:string,body:unknown,success:string)=>{
    setBusy(true);setError('');setNotice('');
    try{await api(url,'POST',body);setNotice(success);setReason('');setHistory([]);await refreshCore();await load()}
    catch(e){setError((e as Error).message)}finally{setBusy(false)}
  };
  if(!activePages.has(page))return null;
  const chosenExpense=expenses.find(e=>String(e.id)===expenseId);
  const eligibleBenefits=verifications.filter(b=>b.enrollment_status==='Active'&&b.employee_id!==userId);
  // Page-specific context replaces the same generic four-stat panel on every page.
  const pageInfo:Record<string,{title:string;description:string;points:string[];links:{name:string;key:string}[]}>= {
    attendance:{title:'Attendance review & guidance',description:'Review recorded check-ins and request corrections when needed.',points:[`Check-in grace reference: ${config?.attendance_grace_minutes??'—'} minutes.`,`Suggested break minimum: ${config?.minimum_break_minutes??'—'} minutes.`,`These settings do not modify recorded attendance or working hours.`],links:[{name:'Request correction',key:'corrections'},{name:'Shift schedules',key:'shifts'}]},
    corrections:{title:'Attendance correction process',description:'Review past attendance and resolve incorrect entries through approvals.',points:['Enter the actual work date and proposed hours with a clear reason.','Submitted corrections require an authorized human decision.','Approved changes remain visible in the attendance and audit histories.'],links:[{name:'Time & attendance',key:'attendance'},{name:'Approval inbox',key:'approvals'}]},
    shifts:{title:'Roster review guidance',description:'Build valid templates before assigning employees to scheduled work.',points:[`Shift duration review threshold: ${config?.shift_duration_review_hours??'—'} hours.`, 'Approved leave conflicts are checked by the scheduling service.','Follow employment and local labor requirements independently.'],links:[{name:'Attendance',key:'attendance'},{name:'Leave management',key:'leave'}]},
    timesheets:{title:'Timesheet preparation',description:'Organize weekly work entries and monitor pending approval.',points:[`Daily hours review threshold: ${config?.timesheet_daily_review_hours??'—'} hours.`,`Recommended submission follow-up: ${config?.timesheet_submission_window_days??'—'} days.`, 'Weekly totals are records of submitted work, not an automatic payroll calculation.'],links:[{name:'Approval inbox',key:'approvals'},{name:'Payroll workbench',key:'payrollengine'}]},
    leave:{title:'Leave configuration & requests',description:'Set up entitlements before employees submit leave requests.',points:[`Recommended notice: ${config?.leave_notice_review_days??'—'} days (not an automatic eligibility restriction).`,'HR-managed leave entitlements determine available allowances.','Authorized reviewers approve requests under applicable HR policies.'],links:[{name:'My calendar',key:'calendar'},{name:'Approval inbox',key:'approvals'}]},
    payrollengine:{title:'Payroll preparation controls',description:'Complete independent checks before preparing any payroll draft.',points:[`Suggested monthly review cutoff: day ${config?.payroll_cutoff_day??'—'}.`,'Review missing salary packages, attendance corrections and expenses.','No settings here certify tax, fund, insurance, or payment compliance.'],links:[{name:'Payslip archive',key:'payroll'},{name:'Tax estimator',key:'taxcalculator'}]},
    payroll:{title:'Payslip archive information',description:'Only authorized pay records are displayed; access remains permission-scoped.',points:[config?.payslip_guidance||'Published payslips will appear here after approved payroll runs.','No payroll figures are generated for empty records.','Pay statements require formal review before distribution.'],links:[{name:'Payroll workbench',key:'payrollengine'},{name:'My requests',key:'selfservice'}]},
    taxcalculator:{title:'Tax estimate limitations',description:'Use estimates for planning, not statutory payroll withholding.',points:['Select the correct jurisdiction, tax year and regime.','Independent statutory and professional verification is required.','Estimated tax is not automatically applied to salary or payslips.'],links:[{name:'Payroll workbench',key:'payrollengine'}]},
    expenses:{title:'Expense claims & audit trail',description:'Follow evidence review and employee notifications for each claim.',points:[`Review target: ${config?.expense_review_target_days??'—'} days (guidance only).`,`Receipt review reference: ₹${(config?.expense_receipt_review_amount??0).toLocaleString('en-IN')}.`,'HR decisions require a documented reason and do not initiate payments.'],links:[{name:'My requests',key:'selfservice'},{name:'Approval inbox',key:'approvals'}]},
    benefits:{title:'Benefit enrollment verification',description:'Track requested benefits separately from provider-confirmed coverage.',points:[config?.benefits_guidance||'Benefits require verification by authorized HR.', 'Only authorized HR reviewers may record eligibility findings.', 'Enrollment alone is not proof of active insurance or coverage.'],links:[{name:'My requests',key:'selfservice'}]}
  };
  const current=pageInfo[page];
  return <section className="compops" aria-label="SASS compensation operations">
    <header className="compops-head"><div className="compops-mark"><ShieldCheck size={22}/></div><div><strong>{current.title}</strong><p>{current.description}</p></div><div className="compops-head-actions">{isHR&&<a className="compops-outline" href={pageUrl('compensationsettings')}>Organization settings ↗</a>}</div></header>
    {error&&<div className="compops-error" role="alert"><AlertTriangle size={16}/>{error}</div>}
    {notice&&<div className="compops-ok" role="status"><BadgeCheck size={16}/>{notice}</div>}
    {page==='payrollengine'&&overview&&<div className="compops-grid" aria-label="Related pending work">
      <div><CalendarDays size={17}/><span>Pending leave</span><strong>{overview.pending_leave}</strong></div>
      <div><Clock3 size={17}/><span>Open timesheets</span><strong>{overview.open_timesheets}</strong></div>
      <div><Wallet size={17}/><span>Expense reviews</span><strong>{overview.pending_expenses}</strong></div>
      <div><ClipboardCheck size={17}/><span>Benefit requests</span><strong>{overview.pending_benefit_enrollments}</strong></div>
    </div>}
    {page==='timesheets'&&<div className="compops-panel"><div className="compops-row"><h3>Weekly work summary</h3><label>Week beginning Monday <input type="date" value={week} onChange={e=>setWeek(e.target.value)} /></label></div>
      <p>Recorded work hours grouped by person, project and approval status. This is not an automatic overtime or payroll calculation.</p>
      {weekly&&<><p className="compops-amount">{weekly.total_hours} total recorded hours · {weekly.week_start} to {weekly.week_end}</p>
        <div className="compops-tablewrap"><table><thead><tr><th>Employee</th><th>Project</th><th>Status</th><th>Hours</th></tr></thead><tbody>{weekly.rows.map((r:Row,i:number)=><tr key={i}><td>{r.employee_name}</td><td>{r.project}</td><td>{r.status}</td><td>{r.hours}</td></tr>)}{!weekly.rows.length&&<tr><td colSpan={4}>No time entries in this week.</td></tr>}</tbody></table></div></>}
    </div>}
    {page==='payrollengine'&&isHR&&<div className="compops-panel"><h3>Pre-payroll readiness</h3><p>Check employee salary setup and unresolved attendance, timesheet and expense decisions before preparing a payroll draft.</p>
      {readiness&&<><div className="compops-smallmetrics"><span>Active employees: <strong>{readiness.active_employees}</strong></span><span>Missing salary: <strong>{readiness.employees_without_salary?.length??0}</strong></span><span>Attendance requests: <strong>{readiness.pending_corrections}</strong></span><span>Time approvals: <strong>{readiness.pending_timesheets}</strong></span></div>
      {!!readiness.blockers?.length&&<div className="compops-warning"><strong>Setup blockers</strong><ul>{readiness.blockers.map((b:string)=><li key={b}>{b}</li>)}</ul></div>}
      {!!readiness.review_alerts?.length&&<div className="compops-warning"><strong>Pending reviews</strong><ul>{readiness.review_alerts.map((b:string)=><li key={b}>{b}</li>)}</ul></div>}
      {readiness.payroll_publication_enabled?<p className="compops-warning">Payroll publication is enabled by configuration; statutory validation and independent approval remain required.</p>:<p className="compops-ok">Payroll publication remains disabled in this environment.</p>}
      <p className="compops-muted">Operational checklist only. It does not certify tax withholding, provident fund, insurance contributions, payment or filing compliance.</p></>}
    </div>}
    {page==='expenses'&&<div className="compops-panel"><h3>Auditable expense review</h3><p>Employees can inspect their own HR decision history. Administrators can approve or reject another employee’s pending claim with a recorded reason.</p>
      <div className="compops-form"><label>Expense claim<select value={expenseId} onChange={e=>{setExpenseId(e.target.value);setHistory([])}}><option value="">Select an expense</option>{expenses.filter(x=>isHR||x.employee_id===userId).map(x=><option value={String(x.id)} key={x.id}>#{x.id} · {x.title} · {x.status}</option>)}</select></label>
      {isHR&&<><label>Decision<select value={decision} onChange={e=>setDecision(e.target.value)}><option>Approved</option><option>Rejected</option></select></label><label className="compops-wide">Review reason<input value={reason} maxLength={500} placeholder="Required explanation for the employee" onChange={e=>setReason(e.target.value)}/></label></>}
      <div className="compops-actions">{expenseId&&<button type="button" className="compops-outline" onClick={async()=>{try{setHistory(await api(`/compensation/expenses/${expenseId}/history`))}catch(e){setError((e as Error).message)}}}>View history</button>}
      {isHR&&chosenExpense?.status==='Pending'&&chosenExpense.employee_id!==userId&&<button type="button" disabled={busy||reason.trim().length<5} className="compops-primary" onClick={()=>void mutate(`/compensation/expenses/${expenseId}/review`,{decision,reason},'Expense decision recorded and employee notified')}>Save reviewed decision</button>}</div></div>
      {!!history.length&&<div className="compops-tablewrap"><table><thead><tr><th>Decision</th><th>Reason</th><th>Reviewed</th></tr></thead><tbody>{history.map((r:Row,i:number)=><tr key={i}><td>{r.decision}</td><td>{r.reason}</td><td>{r.reviewed_at?.slice(0,19)}</td></tr>)}</tbody></table></div>}
    </div>}
    {page==='benefits'&&<div className="compops-panel"><h3>Benefit eligibility reviews</h3><p>A saved enrollment is a request, not proof of coverage. Only HR can record eligibility review; confirmation by the actual provider is separate.</p>
      <div className="compops-tablewrap"><table><thead><tr><th>Program</th><th>Employee</th><th>Enrollment</th><th>HR review</th></tr></thead><tbody>{verifications.map(r=><tr key={r.enrollment_id}><td>{r.program_name}</td><td>{r.employee_name}</td><td>{r.enrollment_status}</td><td>{r.last_review??'Not reviewed'}</td></tr>)}{!verifications.length&&<tr><td colSpan={4}>No benefits have been requested.</td></tr>}</tbody></table></div>
      {isHR&&<div className="compops-form"><label>Review enrollment<select value={benefitId} onChange={e=>setBenefitId(e.target.value)}><option value="">Select enrollment</option>{eligibleBenefits.map(b=><option key={b.enrollment_id} value={String(b.enrollment_id)}>#{b.enrollment_id} · {b.employee_name} · {b.program_name}</option>)}</select></label><label>Verification outcome<select value={benefitDecision} onChange={e=>setBenefitDecision(e.target.value)}><option>Verified</option><option>Needs Information</option><option>Not Eligible</option></select></label><label className="compops-wide">HR notes<input maxLength={500} value={reason} onChange={e=>setReason(e.target.value)} placeholder="Document eligibility checks or missing information"/></label><div className="compops-actions"><button className="compops-primary" type="button" disabled={!benefitId||busy||reason.trim().length<5} onClick={()=>void mutate(`/compensation/benefits/${benefitId}/verify`,{decision:benefitDecision,notes:reason},'HR eligibility review recorded')}>Record HR review</button></div></div>}
    </div>}
    <div className="compops-context"><div><strong>Relevant process & settings</strong><ul>{current.points.map(point=><li key={point}>{point}</li>)}</ul></div><nav aria-label="Related HRM modules"><strong>Related pages</strong>{current.links.map(link=><a key={link.key} href={pageUrl(link.key)}>{link.name} ↗</a>)}</nav></div>
    <p className="compops-muted">Operational settings are advisory until approved policies and applicable local regulations are separately validated. No demo records or automatic compensation decisions are created.</p>
  </section>;
}
