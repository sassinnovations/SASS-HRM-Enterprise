import {hrmFetch} from './apiTransport';
import {useCallback,useEffect,useState} from 'react';
import {AlertTriangle,CheckCircle2,ClipboardCheck,Download,Settings2,ShieldCheck} from 'lucide-react';
import {useRefreshData} from './useRefreshData';
import './data-quality-center.css';

type Issue={key:string;kind:string;record_id:number;subject:string;detail:string;status:string;assigned_to:number|null;note:string;updated_at:string;page:string};
type Results={items:Issue[];total:number;truncated_sources:string[];rule_names:string[]};
type Rule={task_grace_days:number;onboarding_grace_days:number;leave_review_days:number;helpdesk_review_days:number};
type Admin={id:number;name:string;role:string;account_active?:number};
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
const CATEGORIES=[['all','All checks'],['employee_profile','Employee profile'],['manager_relationship','Reporting relationships'],['onboarding_overdue','Overdue onboarding'],['task_overdue','Overdue HR tasks'],['leave_review_delay','Leave awaiting review'],['helpdesk_review_delay','Helpdesk review delay']];
const STATUSES=['all','Open','In progress','Reviewed'];
const initRule:Rule={task_grace_days:0,onboarding_grace_days:0,leave_review_days:7,helpdesk_review_days:14};
async function api<T>(path:string,method='GET',body?:unknown):Promise<T>{
 const token=sessionStorage.getItem('sass_token');
 const r=await hrmFetch(API+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},
  ...(body===undefined?{}:{body:JSON.stringify(body)}),cache:'no-store'});
 const result=await r.json().catch(()=>null);
 if(!r.ok)throw new Error(typeof result?.detail==='string'?result.detail:`Request failed (HTTP ${r.status})`);
 return result as T;
}
const label=(kind:string)=>CATEGORIES.find(x=>x[0]===kind)?.[1]||kind;

