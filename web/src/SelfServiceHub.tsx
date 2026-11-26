import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import {useCallback, useEffect, useRef, useState} from 'react';
import {ArrowDown, ArrowRight, ArrowUp, Bookmark, CalendarDays, Copy, Download, Filter, Pencil, Pin, Plus, Search, Settings2, ShieldCheck, Trash2} from 'lucide-react';
import {pageUrl} from './pageRoutes';
import './self-service.css';

type Activity={id:number;kind:string;title:string;status:string;created_at:string;due_on:string};
type Result={items:Activity[];total:number;offset:number;limit:number;limited_to_recent:number};
type HistoryStatus='all'|'active'|'completed';
type HistorySettings={default_kind:string;default_status:HistoryStatus;page_size:number};
type DraftInput={kind:string;title:string;notes:string};
type DraftStage='drafting'|'ready';
type RequestDraft=DraftInput & {id:number;created_at:string;updated_at:string;stage:DraftStage;pinned:boolean};
type DraftView='all'|DraftStage|'pinned';
type DraftSort='newest'|'oldest'|'title';
type DraftViewSettings={module_filter:string;draft_view:DraftView;sort_order:DraftSort};
const DEFAULT_DRAFT_VIEW:DraftViewSettings={module_filter:'all',draft_view:'all',sort_order:'newest'};
const kinds=[['all','All activity'],['leave','Leave'],['helpdesk','Helpdesk'],['expenses','Expenses'],['offboarding','Offboarding'],['workmode','Work mode'],['requestdesk','Request Desk'],['corrections','Attendance corrections'],['tasks','HR tasks']];
const statuses=[['all','All statuses'],['active','Active'],['completed','Completed or closed']];
const shortcutChoices=[['dashboard','Overview'],['calendar','My calendar'],['profile','My profile'],['inbox','Notifications'],['selfservice','My requests'],['leave','Leave'],['attendance','Attendance'],['timesheets','Timesheets'],['helpdesk','HR helpdesk'],['requestdesk','Request Desk'],['expenses','Expenses'],['onboarding','Onboarding'],['tasks','HR tasks'],['workmode','Work arrangements'],['training','Learning'],['settings','My settings']];
const KIND_PAGE:Record<string,string>={leave:'leave',helpdesk:'helpdesk',expenses:'expenses',offboarding:'offboarding',workmode:'workmode',requestdesk:'requestdesk',corrections:'corrections',tasks:'tasks'};
const DRAFT_KINDS=kinds.filter(([key])=>!['all','offboarding','tasks'].includes(key));
const DEFAULT_SETTINGS:HistorySettings={default_kind:'all',default_status:'all',page_size:20};
const NEW_DRAFT:DraftInput={kind:'leave',title:'',notes:''};
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';

function token(){return sessionStorage.getItem('sass_token')||''}

async function call<T>(path:string,method='GET',payload?:unknown,signal?:AbortSignal):Promise<T>{
 const response=await hrmFetch(API+path,{method,signal,headers:{'Authorization':`Bearer ${token()}`,'Content-Type':'application/json'},...(payload===undefined?{}:{body:JSON.stringify(payload)})});
 const result=await response.json().catch(()=>({}));
 if(!response.ok){
  const message=typeof result.detail==='string'?result.detail:Array.isArray(result.detail)&&result.detail.length?result.detail[0].msg:null;
  throw new Error(message||`Request failed (${response.status})`);
 }
 return result as T;
}

function displayDate(value:string){
 if(!value)return '—';
 const date=new Date(value.length===10?value+'T12:00:00':value);
 return Number.isNaN(date.getTime())?value:date.toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'});
}
function statusClass(status:string){return ['Completed','Approved','Resolved','Closed','Fulfilled'].includes(status)?'good':['Rejected','Declined','Cancelled'].includes(status)?'muted':'open';}
const kindLabel=(key:string)=>kinds.find(([code])=>code===key)?.[1]||key;
const shortcutLabel=(key:string)=>shortcutChoices.find(([code])=>code===key)?.[1]||key;

