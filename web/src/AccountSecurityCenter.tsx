import {useCallback,useEffect,useMemo,useRef,useState} from 'react';
import {AlertCircle,ArrowRight,KeyRound,LockKeyhole,ShieldCheck,Users,Clock3,ClipboardCheck,Settings2,Download} from 'lucide-react';
import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import './account-security-center.css';

type PersonalRecord={id:number;created_at:string};
type PersonalData={events:PersonalRecord[];retention_days:number;session_hours:number;note:string};
type DisplayPreferences={history_limit:10|20|30;display_timezone:'local'|'utc'};
type StatusFilter='all'|'open'|'completed'|'due';
type ChecklistSort='due'|'newest'|'title';
type ChecklistSettings={status_filter:StatusFilter;sort_order:ChecklistSort;default_due:'none'|'today'|'week'};
type ItemInput={title:string;due_on:string|null;completed:boolean};
type ChecklistItem=ItemInput&{id:number;updated_at:string};
const defaultPreferences:DisplayPreferences={history_limit:30,display_timezone:'local'};
const defaultChecklist:ChecklistSettings={status_filter:'all',sort_order:'due',default_due:'none'};
const statusOptions:Record<StatusFilter,string>={all:'All items',open:'Open',completed:'Completed',due:'Due today or overdue'};
const sortOptions:Record<ChecklistSort,string>={due:'Due date',newest:'Newest first',title:'Title (A–Z)'};
const localDate=(days=0)=>{
 const d=new Date();
 d.setDate(d.getDate()+days);
 return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
};
const utcDate=(days=0)=>new Date(Date.now()+days*86400000).toISOString().slice(0,10);
const newChecklistItem=(defaultDue:ChecklistSettings['default_due']):ItemInput=>({
 title:'',completed:false,due_on:defaultDue==='none'?null:localDate(defaultDue==='week'?7:0),
});
const isDue=(item:ChecklistItem,today:string)=>!item.completed&&item.due_on!==null&&item.due_on<=today;
type Account={id:number;code:string;name:string;email:string;role:string;account_active:number;last_login:string|null;successful_logins:number};
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
async function api<T>(path:string,method='GET',body?:unknown):Promise<T>{
  const token=sessionStorage.getItem('sass_token');
  const response=await hrmFetch(API+path,{method,headers:{Authorization:`Bearer ${token||''}`,...(body===undefined?{}:{'Content-Type':'application/json'})},body:body===undefined?undefined:JSON.stringify(body)});
  let payload:any=null;try{payload=await response.json()}catch{}
  if(!response.ok)throw new Error(typeof payload?.detail==='string'?payload.detail:`Request failed (${response.status})`);
  return payload as T;
}
const niceDate=(stamp:string|null,zone:'local'|'utc'='local')=>{
 if(!stamp)return 'No recorded sign-ins';
 const d=new Date(stamp);return isNaN(d.getTime())?stamp:d.toLocaleString('en-IN',{dateStyle:'medium',timeStyle:'short',...(zone==='utc'?{timeZone:'UTC'}:{})});
};
export function AccountSecurityCenter({mode,navigate,onRevoke}:{mode:'me'|'admin';navigate:(page:string)=>void;onRevoke:()=>void}){
 const [mine,setMine]=useState<PersonalData|null>(null);
 const [preferences,setPreferences]=useState<DisplayPreferences>(defaultPreferences);
 const [preferenceForm,setPreferenceForm]=useState<DisplayPreferences>(defaultPreferences);
 const [items,setItems]=useState<ChecklistItem[]>([]);
 const [checklistSettings,setChecklistSettings]=useState(defaultChecklist);
 const [checklistSettingsForm,setChecklistSettingsForm]=useState(defaultChecklist);
 const [itemStatus,setItemStatus]=useState<StatusFilter>(defaultChecklist.status_filter);
 const [itemSort,setItemSort]=useState<ChecklistSort>(defaultChecklist.sort_order);
 const [itemSearch,setItemSearch]=useState('');
 const itemTitleRef=useRef<HTMLInputElement>(null);
 const today=localDate();
 const checklistCounts=useMemo(()=>({
  all:items.length,open:items.filter(item=>!item.completed).length,
  completed:items.filter(item=>item.completed).length,due:items.filter(item=>isDue(item,today)).length,
 }),[items,today]);
 const visibleItems=useMemo(()=>{
  const needle=itemSearch.trim().toLowerCase();
  return items.filter(item=>{
   if(needle&&!item.title.toLowerCase().includes(needle))return false;
   if(itemStatus==='due')return isDue(item,today);
   if(itemStatus==='open')return !item.completed;
   if(itemStatus==='completed')return item.completed;
   return true;
  }).sort((a,b)=>{
   if(itemSort==='title')return a.title.localeCompare(b.title)||b.id-a.id;
   if(itemSort==='newest')return b.id-a.id;
   return Number(a.completed)-Number(b.completed)||(a.due_on??'9999-99-99').localeCompare(b.due_on??'9999-99-99')||b.id-a.id;
  });
 },[itemStatus,itemSort,itemSearch,items,today]);
 const [manageError,setManageError]=useState(''), [manageReady,setManageReady]=useState(false);
 const [notice,setNotice]=useState(''), [saving,setSaving]=useState(false);
 const [editing,setEditing]=useState<number|null>(null), [itemForm,setItemForm]=useState<ItemInput>(()=>newChecklistItem(defaultChecklist.default_due));
 const [showPassword,setShowPassword]=useState(false), [currentPassword,setCurrentPassword]=useState('');
 const [newPassword,setNewPassword]=useState(''), [confirmPassword,setConfirmPassword]=useState('');
 const [passwordError,setPasswordError]=useState(''), [passwordSaving,setPasswordSaving]=useState(false);
 const [accounts,setAccounts]=useState<Account[]>([]);
 const [term,setTerm]=useState('');const [query,setQuery]=useState('');
 const [status,setStatus]=useState('all');
 const [error,setError]=useState('');const [loading,setLoading]=useState(false);
 const [revoking,setRevoking]=useState(false);
 const [exportOpen,setExportOpen]=useState(false), [exporting,setExporting]=useState(false);
 const [reportStart,setReportStart]=useState(()=>utcDate(-29)), [reportEnd,setReportEnd]=useState(()=>utcDate());
 const [exportError,setExportError]=useState(''), [exportNotice,setExportNotice]=useState('');
 const downloadReport=async()=>{
  setExportError('');setExportNotice('');
  if(reportStart&&reportEnd&&reportStart>reportEnd){setExportError('The start date cannot be after the end date.');return;}
  setExporting(true);
  try{
   const query=new URLSearchParams();
   if(reportStart)query.set('start_date',reportStart);
   if(reportEnd)query.set('end_date',reportEnd);
   const token=sessionStorage.getItem('sass_token');
   const result=await hrmFetch(`${API}/security/me/activity/export.csv?${query}`,{headers:{Authorization:`Bearer ${token||''}`}});
   if(!result.ok){
    const payload=await result.json().catch(()=>null);
    throw new Error(typeof payload?.detail==='string'?payload.detail:'Could not download your sign-in report.');
   }
   const url=URL.createObjectURL(await result.blob());
   const link=document.createElement('a');link.href=url;link.download='sass-my-sign-ins.csv';
   document.body.appendChild(link);link.click();link.remove();window.setTimeout(()=>URL.revokeObjectURL(url),2000);
   setExportNotice('Sign-in report prepared for download.');
  }catch(e){setExportError((e as Error).message)}finally{setExporting(false)}
 };
 const load=useCallback(async()=>{
  setLoading(true);setError('');
  try{if(mode==='me')setMine(await api<PersonalData>('/security/me/activity'));
  else{const params=new URLSearchParams({q:query,status,limit:'100'});
   const result=await api<{items:Account[]}>(`/security/admin/activity?${params}`);setAccounts(result.items);}}
  catch(e){setError((e as Error).message)}finally{setLoading(false)}
 },[mode,query,status]);
 useEffect(()=>{void load()},[load]);useRefreshData(load);
 const loadPersonalControls=useCallback(async()=>{
  if(mode!=='me')return;
  setManageError('');
  try{
   const [settings,list,checklist]=await Promise.all([
    api<DisplayPreferences>('/security/me/preferences'),api<{items:ChecklistItem[]}>('/security/me/checklist'),
    api<ChecklistSettings>('/security/me/checklist-settings')
   ]);
   setPreferences(settings);setPreferenceForm(settings);setItems(list.items);
   setChecklistSettings(checklist);setChecklistSettingsForm(checklist);
   setItemStatus(checklist.status_filter);setItemSort(checklist.sort_order);
   setItemForm(newChecklistItem(checklist.default_due));setManageReady(true);
  }catch(e){setManageError((e as Error).message);}
 },[mode]);
 useEffect(()=>{void loadPersonalControls()},[loadPersonalControls]);
 const manage=async(work:()=>Promise<string>)=>{
  setSaving(true);setManageError('');setNotice('');
  try{setNotice(await work())}catch(e){setManageError((e as Error).message)}finally{setSaving(false)}
 };
 const clearItem=()=>{setItemForm(newChecklistItem(checklistSettings.default_due));setEditing(null)};
 const toggleItem=(item:ChecklistItem)=>manage(async()=>{
  const updated=await api<ChecklistItem>(`/security/me/checklist/${item.id}/completion`,'PATCH',{completed:!item.completed});
  setItems(current=>current.map(row=>row.id===updated.id?updated:row));
  if(editing===item.id)setItemForm(current=>({...current,completed:updated.completed}));
  return updated.completed?'Checklist item completed.':'Checklist item reopened.';
 });
 const refreshItems=async()=>setItems((await api<{items:ChecklistItem[]}>('/security/me/checklist')).items);
 const saveItem=()=>manage(async()=>{
  await api(editing===null?'/security/me/checklist':`/security/me/checklist/${editing}`,editing===null?'POST':'PUT',itemForm);
  clearItem();await refreshItems();
  return editing===null?'Checklist item added.':'Checklist item updated.';
 });
 const eraseItem=(id:number)=>{
  if(!window.confirm('Delete this private checklist item? This does not change any security records.'))return;
  void manage(async()=>{
   await api(`/security/me/checklist/${id}`,'DELETE');
   if(editing===id)clearItem();
   await refreshItems();return 'Checklist item deleted.';
  });
 };
 const changePassword=async()=>{
  setPasswordError('');
  if(newPassword!==confirmPassword){setPasswordError('The new passwords do not match.');return;}
  if(!window.confirm('Change your password and sign out all sessions?'))return;
  setPasswordSaving(true);
  try{
   await api('/auth/change-password','POST',{current_password:currentPassword,new_password:newPassword});
   setCurrentPassword('');setNewPassword('');setConfirmPassword('');onRevoke();
  }catch(e){setPasswordError((e as Error).message);setPasswordSaving(false)}
 };
 const revoke=async()=>{
  if(!window.confirm('Sign out every session, including this browser? You will need to sign in again.'))return;
  setRevoking(true);setError('');
  try{await api('/security/me/revoke-all','POST');onRevoke()}
  catch(e){setError((e as Error).message);setRevoking(false)}
 };
 return <section className="sec-center" aria-busy={loading}>
  <div className="sec-head"><span className="sec-label">SASS HRM / IDENTITY SECURITY</span><h1>{mode==='me'?'My Account Security':'Administrator Sign-in Review'}</h1><p>{mode==='me'?'Review your sign-ins, manage your password and sessions, and keep track of your security checks.':'Review recent successful sign-in activity and accounts needing a login setup.'}</p></div>
  {error&&<div className="sec-error" role="alert"><AlertCircle size={18}/>{error}</div>}
  {mode==='me'?<div className="sec-layout">
   <div className="sec-panel"><div className="sec-panel-title"><Clock3 size={21}/><h2>Successful sign-ins</h2></div><p>Showing up to {preferences.history_limit} recent successful sign-ins in {preferences.display_timezone==='utc'?'UTC':'your browser’s timezone'}.</p>
   <div className="sec-history">{mine?.events.length?mine.events.slice(0,preferences.history_limit).map((e,i)=><div key={e.id} className="sec-event"><span className="sec-event-dot"/><div><strong>{niceDate(e.created_at,preferences.display_timezone)}</strong><small>{i===0?'Most recent sign-in':'Successful sign-in'}</small></div></div>):<p>No login activity has been recorded yet.</p>}</div>
   <small className="sec-note">A record older than {mine?.retention_days||180} days is removed when you next sign in. Older activity may be unavailable.</small>
   <div className="sec-report">
    <div className="sec-buttons"><button type="button" aria-expanded={exportOpen} aria-controls="sec-signin-report" onClick={()=>setExportOpen(value=>!value)}><Download size={15} aria-hidden="true"/> {exportOpen?'Hide report options':'Export my sign-ins'}</button></div>
    {exportOpen&&<form id="sec-signin-report" className="sec-edit-form" onSubmit={e=>{e.preventDefault();void downloadReport()}}>
     <small className="sec-note">The CSV contains only your successful sign-in timestamps in UTC. Dates are inclusive. Clear both dates to download all retained sign-ins.</small>
     <div className="sec-report-dates">
      <label>Report start date (UTC)<input type="date" value={reportStart} onChange={e=>setReportStart(e.target.value)}/></label>
      <label>Report end date (UTC)<input type="date" value={reportEnd} onChange={e=>setReportEnd(e.target.value)}/></label>
     </div>
     {exportError&&<div className="sec-error" role="alert">{exportError}</div>}
     {exportNotice&&<p className="sec-success" role="status">{exportNotice}</p>}
     <div className="sec-buttons"><button className="sec-primary" type="submit" disabled={exporting}>{exporting?'Preparing report…':'Download sign-ins CSV'}</button></div>
    </form>}
   </div></div>
   <div className="sec-panel"><div className="sec-panel-title"><ShieldCheck size={21}/><h2>Session controls</h2></div><p>Sessions normally expire after {mine?.session_hours??8} hours. If you suspect unauthorized access, sign out all sessions, including this browser.</p>
   <button type="button" className="sec-danger" onClick={()=>void revoke()} disabled={revoking}>{revoking?'Signing out…':'Sign out all sessions'}</button>
   <div className="sec-links"><button type="button" aria-expanded={showPassword} onClick={()=>{setShowPassword(v=>!v);setPasswordError('');setCurrentPassword('');setNewPassword('');setConfirmPassword('')}} disabled={passwordSaving}><KeyRound size={16}/> Change password</button><button onClick={()=>navigate('profile')}><Users size={16}/> My profile <ArrowRight size={15}/></button></div>
   {showPassword&&<form className="sec-edit-form" onSubmit={e=>{e.preventDefault();void changePassword()}}>
    {passwordError&&<p className="sec-error" role="alert">{passwordError}</p>}
    <label>Current password<input required type="password" autoComplete="current-password" value={currentPassword} onChange={e=>setCurrentPassword(e.target.value)}/></label>
    <label>New password<input required type="password" autoComplete="new-password" minLength={12} maxLength={128} value={newPassword} onChange={e=>setNewPassword(e.target.value)}/></label>
    <label>Confirm new password<input required type="password" autoComplete="new-password" minLength={12} maxLength={128} value={confirmPassword} onChange={e=>setConfirmPassword(e.target.value)}/></label>
    <small className="sec-note">Use at least 12 characters, including a letter and a number. Changing your password signs out all sessions.</small>
    <div className="sec-buttons"><button type="submit" className="sec-primary" disabled={passwordSaving}>{passwordSaving?'Changing password…':'Update password'}</button></div>
   </form>}
   <p className="sec-note">SASS HRM records successful login timestamps only—not passwords, IP addresses, exact device locations, or browser fingerprints. MFA and enterprise SSO are not yet implemented.</p></div>
   <div className="sec-panel sec-personal-controls">
    {manageError&&<div className="sec-error" role="alert"><AlertCircle size={18}/>{manageError}{!manageReady&&<button type="button" onClick={()=>void loadPersonalControls()}>Retry</button>}</div>}
    {notice&&<p className="sec-success" role="status">{notice}</p>}
    {!manageReady&&!manageError&&<p role="status">Loading security settings and checklist…</p>}
    {manageReady&&<div className="sec-control-grid">
     <section aria-labelledby="sec-display-title">
      <div className="sec-panel-title"><Settings2 size={20}/><h2 id="sec-display-title">Sign-in display settings</h2></div>
      <p>Choose how this page displays your sign-in history. These settings do not change retention or session security.</p>
      <form className="sec-edit-form" onSubmit={e=>{e.preventDefault();void manage(async()=>{
       const updated=await api<DisplayPreferences>('/security/me/preferences','PUT',preferenceForm);
       setPreferences(updated);setPreferenceForm(updated);return 'Display settings saved.';
      })}}>
       <label>Number of sign-ins<select value={preferenceForm.history_limit} onChange={e=>setPreferenceForm(p=>({...p,history_limit:Number(e.target.value) as DisplayPreferences['history_limit']}))}><option>10</option><option>20</option><option>30</option></select></label>
       <label>Time zone<select value={preferenceForm.display_timezone} onChange={e=>setPreferenceForm(p=>({...p,display_timezone:e.target.value as DisplayPreferences['display_timezone']}))}><option value="local">Browser time zone</option><option value="utc">UTC</option></select></label>
       <div className="sec-buttons"><button className="sec-primary" disabled={saving}>Save display settings</button></div>
      </form>
      <div className="sec-checklist-settings">
       <div className="sec-panel-title"><Settings2 size={19}/><h2 id="sec-checklist-settings-title">Checklist settings</h2></div>
       <p>Set the view restored when you open this page and an optional due date for new items. No reminders are sent.</p>
       <form className="sec-edit-form" aria-labelledby="sec-checklist-settings-title" onSubmit={e=>{e.preventDefault();void manage(async()=>{
        const updated=await api<ChecklistSettings>('/security/me/checklist-settings','PUT',checklistSettingsForm);
        setChecklistSettings(updated);setChecklistSettingsForm(updated);
        setItemStatus(updated.status_filter);setItemSort(updated.sort_order);
        if(editing===null&&!itemForm.title.trim())setItemForm(newChecklistItem(updated.default_due));
        return 'Checklist settings saved.';
       })}}>
        <label>Default checklist view<select value={checklistSettingsForm.status_filter} onChange={e=>setChecklistSettingsForm(p=>({...p,status_filter:e.target.value as StatusFilter}))}>{Object.entries(statusOptions).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
        <label>Default sort order<select value={checklistSettingsForm.sort_order} onChange={e=>setChecklistSettingsForm(p=>({...p,sort_order:e.target.value as ChecklistSort}))}>{Object.entries(sortOptions).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
        <label>Default due date<select value={checklistSettingsForm.default_due} onChange={e=>setChecklistSettingsForm(p=>({...p,default_due:e.target.value as ChecklistSettings['default_due']}))}><option value="none">No default date</option><option value="today">Today</option><option value="week">One week from today</option></select></label>
        <div className="sec-buttons"><button className="sec-primary" disabled={saving}>Save checklist settings</button></div>
       </form>
      </div>
     </section>
     <section aria-labelledby="sec-checklist-title">
      <div className="sec-panel-title"><ClipboardCheck size={21}/><h2 id="sec-checklist-title">Private security checklist</h2></div>
      <p>Track routine checks, like reviewing sign-ins or clearing an old browser. These items do not enforce security settings. Do not enter passwords, recovery codes, or other secrets.</p>
      <form className="sec-edit-form" onSubmit={e=>{e.preventDefault();void saveItem()}}>
       <label>Checklist item<input ref={itemTitleRef} value={itemForm.title} required maxLength={120} placeholder="e.g. Review my recent sign-ins" onChange={e=>setItemForm(p=>({...p,title:e.target.value}))}/></label>
       <label>Due date (optional)<input type="date" value={itemForm.due_on??''} onChange={e=>setItemForm(p=>({...p,due_on:e.target.value||null}))}/></label>
       <label className="sec-checkbox"><input type="checkbox" checked={itemForm.completed} onChange={e=>setItemForm(p=>({...p,completed:e.target.checked}))}/> Completed</label>
       <div className="sec-buttons"><button className="sec-primary" disabled={saving||!itemForm.title.trim()}>{editing===null?'Add checklist item':'Save checklist item'}</button>{editing!==null&&<button type="button" onClick={clearItem} disabled={saving}>Cancel edit</button>}</div>
      </form>
      <div className="sec-checklist-toolbar">
       <label>Find checklist items<input type="search" placeholder="Filter by title" value={itemSearch} maxLength={120} onChange={e=>setItemSearch(e.target.value)}/></label>
       <label>Checklist status<select value={itemStatus} onChange={e=>setItemStatus(e.target.value as StatusFilter)}>{Object.entries(statusOptions).map(([value,label])=><option key={value} value={value}>{label} ({checklistCounts[value as StatusFilter]})</option>)}</select></label>
       <label>Sort checklist<select value={itemSort} onChange={e=>setItemSort(e.target.value as ChecklistSort)}>{Object.entries(sortOptions).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
      </div>
      {visibleItems.length?<ul className="sec-checklist">{visibleItems.map(item=><li key={item.id}>
       <div><strong>{item.title}</strong><small>{item.completed?'Completed':'Open'}{item.due_on?` · Due ${item.due_on}`:''}</small>{isDue(item,today)&&<small className="sec-due">{item.due_on===today?'Due today':'Overdue'}</small>}</div>
       <div className="sec-buttons"><button type="button" disabled={saving} aria-label={`${item.completed?'Reopen':'Complete'} ${item.title}`} onClick={()=>void toggleItem(item)}>{item.completed?'Reopen':'Mark complete'}</button><button type="button" disabled={saving} aria-label={`Edit ${item.title}`} onClick={()=>{setEditing(item.id);setItemForm({title:item.title,due_on:item.due_on,completed:item.completed});itemTitleRef.current?.focus()}}>Edit</button><button type="button" disabled={saving} aria-label={`Delete ${item.title}`} onClick={()=>eraseItem(item.id)}>Delete</button></div>
      </li>)}</ul>:<p className="sec-note">{items.length?'No checklist items match these filters.':'No checklist items yet.'}</p>}
     </section>
    </div>}
   </div>
  </div>:<div className="sec-panel"><div className="sec-panel-title"><LockKeyhole size={20}/><h2>Account sign-in activity</h2></div><p>Read-only administrator review. Manage account creation, suspensions, and password resets from Account Provisioning.</p>
   <form className="sec-filters" onSubmit={e=>{e.preventDefault();setQuery(term)}}><input aria-label="Find account" value={term} maxLength={100} onChange={e=>setTerm(e.target.value)} placeholder="Search name, staff ID or sign-in email"/><select aria-label="Account status" value={status} onChange={e=>setStatus(e.target.value)}><option value="all">All accounts</option><option value="active">Active</option><option value="inactive">Inactive</option><option value="never">No recorded sign-in</option></select><button type="submit">Search accounts</button></form>
   <div className="sec-table-wrap"><table><thead><tr><th>Employee</th><th>Role</th><th>State</th><th>Last successful sign-in</th><th>Recorded sign-ins</th></tr></thead><tbody>{accounts.length?accounts.map(a=><tr key={a.id}><td><strong>{a.name}</strong><small>{a.code}</small></td><td>{a.role}</td><td>{a.account_active?'Active':'Inactive'}</td><td>{niceDate(a.last_login)}</td><td>{a.successful_logins}</td></tr>):<tr><td colSpan={5}>No matching accounts.</td></tr>}</tbody></table></div>
   {accounts.length===100&&<p className="sec-note">Showing the first 100 results. Narrow your search to find a specific account.</p>}
   <div className="sec-links"><button onClick={()=>navigate('accounts')}>Open Account Provisioning <ArrowRight size={15}/></button><button onClick={()=>navigate('audit')}>Open Audit Trail <ArrowRight size={15}/></button></div>
   <p className="sec-note">This page records successful sign-ins only. It cannot determine the exact device, the user's physical location, or all currently open sessions. Login history begins when this upgrade is installed.</p>
  </div>}
 </section>
}