export function DataQualityCenter({navigate}:{navigate:(page:string)=>void}){
 const [filter,setFilter]=useState('all');const [status,setStatus]=useState('all');const [query,setQuery]=useState('');const [offset,setOffset]=useState(0);
 const [results,setResults]=useState<Results|null>(null);const [policy,setPolicy]=useState<Rule>(initRule);
 const [admins,setAdmins]=useState<Admin[]>([]);const [selected,setSelected]=useState<Issue|null>(null);
 const [reviewStatus,setReviewStatus]=useState('Open');const [assigned,setAssigned]=useState('');const [note,setNote]=useState('');
 const [settingsOpen,setSettingsOpen]=useState(false);const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');
 const load=useCallback(async()=>{
  setError('');
  try{
   const qs=new URLSearchParams({kind:filter,status,q:query.trim(),offset:String(offset),limit:'30'});
   const [issues,rules,employees]=await Promise.all([
    api<Results>(`/admin/data-quality/issues?${qs.toString()}`),
    api<Rule>('/admin/data-quality/policy'),
    api<Admin[]>('/employees')]);
   setResults(issues);setPolicy(rules);
   setAdmins(employees.filter(x=>x.role==='admin'&&x.account_active!==0));
  }catch(e){setError((e as Error).message)}
 },[filter,status,query,offset]);
 useEffect(()=>{void load()},[load]);useRefreshData(load);
 const open=(issue:Issue)=>{setSelected(issue);setReviewStatus(issue.status);setAssigned(issue.assigned_to==null?'':String(issue.assigned_to));setNote(issue.note)};
 const act=async(job:()=>Promise<unknown>,success:string)=>{
  setBusy(true);setError('');setNotice('');
  try{await job();setNotice(success);setSelected(null);await load()}catch(e){setError((e as Error).message)}finally{setBusy(false)}
 };
 const savePolicy=()=>void act(()=>api('/admin/data-quality/policy','PUT',policy),'Review thresholds saved and audited.');
 const saveReview=()=>{if(!selected)return;
  void act(()=>api(`/admin/data-quality/issues/${selected.kind}/${selected.record_id}/review`,'PUT',
   {status:reviewStatus,assigned_to:assigned?Number(assigned):null,note}),'Review recorded. The original HR record is unchanged.');
 };
 const download=async()=>{
  setBusy(true);setError('');
  try{
   const token=sessionStorage.getItem('sass_token');
   const qs=new URLSearchParams({kind:filter,status,q:query.trim()});
   const response=await hrmFetch(`${API}/admin/data-quality/export.csv?${qs.toString()}`,
      {headers:token?{Authorization:`Bearer ${token}`}:{},cache:'no-store'});
   if(!response.ok){const body=await response.json().catch(()=>null);throw Error(body?.detail||`CSV export failed: ${response.status}`)}
   const blob=await response.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');
   a.href=url;a.download='sass-hrm-data-quality.csv';document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);
  }catch(e){setError((e as Error).message)}finally{setBusy(false)}
 };
 const validPolicy=Number.isInteger(policy.task_grace_days)&&policy.task_grace_days>=0&&policy.task_grace_days<=60&&
  Number.isInteger(policy.onboarding_grace_days)&&policy.onboarding_grace_days>=0&&policy.onboarding_grace_days<=60&&
  Number.isInteger(policy.leave_review_days)&&policy.leave_review_days>=1&&policy.leave_review_days<=180&&
  Number.isInteger(policy.helpdesk_review_days)&&policy.helpdesk_review_days>=1&&policy.helpdesk_review_days<=180;
 return <section className="dq-page">
  <div className="dq-hero"><div><span className="dq-eyebrow">PEOPLE MANAGEMENT / ADMINISTRATOR ONLY</span><h1>HR data quality center</h1><p>Identify incomplete directory records and delayed workflows, assign human follow-up, and record review decisions. Findings do not change employee records or automatically decide cases.</p></div>
   <div className="dq-actions"><button onClick={()=>setSettingsOpen(x=>!x)}><Settings2 size={16}/> Quality rules</button><button onClick={()=>void download()} disabled={busy}><Download size={16}/> Export CSV</button></div></div>
  <div className="dq-stats"><article><ClipboardCheck size={20}/><small>Matching findings</small><strong>{results?.total??'—'}</strong></article><article><ShieldCheck size={20}/><small>Active monitoring rules</small><strong>6</strong></article><article><CheckCircle2 size={20}/><small>Access</small><strong>HR only</strong></article></div>
  {error&&<div className="dq-alert error" role="alert">{error}</div>}{notice&&<div className="dq-alert success" role="status">{notice}</div>}
  {!!results?.truncated_sources.length&&<div className="dq-alert error" role="alert"><AlertTriangle size={17}/> Large dataset: source limit reached for {results.truncated_sources.join(', ')}. Results may be incomplete; CSV export is unavailable until you narrow the underlying dataset.</div>}
  {settingsOpen&&<div className="dq-panel"><h2>Monitoring thresholds</h2><p>Configure when overdue items appear. These values only affect this diagnostic view, not attendance, payroll, statutory rules, or employee approvals.</p><div className="dq-policy-grid">
   {([['task_grace_days','HR task grace days',0,60],['onboarding_grace_days','Onboarding grace days',0,60],['leave_review_days','Pending leave review (days)',1,180],['helpdesk_review_days','Open helpdesk review (days)',1,180]] as const).map(([key,name,min,max])=><label key={key}>{name}<input type="number" min={min} max={max} value={policy[key]} onChange={e=>setPolicy(v=>({...v,[key]:Number(e.target.value)}))}/></label>)}
  </div><button className="dq-primary" disabled={busy||!validPolicy} onClick={savePolicy}>Save quality rules</button></div>}
  <div className="dq-panel"><div className="dq-filters"><label>Check type<select value={filter} onChange={e=>{setFilter(e.target.value);setOffset(0)}}>{CATEGORIES.map(([value,text])=><option key={value} value={value}>{text}</option>)}</select></label><label>Review status<select value={status} onChange={e=>{setStatus(e.target.value);setOffset(0)}}>{STATUSES.map(v=><option key={v} value={v}>{v==='all'?'All statuses':v}</option>)}</select></label><label>Find a record<input type="search" value={query} maxLength={80} onChange={e=>{setQuery(e.target.value);setOffset(0)}} placeholder="Employee, case, or task"/></label></div>
   <div className="dq-list">{results?.items.length?results.items.map(issue=><article className="dq-issue" key={issue.key}><div className="dq-issue-detail"><span className="dq-tag">{label(issue.kind)}</span><h3>{issue.subject||'Untitled record'}</h3><p>{issue.detail}</p><small>Reference: {issue.key} · Review status: {issue.status}</small></div><div className="dq-issue-actions"><button onClick={()=>navigate(issue.page)}>Open module</button><button className="dq-primary" onClick={()=>open(issue)}>Review</button></div></article>):<div className="dq-empty">No matching findings. Change filters to review another category.</div>}</div>
   <div className="dq-pagination"><span>{results?`${results.total===0?0:offset+1}–${Math.min(offset+30,results.total)} of ${results.total}`:'Loading findings'}</span><div><button disabled={offset===0} onClick={()=>setOffset(v=>Math.max(0,v-30))}>Previous</button><button disabled={!results||offset+30>=results.total} onClick={()=>setOffset(v=>v+30)}>Next</button></div></div>
  </div>
  {selected&&<div className="dq-panel dq-editor"><h2>Review finding: {selected.subject}</h2><p>Review records track follow-up only. To correct the source record, use its existing HRM module.</p><div className="dq-policy-grid"><label>Review status<select value={reviewStatus} onChange={e=>setReviewStatus(e.target.value)}>{STATUSES.filter(s=>s!=='all').map(s=><option key={s}>{s}</option>)}</select></label><label>Responsible HR administrator<select value={assigned} onChange={e=>setAssigned(e.target.value)}><option value="">Not assigned</option>{admins.map(a=><option key={a.id} value={a.id}>{a.name}</option>)}</select></label></div><label>Review note (HR administrators only)<textarea maxLength={600} rows={3} value={note} onChange={e=>setNote(e.target.value)} placeholder="Describe follow-up without including sensitive details"/></label><div className="dq-actions"><button onClick={()=>setSelected(null)}>Cancel</button><button className="dq-primary" disabled={busy} onClick={saveReview}>Save review</button></div></div>}
  <p className="dq-disclaimer"><ShieldCheck size={17}/> Operational diagnostic only. Reviewed issues remain listed until their source records are fixed. No payroll, leave or compliance decisions are automated.</p>
 </section>;
}
