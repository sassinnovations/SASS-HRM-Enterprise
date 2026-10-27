import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import React, {useCallback,useEffect,useState} from 'react';
import {ArrowRightLeft,CheckCircle2,ClipboardCheck,History,ShieldCheck,SlidersHorizontal, Wrench} from 'lucide-react';
import './employee-services-v20.css';
type Item=Record<string,any>;
type Page='assets'|'documents'|'approvals'|'settings';
const BASE=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
async function api<T=any>(route:string,method='GET',data?:unknown):Promise<T>{
 const token=sessionStorage.getItem('sass_token');
 let response:Response;
 try {response=await hrmFetch(BASE+route,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(data===undefined?{}:{body:JSON.stringify(data)})});}
 catch {throw Error('Could not reach HRM API. Check the backend and MySQL connection.');}
 let value:any;try{value=await response.json()}catch{value={}};
 if(!response.ok)throw Error(value?.detail||`The request failed (HTTP ${response.status})`);
 return value as T;
}
function dateTime(v?:string){return v?new Date(v).toLocaleString():'—';}
function Notice({text,error=false}:{text:string;error?:boolean}){return <div role={error?'alert':'status'} className={`es-notice ${error?'error':'good'}`}>{text}</div>}
function Status({value}:{value?:string}){return <span className={`es-pill ${String(value||'').toLowerCase().replace(/ /g,'-')}`}>{value||'—'}</span>}

type EmployeeServiceProps={page:Page;role:string;userId:number;assets:Item[];documents:Item[];employees?:Item[];refreshCore:()=>void};

