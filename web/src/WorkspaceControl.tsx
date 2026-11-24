import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import {useCallback, useEffect, useState} from 'react';
import {Bell, CheckCheck, Archive, RotateCcw, ShieldCheck, SlidersHorizontal, ListTodo, ClipboardCheck, Headset, AlertCircle, Save, ArrowRight} from 'lucide-react';
import './workspace-control.css';

type Mode='workcenter'|'inbox'|'workflowsettings';
type Alert={id:number;title:string;body:string;is_read:number;is_archived:number;created_at:string};
type Settings={helpdesk_target_days:number;task_warning_days:number;onboarding_warning_days:number;organization_notice:string;updated_at:string};
type Summary={scope:'organization'|'personal';tasks:{active:number;overdue:number};onboarding:{pending:number;overdue:number};helpdesk:{open:number;high_priority:number};settings:Settings};
type Prefs={unread_only:boolean;compact_view:boolean};
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
export function WorkspaceControl({mode,isHR,navigate}:{mode:Mode;isHR:boolean;navigate:(page:string)=>void}){
 const [summary,setSummary]=useState<Summary|null>(null);
 const [settings,setSettings]=useState<Settings>(defaults);
 const [alerts,setAlerts]=useState<Alert[]>([]);
 const [unreadCount,setUnreadCount]=useState(0);
 const [filter,setFilter]=useState<'all'|'unread'|'archived'>('all');
 const [prefs,setPrefs]=useState<Prefs>({unread_only:false,compact_view:false});
 const [loading,setLoading]=useState(false);const [saving,setSaving]=useState(false);
 const [error,setError]=useState('');const [notice,setNotice]=useState('');
 const fetchAll=useCallback(async()=>{
  setLoading(true);setError('');
  try{
   if(mode==='inbox'){
    const [inbox,options]=await Promise.all([api<{items:Alert[];unread_count:number}>(`/workspace/inbox?filter=${filter}&limit=150`),api<Prefs>('/workspace/inbox/preferences')]);
    setAlerts(inbox.items);setUnreadCount(inbox.unread_count);setPrefs(options);
   }else{
    const data=await api<Summary>('/workspace/overview');setSummary(data);setSettings(data.settings);
   }
  }catch(e){setError((e as Error).message)}finally{setLoading(false)}
 },[mode,filter]);
 useEffect(()=>{void fetchAll()},[fetchAll]);
 useRefreshData(fetchAll);
 useEffect(()=>{if(mode==='inbox'){void api<Prefs>('/workspace/inbox/preferences').then(p=>{if(p.unread_only)setFilter('unread')}).catch(()=>{})}},[mode]);
 const run=async(callback:()=>Promise<unknown>,message:string)=>{
  setSaving(true);setError('');setNotice('');
  try{await callback();setNotice(message);await fetchAll()}
  catch(e){setError((e as Error).message)}finally{setSaving(false)}
 };
 const savePrefs=(next:Prefs)=>run(async()=>{const saved=await api<Prefs>('/workspace/inbox/preferences','PUT',next);setPrefs(saved)},'Inbox preferences saved.');
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
    <div className="wc-panel"><div className="wc-toolbar"><div className="wc-tabs">{(['all','unread','archived'] as const).map(kind=><button key={kind} className={filter===kind?'active':''} onClick={()=>setFilter(kind)}>{kind==='all'?'All':kind==='unread'?'Unread':'Archived'}</button>)}</div><span className="wc-unread">{unreadCount} unread</span><button className="wc-outline" disabled={saving||unreadCount===0} onClick={()=>run(()=>api('/workspace/inbox/read-all','POST'),'All active notifications marked read.')}><CheckCheck size={16}/> Mark all read</button></div>
     <div className="wc-pref-row"><label><input type="checkbox" checked={prefs.unread_only} onChange={e=>void savePrefs({...prefs,unread_only:e.target.checked})} disabled={saving}/> Default to unread-only inbox</label><label><input type="checkbox" checked={prefs.compact_view} onChange={e=>void savePrefs({...prefs,compact_view:e.target.checked})} disabled={saving}/> Compact inbox view</label></div>
     <div className={`wc-alerts ${prefs.compact_view?'compact':''}`}>{alerts.length?alerts.map(item=><article key={item.id} className={`wc-alert ${item.is_read?'read':''}`}><span className="wc-alert-icon"><Bell size={17}/></span><div><strong>{item.title}</strong><p>{item.body}</p><small>{dateFmt(item.created_at)}</small></div><div className="wc-alert-actions">{!item.is_archived&&!item.is_read&&<button className="wc-outline" disabled={saving} onClick={()=>run(()=>api(`/notifications/${item.id}/read`,'PATCH'),'Notification marked as read.')}>Read</button>}<button className="wc-outline" disabled={saving} onClick={()=>run(()=>api(`/workspace/inbox/${item.id}/${item.is_archived?'restore':'archive'}`,'POST'),item.is_archived?'Notification restored.':'Notification archived.')}>{item.is_archived?<RotateCcw size={15}/>:<Archive size={15}/>} {item.is_archived?'Restore':'Archive'}</button></div></article>):<div className="wc-empty">No notifications in this view.</div>}</div>
    </div>
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
