import {useMemo, useState, type FormEvent} from 'react';
import {CalendarDays, Megaphone, Pencil, Plus, Settings2, ShieldCheck, Trash2, UsersRound, X} from 'lucide-react';
import {hrmFetch} from './apiTransport';
import './organization-workspace.css';

type RecordData=Record<string,any>;
type Kind='department'|'holiday'|'announcement';
type EditState={kind:Kind;id?:number;values:Record<string,string>};
type DeleteState={kind:Kind;id:number;name:string};
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
const urls:Record<Kind,string>={department:'/organization/departments',holiday:'/organization/holidays',announcement:'/organization/announcements'};
const today=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`};
async function request<T>(path:string,method='GET',data?:unknown):Promise<T>{
 const token=sessionStorage.getItem('sass_token');
 const result=await hrmFetch(API+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(data===undefined?{}:{body:JSON.stringify(data)})});
 let response:any;try{response=await result.json()}catch{response={}}
 if(!result.ok)throw new Error(typeof response?.detail==='string'?response.detail:response?.detail?.message||`Request failed (HTTP ${result.status})`);
 return response as T;
}

export function OrganizationWorkspace({isAdmin,departments,holidays,announcements,employees,onChanged,navigate,search}:{
 isAdmin:boolean;departments:RecordData[];holidays:RecordData[];announcements:RecordData[];employees:RecordData[];
 onChanged:()=>Promise<void>;navigate:(page:string)=>void;search:string;
}){
 const [edit,setEdit]=useState<EditState|null>(null);
 const [removal,setRemoval]=useState<DeleteState|null>(null);
 const [confirm,setConfirm]=useState('');
 const [reason,setReason]=useState('');
 const [busy,setBusy]=useState(false);
 const [notice,setNotice]=useState<{message:string;error:boolean}|null>(null);
 const [showPast,setShowPast]=useState(false);
 const departmentsView=useMemo(()=>departments.filter(x=>!search||String(x.name||'').toLowerCase().includes(search.toLowerCase())),[departments,search]);
 const holidaysView=useMemo(()=>holidays.filter(x=>(showPast||String(x.day||'')>=today())&&(!search||`${x.name} ${x.location}`.toLowerCase().includes(search.toLowerCase()))),[holidays,showPast,search]);
 const announcementsView=useMemo(()=>announcements.filter(x=>!search||`${x.title} ${x.body}`.toLowerCase().includes(search.toLowerCase())),[announcements,search]);

 const launch=(kind:Kind,item?:RecordData)=>{
  setNotice(null);setRemoval(null);
  const values=kind==='department'?{name:String(item?.name||''),location:String(item?.location||'Hyderabad'),head_id:item?.head_id?String(item.head_id):''}:
   kind==='holiday'?{name:String(item?.name||''),day:String(item?.day||today()),location:String(item?.location||'All')}:
   {title:String(item?.title||''),body:String(item?.body||'')};
  setEdit({kind,id:item?.id,values});
 };
 const update=(key:string,value:string)=>setEdit(prev=>prev?{...prev,values:{...prev.values,[key]:value}}:null);
 const save=async(e:FormEvent)=>{
  e.preventDefault();if(!edit||busy)return;
  setBusy(true);setNotice(null);
  try{
   const payload:any={...edit.values};
   if(edit.kind==='department')payload.head_id=payload.head_id?Number(payload.head_id):null;
   await request(`${urls[edit.kind]}${edit.id?`/${edit.id}`:''}`,edit.id?'PUT':'POST',payload);
   await onChanged();setEdit(null);setNotice({message:`${edit.kind[0].toUpperCase()+edit.kind.slice(1)} ${edit.id?'updated':'created'} successfully`,error:false});
  }catch(e){setNotice({message:(e as Error).message,error:true})}finally{setBusy(false)}
 };
 const executeDeletion=async(e:FormEvent)=>{
  e.preventDefault();if(!removal||busy||confirm!=='DELETE'||reason.trim().length<5)return;
  setBusy(true);setNotice(null);
  try{
   await request(`${urls[removal.kind]}/${removal.id}`,'DELETE',{confirm:'DELETE',reason:reason.trim()});
   await onChanged();setRemoval(null);setConfirm('');setReason('');setNotice({message:`${removal.name} was permanently deleted. The change is recorded in the audit trail.`,error:false});
  }catch(e){setNotice({message:(e as Error).message,error:true})}finally{setBusy(false)}
 };

 const toolbar=(kind:Kind,label:string)=><button type="button" className="org-action org-add" onClick={()=>launch(kind)}><Plus size={15}/>{label}</button>;
 const controls=(kind:Kind,item:RecordData,label:string)=><div className="org-controls">
  <button type="button" className="org-action" aria-label={`Edit ${label}`} onClick={()=>launch(kind,item)}><Pencil size={15}/> Edit</button>
  <button type="button" className="org-action org-danger" aria-label={`Delete ${label}`} onClick={()=>{setEdit(null);setRemoval({kind,id:item.id,name:label});setConfirm('');setReason('');setNotice(null)}}><Trash2 size={15}/> Delete</button>
 </div>;
 const empty=(text:string)=><p className="org-empty">{text}</p>;
 return <div className="org-workspace">
  {notice&&<div role={notice.error?'alert':'status'} className={`org-notice ${notice.error?'org-notice-error':''}`}>{notice.message}<button type="button" aria-label="Dismiss message" onClick={()=>setNotice(null)}><X size={15}/></button></div>}
  <div className="org-overview">
   <div><strong>{departments.length}</strong><span>Departments</span></div>
   <div><strong>{holidays.filter(h=>String(h.day)>=today()).length}</strong><span>Upcoming holidays</span></div>
   <div><strong>{announcements.length}</strong><span>Recent announcements</span></div>
   {isAdmin&&<button className="org-settings-toggle" type="button" onClick={()=>navigate('orgsettings')}><Settings2 size={17}/> Company & workspace settings</button>}
  </div>
  <div className="org-columns">
   <section className="org-card"><div className="org-heading"><div><h3>Departments</h3><p>Business units, department heads and office locations</p></div>{isAdmin&&toolbar('department','Add')}</div>
     <div className="org-item-list">{departmentsView.map(d=><div className="org-item" key={d.id}><div className="org-symbol"><UsersRound size={18}/></div><div className="org-item-main"><strong>{d.name}</strong><small>{d.location} · {employees.filter(e=>String(e.department).toLowerCase()===String(d.name).toLowerCase()).length} people{d.head_id?` · Head: ${employees.find(e=>Number(e.id)===Number(d.head_id))?.name||d.head_id}`:''}</small></div>{isAdmin&&controls('department',d,d.name)}</div>)}{departmentsView.length===0&&empty('No departments found. HR can add a business unit here.')}</div>
    </section>
   <section className="org-card"><div className="org-heading"><div><h3>Holidays</h3><p>Organization holiday calendar</p></div>{isAdmin&&toolbar('holiday','Add')}</div>
     <label className="org-toggle"><input type="checkbox" checked={showPast} onChange={e=>setShowPast(e.target.checked)}/> Include previous holidays</label>
     <div className="org-item-list">{holidaysView.map(h=><div className="org-item" key={h.id}><div className="org-symbol"><CalendarDays size={18}/></div><div className="org-item-main"><strong>{h.name}</strong><small>{h.day} · {h.location}</small></div>{isAdmin&&controls('holiday',h,h.name)}</div>)}{holidaysView.length===0&&empty('No matching holidays. Add the approved holiday schedule.')}</div>
    </section>
  </div>
  <section className="org-card"><div className="org-heading"><div><h3>Company announcements</h3><p>Company-wide notices visible to signed-in staff</p></div>{isAdmin&&toolbar('announcement','Publish')}</div>
    <div className="org-item-list">{announcementsView.map(a=><div className="org-item org-announcement" key={a.id}><div className="org-symbol"><Megaphone size={19}/></div><div className="org-item-main"><strong>{a.title}</strong><p>{a.body}</p><small>By {a.author_name||'HR'} · {String(a.created_at||'').slice(0,10)}</small></div>{isAdmin&&controls('announcement',a,a.title)}</div>)}{announcementsView.length===0&&empty('No announcements published yet.')}</div>
  </section>
  {isAdmin&&<p className="org-admin-footnote"><ShieldCheck size={16}/> HR administrator changes are recorded in the audit trail. Department deletion is blocked while linked employees, jobs or JDs remain. Deleted announcements and holidays cannot be restored automatically.</p>}
  {edit&&<div className="org-overlay" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget&&!busy)setEdit(null)}}><form className="org-modal" role="dialog" aria-modal="true" aria-label={`${edit.id?'Edit':'Add'} ${edit.kind}`} onSubmit={save}>
    <div className="org-modal-heading"><h3>{edit.id?'Edit':'Add'} {edit.kind}</h3><button type="button" aria-label="Close editor" onClick={()=>setEdit(null)}><X size={19}/></button></div>
    {edit.kind==='department'&&<><label>Department name<input required minLength={2} maxLength={80} value={edit.values.name} onChange={e=>update('name',e.target.value)}/></label><label>Primary location<input required minLength={2} maxLength={80} value={edit.values.location} onChange={e=>update('location',e.target.value)}/></label><label>Department head<select value={edit.values.head_id} onChange={e=>update('head_id',e.target.value)}><option value="">Not assigned</option>{employees.filter(e=>['manager','admin'].includes(e.role)&&String(e.department).toLowerCase()===String(edit.values.name).toLowerCase()).map(e=><option key={e.id} value={e.id}>{e.name}</option>)}</select></label><small>Reassign staff, job postings and JDs before renaming a department currently in use.</small></>}
    {edit.kind==='holiday'&&<><label>Holiday name<input required minLength={2} maxLength={100} value={edit.values.name} onChange={e=>update('name',e.target.value)}/></label><label>Holiday date<input required type="date" value={edit.values.day} onChange={e=>update('day',e.target.value)}/></label><label>Location<input required minLength={2} maxLength={80} value={edit.values.location} onChange={e=>update('location',e.target.value)}/></label><small>The current calendar allows one holiday record per date.</small></>}
    {edit.kind==='announcement'&&<><label>Title<input required minLength={3} maxLength={150} value={edit.values.title} onChange={e=>update('title',e.target.value)}/></label><label>Announcement<textarea required minLength={5} maxLength={3000} rows={6} value={edit.values.body} onChange={e=>update('body',e.target.value)}/></label><small>Publishing makes this notice visible across the organization.</small></>}
    <div className="org-modal-actions"><button className="org-action" type="button" onClick={()=>setEdit(null)}>Cancel</button><button className="org-primary" disabled={busy} type="submit">{busy?'Saving...':'Save changes'}</button></div>
  </form></div>}
  {removal&&<div className="org-overlay" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget&&!busy)setRemoval(null)}}><form className="org-modal" role="alertdialog" aria-modal="true" aria-label={`Delete ${removal.kind}`} onSubmit={executeDeletion}>
    <div className="org-modal-heading"><h3>Delete {removal.kind} permanently?</h3><button type="button" aria-label="Cancel deletion" onClick={()=>setRemoval(null)}><X size={19}/></button></div>
    <p><strong>{removal.name}</strong> will be removed from the active organization records. This action cannot be undone automatically.</p>
    <label>Reason for deletion<textarea minLength={5} maxLength={500} required value={reason} onChange={e=>setReason(e.target.value)} rows={3} placeholder="Explain why this record is being deleted"/></label>
    <label>Type DELETE to confirm<input required value={confirm} onChange={e=>setConfirm(e.target.value)} autoComplete="off" placeholder="DELETE"/></label>
    <div className="org-modal-actions"><button type="button" className="org-action" onClick={()=>setRemoval(null)}>Cancel</button><button type="submit" className="org-primary org-primary-danger" disabled={busy||confirm!=='DELETE'||reason.trim().length<5}><Trash2 size={15}/>{busy?'Deleting...':'Delete permanently'}</button></div>
  </form></div>}
 </div>
}