export function SelfServiceHub({navigate}:{navigate:(page:string)=>void}){
 const [kind,setKind]=useState('all');
 const [status,setStatus]=useState<HistoryStatus>('all');
 const [queryInput,setQueryInput]=useState('');
 const [search,setSearch]=useState('');
 const [offset,setOffset]=useState(0);
 const [data,setData]=useState<Result|null>(null);
 const [settings,setSettings]=useState(DEFAULT_SETTINGS);
 const [settingsInput,setSettingsInput]=useState(DEFAULT_SETTINGS);
 const [showSettings,setShowSettings]=useState(false);
 const [settingsReady,setSettingsReady]=useState(false);
 const [settingsError,setSettingsError]=useState('');
 const [settingsSaving,setSettingsSaving]=useState(false);
 const [shortcuts,setShortcuts]=useState<string[]>([]);
 const [savedShortcuts,setSavedShortcuts]=useState<string[]>([]);
 const [shortcutChoice,setShortcutChoice]=useState('');
 const [shortcutsLoaded,setShortcutsLoaded]=useState(false);
 const [shortcutSaving,setShortcutSaving]=useState(false);
 const [shortcutError,setShortcutError]=useState('');
 const [loading,setLoading]=useState(true);
 const [activityError,setActivityError]=useState('');
 const [notice,setNotice]=useState('');
 const activityRequest=useRef<AbortController|null>(null);

 const applySettings=useCallback((prefs:HistorySettings)=>{
  setSettings(prefs);setSettingsInput(prefs);setKind(prefs.default_kind);setStatus(prefs.default_status);setOffset(0);
 },[]);

 const loadPreferences=useCallback(async(signal?:AbortSignal)=>{
  setSettingsError('');
  try{
   const prefs=await call<HistorySettings>('/self-service/settings','GET',undefined,signal);
   if(!signal?.aborted)applySettings(prefs);
  }catch(e){if(!signal?.aborted)setSettingsError((e as Error).message)}
  finally{if(!signal?.aborted)setSettingsReady(true)}
 },[applySettings]);

 const loadShortcuts=useCallback(async(signal?:AbortSignal)=>{
  setShortcutError('');
  try{
   const links=await call<{pages:string[]}>('/self-service/shortcuts','GET',undefined,signal);
   if(!signal?.aborted){setShortcuts(links.pages);setSavedShortcuts(links.pages);setShortcutsLoaded(true);}
  }catch(e){if(!signal?.aborted)setShortcutError((e as Error).message)}
 },[]);

 useEffect(()=>{
  const controller=new AbortController();
  void loadPreferences(controller.signal);
  void loadShortcuts(controller.signal);
  return ()=>controller.abort();
 },[loadPreferences,loadShortcuts]);

 const loadActivity=useCallback(async()=>{
  if(!settingsReady)return;
  activityRequest.current?.abort();
  const controller=new AbortController();
  activityRequest.current=controller;
  setLoading(true);setActivityError('');
  try{
   const params=new URLSearchParams({kind,status,search,offset:String(offset),limit:String(settings.page_size)});
   const activity=await call<Result>(`/self-service/activity?${params}`,'GET',undefined,controller.signal);
   if(!controller.signal.aborted){
    if(offset&&offset>=activity.total){setOffset(Math.max(0,Math.floor((activity.total-1)/settings.page_size)*settings.page_size));return;}
    setData(activity);
   }
  }catch(e){if(!controller.signal.aborted){setData(null);setActivityError((e as Error).message);}}
  finally{if(!controller.signal.aborted)setLoading(false)}
 },[kind,status,search,offset,settings.page_size,settingsReady]);
 useEffect(()=>{void loadActivity();return ()=>activityRequest.current?.abort()},[loadActivity]);
 useRefreshData(async()=>{
  await Promise.all([loadActivity(),...(!shortcutsLoaded&&!shortcutSaving?[loadShortcuts()]:[])]);
 });

 const saveSettings=async(reset=false)=>{
  setSettingsSaving(true);setSettingsError('');setNotice('');
  try{
   const prefs=await call<HistorySettings>('/self-service/settings',reset?'DELETE':'PUT',reset?undefined:settingsInput);
   applySettings(prefs);setNotice(reset?'History settings reset.':'History settings saved.');
  }catch(e){setSettingsError((e as Error).message)}
  finally{setSettingsSaving(false)}
 };
 const historyDefaults=()=>{setKind(settings.default_kind);setStatus(settings.default_status);setQueryInput('');setSearch('');setOffset(0)};
 const moveShortcut=(index:number,direction:number)=>{
  setShortcuts(previous=>{
   if(index+direction<0||index+direction>=previous.length)return previous;
   const next=[...previous];
   [next[index],next[index+direction]]=[next[index+direction],next[index]];
   return next;
  });
 };
 const saveShortcuts=async()=>{
  setShortcutSaving(true);setShortcutError('');setNotice('');
  try{
   const result=await call<{pages:string[]}>('/self-service/shortcuts','PUT',{pages:shortcuts});
   setSavedShortcuts(result.pages);setShortcuts(result.pages);setNotice('Shortcuts saved to your account.');
  }catch(e){setShortcutError((e as Error).message)}
  finally{setShortcutSaving(false)}
 };
 const download=async()=>{
  setActivityError('');
  try{
   const response=await hrmFetch(API+'/self-service/activity.csv',{headers:{Authorization:`Bearer ${token()}`}});
   if(!response.ok)throw new Error('Could not export your request history.');
   const blob=await response.blob();const url=URL.createObjectURL(blob);
   const anchor=document.createElement('a');anchor.href=url;anchor.download='sass-my-requests.csv';
   document.body.appendChild(anchor);anchor.click();anchor.remove();
   window.setTimeout(()=>URL.revokeObjectURL(url),1000);
  }catch(e){setActivityError((e as Error).message)}
 };
 const link=(page:string,event:React.MouseEvent<HTMLAnchorElement>)=>{
  if(event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
  event.preventDefault();navigate(page);
 };
 const shortcutsChanged=JSON.stringify(shortcuts)!==JSON.stringify(savedShortcuts);
 const settingsChanged=JSON.stringify(settingsInput)!==JSON.stringify(settings);
 return <section className="ssh-page">
   <div className="ssh-heading"><div><span className="ssh-eyebrow">SASS HRM / EMPLOYEE SELF SERVICE</span><h1>My requests & shortcuts</h1><p>Prepare requests, track submissions and pin the modules you use most.</p></div>
    <button type="button" className="ssh-outline" aria-expanded={showSettings} aria-controls="ssh-history-settings" onClick={()=>setShowSettings(!showSettings)}><Settings2 size={16}/> History settings</button>
   </div>
   <div className="ssh-privacy"><ShieldCheck size={18}/><span>This workspace only shows your account’s requests and drafts. Drafts are never submitted automatically. Submitted records are managed in their original modules.</span></div>
   {notice&&<div role="status" className="ssh-notice">{notice}</div>}
   {(showSettings||settingsError)&&<section className="ssh-panel" id="ssh-history-settings" aria-labelledby="ssh-settings-title">
    <div className="ssh-panel-header"><div><h2 id="ssh-settings-title">History settings</h2><p>Choose the category, status and page size to use when you open My requests.</p></div></div>
    {settingsError&&<p role="alert" className="ssh-error">{settingsError}</p>}
    <form className="ssh-control-grid" onSubmit={e=>{e.preventDefault();void saveSettings();}}>
     <label>Default category<select disabled={!settingsReady||settingsSaving} value={settingsInput.default_kind} onChange={e=>setSettingsInput({...settingsInput,default_kind:e.target.value})}>{kinds.map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
     <label>Default status<select disabled={!settingsReady||settingsSaving} value={settingsInput.default_status} onChange={e=>setSettingsInput({...settingsInput,default_status:e.target.value as HistoryStatus})}>{statuses.map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
     <label>Rows per page<select disabled={!settingsReady||settingsSaving} value={settingsInput.page_size} onChange={e=>setSettingsInput({...settingsInput,page_size:Number(e.target.value)})}>{[10,20,50].map(size=><option key={size} value={size}>{size}</option>)}</select></label>
     <div className="ssh-actions"><button className="ssh-primary" type="submit" disabled={!settingsReady||settingsSaving||!settingsChanged}>Save settings</button><button type="button" className="ssh-outline" disabled={!settingsReady||settingsSaving} onClick={()=>void saveSettings(true)}>Restore defaults</button></div>
    </form>
   </section>}
   <RequestDrafts openPage={link}/>
   <section className="ssh-panel"><div className="ssh-panel-header"><div><h2>My request history</h2><p>Recent submitted records across employee workflows. The export includes all of these records, regardless of the current filters.</p></div><button type="button" className="ssh-outline" onClick={()=>void download()}><Download size={16}/> Export my CSV</button></div>
    {activityError&&<p role="alert" className="ssh-error">{activityError}</p>}
    <form className="ssh-filterbar" onSubmit={e=>{e.preventDefault();setOffset(0);setSearch(queryInput.trim())}}>
     <label><span><Filter size={14}/> Category</span><select value={kind} disabled={!settingsReady} onChange={e=>{setKind(e.target.value);setOffset(0)}}>{kinds.map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
     <label><span>Status</span><select value={status} disabled={!settingsReady} onChange={e=>{setStatus(e.target.value as HistoryStatus);setOffset(0)}}>{statuses.map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
     <label className="ssh-search"><span>Search</span><div><Search size={16}/><input value={queryInput} maxLength={100} placeholder="Title or status" onChange={e=>setQueryInput(e.target.value)}/></div></label>
     <div className="ssh-actions"><button className="ssh-primary" type="submit">Search</button><button className="ssh-outline" type="button" onClick={historyDefaults}>Reset filters</button></div>
    </form>
    <div className="ssh-results-count" aria-live="polite">{loading?'Loading records…':activityError?'Request history unavailable':`${data?.total??0} matching records`} <small>Up to 250 recent records per category</small></div>
    {!loading&&!activityError&&<div className="ssh-list">{!data?.items.length?<div className="ssh-empty">No matching records. Try a different category or search.</div>:data.items.map(item=><article className="ssh-item" key={`${item.kind}-${item.id}`}><div className="ssh-entry-icon"><CalendarDays size={18}/></div><div className="ssh-entry-copy"><strong>{item.title}</strong><span>{kindLabel(item.kind)} · Created {displayDate(item.created_at)} · Relevant date {displayDate(item.due_on)}</span></div><span className={`ssh-state ${statusClass(item.status)}`}>{item.status}</span><a href={pageUrl(KIND_PAGE[item.kind])} onClick={e=>link(KIND_PAGE[item.kind],e)} aria-label={`Open ${kindLabel(item.kind)} module`} className="ssh-open">Open <ArrowRight size={14}/></a></article>)}</div>}
    <div className="ssh-pager"><button type="button" className="ssh-outline" disabled={loading||offset===0} onClick={()=>setOffset(Math.max(0,offset-settings.page_size))}>Previous</button><span>{!loading&&data?.total?`${data.offset+1}–${Math.min(data.offset+data.limit,data.total)} of ${data.total}`:''}</span><button type="button" className="ssh-outline" disabled={loading||!data||offset+settings.page_size>=data.total} onClick={()=>setOffset(offset+settings.page_size)}>Next</button></div>
   </section>
   <section className="ssh-panel"><div className="ssh-panel-header"><div><h2>My shortcuts</h2><p>Add, replace, reorder or remove up to eight modules. Save to apply the changes to your account.</p></div><button type="button" className="ssh-primary" disabled={!shortcutsLoaded||shortcutSaving||!shortcutsChanged} onClick={()=>void saveShortcuts()}><Bookmark size={15}/>{shortcutSaving?'Saving…':'Save shortcuts'}</button></div>
    {shortcutError&&<p role="alert" className="ssh-error">{shortcutError} {!shortcutsLoaded&&<button type="button" className="ssh-outline" onClick={()=>void loadShortcuts()}>Retry</button>}</p>}
    <div className="ssh-shortcuts-selected">{savedShortcuts.length?savedShortcuts.map(page=><a key={page} href={pageUrl(page)} onClick={e=>link(page,e)}>{shortcutLabel(page)} <ArrowRight size={15}/></a>):<span>{shortcutsLoaded?'Nothing pinned yet.':'Loading shortcuts…'}</span>}</div>
    {shortcutsLoaded&&<>
     <form className="ssh-shortcut-add" onSubmit={e=>{e.preventDefault();if(shortcutChoice&&shortcuts.length<8&&!shortcuts.includes(shortcutChoice))setShortcuts([...shortcuts,shortcutChoice]);setShortcutChoice('');}}>
      <label>Module to pin<select value={shortcutChoice} disabled={shortcutSaving||shortcuts.length>=8} onChange={e=>setShortcutChoice(e.target.value)}><option value="">Choose a module</option>{shortcutChoices.filter(([key])=>!shortcuts.includes(key)).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
      <button type="submit" className="ssh-outline" disabled={!shortcutChoice||shortcutSaving||shortcuts.length>=8}><Plus size={15}/> Add shortcut</button>
     </form>
     {!!shortcuts.length&&<ol className="ssh-editor-list">{shortcuts.map((page,index)=><li key={page} className="ssh-item"><div className="ssh-entry-copy"><label className="ssh-shortcut-editor"><span>Shortcut {index+1}</span><select aria-label={`Replace ${shortcutLabel(page)} shortcut`} value={page} disabled={shortcutSaving} onChange={e=>{
       const next=e.target.value;
       setShortcuts(previous=>previous.includes(next)?previous:previous.map(key=>key===page?next:key));
       if(shortcutChoice===next)setShortcutChoice('');
      }}>{shortcutChoices.filter(([key])=>key===page||!shortcuts.includes(key)).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label></div><div className="ssh-actions">
      <button type="button" className="ssh-outline" aria-label={`Move ${shortcutLabel(page)} up`} disabled={shortcutSaving||index===0} onClick={()=>moveShortcut(index,-1)}><ArrowUp size={15}/></button>
      <button type="button" className="ssh-outline" aria-label={`Move ${shortcutLabel(page)} down`} disabled={shortcutSaving||index===shortcuts.length-1} onClick={()=>moveShortcut(index,1)}><ArrowDown size={15}/></button>
      <button type="button" className="ssh-outline" aria-label={`Remove ${shortcutLabel(page)} shortcut`} disabled={shortcutSaving} onClick={()=>setShortcuts(previous=>previous.filter(key=>key!==page))}><Trash2 size={15}/> Remove</button>
     </div></li>)}</ol>}
     <small className="ssh-helper">{shortcuts.length}/8 selected {shortcutsChanged?'· Unsaved changes':''}</small>
     {shortcutsChanged&&<button type="button" className="ssh-outline ssh-gap-top" disabled={shortcutSaving} onClick={()=>{setShortcuts(savedShortcuts);setShortcutChoice('')}}>Discard shortcut changes</button>}
    </>}
   </section>
 </section>;
}

function RequestDrafts({openPage}:{openPage:(page:string,event:React.MouseEvent<HTMLAnchorElement>)=>void}){
 const [rows,setRows]=useState<RequestDraft[]>([]);
 const [limit,setLimit]=useState(100);
 const [loading,setLoading]=useState(true);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const [notice,setNotice]=useState('');
 const [editing,setEditing]=useState<number|'new'|null>(null);
 const [input,setInput]=useState<DraftInput>(NEW_DRAFT);
 const [removing,setRemoving]=useState<RequestDraft|null>(null);
 const [loaded,setLoaded]=useState(false);
 const [query,setQuery]=useState('');
 const [moduleFilter,setModuleFilter]=useState('all');
 const [view,setView]=useState<DraftView>('all');
 const [sort,setSort]=useState<DraftSort>('newest');
 const [savedView,setSavedView]=useState(DEFAULT_DRAFT_VIEW);
 const [viewLoaded,setViewLoaded]=useState(false);
 const [viewError,setViewError]=useState('');
 const [viewSaving,setViewSaving]=useState(false);
 const draftRequest=useRef<AbortController|null>(null);
 const load=useCallback(async()=>{
  draftRequest.current?.abort();
  const controller=new AbortController();
  draftRequest.current=controller;
  setLoading(true);setError('');
  try{
   const result=await call<{items:RequestDraft[];limit:number}>('/self-service/drafts','GET',undefined,controller.signal);
   if(!controller.signal.aborted){setRows(result.items);setLimit(result.limit);setLoaded(true);}
  }catch(e){if(!controller.signal.aborted)setError((e as Error).message)}
  finally{if(!controller.signal.aborted)setLoading(false)}
 },[]);
 useEffect(()=>{void load();return ()=>draftRequest.current?.abort()},[load]);
 useRefreshData(()=>{if(!busy)void load()});
 const applyDraftView=useCallback((settings:DraftViewSettings)=>{
  setModuleFilter(settings.module_filter);setView(settings.draft_view);setSort(settings.sort_order);setQuery('');
 },[]);
 const loadDraftView=useCallback(async(signal?:AbortSignal)=>{
  setViewError('');
  try{
   const result=await call<DraftViewSettings>('/self-service/draft-view','GET',undefined,signal);
   if(!signal?.aborted){setSavedView(result);applyDraftView(result);setViewLoaded(true);}
  }catch(e){if(!signal?.aborted)setViewError((e as Error).message);}
 },[applyDraftView]);
 useEffect(()=>{
  const controller=new AbortController();
  void loadDraftView(controller.signal);
  return ()=>controller.abort();
 },[loadDraftView]);
 const saveDraftView=async(reset=false)=>{
  setViewSaving(true);setNotice('');setViewError('');
  try{
   const result=await call<DraftViewSettings>('/self-service/draft-view',reset?'DELETE':'PUT',
    reset?undefined:{module_filter:moduleFilter,draft_view:view,sort_order:sort});
   setSavedView(result);
   if(reset)applyDraftView(result);
   setNotice(reset?'Saved draft view reset.':'Default draft view saved.');
  }catch(e){setViewError((e as Error).message)}
  finally{setViewSaving(false)}
 };
 const open=(row:RequestDraft|null)=>{
  setInput(row?{kind:row.kind,title:row.title,notes:row.notes}:NEW_DRAFT);setEditing(row?.id??'new');setError('');setNotice('');
 };
 const searchText=query.trim().toLowerCase();
 const matchesDraft=(row:RequestDraft)=>
  (moduleFilter==='all'||row.kind===moduleFilter)
  &&(view==='all'||(view==='pinned'?row.pinned:row.stage===view))
  &&(!searchText||row.title.toLowerCase().includes(searchText)||row.notes.toLowerCase().includes(searchText));
 const save=async()=>{
  if(editing===null)return;
  setBusy(true);setError('');setNotice('');
  try{
   const isNew=editing==='new';
   const row=await call<RequestDraft>(isNew?'/self-service/drafts':`/self-service/drafts/${editing}`,isNew?'POST':'PATCH',input);
   draftRequest.current?.abort();setLoading(false);
   setRows(previous=>[row,...previous.filter(r=>r.id!==row.id)]);
   if(!matchesDraft(row))applyDraftView(DEFAULT_DRAFT_VIEW);
   setEditing(null);setNotice(isNew?'Private draft added.':'Draft updated.');
  }catch(e){setError((e as Error).message)}
  finally{setBusy(false)}
 };
 const duplicate=async(source:RequestDraft)=>{
  setBusy(true);setError('');setNotice('');
  try{
   const copy=await call<RequestDraft>(`/self-service/drafts/${source.id}/duplicate`,'POST');
   draftRequest.current?.abort();setLoading(false);
   setRows(previous=>[copy,...previous]);
   // Reveal the copy if needed without changing the account's saved default view.
   if(!matchesDraft(copy))applyDraftView(DEFAULT_DRAFT_VIEW);
   setNotice(`Draft duplicated as “${copy.title}”. Nothing was submitted.`);
  }catch(e){setError((e as Error).message)}
  finally{setBusy(false)}
 };
 const organize=async(row:RequestDraft,change:Partial<Pick<RequestDraft,'stage'|'pinned'>>)=>{
  setBusy(true);setError('');setNotice('');
  try{
   const next=await call<RequestDraft>(`/self-service/drafts/${row.id}/organization`,'PATCH',change);
   draftRequest.current?.abort();setLoading(false);
   setRows(previous=>previous.map(item=>item.id===row.id?next:item));
   setNotice(change.pinned!==undefined?(next.pinned?'Draft pinned.':'Draft unpinned.'):(next.stage==='ready'?'Draft marked ready. Nothing was submitted.':'Draft moved back to Drafting.'));
  }catch(e){setError((e as Error).message)}
  finally{setBusy(false)}
 };
 const remove=async()=>{
  if(!removing)return;
  setBusy(true);setError('');setNotice('');
  try{
   await call(`/self-service/drafts/${removing.id}`,'DELETE');
   draftRequest.current?.abort();setLoading(false);
   setRows(previous=>previous.filter(row=>row.id!==removing.id));setRemoving(null);setNotice('Draft deleted.');
  }catch(e){setError((e as Error).message)}
  finally{setBusy(false)}
 };
 const visible=rows.filter(matchesDraft).sort((a,b)=>Number(b.pinned)-Number(a.pinned)||
  (sort==='title'?a.title.localeCompare(b.title):sort==='oldest'?a.updated_at.localeCompare(b.updated_at):b.updated_at.localeCompare(a.updated_at))
  ||b.id-a.id
 );
 const readyCount=rows.filter(row=>row.stage==='ready').length;
 const pinnedCount=rows.filter(row=>row.pinned).length;
 const currentViewChanged=moduleFilter!==savedView.module_filter||view!==savedView.draft_view||sort!==savedView.sort_order;
 const hasCustomView=savedView.module_filter!=='all'||savedView.draft_view!=='all'||savedView.sort_order!=='newest';
 const resetDraftFilters=()=>applyDraftView(DEFAULT_DRAFT_VIEW);
 return <section className="ssh-panel">
  <div className="ssh-panel-header"><div><h2>Private request drafts</h2><p>Prepare a request, then open its module to review and submit it there. Keep passwords, payment details and medical information out of drafts.</p></div><button type="button" className="ssh-primary" disabled={busy||loading||!loaded||rows.length>=limit||editing!==null||!!removing} onClick={()=>open(null)}><Plus size={16}/> New draft</button></div>
  {error&&<p role="alert" className="ssh-error">{error} {!loaded&&<button type="button" className="ssh-outline" onClick={()=>void load()}>Retry</button>}</p>}
  {notice&&<p role="status" className="ssh-notice">{notice}</p>}
  {editing!==null&&<form className="ssh-control-grid ssh-draft-form" aria-label={editing==='new'?'New request draft':'Edit request draft'} onSubmit={e=>{e.preventDefault();void save();}}>
   <label>Request module<select value={input.kind} disabled={busy} onChange={e=>setInput({...input,kind:e.target.value})}>{DRAFT_KINDS.map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
   <label>Draft title<input autoFocus required minLength={2} maxLength={150} disabled={busy} value={input.title} onChange={e=>setInput({...input,title:e.target.value})}/></label>
   <label className="ssh-field-wide">Notes<textarea rows={4} maxLength={2000} disabled={busy} value={input.notes} onChange={e=>setInput({...input,notes:e.target.value})}/></label>
   <div className="ssh-actions"><button className="ssh-primary" type="submit" disabled={busy||input.title.trim().length<2}>{busy?'Saving…':'Save draft'}</button><button className="ssh-outline" type="button" disabled={busy} onClick={()=>setEditing(null)}>Cancel</button></div>
  </form>}
  {removing&&<div className="ssh-confirm" role="group" aria-label="Confirm draft deletion"><p>Delete the private draft “{removing.title}”? Submitted requests are not affected.</p><div className="ssh-actions"><button type="button" className="ssh-outline ssh-danger" disabled={busy} onClick={()=>void remove()}>Delete draft</button><button type="button" className="ssh-outline" disabled={busy} onClick={()=>setRemoving(null)}>Keep draft</button></div></div>}
  {loaded&&<div className="ssh-control-grid ssh-draft-filters" role="group" aria-label="Draft queue filters and settings">
   <label>Search drafts<input type="search" maxLength={120} placeholder="Search titles or notes" value={query} onChange={e=>setQuery(e.target.value)}/></label>
   <label>Draft module<select value={moduleFilter} disabled={viewSaving||(!viewLoaded&&!viewError)} onChange={e=>setModuleFilter(e.target.value)}><option value="all">All modules</option>{DRAFT_KINDS.map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
   <label>Draft view<select value={view} disabled={viewSaving||(!viewLoaded&&!viewError)} onChange={e=>setView(e.target.value as DraftView)}><option value="all">All drafts</option><option value="drafting">Drafting</option><option value="ready">Ready to submit</option><option value="pinned">Pinned drafts</option></select></label>
   <label>Sort drafts<select value={sort} disabled={viewSaving||(!viewLoaded&&!viewError)} onChange={e=>setSort(e.target.value as DraftSort)}><option value="newest">Newest updated</option><option value="oldest">Oldest updated</option><option value="title">Title A–Z</option></select></label>
   <div className="ssh-actions">
    <button type="button" className="ssh-outline" disabled={viewSaving||(!query&&moduleFilter==='all'&&view==='all'&&sort==='newest')} onClick={resetDraftFilters}>Reset draft filters</button>
    <button type="button" className="ssh-outline" disabled={!viewLoaded||viewSaving||!currentViewChanged} onClick={()=>void saveDraftView()}><Bookmark size={14}/> Save view as default</button>
    <button type="button" className="ssh-outline" disabled={!viewLoaded||viewSaving||(!currentViewChanged&&!query)} onClick={()=>applyDraftView(savedView)}>Use saved view</button>
    <button type="button" className="ssh-outline" disabled={!viewLoaded||viewSaving||!hasCustomView} onClick={()=>void saveDraftView(true)}>Reset saved draft view</button>
   </div>
   <small className="ssh-draft-view-help">The default saves the module, view and sort to your account. Search terms are not saved.</small>
   {viewError&&<p className="ssh-error ssh-field-wide" role="alert">{viewError} {!viewLoaded&&<button type="button" className="ssh-outline" onClick={()=>void loadDraftView()}>Retry draft view</button>}</p>}
  </div>}
  <div className="ssh-results-count" aria-live="polite">{loading?'Loading drafts…':loaded?`${visible.length} shown · ${rows.length}/${limit} drafts`:'Drafts unavailable'}{loaded&&rows.length>0&&<small>{readyCount} ready · {pinnedCount} pinned · Pinned drafts appear first</small>}</div>
  {loaded&&<div className="ssh-list">{!rows.length?<p className="ssh-empty">No drafts yet. Use New draft to prepare one.</p>:!visible.length?<p className="ssh-empty">No drafts match these filters.</p>:visible.map(row=><article className="ssh-item" key={row.id}>
   <div className="ssh-entry-icon">{row.pinned?<Pin size={17}/>:<Pencil size={17}/>}</div><div className="ssh-entry-copy"><strong>{row.title}</strong><span>{kindLabel(row.kind)} · Updated {displayDate(row.updated_at)}{row.pinned?' · Pinned':''}</span>{row.notes&&<details className="ssh-draft-notes"><summary>Show draft notes</summary><p>{row.notes}</p></details>}
    <label className="ssh-draft-stage"><span>Stage</span><select aria-label={`Draft stage: ${row.title}`} value={row.stage} disabled={busy||editing!==null||!!removing} onChange={e=>void organize(row,{stage:e.target.value as DraftStage})}><option value="drafting">Drafting</option><option value="ready">Ready to submit</option></select></label>
   </div>
   <div className="ssh-actions">
    <a className="ssh-open" href={pageUrl(KIND_PAGE[row.kind])} onClick={e=>openPage(KIND_PAGE[row.kind],e)}>Open module <ArrowRight size={14}/></a>
    <button type="button" className="ssh-outline" aria-label={`${row.pinned?'Unpin':'Pin'} draft: ${row.title}`} disabled={busy||editing!==null||!!removing} onClick={()=>void organize(row,{pinned:!row.pinned})}><Pin size={14}/> {row.pinned?'Unpin':'Pin'}</button>
    <button type="button" className="ssh-outline" aria-label={`Edit draft: ${row.title}`} disabled={busy||editing!==null||!!removing} onClick={()=>open(row)}><Pencil size={14}/> Edit</button>
    <button type="button" className="ssh-outline" aria-label={`Duplicate draft: ${row.title}`} disabled={busy||editing!==null||!!removing||rows.length>=limit} onClick={()=>void duplicate(row)}><Copy size={14}/> Duplicate</button>
    <button type="button" className="ssh-outline" aria-label={`Delete draft: ${row.title}`} disabled={busy||editing!==null||!!removing} onClick={()=>{setRemoving(row);setError('');setNotice('')}}><Trash2 size={14}/> Delete</button>
   </div>
  </article>)}</div>}
 </section>;
}
