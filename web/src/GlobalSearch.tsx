import {hrmFetch} from './apiTransport';
import {FormEvent, useCallback, useEffect, useState} from 'react';
import {ArrowRight, Bookmark, Search, Trash2} from 'lucide-react';
import {useRefreshData} from './useRefreshData';
import './global-search.css';

type SearchRow={id:number;category:string;title:string;context:string;status:string;page:string};
type Saved={id:number;query:string;category:string;created_at:string};
type SearchPage={items:SearchRow[];total:number;offset:number;limit:number;max_per_category:number};
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
const CATEGORIES=[
 ['all','All records'],['people','People'],['tasks','HR tasks'],['leave','Leave'],
 ['helpdesk','HR helpdesk'],['expenses','Expenses'],['policies','Policies'],
 ['announcements','Announcements'],['recruitment','Recruitment'],['requests','Request Desk'],
] as const;
async function call<T>(path:string,method='GET',payload?:unknown):Promise<T>{
 const token=sessionStorage.getItem('sass_token');
 const response=await hrmFetch(API+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},
   ...(payload===undefined?{}:{body:JSON.stringify(payload)}),cache:'no-store'});
 if(!response.ok){const body=await response.json().catch(()=>null);throw Error(typeof body?.detail==='string'?body.detail:`Search request failed (HTTP ${response.status})`)}
 return response.json();
}
export function GlobalSearch({navigate,role}:{navigate:(page:string)=>void;role:string}){
 const [q,setQ]=useState('');const [category,setCategory]=useState('all');
 const [submitted,setSubmitted]=useState('');const [currentCategory,setCurrentCategory]=useState('all');
 const [page,setPage]=useState(0);const [results,setResults]=useState<SearchPage|null>(null);
 const [saved,setSaved]=useState<Saved[]>([]);const [busy,setBusy]=useState(false);
 const [message,setMessage]=useState('');const [error,setError]=useState('');
 const loadSaved=useCallback(async()=>{
  try{setSaved(await call<Saved[]>('/search/saved'))}catch(e){setError((e as Error).message)}
 },[]);
 const loadResults=useCallback(async()=>{
  if(!submitted)return;
  setBusy(true);setError('');
  try{
   const p=new URLSearchParams({q:submitted,category:currentCategory,offset:String(page*20),limit:'20'});
   setResults(await call<SearchPage>('/search/records?'+p.toString()));
  }catch(e){setError((e as Error).message);setResults(null)}finally{setBusy(false)}
 },[submitted,currentCategory,page]);
 useEffect(()=>{void loadSaved()},[loadSaved]);
 useEffect(()=>{void loadResults()},[loadResults]);
 useRefreshData(()=>Promise.all([loadSaved(),loadResults()]));
 function onSubmit(e:FormEvent){e.preventDefault();setMessage('');setError('');
  const term=q.trim();if(term.length<2){setError('Enter at least 2 characters to search');return}
  setPage(0);setSubmitted(term);setCurrentCategory(category);
 }
 function openSaved(item:Saved){setQ(item.query);setCategory(item.category);
  setPage(0);setSubmitted(item.query);setCurrentCategory(item.category);setMessage('');setError('')}
 async function save(){const term=q.trim();if(term.length<2){setError('Enter at least two characters');return}
  try{await call('/search/saved','POST',{query:term,category});await loadSaved();setMessage('Saved to your private searches');setError('')}
  catch(e){setError((e as Error).message)}
 }
 async function remove(id:number){try{await call('/search/saved/'+id,'DELETE');await loadSaved();setMessage('Saved search removed');setError('')}
  catch(e){setError((e as Error).message)}}
 const accessible=role==='employee'?CATEGORIES.filter(([id])=>id!=='recruitment'):CATEGORIES;
 return <section className="hr-search-page">
  <div className="hr-search-intro"><div className="hr-search-icon"><Search size={22}/></div><div>
    <span className="eyebrow">WORKSPACE / RECORD FINDER</span><h1>Global HR search</h1>
    <p>Find authorized HR records across modules, without opening each page separately. Results respect your account permissions.</p>
  </div></div>
  <form className="hr-search-form" onSubmit={onSubmit}>
   <label className="hr-search-field">Search records
    <input type="search" aria-label="Search HR records" autoComplete="off" maxLength={80} placeholder="Employee name, task title, request status…" value={q} onChange={e=>setQ(e.target.value)}/>
   </label>
   <label className="hr-search-filter">Category
    <select aria-label="Search category" value={category} onChange={e=>setCategory(e.target.value)}>{accessible.map(([key,label])=><option key={key} value={key}>{label}</option>)}</select>
   </label>
   <button type="submit" className="hr-search-primary" disabled={busy||q.trim().length<2}><Search size={16}/> Search</button>
   <button type="button" className="hr-search-secondary" disabled={saved.length>=8||q.trim().length<2} onClick={()=>void save()}><Bookmark size={16}/> Save search</button>
  </form>
  <div className="hr-search-saved"><h2>My saved searches <span>{saved.length}/8</span></h2>
   {saved.length?<div className="hr-search-chips">{saved.map(item=><span key={item.id} className="hr-search-chip"><button type="button" onClick={()=>openSaved(item)}>{item.query} <small>· {CATEGORIES.find(([k])=>k===item.category)?.[1]||item.category}</small></button><button type="button" aria-label={'Remove saved search '+item.query} title="Remove saved search" onClick={()=>void remove(item.id)}><Trash2 size={13}/></button></span>)}</div>:<p>No saved searches yet. Save frequent searches for faster access next time.</p>}
  </div>
  {error&&<p className="hr-search-error" role="alert">{error}</p>}
  {message&&<p className="hr-search-success" role="status">{message}</p>}
  <div className="hr-search-results"><div className="hr-search-results-header"><div><h2>Search results</h2><p>{busy?'Searching authorized records…':results?`${results.total} matching records${results.max_per_category?' · up to 60 recent matches per category':''}`:'Enter a search to find records you can access.'}</p></div></div>
   {busy&&<p role="status">Loading results…</p>}
   {!busy&&results&&(!results.items.length?<div className="hr-search-empty">No records match this search. Try another phrase or category.</div>:
    <div className="hr-search-list">{results.items.map(row=><button type="button" key={row.category+'-'+row.id} className="hr-search-result" onClick={()=>navigate(row.page)} title={'Open '+row.category+' module'}><span className="hr-search-category">{row.category}</span><span className="hr-search-detail"><strong>{row.title}</strong><small>{row.context}{row.status?' · '+row.status:''}</small><small>Record #{row.id} · Open module to review details</small></span><ArrowRight size={18}/></button>)}</div>)}
   {!busy&&results&&results.total>20&&<div className="hr-search-paging"><button disabled={page===0} onClick={()=>setPage(p=>p-1)}>Previous</button><span>Page {page+1} / {Math.ceil(results.total/20)}</span><button disabled={(page+1)*20>=results.total} onClick={()=>setPage(p=>p+1)}>Next</button></div>}
  </div>
  <p className="hr-search-privacy">Search includes summary fields only. Private messages, leave reasons, passwords, salary data and medical details are not searched or returned. Some modules open at their main list, rather than at a specific record.</p>
 </section>;
}
