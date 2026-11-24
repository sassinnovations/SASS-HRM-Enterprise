import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import {useCallback,useEffect,useMemo,useState} from 'react';
import {AlertTriangle,BellRing,CalendarClock,CheckCircle2,Send,ShieldCheck} from 'lucide-react';
import './workflow-reminders.css';
type Item={kind:'task'|'onboarding'|'helpdesk';id:number;title:string;employee_name:string;due_date:string;days_remaining:number;status:string;sent_today:boolean;page:string};
type Result={scope:'personal'|'organization';total:number;overdue_count:number;items:Item[];manual_delivery_only:boolean};
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
async function request<T>(path:string,method='GET',body?:unknown):Promise<T>{
 const token=sessionStorage.getItem('sass_token');
 const response=await hrmFetch(API+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});
 const json=await response.json().catch(()=>null);
 if(!response.ok)throw new Error(typeof json?.detail==='string'?json.detail:`Request failed (${response.status})`);
 return json as T;
}
export function WorkflowReminders({isHR,navigate}:{isHR:boolean;navigate:(page:string)=>void}){
 const [filter,setFilter]=useState<'all'|'overdue'|'upcoming'>('all');
 const [search,setSearch]=useState('');
 const [data,setData]=useState<Result|null>(null);
 const [loading,setLoading]=useState(false);
 const [sending,setSending]=useState(false);
 const [error,setError]=useState('');
 const [notice,setNotice]=useState('');
 const load=useCallback(async()=>{
  setLoading(true);setError('');
  try{setData(await request<Result>(`/workflow/reminders?status=${filter}&limit=500`))}
  catch(e){setError((e as Error).message)}finally{setLoading(false)}
 },[filter]);
 useEffect(()=>{void load()},[load]);
 useRefreshData(load);
 const visible=useMemo(()=>data?.items.filter(item=>[item.title,item.kind,item.employee_name].join(' ').toLowerCase().includes(search.trim().toLowerCase()))||[],[data,search]);
 const unsent=data?.items.filter(x=>!x.sent_today).length||0;
 const dispatch=async(item?:Item)=>{
  const question=item?`Send a reminder for ${item.title} to its assigned employee?`:'Send in-app deadline reminders to all eligible assigned employees?';
  if(!isHR||sending||!window.confirm(`${question} No emails or approvals will be sent.`))return;
  setSending(true);setError('');setNotice('');
  try{
   const options=item?{max_items:1,kind:item.kind,record_id:item.id}:{max_items:500};
   const out=await request<{sent:number;already_sent_today:number}>('/workflow/reminders/dispatch','POST',options);
   setNotice(`${out.sent} in-app reminder(s) delivered. ${out.already_sent_today} already sent today.`);
   await load();
  }catch(e){setError((e as Error).message)}finally{setSending(false)}
 };
 return <section className="rm-page" aria-busy={loading}>
  <header className="rm-header"><div><span className="rm-eyebrow">WORKSPACE / DEADLINES & FOLLOW-UPS</span><h1>Workflow reminders</h1><p>{isHR?'Review HR deadlines and explicitly send employees their in-app follow-ups.':'See your approaching and overdue HR assignments.'}</p></div><div className="rm-top-actions">{isHR&&<button className="rm-primary" onClick={()=>void dispatch()} disabled={sending||!unsent}><Send size={16}/>{sending?'Sending…':'Send reminders'}</button>}</div></header>
  <div className="rm-metrics"><article><CalendarClock size={20}/><span>Due soon & overdue</span><strong>{data?.total??'—'}</strong></article><article><AlertTriangle size={20}/><span>Overdue</span><strong>{data?.overdue_count??'—'}</strong></article><article><BellRing size={20}/><span>{isHR?'Not sent today':'Available categories'}</span><strong>{isHR?unsent:new Set(data?.items.map(x=>x.kind)||[]).size}</strong></article></div>
  <div className="rm-panel"><div className="rm-toolbar"><div className="rm-tabs">{(['all','overdue','upcoming'] as const).map(s=><button key={s} className={filter===s?'active':''} onClick={()=>setFilter(s)}>{s==='all'?'All':s==='overdue'?'Overdue':'Due soon'}</button>)}</div><input type="search" aria-label="Search workflow reminders" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search task or employee"/></div>
   {error&&<div className="rm-error" role="alert">{error}</div>}{notice&&<div className="rm-success" role="status"><CheckCircle2 size={16}/>{notice}</div>}
   <div className="rm-list">{visible.length?visible.map(x=><article className="rm-item" key={`${x.kind}-${x.id}`}><div className="rm-item-main"><strong>{x.title}</strong><small>{x.kind==='task'?'HR task':x.kind==='onboarding'?'Onboarding':'Helpdesk'} · {x.employee_name} · due {x.due_date}</small></div><span className={'rm-pill '+(x.days_remaining<0?'bad':'good')}>{x.days_remaining<0?`${-x.days_remaining} day(s) overdue`:x.days_remaining===0?'Due today':`Due in ${x.days_remaining} day(s)`}</span>{isHR&&<span className="rm-pill neutral">{x.sent_today?'Sent today':'Ready to send'}</span>}{isHR&&!x.sent_today&&<button className="rm-link" disabled={sending} onClick={()=>void dispatch(x)}><Send size={14}/> Send one</button>}<button className="rm-link" onClick={()=>navigate(x.page)}>Open module →</button></article>):<p className="rm-empty">No matching reminders. Deadlines appear after HR tasks, onboarding items or assigned tickets have due dates.</p>}</div>
  </div>
  <p className="rm-disclaimer"><ShieldCheck size={17}/> In-app reminders require an administrator to press Send. Sending is deduplicated per day, person and record. This page does not send email, approve requests or alter payroll.</p>
 </section>
}