export function EmployeeServiceOperations(props: EmployeeServiceProps){
  const {page,role,assets,documents,refreshCore}=props;
 const admin=role==='admin';
 const [active,setActive]=useState<number|null>(null);
 const [action,setAction]=useState('Return');const[target,setTarget]=useState('');const[note,setNote]=useState('');
 const [decision,setDecision]=useState('Verified');const[expiry,setExpiry]=useState('');
 const [history,setHistory]=useState<Item[]>([]);const[loading,setLoading]=useState(false);
 const [busy,setBusy]=useState(false);const[message,setMessage]=useState('');const[error,setError]=useState('');
 const [summary,setSummary]=useState<Item|null>(null);
 const [activeStaff,setActiveStaff]=useState<Item[]>([]);
 const collection=page==='assets'?assets:documents;
 const selected=collection.find(r=>r.id===active);
 useEffect(()=>{if(page==='assets'){setAction(selected?.status==='Returned'?'Reassign':selected?.status==='Maintenance'?'Restore to service':'Return');setTarget('')}},[active,page,selected?.status]);
 const loadHistory=useCallback(async(id:number)=>{
  setLoading(true);setError('');
  try{setHistory(await api(`/`+(page==='assets'?`assets/${id}/lifecycle`:`documents/${id}/reviews`)))}
  catch(e){setError((e as Error).message);setHistory([])}finally{setLoading(false)}
 },[page]);
 useEffect(()=>{setActive(null);setHistory([]);setError('');setMessage('')},[page]);
 useEffect(()=>{if(active!==null){loadHistory(active)}},[active,loadHistory]);
 useEffect(()=>{if(admin&&page==='assets'){api<Item[]>('/admin/accounts').then(accounts=>setActiveStaff(accounts.filter(a=>Boolean(a.account_active)))).catch(()=>setActiveStaff([]))}},[admin,page]);
 useEffect(()=>{if(page==='approvals'&&admin){api('/admin/employee-services/summary').then(setSummary).catch(e=>setError(e.message))}},[page,admin]);
 useRefreshData(()=>{
   if(active!==null)void loadHistory(active);
   if(page==='approvals'&&admin)void api('/admin/employee-services/summary').then(setSummary).catch(e=>setError(e.message));
   if(page==='assets'&&admin)void api<Item[]>('/admin/accounts').then(accounts=>setActiveStaff(accounts.filter(a=>Boolean(a.account_active)))).catch(()=>setActiveStaff([]));
 });
 async function submit(e:React.FormEvent){e.preventDefault();if(!selected)return;
  setBusy(true);setError('');setMessage('');
  try{
   if(page==='assets'){
    await api(`/assets/${active}/lifecycle`,'POST',{action,new_employee_id:['Transfer','Reassign'].includes(action)?Number(target):null,note});
    setMessage('Asset custody updated and recorded in the audit trail.');
   }else{
    await api(`/documents/${active}/review`,'POST',{decision,note,expires_on:decision==='Verified'&&expiry?expiry:null});
    setMessage('Document metadata review recorded. The actual file is not verified by this action.');
   }
   setNote('');setExpiry('');refreshCore();await loadHistory(active!);
  }catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 if(page==='approvals')return admin?<section className="es-card"><div className="es-heading"><div><h3>Employee Services review queue</h3><p>Additional HR follow-ups alongside leave and attendance approvals.</p></div></div>
  {error&&<Notice text={error} error/>}<div className="es-metrics">{[['Documents awaiting review','documents_pending'],['Rejected document entries','documents_rejected'],['Assets under maintenance','maintenance_assets'],['Returned assets','returned_assets']].map(([label,key])=><div key={key}><strong>{summary?.[key]??'—'}</strong><span>{label}</span></div>)}</div><p className="es-small">HR can complete document reviews and asset handovers in their respective modules. This queue never auto-approves either workflow.</p></section>:null;
 if(page!=='assets'&&page!=='documents')return null;
 return <section className="es-card"><div className="es-heading"><div><h3>{page==='assets'?'Asset custody & lifecycle':'Document verification & expiry'}</h3><p>{page==='assets'?'Track equipment handovers, returns and servicing with an immutable event history.':'Review registered document metadata; no file content is uploaded or verified here.'}</p></div><History size={23}/></div>
 {error&&<Notice text={error} error/>}{message&&<Notice text={message}/>}
 {collection.length===0?<div className="es-empty">{page==='assets'?'No equipment has been assigned. HR can use Assign asset to register the first item.':'There are no registered documents yet. HR can register document metadata above.'}</div>:<div className="es-records" aria-label="Select record to inspect its history">{collection.map(item=><button key={item.id} className={active===item.id?'selected':''} onClick={()=>{setActive(item.id);setMessage('');setNote('')}}><strong>{page==='assets'?item.asset_name:item.title}</strong><small>{page==='assets'?item.serial_number:item.document_type} · {item.employee_name}</small><Status value={item.status}/></button>)}</div>}
 {selected&&<div className="es-detail"><div className="es-heading"><h4>{page==='assets'?'Equipment record':'Document record'}: {page==='assets'?selected.serial_number:selected.title}</h4><Status value={selected.status}/></div>
  {admin&&<form className="es-form" onSubmit={submit}><h4>Record an authorized {page==='assets'?'asset action':'HR metadata review'}</h4>
  <div className="es-fields">{page==='assets'?<><label>Action<select value={action} onChange={e=>setAction(e.target.value)}>{(selected.status==='Returned'?['Reassign']:selected.status==='Maintenance'?['Restore to service','Return']:['Return','Transfer','Send for repair']).map(a=><option key={a}>{a}</option>)}</select></label>{['Transfer','Reassign'].includes(action)&&<label>New custodian<select required value={target} onChange={e=>setTarget(e.target.value)}><option value="">Choose active employee</option>{activeStaff.filter(e=>e.id!==selected.employee_id).map(e=><option key={e.id} value={e.id}>{e.name} ({e.code})</option>)}</select></label>}</>:<><label>Review result<select value={decision} onChange={e=>setDecision(e.target.value)}>{['Verified','Rejected','Expired'].map(a=><option key={a}>{a}</option>)}</select></label>{decision==='Verified'&&<label>Expiry date (optional)<input type="date" value={expiry} onChange={e=>setExpiry(e.target.value)}/></label>}</>}
  <label className="es-full">{page==='assets'?'Internal handover / maintenance note':'Internal HR review note'}<textarea rows={2} maxLength={page==='assets'?350:500} value={note} onChange={e=>setNote(e.target.value)} placeholder={page==='documents'&&decision==='Rejected'?'Rejection reason (required)':'Optional internal note'} required={page==='documents'&&decision==='Rejected'}/></label></div>
  <button className="es-primary" disabled={busy}>{busy?'Saving…':page==='assets'?'Record asset action':'Save HR review'} <CheckCircle2 size={15}/></button>
  </form>}
  <div className="es-history"><div className="es-heading"><h4>Recorded activity</h4></div>{loading?<p>Loading history…</p>:history.length?history.map((event,i)=><div className="es-event" key={i}><span className="es-event-dot"/><div><strong>{event.event_type||event.decision}</strong><small>{dateTime(event.created_at||event.reviewed_at)}</small>{admin&&event.note&&<p>{event.note}</p>}{event.expires_on&&<p>Expiry: {event.expires_on}</p>}</div></div>):<p className="es-small">No recorded review or lifecycle events yet. Original records are preserved.</p>}</div>
 </div>}
 <div className="es-footnote"><ShieldCheck size={18}/> Employees see only their authorized records. HR decisions are tracked. File verification is metadata-only and is not a digital-signature or compliance certification.</div>
 </section>
}

export function WorkspacePreferences(){
 const [value,setValue]=useState({date_format:'DD MMM YYYY',density:'Comfortable',reduce_motion:false});
 const [busy,setBusy]=useState(false);const[error,setError]=useState('');const[message,setMessage]=useState('');
 const loadPreferences=()=>api<typeof value>('/me/preferences').then(v=>{setValue(v);document.documentElement.dataset.hrDensity=v.density.toLowerCase();document.documentElement.dataset.hrReduceMotion=String(v.reduce_motion);document.documentElement.dataset.hrDateFormat=v.date_format}).catch(e=>setError(e.message));
 useEffect(()=>{void loadPreferences()},[]);
 useRefreshData(loadPreferences);
 async function save(e:React.FormEvent){e.preventDefault();setBusy(true);setError('');setMessage('');try{const v=await api<typeof value>('/me/preferences','PUT',value);setValue(v);document.documentElement.dataset.hrDensity=v.density.toLowerCase();document.documentElement.dataset.hrReduceMotion=String(v.reduce_motion);document.documentElement.dataset.hrDateFormat=v.date_format;setMessage('Your preferences were saved to your employee account.')}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 return <section className="es-card"><div className="es-heading"><div><h3>Personal display preferences</h3><p>Saved to your own employee account, not shared with coworkers.</p></div><SlidersHorizontal size={23}/></div>{error&&<Notice text={error} error/>}{message&&<Notice text={message}/>}
 <form className="es-form" onSubmit={save}><div className="es-fields"><label>Display density<select value={value.density} onChange={e=>setValue(v=>({...v,density:e.target.value}))}><option>Comfortable</option><option>Compact</option></select></label><label>Preferred date format<select value={value.date_format} onChange={e=>setValue(v=>({...v,date_format:e.target.value}))}>{['DD MMM YYYY','YYYY-MM-DD','MM/DD/YYYY'].map(s=><option key={s}>{s}</option>)}</select></label><label className="es-checkbox"><input type="checkbox" checked={value.reduce_motion} onChange={e=>setValue(v=>({...v,reduce_motion:e.target.checked}))}/> Reduce interface motion</label></div><button className="es-primary" disabled={busy}>Save my preferences</button></form><div className="es-footnote">Date formats apply to dates using the shared application formatter; certain specialized payroll and form fields retain their legally required formats. Motion and layout density apply immediately.</div></section>
}

export function AICapabilities(){const [data,setData]=useState<any>(null);const load=()=>api('/ai/capabilities').then(setData).catch(()=>{});useEffect(()=>{void load()},[]);useRefreshData(load);return <div className="es-ai-capabilities"><span><ClipboardCheck size={16}/> Authorized HR data lookup: {data?.account_lookup?'Enabled':'Checking…'}</span><span><Wrench size={16}/> Optional LLM: {data?.llm_configured?'Configured':'Not configured'}</span><span><ArrowRightLeft size={16}/> HR write actions: Disabled</span></div>}
