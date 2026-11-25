import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import {useCallback, useEffect, useRef, useState} from 'react';
import {Bell, CheckCheck, Archive, RotateCcw, ShieldCheck, SlidersHorizontal, ListTodo, ClipboardCheck, Headset, AlertCircle, Save, ArrowRight, Search} from 'lucide-react';
import {InboxReminders,reminderViews,type ReminderView} from './InboxReminders';
import './workspace-control.css';

type Mode='workcenter'|'inbox'|'workflowsettings';
type Alert={id:number;title:string;body:string;is_read:number;is_archived:number;created_at:string};
type Settings={helpdesk_target_days:number;task_warning_days:number;onboarding_warning_days:number;organization_notice:string;updated_at:string};
type Summary={scope:'organization'|'personal';tasks:{active:number;overdue:number};onboarding:{pending:number;overdue:number};helpdesk:{open:number;high_priority:number};settings:Settings};
type Prefs={unread_only:boolean;compact_view:boolean};
type BulkAction='read'|'unread'|'archive'|'restore';
const bulkLabels:Record<BulkAction,string>={read:'Mark read',unread:'Mark unread',archive:'Archive',restore:'Restore'};
const bulkButtons:Record<BulkAction,string>={read:'Mark selected read',unread:'Mark selected unread',archive:'Archive selected',restore:'Restore selected'};
const bulkPast:Record<BulkAction,string>={read:'marked read',unread:'marked unread',archive:'archived',restore:'restored'};
const defaultPrefs:Prefs={unread_only:false,compact_view:false};
type DisplayDefaults={notification_order:'newest'|'oldest';notification_page_size:10|25|50;reminder_view:ReminderView};
const displayDefaults:DisplayDefaults={notification_order:'newest',notification_page_size:25,reminder_view:'open'};
const displayPath='/workspace/inbox/display-defaults';
const defaults:Settings={helpdesk_target_days:3,task_warning_days:2,onboarding_warning_days:3,organization_notice:'',updated_at:''};
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
async function api<T>(path:string,method='GET',body?:unknown):Promise<T>{
 const token=sessionStorage.getItem('sass_token');
 const response=await hrmFetch(API+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});
 let result:any=null;try{result=await response.json()}catch{}
 if(!response.ok)throw new Error(typeof result?.detail==='string'?result.detail:`Request failed (${response.status})`);
 return result as T;
}
const dateFmt=(v:string)=>{const d=new Date(v);return Number.isNaN(d.valueOf())?v:d.toLocaleString('en-IN',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'})};
function Metric({label,value,sub}:{label:string;value:number;sub:string}){return <div className="wc-metric"><span>{label}</span><strong>{value}</strong><small>{sub}</small></div>}
export function WorkspaceControl({mode,isHR,navigate,onInboxChanged}:{mode:Mode;isHR:boolean;navigate:(page:string)=>void;onInboxChanged?:()=>void}){
 const [summary,setSummary]=useState<Summary|null>(null);
 const [settings,setSettings]=useState<Settings>(defaults);
 const [alerts,setAlerts]=useState<Alert[]>([]);
 const [unreadCount,setUnreadCount]=useState(0);
 const [filter,setFilter]=useState<'all'|'unread'|'archived'>('all');
 const [prefs,setPrefs]=useState<Prefs>(defaultPrefs);
 const [display,setDisplay]=useState<DisplayDefaults>(displayDefaults);
 const [displayDraft,setDisplayDraft]=useState<DisplayDefaults>(displayDefaults);
 const [displayReady,setDisplayReady]=useState(false);
 const [displayError,setDisplayError]=useState('');
 const [prefsReady,setPrefsReady]=useState(false);
 const [searchInput,setSearchInput]=useState('');
 const [search,setSearch]=useState('');
 const [order,setOrder]=useState<'newest'|'oldest'>('newest');
 const [page,setPage]=useState(0);
 const [hasMore,setHasMore]=useState(false);
 const [bulkMode,setBulkMode]=useState(false);
 const [selected,setSelected]=useState<number[]>([]);
 const [pendingBulk,setPendingBulk]=useState<BulkAction|null>(null);
 const [loading,setLoading]=useState(false);const [saving,setSaving]=useState(false);
 const [error,setError]=useState('');const [notice,setNotice]=useState('');
 const requestNumber=useRef(0);
 const clearSelection=()=>{setSelected([]);setPendingBulk(null)};
 const fetchAll=useCallback(async()=>{
  if(mode==='inbox'&&!prefsReady)return;
  const request=++requestNumber.current;
  setLoading(true);setError('');
  try{
   if(mode==='inbox'){
    const size=display.notification_page_size;
    const query=new URLSearchParams({filter,limit:String(size),offset:String(page*size),q:search,order});
    const inbox=await api<{items:Alert[];unread_count:number;has_more:boolean}>(`/workspace/inbox?${query}`);
    if(request!==requestNumber.current)return;
    if(inbox.items.length===0&&page>0){setSelected([]);setPendingBulk(null);setPage(page-1);return}
    setAlerts(inbox.items);setUnreadCount(inbox.unread_count);setHasMore(inbox.has_more);
   }else{
    const data=await api<Summary>('/workspace/overview');if(request===requestNumber.current){setSummary(data);setSettings(data.settings)}
   }
  }catch(e){if(request===requestNumber.current)setError((e as Error).message)}finally{if(request===requestNumber.current)setLoading(false)}
 },[mode,filter,page,search,order,prefsReady,display.notification_page_size]);
 useEffect(()=>{void fetchAll();return()=>{requestNumber.current++}},[fetchAll]);
 useRefreshData(fetchAll);
 const visibleSelection=selected.filter(id=>alerts.some(item=>item.id===id));
 useEffect(()=>{
  if(mode!=='inbox'){setPrefsReady(false);setDisplayReady(false);return}
  let active=true;
  void Promise.allSettled([api<Prefs>('/workspace/inbox/preferences'),api<DisplayDefaults>(displayPath)]).then(([base,extended])=>{
   if(!active)return;
   const p=base.status==='fulfilled'?base.value:defaultPrefs;
   const d=extended.status==='fulfilled'?extended.value:displayDefaults;
   setPrefs(p);setFilter(p.unread_only?'unread':'all');setPage(0);
   setDisplay(d);setDisplayDraft(d);setOrder(d.notification_order);setDisplayReady(extended.status==='fulfilled');
   if(extended.status==='rejected')setDisplayError('Saved display defaults could not be loaded. Refresh the page to try again.');
   setPrefsReady(true);
  });
  return()=>{active=false};
 },[mode]);
 const run=async(callback:()=>Promise<unknown>,message:string|(()=>string),systemNotificationChanged=false)=>{
  setSaving(true);setError('');setNotice('');
  try{await callback();if(systemNotificationChanged){clearSelection();onInboxChanged?.()}setNotice(typeof message==='string'?message:message());await fetchAll()}
  catch(e){setError((e as Error).message)}finally{setSaving(false)}
 };
 const confirmBulk=()=>{
  if(!pendingBulk||saving||loading||!visibleSelection.length||visibleSelection.length!==selected.length)return;
  const action=pendingBulk;
  let updated=0;
  return run(async()=>{
   const result=await api<{selected:number;updated:number}>('/workspace/inbox/bulk','POST',{action,notification_ids:visibleSelection});
   updated=result.updated;
  },()=>`${updated} of ${visibleSelection.length} selected notifications ${bulkPast[action]}.`,true);
 };
 const savePrefs=(next:Prefs)=>{
  const previous=prefs;
  setPrefs(next);
  return run(async()=>{
   try{setPrefs(await api<Prefs>('/workspace/inbox/preferences','PUT',next))}
   catch(e){setPrefs(previous);throw e}
  },'Inbox preferences saved.');
 };
 const saveDisplay=async(reset=false)=>{
  setSaving(true);setDisplayError('');setNotice('');
  try{
   const saved=await api<DisplayDefaults>(displayPath,reset?'DELETE':'PUT',reset?undefined:displayDraft);
   setDisplay(saved);setDisplayDraft(saved);
   setOrder(saved.notification_order);setPage(0);clearSelection();
   setNotice(reset?'Display defaults reset.':'Display defaults saved.');
  }catch(e){setDisplayError((e as Error).message)}finally{setSaving(false)}
 };
 const heading=mode==='inbox'?'Notification inbox':mode==='workflowsettings'?'Workflow settings':'My action center';
 const subtitle=mode==='inbox'?'Manage important HR updates in your own account.':mode==='workflowsettings'?'Organization-wide guidance and response target settings, restricted to HR administrators.':'A focused summary of HR tasks, onboarding and service cases in your permitted view.';
 return <section className="wc-page" aria-busy={loading}>
  <div className="wc-header"><div><span className="wc-eyebrow">SASS HRM / WORKSPACE OPERATIONS</span><h1>{heading}</h1><p>{subtitle}</p></div></div>
  {error&&<div role="alert" className="wc-error"><AlertCircle size={17}/>{error}</div>}
  {notice&&<div role="status" className="wc-success"><CheckCheck size={17}/>{notice}</div>}
  {mode==='workcenter'&&<>
   {summary?.settings.organization_notice&&<div className="wc-announcement"><Bell size={19}/><span>{summary.settings.organization_notice}</span></div>}
   <div className="wc-metrics"><Metric label="Active HR tasks" value={summary?.tasks.active??0} sub={`${summary?.tasks.overdue??0} past due`}/><Metric label="Onboarding pending" value={summary?.onboarding.pending??0} sub={`${summary?.onboarding.overdue??0} past due`}/><Metric label="Open helpdesk cases" value={summary?.helpdesk.open??0} sub={`${summary?.helpdesk.high_priority??0} high priority`}/></div>
   <div className="wc-columns"><div className="wc-panel"><h3>Open a workflow</h3><p>Review and update records in the existing HRM modules.</p>
    <div className="wc-actions"><button onClick={()=>navigate('tasks')}><ListTodo/><span><strong>HR tasks</strong><small>Assignments, due dates and comments</small></span><ArrowRight/></button><button onClick={()=>navigate('onboarding')}><ClipboardCheck/><span><strong>Onboarding</strong><small>New-joiner checklists and templates</small></span><ArrowRight/></button><button onClick={()=>navigate('helpdesk')}><Headset/><span><strong>HR helpdesk</strong><small>Support tickets and conversations</small></span><ArrowRight/></button></div>
   </div><div className="wc-panel"><h3>Response guidance</h3><p>Current organizational targets for the workforce.</p><div className="wc-detail"><span>Helpdesk response target</span><strong>{summary?.settings.helpdesk_target_days??3} days</strong></div><div className="wc-detail"><span>Task warning window</span><strong>{summary?.settings.task_warning_days??2} days</strong></div><div className="wc-detail"><span>Onboarding warning window</span><strong>{summary?.settings.onboarding_warning_days??3} days</strong></div><p className="wc-help">These are guidance settings, not automatic approvals, SLA timers or notifications.</p>{isHR&&<button className="wc-primary" onClick={()=>navigate('workflowsettings')}><SlidersHorizontal size={15}/> Configure workflow settings</button>}</div></div>
  </>}
  {mode==='inbox'&&<>
    <div className="wc-panel">
     <h3>HR notifications</h3><p>Review updates from HRM. Read, archive, or restore them without altering the original messages.</p>
     <div className="wc-toolbar"><div className="wc-tabs" aria-label="Notification views">{(['all','unread','archived'] as const).map(kind=><button key={kind} className={filter===kind?'active':''} aria-pressed={filter===kind} disabled={saving||!prefsReady} onClick={()=>{setFilter(kind);setPage(0);clearSelection()}}>{kind==='all'?'All':kind==='unread'?'Unread':'Archived'}</button>)}</div>
     <span className="wc-unread">{unreadCount} unread</span><button className="wc-outline" disabled={loading||saving||bulkMode||unreadCount===0} onClick={()=>run(()=>api('/workspace/inbox/read-all','POST'),'All active notifications marked read.',true)}><CheckCheck size={16}/> Mark all read</button></div>
     <details className="wc-inbox-settings"><summary>Inbox settings</summary><p>Choose how your inbox opens. Preferences are saved to your account.</p>
      <div className="wc-pref-row"><label><input type="checkbox" checked={prefs.unread_only} onChange={e=>void savePrefs({...prefs,unread_only:e.target.checked})} disabled={saving||!prefsReady}/> Default to unread-only inbox</label><label><input type="checkbox" checked={prefs.compact_view} onChange={e=>void savePrefs({...prefs,compact_view:e.target.checked})} disabled={saving||!prefsReady}/> Compact inbox view</label></div>
      <button type="button" className="wc-outline" disabled={saving||!prefsReady||(!prefs.unread_only&&!prefs.compact_view)} onClick={()=>void savePrefs(defaultPrefs)}>Reset preferences</button>
      <form className="wc-display-settings" onSubmit={e=>{e.preventDefault();void saveDisplay()}}>
       <h4>Display defaults</h4>
       {displayError&&<div className="wc-error" role="alert">{displayError}</div>}
       <div className="wc-inbox-search">
        <label className="wc-field">Default notification sort<select disabled={saving||!displayReady} value={displayDraft.notification_order} onChange={e=>setDisplayDraft({...displayDraft,notification_order:e.target.value==='oldest'?'oldest':'newest'})}><option value="newest">Newest first</option><option value="oldest">Oldest first</option></select></label>
        <label className="wc-field">Notifications per page<select disabled={saving||!displayReady} value={displayDraft.notification_page_size} onChange={e=>setDisplayDraft({...displayDraft,notification_page_size:Number(e.target.value) as DisplayDefaults['notification_page_size']})}>{[10,25,50].map(size=><option key={size} value={size}>{size}</option>)}</select></label>
        <label className="wc-field">Default reminder view<select disabled={saving||!displayReady} value={displayDraft.reminder_view} onChange={e=>setDisplayDraft({...displayDraft,reminder_view:e.target.value as ReminderView})}>{Object.entries(reminderViews).map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></label>
       </div>
       <div className="wc-alert-actions"><button type="submit" className="wc-primary" disabled={saving||!displayReady}><Save size={15}/> Save display defaults</button><button type="button" className="wc-outline" disabled={saving||!displayReady} onClick={()=>void saveDisplay(true)}>Reset display defaults</button></div>
      </form>
     </details>
     <form className="wc-inbox-search" onSubmit={e=>{e.preventDefault();setSearch(searchInput.trim());setPage(0);clearSelection()}}>
      <label className="wc-field">Find a notification<input type="search" maxLength={100} placeholder="Search title or message" value={searchInput} disabled={saving} onChange={e=>setSearchInput(e.target.value)}/></label>
      <button className="wc-outline" type="submit" disabled={saving||!prefsReady}><Search size={15}/> Search</button>
      {(search||searchInput)&&<button className="wc-outline" type="button" disabled={saving} onClick={()=>{setSearch('');setSearchInput('');setPage(0);clearSelection()}}>Clear search</button>}
      <label className="wc-field">Sort by<select aria-label="Sort by" value={order} disabled={saving} onChange={e=>{setOrder(e.target.value==='oldest'?'oldest':'newest');setPage(0);clearSelection()}}><option value="newest">Newest first</option><option value="oldest">Oldest first</option></select></label>
     </form>
     <div className="wc-toolbar wc-bulk-bar">
      <button type="button" className="wc-outline" aria-pressed={bulkMode} disabled={saving||(!alerts.length&&!bulkMode)} onClick={()=>{setBulkMode(!bulkMode);clearSelection()}}>{bulkMode?'Exit selection':'Select notifications'}</button>
      {bulkMode&&<>
       <span role="status">{visibleSelection.length} selected on this page</span>
       {!pendingBulk&&<>
        <button type="button" className="wc-outline" disabled={saving||loading||!alerts.length||visibleSelection.length===alerts.length} onClick={()=>setSelected(alerts.map(item=>item.id))}>Select this page</button>
        <button type="button" className="wc-outline" disabled={saving||!selected.length} onClick={clearSelection}>Clear selection</button>
        {(filter==='archived'?['restore'] as const:['read','unread','archive'] as const).map(action=><button key={action} type="button" className="wc-outline" disabled={saving||loading||!visibleSelection.length} onClick={()=>{setSelected(visibleSelection);setPendingBulk(action)}}>{bulkButtons[action]}</button>)}
       </>}
       {pendingBulk&&<div className="wc-bulk-confirm" role="group" aria-label="Confirm bulk notification action">
        <strong>{pendingBulk==='read'||pendingBulk==='unread'?'Mark':bulkLabels[pendingBulk]} {selected.length} selected {selected.length===1?'notification':'notifications'}{pendingBulk==='read'||pendingBulk==='unread'?' as '+pendingBulk:''}?</strong>
        {visibleSelection.length!==selected.length&&<span>The page changed. Cancel and select again.</span>}
        <button type="button" className="wc-primary" disabled={saving||loading||!visibleSelection.length||visibleSelection.length!==selected.length} onClick={()=>void confirmBulk()}>Confirm {bulkLabels[pendingBulk].toLowerCase()}</button>
        <button type="button" className="wc-outline" disabled={saving} onClick={()=>setPendingBulk(null)}>Cancel bulk action</button>
       </div>}
      </>}
     </div>
     <div className={`wc-alerts ${prefs.compact_view?'compact':''}`}>{alerts.length?alerts.map(item=><article key={item.id} className={`wc-alert ${item.is_read?'read':''} ${selected.includes(item.id)?'wc-alert-selected':''}`}><span className="wc-alert-icon">{bulkMode?<input className="wc-alert-checkbox" type="checkbox" aria-label={`Select notification: ${item.title}`} checked={selected.includes(item.id)} disabled={saving||loading||!!pendingBulk} onChange={e=>setSelected(e.target.checked?[...visibleSelection,item.id]:visibleSelection.filter(id=>id!==item.id))}/>:<Bell size={17} aria-hidden/>}</span><div><strong>{item.title}</strong><p>{item.body}</p><small>{item.is_read?'Read':'Unread'} · {dateFmt(item.created_at)}</small></div>
      {!bulkMode&&<div className="wc-alert-actions">{!item.is_archived&&<button className="wc-outline" disabled={saving||loading} onClick={()=>run(()=>item.is_read?api(`/workspace/inbox/${item.id}/unread`,'POST'):api(`/notifications/${item.id}/read`,'PATCH'),item.is_read?'Notification marked as unread.':'Notification marked as read.',true)}>{item.is_read?'Mark unread':'Mark read'}</button>}
      <button className="wc-outline" disabled={saving||loading} onClick={()=>run(()=>api(`/workspace/inbox/${item.id}/${item.is_archived?'restore':'archive'}`,'POST'),item.is_archived?'Notification restored.':'Notification archived.',true)}>{item.is_archived?<RotateCcw size={15}/>:<Archive size={15}/>} {item.is_archived?'Restore':'Archive'}</button></div>}</article>):<div className="wc-empty">{loading||!prefsReady?'Loading notifications…':search?'No notifications match your search.':'No notifications in this view.'}</div>}</div>
     {(page>0||hasMore)&&<div className="wc-alert-actions wc-pagination"><button className="wc-outline" disabled={saving||loading||page===0} onClick={()=>{setPage(page-1);clearSelection()}}>Previous notifications</button><small>Page {page+1}</small><button className="wc-outline" disabled={saving||loading||!hasMore} onClick={()=>{setPage(page+1);clearSelection()}}>Next notifications</button></div>}
    </div>
    {prefsReady&&<InboxReminders api={api} initialView={display.reminder_view}/>}
  </>}
  {mode==='workflowsettings'&&isHR&&<div className="wc-columns settings"><form className="wc-panel" onSubmit={e=>{e.preventDefault();void run(()=>api('/workspace/settings','PUT',settings),'Organization workflow settings saved.')}}><h3>Operational configuration</h3><p>Set human-reviewed guidance for deadlines; these values do not automatically close or escalate cases.</p>
    <label className="wc-field">Helpdesk response target (days)<input type="number" min={1} max={30} required value={settings.helpdesk_target_days} onChange={e=>setSettings(v=>({...v,helpdesk_target_days:Number(e.target.value)}))}/></label>
    <label className="wc-field">Task warning window (days)<input type="number" min={0} max={30} required value={settings.task_warning_days} onChange={e=>setSettings(v=>({...v,task_warning_days:Number(e.target.value)}))}/></label>
    <label className="wc-field">Onboarding warning window (days)<input type="number" min={0} max={30} required value={settings.onboarding_warning_days} onChange={e=>setSettings(v=>({...v,onboarding_warning_days:Number(e.target.value)}))}/></label>
    <label className="wc-field">Organization notice (optional, up to 280 characters)<textarea rows={3} maxLength={280} value={settings.organization_notice} onChange={e=>setSettings(v=>({...v,organization_notice:e.target.value}))} placeholder="Operational notice shown in the Action Center"/></label>
    <button className="wc-primary" disabled={saving}><Save size={15}/>{saving?'Saving…':'Save settings'}</button>
   </form><div className="wc-panel"><h3>Administrative safeguards</h3><div className="wc-safety"><ShieldCheck size={20}/><span>Only active HR administrators can save workspace settings. Edits appear in the audit trail.</span></div><div className="wc-detail"><span>Last updated</span><strong>{settings.updated_at?dateFmt(settings.updated_at):'Not configured yet'}</strong></div><p className="wc-help">For changes to JWT accounts, payroll, employee access, organization identity or leave policy, continue using their dedicated administration screens.</p><div className="wc-actions"><button type="button" onClick={()=>navigate('accounts')}>Account administration <ArrowRight size={16}/></button><button type="button" onClick={()=>navigate('orgsettings')}>Organization settings <ArrowRight size={16}/></button><button type="button" onClick={()=>navigate('audit')}>Audit trail <ArrowRight size={16}/></button></div></div></div>}
  {mode==='workflowsettings'&&!isHR&&<div className="wc-error">Administrator access required.</div>}
 </section>
}
