import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import {useEffect, useState} from 'react';
import {ArrowRight, Building2, CheckCircle2, ClipboardCheck, MapPin, Plus, Save, Settings2, ShieldCheck, UsersRound, X} from 'lucide-react';
import './organization-settings.css';

type Profile={name:string;legal_name:string;country:string;timezone:string;contact_email:string;website:string};
type Preferences={currency:'INR'|'USD'|'GBP'|'EUR'|'AED'|'CAD'|'AUD';date_format:'DD/MM/YYYY'|'MM/DD/YYYY'|'YYYY-MM-DD';week_start:'Monday'|'Sunday'|'Saturday';fiscal_year_start_month:number;hours_per_day:number;updated_at?:string|null};
type Office={id?:number;code:string;name:string;city:string;country:string;address:string;timezone:string;is_active:boolean;employee_count?:number};
type Setup={completed:number;total:number;checks:{key:string;label:string;ready:boolean;hint:string}[]};
const defaultProfile:Profile={name:'',legal_name:'',country:'India',timezone:'Asia/Kolkata',contact_email:'',website:''};
const defaultOffice:Office={code:'',name:'',city:'',country:'India',address:'',timezone:'Asia/Kolkata',is_active:true};
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
async function request<T>(path:string,method='GET',data?:unknown):Promise<T>{
 const token=sessionStorage.getItem('sass_token');
 const res=await hrmFetch(API+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(data===undefined?{}:{body:JSON.stringify(data)})});
 let body:any;try{body=await res.json()}catch{body={}}
 if(!res.ok)throw new Error(typeof body.detail==='string'?body.detail:body.detail?.message||`API returned ${res.status}`);
 return body as T;
}
export function OrganizationSettings({navigate,onOrganizationSaved}:{navigate:(page:string)=>void;onOrganizationSaved:()=>void}){
 const [profile,setProfile]=useState<Profile>(defaultProfile);
 const [prefs,setPrefs]=useState<Preferences|null>(null);
 const [offices,setOffices]=useState<Office[]>([]);
 const [overview,setOverview]=useState<Setup|null>(null);
 const [editingOffice,setEditingOffice]=useState<Office|null>(null);
 const [busy,setBusy]=useState(false);const [loading,setLoading]=useState(true);
 const [error,setError]=useState('');const [success,setSuccess]=useState('');
 async function load(){setError('');try{
   const [p,s,o,a]=await Promise.all([
    request<Profile|null>('/admin/organization-profile'),request<Preferences>('/admin/organization/settings'),
    request<Office[]>('/admin/organization/offices'),request<Setup>('/admin/setup/overview')]);
   setProfile(p||defaultProfile);setPrefs(s);setOffices(o);setOverview(a);
  }catch(e){setError((e as Error).message)}finally{setLoading(false)}}
 useEffect(()=>{void load()},[]);
 useRefreshData(load);
 async function run(operation:()=>Promise<unknown>,message:string):Promise<boolean>{setBusy(true);setError('');setSuccess('');try{await operation();setSuccess(message);await load();return true}catch(e){setError((e as Error).message);return false}finally{setBusy(false)}}
 const links=[
  {title:'Departments & holidays',desc:'Create business units, calendars and announcements.',key:'organization',Icon:Building2},
  {title:'Account administration',desc:'Invite staff, manage administrators, roles and sessions.',key:'accounts',Icon:UsersRound},
  {title:'Leave and attendance',desc:'Set leave categories and review time tracking.',key:'leave',Icon:ClipboardCheck},
  {title:'Policies and handbook',desc:'Publish approved policies and acknowledgement requirements.',key:'policies',Icon:ShieldCheck},
  {title:'HRIS import & readiness',desc:'Validate workforce CSV and check deployment readiness.',key:'companysetup',Icon:Settings2},
  {title:'Audit trail',desc:'Review changes made by administrators.',key:'audit',Icon:ShieldCheck},
 ];
 return <div className="org-settings-page">
  <header className="org-settings-hero"><div><div className="eyebrow">SASS HRM / ORGANIZATION ADMINISTRATION</div><h1>Set up the SASS organization</h1><p>Configure your company identity, office directory and workspace preferences. Keep employee and payroll records intact.</p></div></header>
  {loading&&<p role="status">Loading organization settings…</p>}
  {error&&<div className="org-alert error" role="alert">{error}</div>}
  {success&&<div className="org-alert success" role="status"><CheckCircle2 size={17}/>{success}</div>}
  <div className="org-overview"><div><strong>{overview?`${overview.completed}/${overview.total}`:'—'}</strong><span>Setup checks completed</span></div><div><strong>{offices.filter(o=>o.is_active).length}</strong><span>Active offices</span></div><div><strong>{profile.name||'Not configured'}</strong><span>Organization display name</span></div></div>
  <div className="org-settings-grid">
   <section className="section-card org-panel"><div className="section-heading"><div><h3>Company identity</h3><p>Saved securely to the organization profile.</p></div><Building2 size={19}/></div>
    <form className="org-fields" onSubmit={e=>{e.preventDefault();void run(async()=>{await request('/admin/organization-profile','PUT',profile);onOrganizationSaved()},'Company profile saved.')}}>
     {([['name','Organization display name'],['legal_name','Registered legal name'],['contact_email','HR contact email'],['website','Website (https://)'],['country','Country'],['timezone','Organization timezone (IANA)']] as [keyof Profile,string][]).map(([key,label])=><label key={key}>{label}<input value={profile[key]} onChange={e=>setProfile(p=>({...p,[key]:e.target.value}))} type={key==='contact_email'?'email':key==='website'?'url':'text'} required={key!=='website'} maxLength={key==='website'?250:180} placeholder={key==='timezone'?'Asia/Kolkata':label}/></label>)}
     <button className="btn primary org-submit" disabled={busy||loading} type="submit"><Save size={16}/> Save company details</button>
    </form>
   </section>
   <section className="section-card org-panel"><div className="section-heading"><div><h3>Workspace preferences</h3><p>Administrative defaults, not automatic payroll-rule changes.</p></div><Settings2 size={19}/></div>
    {prefs&&<form className="org-fields" onSubmit={e=>{e.preventDefault();void run(()=>request('/admin/organization/settings','PUT',prefs),'Workspace preferences saved and audited.')}}>
     <label>Default reporting currency<select value={prefs.currency} onChange={e=>setPrefs(p=>p&&({...p,currency:e.target.value as Preferences['currency']}))}>{['INR','USD','GBP','EUR','AED','CAD','AUD'].map(v=><option key={v}>{v}</option>)}</select></label>
     <label>Date display format<select value={prefs.date_format} onChange={e=>setPrefs(p=>p&&({...p,date_format:e.target.value as Preferences['date_format']}))}>{['DD/MM/YYYY','MM/DD/YYYY','YYYY-MM-DD'].map(v=><option key={v}>{v}</option>)}</select></label>
     <label>Week starts on<select value={prefs.week_start} onChange={e=>setPrefs(p=>p&&({...p,week_start:e.target.value as Preferences['week_start']}))}>{['Monday','Sunday','Saturday'].map(v=><option key={v}>{v}</option>)}</select></label>
     <label>Financial year starts in<select value={prefs.fiscal_year_start_month} onChange={e=>setPrefs(p=>p&&({...p,fiscal_year_start_month:Number(e.target.value)}))}>{['January','February','March','April','May','June','July','August','September','October','November','December'].map((v,i)=><option key={v} value={i+1}>{v}</option>)}</select></label>
     <label>Standard hours per day<input type="number" min={1} max={16} required value={prefs.hours_per_day} onChange={e=>setPrefs(p=>p&&({...p,hours_per_day:Number(e.target.value)}))}/></label>
     <p className="org-help">These settings are saved as organization metadata. Statutory tax rules, historical payroll records, approved leave allocations and attendance calculations are not changed automatically.</p>
     <button className="btn primary org-submit" disabled={busy||loading} type="submit"><Save size={16}/> Save workspace preferences</button>
    </form>}
   </section>
  </div>
  <section className="section-card org-panel"><div className="section-heading"><div><h3>Office locations</h3><p>Add physical offices, edit details, or deactivate unused locations.</p></div><button type="button" className="btn primary" onClick={()=>setEditingOffice({...defaultOffice})}><Plus size={15}/> Add office</button></div>
   <div className="org-offices">{offices.map(o=><div className="org-office" key={o.id}><div className="org-office-icon"><MapPin size={20}/></div><div className="org-office-body"><strong>{o.name} <span className={o.is_active?'org-active':'org-inactive'}>{o.is_active?'Active':'Inactive'}</span></strong><small>{o.code} · {o.city}, {o.country} · {o.timezone}</small><small>{o.employee_count||0} employee(s) assigned · {o.address||'Address not provided'}</small></div><button className="btn outline" type="button" onClick={()=>setEditingOffice({...o})}>Edit</button></div>)}{!offices.length&&<div className="org-empty"><MapPin size={25}/><strong>No office locations yet</strong><p>Add your first SASS office to start maintaining an official location directory.</p></div>}</div>
  </section>
  <section className="section-card org-panel"><div className="section-heading"><div><h3>HRM setup checklist</h3><p>Links to your existing HRM workflows; no duplicate modules.</p></div><ClipboardCheck size={19}/></div><div className="org-check-list">{overview?.checks.map(c=><div key={c.key}><span className={c.ready?'org-check-ok':'org-check-pending'}>{c.ready?<CheckCircle2 size={17}/>:<ClipboardCheck size={17}/>}</span><span><strong>{c.label}</strong><small>{c.ready?'Configured':c.hint}</small></span></div>)}</div>
   <div className="org-links">{links.map(({title,desc,key,Icon})=><button key={key} onClick={()=>navigate(key)} type="button"><Icon size={20}/><span><strong>{title}</strong><small>{desc}</small></span><ArrowRight size={17}/></button>)}</div>
  </section>
  {editingOffice&&<div className="org-modal-backdrop" onMouseDown={e=>{if(e.currentTarget===e.target&&!busy)setEditingOffice(null)}}><div className="org-office-modal" role="dialog" aria-modal="true" aria-labelledby="org-office-title"><div className="org-modal-head"><h2 id="org-office-title">{editingOffice.id?'Edit office location':'Add office location'}</h2><button type="button" aria-label="Close office editor" onClick={()=>setEditingOffice(null)}><X size={20}/></button></div>{error&&<div role="alert" className="org-alert error" style={{margin:"12px 22px 0"}}>{error}</div>}<form onSubmit={e=>{e.preventDefault();const item=editingOffice;void run(()=>request(item.id?`/admin/organization/offices/${item.id}`:'/admin/organization/offices',item.id?'PUT':'POST',item),item.id?'Office updated.':'Office created.').then(ok=>{if(ok)setEditingOffice(null)});}} className="org-fields">
     {([['code','Office code'],['name','Office name'],['city','City'],['country','Country'],['address','Street address (optional)'],['timezone','Timezone (IANA)']] as [keyof Office,string][]).map(([key,label])=><label key={key}>{label}<input required={key!=='address'} maxLength={key==='address'?500:120} value={String(editingOffice[key]??'')} onChange={e=>setEditingOffice(p=>p&&({...p,[key]:e.target.value}))}/></label>)}
     <label className="org-toggle"><input type="checkbox" checked={editingOffice.is_active} onChange={e=>setEditingOffice(p=>p&&({...p,is_active:e.target.checked}))}/> Office active</label>
     <p className="org-help">Offices with assigned employees cannot be renamed or deactivated until HR reassigns those employees.</p>
     <div className="org-modal-footer"><button className="btn outline" type="button" onClick={()=>setEditingOffice(null)} disabled={busy}>Cancel</button><button className="btn primary" type="submit" disabled={busy}>{busy?'Saving…':'Save office'}</button></div>
    </form></div></div>}
 </div>
}
