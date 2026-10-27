import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import {useEffect,useState} from 'react';
import {AlertCircle,CalendarClock,CheckCircle2,Clock3,FileText,HeartHandshake,Save,Settings2,ShieldCheck,WalletCards} from 'lucide-react';
import {pageUrl} from './pageRoutes';
import './compensation-settings.css';

export type CompensationPolicy = {
  attendance_grace_minutes:number;
  minimum_break_minutes:number;
  shift_duration_review_hours:number;
  timesheet_daily_review_hours:number;
  timesheet_submission_window_days:number;
  leave_notice_review_days:number;
  expense_review_target_days:number;
  expense_receipt_review_amount:number;
  payroll_cutoff_day:number;
  benefits_guidance:string;
  payslip_guidance:string;
};
export type StoredPolicy={settings:CompensationPolicy;updated_at:string|null;updated_by:number|null;source:string};

const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
export const POLICY_DEFAULTS:CompensationPolicy={attendance_grace_minutes:10,minimum_break_minutes:30,shift_duration_review_hours:10,timesheet_daily_review_hours:9,timesheet_submission_window_days:7,leave_notice_review_days:3,expense_review_target_days:5,expense_receipt_review_amount:1000,payroll_cutoff_day:25,benefits_guidance:'Benefit requests require HR verification and separate provider confirmation.',payslip_guidance:'Payslips become available only after reviewed payroll records are published.'};

async function request(method='GET',body?:CompensationPolicy):Promise<StoredPolicy>{
  const token=sessionStorage.getItem('sass_token');
  const response=await hrmFetch(API+'/compensation/settings',{method,headers:{'Content-Type':'application/json',...(token?{'Authorization':`Bearer ${token}`}:{})},...(body?{body:JSON.stringify(body)}:{})});
  const result=await response.json().catch(()=>({}));
  if(!response.ok)throw new Error(typeof result?.detail==='string'?result.detail:`Settings request failed (HTTP ${response.status})`);
  return result as StoredPolicy;
}

type NumericKey=Exclude<keyof CompensationPolicy,'benefits_guidance'|'payslip_guidance'>;
const groups:{title:string;description:string;icon:typeof Clock3;fields:{key:NumericKey;label:string;unit:string;min:number;max:number;hint:string}[];paths:{label:string;key:string}[]}[]=[
 {title:'Attendance & shifts',description:'Reference windows for timekeeping and roster reviews.',icon:Clock3,fields:[
  {key:'attendance_grace_minutes',label:'Check-in grace reference',unit:'minutes',min:0,max:60,hint:'Shown as guidance; check-in data is not automatically altered.'},
  {key:'minimum_break_minutes',label:'Suggested break minimum',unit:'minutes',min:0,max:120,hint:'A review reference, not an automatic deduction.'},
  {key:'shift_duration_review_hours',label:'Shift duration review threshold',unit:'hours',min:4,max:16,hint:'Highlight long shifts for an HR review.'}
 ],paths:[{key:'attendance',label:'Attendance'},{key:'corrections',label:'Corrections'},{key:'shifts',label:'Shifts'}]},
 {title:'Timesheets & leave',description:'Review cadence and scheduling expectations.',icon:CalendarClock,fields:[
  {key:'timesheet_daily_review_hours',label:'Daily hours review threshold',unit:'hours',min:1,max:24,hint:'A warning reference; does not change payable hours.'},
  {key:'timesheet_submission_window_days',label:'Submission follow-up window',unit:'days',min:1,max:31,hint:'Suggested follow-up time after work is recorded.'},
  {key:'leave_notice_review_days',label:'Leave notice recommendation',unit:'days',min:0,max:90,hint:'An informational expectation; statutory and approved leave policies take priority.'}
 ],paths:[{key:'timesheets',label:'Timesheets'},{key:'leave',label:'Leave management'}]},
 {title:'Expense approvals & payroll',description:'Administrative review targets, never statutory calculations.',icon:WalletCards,fields:[
  {key:'expense_review_target_days',label:'Expense review target',unit:'days',min:1,max:60,hint:'Requested time for an HR review, not a reimbursement promise.'},
  {key:'expense_receipt_review_amount',label:'Receipt review threshold',unit:'INR',min:0,max:10000000,hint:'An evidence-review prompt; this does not reject claims automatically.'},
  {key:'payroll_cutoff_day',label:'Suggested monthly review cutoff',unit:'day of month',min:1,max:28,hint:'Scheduling only. No salary or tax computation changes.'}
 ],paths:[{key:'expenses',label:'Expenses'},{key:'payrollengine',label:'Payroll workbench'},{key:'payroll',label:'Payslips'}]}
];

