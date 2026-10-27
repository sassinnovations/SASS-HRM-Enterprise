import {hrmFetch} from './apiTransport';
import {useCallback,useEffect,useMemo,useState} from 'react';
import {ClipboardCheck,CalendarRange,ShieldCheck} from 'lucide-react';
import {useRefreshData} from './useRefreshData';
import './performance-suite.css';

type Employee={id:number;name:string;manager_id?:number;account_active?:boolean};
type Action={id:number;employee_id:number;employee_name:string;creator_name:string;title:string;notes:string;category:string;due_on:string;status:'Open'|'Completed'|'Cancelled';completed_at?:string};
type Cycle={id:number;name:string;status:string;starts_on:string;ends_on:string;self_due_on:string;manager_due_on:string;eligible_employees:number;submitted_assessments:number;manager_reviews:number;acknowledgements:number};
type Progress={cycles:Cycle[];scope:string};
type Props={page:'followups'|'reviewprogress';userId:number;role:string;employees:Employee[];navigate:(p:string)=>void};
const today=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`};
async function api<T>(path:string,method='GET',data?:unknown):Promise<T>{
 const token=sessionStorage.getItem('sass_token');
 const r=await hrmFetch('/api/performance-followups'+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(data!==undefined?{body:JSON.stringify(data)}:{})});
 let body:any={};try{body=await r.json()}catch{}
 if(!r.ok)throw new Error(typeof body?.detail==='string'?body.detail:`Request failed (HTTP ${r.status})`);
 return body as T;
}
export function PerformanceFollowups({page,userId,role,employees,navigate}:Props){
 const [actions,setActions]=useState<Action[]>([]),[progress,setProgress]=useState<Progress>({cycles:[],scope:''});
 const [status,setStatus]=useState('All'),[error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false);
 const [form,setForm]=useState({employee_id:String(userId),title:'',notes:'',category:'Goals',due_on:today()});
 const choices=useMemo(()=>employees.filter(e=>Boolean(e.account_active)&&(role==='admin'||e.id===userId||(role==='manager'&&e.manager_id===userId))),[employees,role,userId]);
 const load=useCallback(async()=>{setError('');try{
  if(page==='followups')setActions(await api<Action[]>(`/actions?status=${encodeURIComponent(status)}`));
  else setProgress(await api<Progress>('/progress'));
 }catch(e){setError((e as Error).message)}},[page,status]);
 useEffect(()=>{void load()},[load]);useRefreshData(load);
 const change=async(fn:()=>Promise<unknown>,success:string)=>{setBusy(true);setError('');setNotice('');try{await fn();await load();setNotice(success)}catch(e){setError((e as Error).message)}finally{setBusy(false)}};
 const open=actions.filter(x=>x.status==='Open');
 const overdue=open.filter(x=>x.due_on<today());
 return <section className="ps-layout">
  <header className="ps-hero"><div className="ps-hero-icon">{page==='followups'?<ClipboardCheck size={24}/>:<CalendarRange size={24}/>}</div><div><span>EMPLOYEE PERFORMANCE / HUMAN REVIEW</span><h1>{page==='followups'?'Performance action tracker':'Review cycle progress'}</h1><p>{page==='followups'?'Record agreed next steps, assign ownership and track completion.':'See how many reviews have been submitted and acknowledged, within your permission scope.'}</p></div></header>
  <nav className="ps-links" aria-label="Performance navigation">{([['performance','Goals'],['performancecycles','Review cycles'],['appraisals','Appraisals'],['checkins','1:1 check-ins'],['growthplans','Development plans'],['feedbackrequests','Manager feedback'],['followups','Action tracker'],['reviewprogress','Review progress'],['evidence','Evidence portfolio'],['goaljournal','Goal journal']] as const).map(([key,label])=><button type="button" key={key} aria-current={page===key?'page':undefined} onClick={()=>navigate(key)}>{label}</button>)}</nav>
  {error&&<div className="ps-alert ps-error" role="alert">{error}</div>}{notice&&<div className="ps-alert ps-success" role="status">{notice}</div>}
  {page==='followups'?<>
   <div className="ps-metrics"><article><small>Visible actions</small><strong>{actions.length}</strong></article><article><small>Open actions</small><strong>{open.length}</strong></article><article><small>Past due</small><strong>{overdue.length}</strong></article></div>
   <section className="ps-panel"><h2>New performance follow-up</h2><p>Use this for agreed goals or meeting actions. Human reviewers are responsible for deciding whether work is completed.</p>
    <form onSubmit={e=>{e.preventDefault();void change(()=>api('/actions','POST',{...form,employee_id:Number(form.employee_id)}),'Follow-up created.')}}>
     <div className="ps-fields"><label>Employee<select required value={form.employee_id} onChange={e=>setForm(v=>({...v,employee_id:e.target.value}))}>{choices.map(e=><option key={e.id} value={e.id}>{e.name}{e.id===userId?' (me)':''}</option>)}</select></label><label>Category<select value={form.category} onChange={e=>setForm(v=>({...v,category:e.target.value}))}>{['Goals','Appraisal','1:1 meeting','Development','Other'].map(v=><option key={v}>{v}</option>)}</select></label><label>Due date<input type="date" min={today()} required value={form.due_on} onChange={e=>setForm(v=>({...v,due_on:e.target.value}))}/></label></div>
     <label>Follow-up action<input required minLength={5} maxLength={160} value={form.title} onChange={e=>setForm(v=>({...v,title:e.target.value}))} placeholder="Example: Share updated project learning goals"/></label>
     <label>Agreed next steps (optional)<textarea maxLength={1000} rows={2} value={form.notes} onChange={e=>setForm(v=>({...v,notes:e.target.value}))}/></label>
     <button className="ps-primary" disabled={busy||!choices.some(e=>e.id===Number(form.employee_id))}>Assign follow-up</button>
    </form></section>
   <section className="ps-panel"><div className="ps-record-heading"><h2>Actions and progress</h2><label>Filter<select aria-label="Filter follow-up status" value={status} onChange={e=>setStatus(e.target.value)}>{['All','Open','Completed','Cancelled'].map(v=><option key={v}>{v}</option>)}</select></label></div>
    {actions.map(x=><article className="ps-appraisal" key={x.id}><div className="ps-record-heading"><div><strong>{x.title}</strong><small>{x.employee_name} · {x.category} · Due {x.due_on} · Created by {x.creator_name}</small></div><span className="ps-chip">{x.status==='Open'&&x.due_on<today()?'Overdue':x.status}</span></div>{x.notes&&<p>{x.notes}</p>}
     <div className="ps-links">{x.status==='Open'&&<><button type="button" disabled={busy} onClick={()=>void change(()=>api(`/actions/${x.id}`,'PATCH',{status:'Completed'}),'Action completed.')}>Mark completed</button><button type="button" disabled={busy} onClick={()=>void change(()=>api(`/actions/${x.id}`,'PATCH',{status:'Cancelled'}),'Action cancelled.')}>Cancel</button></>}{x.status==='Completed'&&<button type="button" disabled={busy} onClick={()=>void change(()=>api(`/actions/${x.id}`,'PATCH',{status:'Open'}),'Action reopened.')}>Reopen</button>}</div>
    </article>)}{!actions.length&&<p className="ps-empty">No follow-up actions in this filter.</p>}</section>
  </>:<>
   <div className="ps-metrics"><article><small>My visibility</small><strong style={{fontSize:18}}>{progress.scope||'—'}</strong></article><article><small>Review cycles</small><strong>{progress.cycles.length}</strong></article><article><small>Open cycles</small><strong>{progress.cycles.filter(c=>c.status==='Open').length}</strong></article></div>
   <section className="ps-panel"><h2>Appraisal completion overview</h2><p>Completion counts are calculated from submitted records in your permitted team or personal scope. These are not ratings, rankings, or employee performance scores.</p>
    {progress.cycles.map(c=><article className="ps-appraisal" key={c.id}><div className="ps-record-heading"><div><strong>{c.name}</strong><small>{c.starts_on} to {c.ends_on} · Self due {c.self_due_on} · Manager due {c.manager_due_on}</small></div><span className="ps-chip">{c.status}</span></div><div className="ps-fields" style={{marginTop:12}}>{[['Eligible employees',c.eligible_employees],['Self-assessments',c.submitted_assessments],['Manager reviews',c.manager_reviews],['Acknowledged',c.acknowledgements]].map(([label,n])=><div className="ps-review" key={label}><small>{label}</small><strong>{n}</strong></div>)}</div></article>)}{!progress.cycles.length&&<p className="ps-empty">No appraisal cycles in your scope yet.</p>}
   </section>
  </>}
  <p className="ps-privacy"><ShieldCheck size={17}/> Only authorized employees, current reporting managers and HR can view their permitted records. Follow-up actions do not automatically change appraisals, salaries or employment decisions.</p>
 </section>;
}
