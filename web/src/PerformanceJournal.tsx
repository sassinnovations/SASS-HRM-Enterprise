import {apiUrl,hrmFetch} from './apiTransport';
import {useCallback,useEffect,useMemo,useState} from 'react';
import {BookOpenCheck,NotebookPen,ShieldCheck} from 'lucide-react';
import {useRefreshData} from './useRefreshData';
import './performance-suite.css';

type Evidence={id:number;employee_id:number;employee_name:string;title:string;details:string;category:string;occurred_on:string;visibility:'Private'|'Shared';archived:number};
type Checkin={id:number;goal_id:number;goal_title:string;employee_name:string;author_name:string;summary:string;blockers:string;next_step:string;created_at:string};
type Goal={id:number;employee_id:number;title:string;employee_name:string;progress:number};
type Props={page:'evidence'|'goaljournal';userId:number;role:string;navigate:(page:string)=>void};
const localToday=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`};
async function request<T>(endpoint:string,method='GET',data?:unknown):Promise<T>{
 const token=sessionStorage.getItem('sass_token');
 const res=await hrmFetch(apiUrl(endpoint),{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(data===undefined?{}:{body:JSON.stringify(data)})});
 let result:any={};try{result=await res.json()}catch{}
 if(!res.ok)throw new Error(typeof result?.detail==='string'?result.detail:`Request failed (HTTP ${res.status})`);
 return result as T;
}
export function PerformanceJournal({page,userId,navigate}:Props){
 const [evidence,setEvidence]=useState<Evidence[]>([]),[checkins,setCheckins]=useState<Checkin[]>([]),[goals,setGoals]=useState<Goal[]>([]);
 const [showArchived,setShowArchived]=useState(false),[category,setCategory]=useState('All'),[query,setQuery]=useState('');
 const [entry,setEntry]=useState({title:'',details:'',category:'Achievement',occurred_on:localToday(),visibility:'Private'});
 const [note,setNote]=useState({goal_id:'',summary:'',blockers:'',next_step:''});
 const [error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false);
 const load=useCallback(async()=>{try{setError('');if(page==='evidence'){
   setEvidence(await request<Evidence[]>(`/performance-journal/evidence?include_archived=${showArchived}`));
  }else{const [g,c]=await Promise.all([request<Goal[]>('/performance/goals'),request<Checkin[]>('/performance-journal/checkins')]);setGoals(g);setCheckins(c);setNote(v=>({...v,goal_id:v.goal_id||(g[0]?.id?String(g[0].id):'')}))}
 }catch(e){setError((e as Error).message)}},[page,showArchived]);
 useEffect(()=>{void load()},[load]);useRefreshData(load);
 const mutate=async(fn:()=>Promise<unknown>,message:string)=>{setBusy(true);setError('');setNotice('');try{await fn();await load();setNotice(message)}catch(e){setError((e as Error).message)}finally{setBusy(false)}};
 const visible=useMemo(()=>evidence.filter(e=>(category==='All'||e.category===category)&&(`${e.title} ${e.details} ${e.employee_name}`.toLowerCase().includes(query.toLowerCase()))),[evidence,category,query]);
 return <section className="ps-layout">
  <header className="ps-hero"><div className="ps-hero-icon">{page==='evidence'?<BookOpenCheck size={24}/>:<NotebookPen size={24}/>}</div><div><span>EMPLOYEE PERFORMANCE / EVIDENCE-LED DEVELOPMENT</span><h1>{page==='evidence'?'Performance evidence portfolio':'Goal check-in journal'}</h1><p>{page==='evidence'?'Keep a record of completed work and choose what to share with reviewers.':'Record regular progress conversations and next steps without altering goal scores.'}</p></div></header>
  <nav className="ps-links" aria-label="Performance pages">{([['performance','Goals'],['performancecycles','Review cycles'],['appraisals','Appraisals'],['checkins','1:1 meetings'],['growthplans','Development plans'],['feedbackrequests','Manager feedback'],['followups','Actions'],['reviewprogress','Review progress'],['evidence','Evidence portfolio'],['goaljournal','Goal journal']] as const).map(([key,label])=><button type="button" aria-current={page===key?'page':undefined} key={key} onClick={()=>navigate(key)}>{label}</button>)}</nav>
  {error&&<div className="ps-alert ps-error" role="alert">{error}</div>}{notice&&<div className="ps-alert ps-success" role="status">{notice}</div>}
  {page==='evidence'?<>
   <div className="ps-metrics"><article><small>Visible records</small><strong>{evidence.length}</strong></article><article><small>My records</small><strong>{evidence.filter(e=>e.employee_id===userId).length}</strong></article><article><small>Shared with reviewers</small><strong>{evidence.filter(e=>e.visibility==='Shared').length}</strong></article></div>
   <section className="ps-panel"><h2>Add evidence of your work</h2><p>New entries are private by default. You control whether a record is shared with authorized HR and your current reporting manager.</p>
    <form onSubmit={e=>{e.preventDefault();void mutate(async()=>{await request('/performance-journal/evidence','POST',entry);setEntry(v=>({...v,title:'',details:'',visibility:'Private'}))},'Evidence saved.')}}>
     <div className="ps-fields"><label>Category<select value={entry.category} onChange={e=>setEntry(v=>({...v,category:e.target.value}))}>{['Achievement','Project','Learning','Collaboration','Other'].map(k=><option key={k}>{k}</option>)}</select></label><label>Date<input type="date" required max={localToday()} value={entry.occurred_on} onChange={e=>setEntry(v=>({...v,occurred_on:e.target.value}))}/></label><label>Visibility<select value={entry.visibility} onChange={e=>setEntry(v=>({...v,visibility:e.target.value}))}><option>Private</option><option>Shared</option></select></label></div>
     <label>Title<input minLength={5} maxLength={160} required value={entry.title} onChange={e=>setEntry(v=>({...v,title:e.target.value}))}/></label>
     <label>What did you accomplish?<textarea required minLength={10} maxLength={1500} rows={3} value={entry.details} onChange={e=>setEntry(v=>({...v,details:e.target.value}))}/></label>
     <button className="ps-primary" disabled={busy}>Save evidence</button>
    </form></section>
   <section className="ps-panel"><div className="ps-record-heading"><h2>Evidence history</h2><div className="ps-links"><label>Category<select aria-label="Filter evidence category" value={category} onChange={e=>setCategory(e.target.value)}>{['All','Achievement','Project','Learning','Collaboration','Other'].map(k=><option key={k}>{k}</option>)}</select></label><label>Search<input aria-label="Search evidence" maxLength={100} value={query} onChange={e=>setQuery(e.target.value)}/></label><label><input type="checkbox" checked={showArchived} onChange={e=>setShowArchived(e.target.checked)}/> Include archived</label></div></div>
    {visible.map(x=><article className="ps-appraisal" key={x.id}><div className="ps-record-heading"><div><strong>{x.title}</strong><small>{x.employee_name} · {x.category} · {x.occurred_on}</small></div><span className="ps-chip">{x.archived?'Archived':x.visibility}</span></div><p>{x.details}</p>{x.employee_id===userId&&<div className="ps-links"><button type="button" disabled={busy} onClick={()=>void mutate(()=>request(`/performance-journal/evidence/${x.id}`,'PATCH',{visibility:x.visibility==='Private'?'Shared':'Private'}),'Visibility updated.')}>{x.visibility==='Private'?'Share with reviewers':'Make private'}</button><button type="button" disabled={busy} onClick={()=>void mutate(()=>request(`/performance-journal/evidence/${x.id}`,'PATCH',{archived:!Boolean(x.archived)}),x.archived?'Evidence restored.':'Evidence archived.')}>{x.archived?'Restore':'Archive'}</button></div>}</article>)}{!visible.length&&<p className="ps-empty">No evidence matches your filters.</p>}
   </section>
  </>:<>
   <div className="ps-metrics"><article><small>Visible goals</small><strong>{goals.length}</strong></article><article><small>Check-in notes</small><strong>{checkins.length}</strong></article><article><small>Goals with check-ins</small><strong>{new Set(checkins.map(x=>x.goal_id)).size}</strong></article></div>
   <section className="ps-panel"><h2>Record a goal check-in</h2><p>Entries are append-only and include the author and date. Use the existing Performance & goals page to update actual progress percentages.</p>
    <form onSubmit={e=>{e.preventDefault();void mutate(async()=>{await request('/performance-journal/checkins','POST',{...note,goal_id:Number(note.goal_id)});setNote(v=>({...v,summary:'',blockers:'',next_step:''}))},'Check-in recorded.')}}>
     <label>Goal<select required value={note.goal_id} onChange={e=>setNote(v=>({...v,goal_id:e.target.value}))}><option value="">Choose goal</option>{goals.map(g=><option key={g.id} value={g.id}>{g.employee_name}: {g.title} ({g.progress}%)</option>)}</select></label>
     <label>Progress and discussion<textarea required minLength={10} maxLength={1500} rows={3} value={note.summary} onChange={e=>setNote(v=>({...v,summary:e.target.value}))}/></label>
     <label>Blockers (optional)<textarea maxLength={1000} rows={2} value={note.blockers} onChange={e=>setNote(v=>({...v,blockers:e.target.value}))}/></label>
     <label>Next agreed step (optional)<textarea maxLength={1000} rows={2} value={note.next_step} onChange={e=>setNote(v=>({...v,next_step:e.target.value}))}/></label>
     <button className="ps-primary" disabled={busy||!note.goal_id}>Record check-in</button>
    </form></section>
   <section className="ps-panel"><h2>Check-in history</h2>{checkins.map(x=><article className="ps-appraisal" key={x.id}><div className="ps-record-heading"><div><strong>{x.goal_title}</strong><small>{x.employee_name} · Recorded by {x.author_name} · {x.created_at.slice(0,10)}</small></div><span className="ps-chip">Check-in</span></div><p>{x.summary}</p>{x.blockers&&<p><strong>Blockers:</strong> {x.blockers}</p>}{x.next_step&&<p><strong>Next step:</strong> {x.next_step}</p>}</article>)}{!checkins.length&&<p className="ps-empty">No check-in notes yet.</p>}</section>
  </>}
  <p className="ps-privacy"><ShieldCheck size={17}/> Your private evidence is accessible only to you. Shared evidence is limited to HR and your current reporting manager. Goal notes follow existing goal permissions. No automatic ratings, pay changes or employment decisions.</p>
 </section>
}