export function CompensationSettings({isHR}:{isHR:boolean}){
 const [saved,setSaved]=useState<CompensationPolicy>(POLICY_DEFAULTS);
 const [form,setForm]=useState<CompensationPolicy>(POLICY_DEFAULTS);
 const [meta,setMeta]=useState<Pick<StoredPolicy,'updated_at'|'source'>>({updated_at:null,source:'defaults'});
 const [loading,setLoading]=useState(true),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const dirty=JSON.stringify(saved)!==JSON.stringify(form);
 const load=async()=>{setLoading(true);setError('');try{const r=await request();setSaved({...r.settings});setForm({...r.settings});setMeta({updated_at:r.updated_at,source:r.source})}catch(e){setError((e as Error).message)}finally{setLoading(false)}};
 useEffect(()=>{void load()},[]);
 useRefreshData(load);
 const save=async()=>{setError('');setNotice('');setBusy(true);try{const r=await request('PUT',form);setSaved({...r.settings});setForm({...r.settings});setMeta({updated_at:r.updated_at,source:r.source});setNotice('Compensation settings saved and audited.')}catch(e){setError((e as Error).message)}finally{setBusy(false)}};
 const numberField=(key:NumericKey,value:number)=>setForm(old=>({...old,[key]:value}));
 return <div className="cset">
  <header className="cset-heading"><div className="cset-icon"><Settings2 size={25}/></div><div><div className="cset-overline">SASS HRM / COMPENSATION ADMINISTRATION</div><h1>Compensation settings</h1><p>Review guidance for attendance, shifts, leave, timesheets, expenses, benefits, and payroll.</p></div></header>
  <div className="cset-notice"><ShieldCheck size={20}/><div><strong>Policies are guidance, not automated payroll rules.</strong><p>Values on this screen do not override approved HR policies, statutory obligations, leave eligibility, salary packages, actual check-in records, tax rates, or insurer coverage. Only HR administrators may edit them.</p></div></div>
  {error&&<div role="alert" className="cset-error"><AlertCircle size={17}/>{error}</div>}
  {notice&&<div role="status" className="cset-success"><CheckCircle2 size={17}/>{notice}</div>}
  <div className="cset-status"><span>Configuration: <strong>{meta.source==='organization'?'Saved organization settings':'Initial recommended defaults'}</strong></span><span>{meta.updated_at?'Updated '+new Date(meta.updated_at).toLocaleString('en-IN'):'Not yet customized'}</span><span>{isHR?'HR Administrator · editing enabled':'View-only access'}</span></div>
  {loading?<div className="cset-loading">Loading saved settings…</div>:<>
   <div className="cset-groups">{groups.map(group=>{const Icon=group.icon;return <section className="cset-card" key={group.title}><header><span className="cset-group-icon"><Icon size={20}/></span><div><h2>{group.title}</h2><p>{group.description}</p></div></header><div className="cset-fields">{group.fields.map(field=><label key={field.key} className="cset-field"><span>{field.label}</span><div><input disabled={!isHR||busy} type="number" step="1" min={field.min} max={field.max} value={form[field.key]} onChange={e=>numberField(field.key,Number(e.target.value))}/><small>{field.unit}</small></div><em>{field.hint}</em></label>)}</div><nav className="cset-links" aria-label={`${group.title} modules`}>{group.paths.map(item=><a href={pageUrl(item.key)} key={item.key}>{item.label} ↗</a>)}</nav></section>})}</div>
   <div className="cset-groups cset-notes"><section className="cset-card"><header><span className="cset-group-icon"><HeartHandshake size={20}/></span><div><h2>Benefits & enrollment</h2><p>Explain the benefits-review process to employees.</p></div></header><label className="cset-field"><span>Employee guidance</span><textarea rows={3} disabled={!isHR||busy} maxLength={400} value={form.benefits_guidance} onChange={e=>setForm(old=>({...old,benefits_guidance:e.target.value}))}/><em>HR eligibility verification is separate from provider confirmation.</em></label><nav className="cset-links"><a href={pageUrl('benefits')}>Benefits & programs ↗</a></nav></section>
   <section className="cset-card"><header><span className="cset-group-icon"><FileText size={20}/></span><div><h2>Payslips & employee information</h2><p>Publication and archive information, without exposing salaries.</p></div></header><label className="cset-field"><span>Payslip guidance</span><textarea rows={3} disabled={!isHR||busy} maxLength={400} value={form.payslip_guidance} onChange={e=>setForm(old=>({...old,payslip_guidance:e.target.value}))}/><em>All payroll publication and statutory checks remain independent.</em></label><nav className="cset-links"><a href={pageUrl('payroll')}>Payslip archive ↗</a><a href={pageUrl('taxcalculator')}>Tax estimator ↗</a></nav></section></div>
   {isHR&&<div className="cset-actions"><button type="button" className="cset-outline" disabled={!dirty||busy} onClick={()=>setForm({...saved})}>Discard unsaved changes</button><button type="button" className="cset-primary" disabled={!dirty||busy} onClick={()=>void save()}><Save size={16}/>{busy?'Saving…':'Save settings'}</button></div>}
  </>}
 </div>
}
