import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import {useCallback, useEffect, useState} from 'react';
import {ArrowRight, Bookmark, CalendarDays, Check, Download, Filter, Search, ShieldCheck} from 'lucide-react';
import {pageUrl} from './pageRoutes';
import './self-service.css';

type Activity={id:number;kind:string;title:string;status:string;created_at:string;due_on:string};
type Result={items:Activity[];total:number;offset:number;limit:number;limited_to_recent:number};
const kinds=[['all','All activity'],['leave','Leave'],['helpdesk','Helpdesk'],['expenses','Expenses'],['offboarding','Offboarding'],['workmode','Work mode'],['requestdesk','Request Desk'],['corrections','Attendance corrections'],['tasks','HR tasks']];
const shortcutChoices=[['dashboard','Overview'],['calendar','My calendar'],['profile','My profile'],['inbox','Notifications'],['selfservice','My requests'],['leave','Leave'],['attendance','Attendance'],['timesheets','Timesheets'],['helpdesk','HR helpdesk'],['requestdesk','Request Desk'],['expenses','Expenses'],['onboarding','Onboarding'],['tasks','HR tasks'],['workmode','Work arrangements'],['training','Learning'],['settings','My settings']];
const KIND_PAGE:Record<string,string>={leave:'leave',helpdesk:'helpdesk',expenses:'expenses',offboarding:'offboarding',workmode:'workmode',requestdesk:'requestdesk',corrections:'corrections',tasks:'tasks'};
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
function token(){return sessionStorage.getItem('sass_token')||''}
async function call<T>(path:string,method='GET',payload?:unknown):Promise<T>{
 const response=await hrmFetch(API+path,{method,headers:{'Authorization':`Bearer ${token()}`,'Content-Type':'application/json'},...(payload===undefined?{}:{body:JSON.stringify(payload)})});
 const result=await response.json().catch(()=>({}));
 if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:`Request failed (${response.status})`);
 return result as T;
}
function displayDate(value:string){if(!value)return '—';const date=new Date(value.length===10?value+'T12:00:00':value);return Number.isNaN(date.getTime())?value:date.toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'});}
function statusClass(status:string){return ['Completed','Approved','Resolved','Closed','Fulfilled'].includes(status)?'good':['Rejected','Declined','Cancelled'].includes(status)?'muted':'open';}
export function SelfServiceHub({navigate}:{navigate:(page:string)=>void}){
 const [kind,setKind]=useState('all');const [status,setStatus]=useState('all');const [draft,setDraft]=useState('');const [search,setSearch]=useState('');const [offset,setOffset]=useState(0);
 const [data,setData]=useState<Result|null>(null);const [shortcuts,setShortcuts]=useState<string[]>([]);const [saved,setSaved]=useState<string[]>([]);
 const [loading,setLoading]=useState(false);const [saving,setSaving]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');
 const load=useCallback(async()=>{
  setLoading(true);setError('');try{
   const params=new URLSearchParams({kind,status,search,offset:String(offset),limit:'20'});
   const [activity,links]=await Promise.all([call<Result>(`/self-service/activity?${params}`),call<{pages:string[]}>('/self-service/shortcuts')]);
   setData(activity);setShortcuts(links.pages);setSaved(links.pages);
  }catch(e){setError((e as Error).message)}finally{setLoading(false)}
 },[kind,status,search,offset]);
 useEffect(()=>{void load()},[load]);
 useRefreshData(load);
 const toggle=(page:string)=>{setShortcuts(previous=>previous.includes(page)?previous.filter(p=>p!==page):previous.length<8?[...previous,page]:previous);};
 const save=async()=>{setSaving(true);setError('');setNotice('');try{
  const result=await call<{pages:string[]}>('/self-service/shortcuts','PUT',{pages:shortcuts});setSaved(result.pages);setShortcuts(result.pages);setNotice('Shortcuts saved to your employee account.');
 }catch(e){setError((e as Error).message)}finally{setSaving(false)}};
 const download=async()=>{setError('');try{
   const response=await hrmFetch(API+'/self-service/activity.csv',{headers:{Authorization:`Bearer ${token()}`}});
   if(!response.ok)throw new Error('Could not export your request history.');
   const blob=await response.blob();const url=URL.createObjectURL(blob);
   const anchor=document.createElement('a');anchor.href=url;anchor.download='sass-my-requests.csv';document.body.appendChild(anchor);anchor.click();anchor.remove();URL.revokeObjectURL(url);
  }catch(e){setError((e as Error).message)}};
 return <section className="ssh-page">
   <div className="ssh-heading"><div><span className="ssh-eyebrow">SASS HRM / EMPLOYEE SELF SERVICE</span><h1>My requests & shortcuts</h1><p>Your own workplace activity in one place, with quick access to your favorite modules.</p></div></div>
   <div className="ssh-privacy"><ShieldCheck size={18}/><span>Private to your signed-in account. Administrators also see only their own requests here. Open the original module to edit or approve records.</span></div>
   {error&&<div role="alert" className="ssh-error">{error}</div>}{notice&&<div role="status" className="ssh-notice">{notice}</div>}
   <section className="ssh-panel"><div className="ssh-panel-header"><div><h2>My request history</h2><p>Recent records across the main employee workflows.</p></div><button className="ssh-outline" onClick={()=>void download()}><Download size={16}/> Export my CSV</button></div>
    <form className="ssh-filterbar" onSubmit={e=>{e.preventDefault();setOffset(0);setSearch(draft.trim())}}>
     <label><span><Filter size={14}/> Category</span><select value={kind} onChange={e=>{setKind(e.target.value);setOffset(0)}}>{kinds.map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
     <label><span>Status</span><select value={status} onChange={e=>{setStatus(e.target.value);setOffset(0)}}><option value="all">All statuses</option><option value="active">Active</option><option value="completed">Completed or closed</option></select></label>
     <label className="ssh-search"><span>Search</span><div><Search size={16}/><input value={draft} maxLength={100} placeholder="Title or status" onChange={e=>setDraft(e.target.value)}/></div></label>
     <button className="ssh-primary" type="submit">Search</button>
    </form>
    <div className="ssh-results-count">{loading?'Loading records…':`${data?.total??0} matching records`} <small>Showing up to 250 recent records per category</small></div>
    <div className="ssh-list">{!loading&&(data?.items.length??0)===0?<div className="ssh-empty">No matching records. Try a different category or search.</div>:data?.items.map(item=><article className="ssh-item" key={`${item.kind}-${item.id}`}><div className="ssh-entry-icon"><CalendarDays size={18}/></div><div className="ssh-entry-copy"><strong>{item.title}</strong><span>{kinds.find(k=>k[0]===item.kind)?.[1]||item.kind} · Created {displayDate(item.created_at)} · Relevant date {displayDate(item.due_on)}</span></div><span className={`ssh-state ${statusClass(item.status)}`}>{item.status}</span><a href={pageUrl(KIND_PAGE[item.kind])} onClick={e=>{if(e.button!==0||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;e.preventDefault();navigate(KIND_PAGE[item.kind])}} aria-label={`Open ${item.kind} module`} className="ssh-open">Open <ArrowRight size={14}/></a></article>)}</div>
    <div className="ssh-pager"><button className="ssh-outline" disabled={loading||offset===0} onClick={()=>setOffset(Math.max(0,offset-20))}>Previous</button><span>{data?.total?`${offset+1}–${Math.min(offset+20,data.total)} of ${data.total}`:'No records'}</span><button className="ssh-outline" disabled={loading||!data||offset+20>=data.total} onClick={()=>setOffset(offset+20)}>Next</button></div>
   </section>
   <section className="ssh-panel"><div className="ssh-panel-header"><div><h2>My shortcuts</h2><p>Choose up to eight modules. Your selections are saved to your account and work after sign-in or refresh.</p></div><button className="ssh-primary" disabled={saving||JSON.stringify(shortcuts)===JSON.stringify(saved)} onClick={()=>void save()}><Bookmark size={15}/>{saving?'Saving…':'Save shortcuts'}</button></div>
    <div className="ssh-shortcuts-selected">{saved.length?saved.map(page=><a key={page} href={pageUrl(page)} onClick={e=>{if(e.button!==0||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;e.preventDefault();navigate(page)}}>{shortcutChoices.find(([code])=>code===page)?.[1]||page} <ArrowRight size={15}/></a>):<span>Nothing pinned yet. Select modules below and save.</span>}</div>
    <div className="ssh-shortcut-choices">{shortcutChoices.map(([key,label])=><button key={key} type="button" className={shortcuts.includes(key)?'selected':''} disabled={!shortcuts.includes(key)&&shortcuts.length>=8} onClick={()=>toggle(key)}>{shortcuts.includes(key)?<Check size={15}/>:<Bookmark size={15}/>} {label}</button>)}</div>
    <small className="ssh-helper">{shortcuts.length}/8 selected · Changes are visible only after you save.</small>
   </section>
 </section>;
}
