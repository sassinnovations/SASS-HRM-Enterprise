import {apiUrl,hrmFetch} from './apiTransport';
import {useCallback,useEffect,useMemo,useState} from 'react';
import {BookOpenCheck,MessageSquareMore,ShieldCheck} from 'lucide-react';
import {useRefreshData} from './useRefreshData';
import './performance-suite.css';

type Plan={id:number;employee_id:number;employee_name:string;title:string;focus_area:string;success_outcome:string;support_needed:string;target_date:string;status:string;milestone_count:number;completed_milestones:number};
type Milestone={id:number;plan_id:number;title:string;due_on:string;completed_at?:string};
type Feedback={id:number;employee_id:number;manager_id:number;employee_name:string;manager_name:string;topic:string;question:string;status:string;response?:string;created_at:string};
type Employee={id:number;name:string;manager_id?:number;account_active?:boolean};
type Props={page:'growthplans'|'feedbackrequests';userId:number;role:string;employees:Employee[];navigate:(p:string)=>void};
const today=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`};
async function api<T>(path:string,method='GET',data?:unknown):Promise<T>{
 const token=sessionStorage.getItem('sass_token');
 const response=await hrmFetch(apiUrl('/performance-growth'+path),{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(data!==undefined?{body:JSON.stringify(data)}:{})});
 let parsed:any={};try{parsed=await response.json()}catch{}
 if(!response.ok)throw new Error(typeof parsed?.detail==='string'?parsed.detail:`Request failed: HTTP ${response.status}`);
 return parsed as T;
}
export function PerformanceGrowth({page,userId,role,employees,navigate}:Props){
 const [plans,setPlans]=useState<Plan[]>([]),[feedback,setFeedback]=useState<Feedback[]>([]);
 const [milestones,setMilestones]=useState<Record<number,Milestone[]>>({});
 const [error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false);
 const [owner,setOwner]=useState(String(userId));
 const [planForm,setPlanForm]=useState({title:'',focus_area:'Technical skills',success_outcome:'',support_needed:'',target_date:today()});
 const [newMilestone,setNewMilestone]=useState<Record<number,{title:string;due_on:string}>>({});
 const [question,setQuestion]=useState({topic:'',question:''});
 const [replies,setReplies]=useState<Record<number,string>>({});
 const accessible=useMemo(()=>employees.filter(e=>Boolean(e.account_active)&&(e.id===userId||role==='admin'||(role==='manager'&&e.manager_id===userId))),[employees,role,userId]);
 const load=useCallback(async()=>{
  setError('');try{
   if(page==='growthplans'){
    const found=await api<Plan[]>('/plans');setPlans(found);
    const all=await Promise.all(found.map(async p=>[p.id,await api<Milestone[]>(`/plans/${p.id}/milestones`)] as const));
    setMilestones(Object.fromEntries(all));
   }else setFeedback(await api<Feedback[]>('/feedback'));
  }catch(e){setError((e as Error).message)}
 },[page]);
 useEffect(()=>{void load()},[load]);useRefreshData(load);
 const change=async(run:()=>Promise<unknown>,message:string)=>{
  setBusy(true);setError('');setNotice('');
  try{await run();await load();setNotice(message)}catch(e){setError((e as Error).message)}finally{setBusy(false)}
 };
 return <section className="ps-layout">
  <header className="ps-hero"><div className="ps-hero-icon">{page==='growthplans'?<BookOpenCheck size={24}/>:<MessageSquareMore size={24}/>}</div><div><span>EMPLOYEE PERFORMANCE / CONTINUOUS DEVELOPMENT</span><h1>{page==='growthplans'?'Individual development plans':'Manager feedback requests'}</h1><p>{page==='growthplans'?'Set development outcomes, break them into milestones, and track progress with your manager.':'Ask your reporting manager for written feedback on specific work and acknowledge their response.'}</p></div></header>
  <nav className="ps-links" aria-label="Performance modules">
   {([['performance','Goals'],['performancecycles','Review cycles'],['appraisals','Appraisals'],['checkins','1:1 check-ins'],['growthplans','Development plans'],['feedbackrequests','Feedback requests']] as const).map(([key,label])=><button type="button" key={key} aria-current={page===key?'page':undefined} onClick={()=>navigate(key)}>{label}</button>)}
  </nav>
  {error&&<div role="alert" className="ps-alert ps-error">{error}</div>}
  {notice&&<div role="status" className="ps-alert ps-success">{notice}</div>}
  {page==='growthplans'?<>
   <div className="ps-metrics"><article><small>Plans in your scope</small><strong>{plans.length}</strong></article><article><small>Active plans</small><strong>{plans.filter(p=>p.status==='Active').length}</strong></article><article><small>Completed milestones</small><strong>{plans.reduce((n,p)=>n+p.completed_milestones,0)}</strong></article></div>
   <section className="ps-panel"><h2>Create a development plan</h2><p>Employees can create personal plans; managers can support direct reports. Plans and their milestones are visible only to authorized users.</p>
    <form onSubmit={e=>{e.preventDefault();void change(()=>api('/plans','POST',{...planForm,employee_id:Number(owner)}),'Development plan created.')}}>
     <div className="ps-fields"><label>Employee<select value={owner} onChange={e=>setOwner(e.target.value)} required>{accessible.map(e=><option key={e.id} value={e.id}>{e.name}{e.id===userId?' (me)':''}</option>)}</select></label><label>Development focus<select value={planForm.focus_area} onChange={e=>setPlanForm(v=>({...v,focus_area:e.target.value}))}>{['Technical skills','Communication','Leadership','Role development','Other'].map(x=><option key={x}>{x}</option>)}</select></label><label>Target date<input type="date" required min={today()} value={planForm.target_date} onChange={e=>setPlanForm(v=>({...v,target_date:e.target.value}))}/></label></div>
     <label>Plan title<input required minLength={5} maxLength={150} value={planForm.title} onChange={e=>setPlanForm(v=>({...v,title:e.target.value}))}/></label>
     <label>Expected outcome<textarea required minLength={10} maxLength={1500} rows={3} value={planForm.success_outcome} onChange={e=>setPlanForm(v=>({...v,success_outcome:e.target.value}))}/></label>
     <label>Support or learning resources needed<textarea maxLength={1200} rows={2} value={planForm.support_needed} onChange={e=>setPlanForm(v=>({...v,support_needed:e.target.value}))}/></label>
     <button className="ps-primary" disabled={busy||!accessible.some(e=>String(e.id)===owner)}>Create plan</button>
    </form>
   </section>
   <section className="ps-panel"><h2>Development plans and milestones</h2>
    {plans.map(p=><article className="ps-appraisal" key={p.id}><div className="ps-record-heading"><div><strong>{p.employee_name} · {p.title}</strong><small>{p.focus_area} · Target {p.target_date}</small></div><span className="ps-chip">{p.status}</span></div><p><b>Outcome:</b> {p.success_outcome}</p>{p.support_needed&&<p><b>Support:</b> {p.support_needed}</p>}
     <div className="ps-review"><strong>Milestones · {p.completed_milestones}/{p.milestone_count} complete</strong>
      {(milestones[p.id]||[]).map(m=><div className="ps-record" key={m.id}><div><strong>{m.title}</strong><small>Due {m.due_on} · {m.completed_at?'Completed':'Open'}</small></div>{p.status==='Active'&&<button disabled={busy} onClick={()=>void change(()=>api(`/milestones/${m.id}/completion?complete=${!m.completed_at}`,'PATCH'),'Milestone updated.')}>{m.completed_at?'Reopen':'Mark complete'}</button>}</div>)}
      {p.status==='Active'&&<form onSubmit={e=>{e.preventDefault();const m=newMilestone[p.id];if(m)void change(()=>api(`/plans/${p.id}/milestones`,'POST',m),'Milestone added.')}}><div className="ps-fields"><label>New milestone<input required minLength={5} maxLength={180} value={newMilestone[p.id]?.title||''} onChange={e=>setNewMilestone(v=>({...v,[p.id]:{title:e.target.value,due_on:v[p.id]?.due_on||today()}}))}/></label><label>Due on<input type="date" required max={p.target_date} value={newMilestone[p.id]?.due_on||today()} onChange={e=>setNewMilestone(v=>({...v,[p.id]:{title:v[p.id]?.title||'',due_on:e.target.value}}))}/></label></div><button disabled={busy}>Add milestone</button></form>}
      {p.status!=='Archived'&&<div className="ps-links"><button type="button" disabled={busy} onClick={()=>void change(()=>api(`/plans/${p.id}`,'PATCH',{status:p.status==='Active'?'Completed':'Active'}), 'Plan updated.')}>{p.status==='Active'?'Complete plan':'Reopen plan'}</button><button type="button" disabled={busy} onClick={()=>void change(()=>api(`/plans/${p.id}`,'PATCH',{status:'Archived'}),'Plan archived.')}>Archive</button></div>}
     </div>
    </article>)}{!plans.length&&<p className="ps-empty">No development plans yet.</p>}
   </section>
  </>:<>
   <div className="ps-metrics"><article><small>Requests visible to me</small><strong>{feedback.length}</strong></article><article><small>Awaiting manager response</small><strong>{feedback.filter(f=>f.status==='Pending').length}</strong></article><article><small>Responded or acknowledged</small><strong>{feedback.filter(f=>f.status!=='Pending').length}</strong></article></div>
   <section className="ps-panel"><h2>Request feedback from my manager</h2><p>Your active reporting manager receives an in-app notification. Responses are written by a person, not generated ratings.</p><form onSubmit={e=>{e.preventDefault();void change(()=>api('/feedback','POST',question),'Feedback request submitted to your reporting manager.')}}>
     <label>Topic<input required minLength={5} maxLength={140} value={question.topic} onChange={e=>setQuestion(v=>({...v,topic:e.target.value}))} placeholder="Example: Presenting technical design decisions"/></label>
     <label>What feedback would help you?<textarea required minLength={10} maxLength={1500} rows={3} value={question.question} onChange={e=>setQuestion(v=>({...v,question:e.target.value}))}/></label>
     <button className="ps-primary" disabled={busy}>Request feedback</button>
    </form></section>
   <section className="ps-panel"><h2>Feedback conversations</h2>{feedback.map(f=><article className="ps-appraisal" key={f.id}>
    <div className="ps-record-heading"><div><strong>{f.employee_name} → {f.manager_name}: {f.topic}</strong><small>Requested {f.created_at.slice(0,10)}</small></div><span className="ps-chip">{f.status}</span></div>
    <p>{f.question}</p>{f.response&&<div className="ps-review"><strong>Manager response</strong><p>{f.response}</p>{f.employee_id===userId&&f.status==='Responded'&&<button className="ps-primary" disabled={busy} onClick={()=>void change(()=>api(`/feedback/${f.id}/acknowledge`,'POST'),'Feedback receipt acknowledged.')}>Acknowledge receipt</button>}</div>}
    {f.employee_id===userId&&f.status==='Pending'&&<button type="button" disabled={busy} onClick={()=>void change(()=>api(`/feedback/${f.id}/cancel`,'POST'),'Pending feedback request cancelled.')}>Cancel request</button>}
    {f.manager_id===userId&&f.status==='Pending'&&<form onSubmit={e=>{e.preventDefault();void change(()=>api(`/feedback/${f.id}/respond`,'POST',{response:replies[f.id]||''}),'Feedback delivered to the employee.')}}><label>Write your response<textarea required minLength={10} maxLength={2000} rows={3} value={replies[f.id]||''} onChange={e=>setReplies(v=>({...v,[f.id]:e.target.value}))}/></label><button className="ps-primary" disabled={busy}>Send manager feedback</button></form>}
   </article>)}{!feedback.length&&<p className="ps-empty">No feedback requests in your scope yet.</p>}</section>
  </>}
  <p className="ps-privacy"><ShieldCheck size={17}/> Development and feedback records are human-authored. Only the employee, authorized management and HR can access relevant records. Nothing here automatically affects salary, hiring or employment outcomes.</p>
 </section>;
}
