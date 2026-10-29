import {apiUrl,hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import React,{useCallback,useEffect,useMemo,useState} from 'react';
import {UserRound,ShieldCheck,Save,Search,UsersRound,CheckCircle2,ArrowRight,LockKeyhole,Mail,Building2,Phone,FileClock,Trash2,Undo2,ImagePlus} from 'lucide-react';
import './profile-center.css';

type Profile={id:number;code:string;name:string;email:string;role:string;designation:string;department:string;location:string;work_mode:string;join_date:string;manager_id:number|null;preferred_name:string;headline:string;biography:string;work_phone:string;timezone:string;language:string;directory_visible:number|boolean;avatar_color:string;has_photo?:boolean;work_email?:string;profile_updated_at:string};
type Row=Record<string,any>;
type Draft={preferred_name:string;headline:string;biography:string;work_phone:string;timezone:string;language:string;directory_visible:boolean;avatar_color:string};
const defaultDraft:Draft={preferred_name:'',headline:'',biography:'',work_phone:'',timezone:'Asia/Kolkata',language:'en',directory_visible:true,avatar_color:'#3C6DF0'};
const timezones=['Asia/Kolkata','Asia/Dubai','America/New_York','America/Chicago','America/Los_Angeles','Europe/London','Europe/Berlin','Australia/Sydney','UTC'];
const colors=['#3C6DF0','#5F5CEB','#0F766E','#B45309','#C0267B','#6B7280'];
function initials(s:string){return s.trim().split(/\s+/).slice(0,2).map(w=>w[0]||'').join('').toUpperCase()||'HR'}
function dateLabel(date?:string){return date?new Date(date).toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'}):'Not configured'}
async function api<T>(path:string,method='GET',payload?:unknown):Promise<T>{
 const token=sessionStorage.getItem('sass_token');
 const response=await hrmFetch(apiUrl(path),{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(payload===undefined?{}:{body:JSON.stringify(payload)})});
 const raw=await response.json().catch(()=>null);
 if(!response.ok)throw new Error(typeof raw?.detail==='string'?raw.detail:`Request failed (HTTP ${response.status})`);
 return raw as T;
}
async function avatarRequest(path:string,method='GET',body?:Blob):Promise<Response>{
 const token=sessionStorage.getItem('sass_token');
 return hrmFetch(apiUrl(path),{method,headers:{...(token?{Authorization:`Bearer ${token}`}:{}),...(body?{'Content-Type':body.type}:{})},...(body?{body}:{})});
}
function ProfileAvatar({id,hasPhoto,color,name,small=false,revision=0}:{id:number;hasPhoto?:boolean;color:string;name:string;small?:boolean;revision?:number}){
 const [url,setUrl]=useState('');
 useEffect(()=>{
  if(!hasPhoto){setUrl('');return}
  let active=true;let current='';
  const path=small?`/profile/directory/${id}/photo`:'/profile/me/photo';
  void avatarRequest(path).then(async response=>{
   if(!response.ok)throw new Error('Picture unavailable');
   const blob=await response.blob();current=URL.createObjectURL(blob);
   if(active)setUrl(current);else URL.revokeObjectURL(current);
  }).catch(()=>{if(active)setUrl('')});
  return ()=>{active=false;if(current)URL.revokeObjectURL(current)};
 },[id,hasPhoto,small,revision]);
 return <span className={'profile-avatar'+(small?' small':'')} style={{background:color}}>{url?<img src={url} alt={`${name} profile photo`}/>:initials(name)}</span>;
}
function Notice({text,error=false}:{text:string;error?:boolean}){return text?<div className={'profile-alert '+(error?'error':'success')} role={error?'alert':'status'}>{error?'!':'✓'} {text}</div>:null}
function Field({title,children}:{title:string;children:React.ReactNode}){return <label className="profile-field"><span>{title}</span>{children}</label>}
export function MyProfile({navigate,onSaved}:{navigate:(page:string)=>void;onSaved:()=>Promise<void>}){
 const [profile,setProfile]=useState<Profile|null>(null);
 const [draft,setDraft]=useState<Draft>(defaultDraft);
 const [directory,setDirectory]=useState<Row[]>([]);
 const [requests,setRequests]=useState<Row[]>([]);
 const [correction,setCorrection]=useState({requested_value:'',reason:''});
 const [filter,setFilter]=useState('');
 const [tab,setTab]=useState<'edit'|'directory'|'corrections'>('edit');
 const [pictureRevision,setPictureRevision]=useState(0);const [saving,setSaving]=useState(false);const [loading,setLoading]=useState(true);const [error,setError]=useState('');const [success,setSuccess]=useState('');
 const load=useCallback(async()=>{
  setError('');setLoading(true);
  try{const [me,people,changes]=await Promise.all([api<Profile>('/profile/me'),api<Row[]>('/profile/directory'),api<Row[]>('/profile/me/requests')]);
   setProfile(me);setDraft({preferred_name:me.preferred_name,headline:me.headline,biography:me.biography,work_phone:me.work_phone,timezone:me.timezone,language:me.language,directory_visible:!!me.directory_visible,avatar_color:me.avatar_color});setDirectory(people);setRequests(changes);
  }catch(e){setError((e as Error).message)}finally{setLoading(false)}
 },[]);
 useEffect(()=>{void load()},[load]);
 useRefreshData(load);
 const restoreDraft=()=>{if(profile)setDraft({preferred_name:profile.preferred_name,headline:profile.headline,biography:profile.biography,work_phone:profile.work_phone,timezone:profile.timezone,language:profile.language,directory_visible:!!profile.directory_visible,avatar_color:profile.avatar_color})};
 async function uploadPhoto(file?:File){if(!file)return;
  setError('');setSuccess('');
  if(!['image/jpeg','image/png','image/webp'].includes(file.type)){setError('Please select a JPEG, PNG or WebP image.');return}
  if(file.size>2*1024*1024){setError('Choose a photo smaller than 2 MB.');return}
  setSaving(true);
  try{const response=await avatarRequest('/profile/me/photo','PUT',file);if(!response.ok){const data=await response.json().catch(()=>null);throw new Error(data?.detail||'Could not upload photo')}
   await load();setPictureRevision(n=>n+1);window.dispatchEvent(new Event('sass-hrm:profile-photo-changed'));setSuccess('Profile photo saved to your HR account.');
  }catch(e){setError((e as Error).message)}finally{setSaving(false)}
 }
 async function removePhoto(){if(!window.confirm('Remove your uploaded profile photograph?'))return;
  setSaving(true);setError('');setSuccess('');
  try{const r=await avatarRequest('/profile/me/photo','DELETE');if(!r.ok)throw new Error('Unable to remove photo');await load();setPictureRevision(n=>n+1);window.dispatchEvent(new Event('sass-hrm:profile-photo-changed'));setSuccess('Profile photo removed.');}
  catch(e){setError((e as Error).message)}finally{setSaving(false)}
 }
 async function clearOptional(){if(!window.confirm('Delete your optional profile fields and photograph? This does not delete your employee account, HR data or password.'))return;
  setSaving(true);setError('');setSuccess('');
  try{const r=await avatarRequest('/profile/me/optional','DELETE');if(!r.ok)throw new Error('Unable to reset optional profile');await load();setPictureRevision(n=>n+1);window.dispatchEvent(new Event('sass-hrm:profile-photo-changed'));setSuccess('Optional profile information and photo cleared. Your official HR record remains unchanged.');}
  catch(e){setError((e as Error).message)}finally{setSaving(false)}
 }
 const visible=useMemo(()=>directory.filter(p=>`${p.name} ${p.preferred_name} ${p.department} ${p.designation} ${p.headline}`.toLowerCase().includes(filter.toLowerCase())),[directory,filter]);
 async function save(e:React.FormEvent){e.preventDefault();setSaving(true);setSuccess('');setError('');
  try{const result=await api<Profile>('/profile/me','PUT',draft);setProfile(result);await onSaved();setSuccess('Professional profile saved. Directory visibility changes take effect immediately.');setDirectory(await api<Row[]>('/profile/directory'))}catch(e){setError((e as Error).message)}finally{setSaving(false)}
 }
 async function sendCorrection(e:React.FormEvent){e.preventDefault();setSaving(true);setError('');setSuccess('');
  try{await api('/profile/me/requests','POST',correction);setCorrection({requested_value:'',reason:''});setRequests(await api<Row[]>('/profile/me/requests'));setSuccess('Your official name-correction request was sent to HR for review.')}catch(e){setError((e as Error).message)}finally{setSaving(false)}
 }
 return <div className="profile-center">
  <header className="profile-hero"><div><div className="profile-eyebrow">ACCOUNT / PROFESSIONAL IDENTITY</div><h1>My profile & settings</h1><p>Manage your professional identity, coworker visibility and official change requests in one place.</p></div></header>
  {error&&<Notice text={error} error/>}{success&&<Notice text={success}/>}{loading&&<p className="profile-helper">Loading your profile…</p>}
  {profile&&<div className="profile-overview"><ProfileAvatar id={profile.id} hasPhoto={profile.has_photo} color={draft.avatar_color} name={draft.preferred_name||profile.name} revision={pictureRevision}/><div className="profile-person"><h2>{draft.preferred_name||profile.name}</h2><p>{profile.designation} · {profile.department}</p><span>{profile.email}</span></div><span className="profile-state"><ShieldCheck size={16}/> {profile.role.toUpperCase()} ACCOUNT</span></div>}
  <nav aria-label="Profile views" className="profile-tabs"><button className={tab==='edit'?'chosen':''} onClick={()=>setTab('edit')}><UserRound size={17}/> My details</button><button className={tab==='directory'?'chosen':''} onClick={()=>setTab('directory')}><UsersRound size={17}/> Staff directory</button><button className={tab==='corrections'?'chosen':''} onClick={()=>setTab('corrections')}><FileClock size={17}/> Identity requests</button></nav>
  {profile&&tab==='edit'&&<div className="profile-two-col"><section className="profile-card"><div className="profile-card-heading"><h3>Professional profile</h3><span>Self-service</span></div>
   <div className="profile-photo-settings">
    <ProfileAvatar id={profile.id} hasPhoto={profile.has_photo} color={draft.avatar_color} name={draft.preferred_name||profile.name} revision={pictureRevision}/>
    <div className="profile-photo-actions"><strong>Profile photograph</strong><small>JPEG, PNG or WebP · up to 2 MB · automatically resized and metadata removed</small>
     <label className="profile-ghost profile-file-picker"><ImagePlus size={16}/> {profile.has_photo?'Replace photo':'Upload photo'}<input aria-label="Upload profile photo" type="file" accept="image/jpeg,image/png,image/webp" disabled={saving} onChange={e=>{void uploadPhoto(e.target.files?.[0]);e.target.value=''}}/></label>
     {profile.has_photo&&<button type="button" className="profile-ghost danger" disabled={saving} onClick={()=>void removePhoto()}><Trash2 size={16}/> Remove photo</button>}
    </div>
   </div>
   <form onSubmit={save} className="profile-form"><div className="profile-fields-two"><Field title="Preferred display name"><input maxLength={80} value={draft.preferred_name} onChange={e=>setDraft(d=>({...d,preferred_name:e.target.value}))} placeholder={profile.name}/></Field><Field title="Professional headline"><input maxLength={140} value={draft.headline} onChange={e=>setDraft(d=>({...d,headline:e.target.value}))} placeholder="e.g. HR Operations Specialist"/></Field><Field title="Work contact number"><input maxLength={32} value={draft.work_phone} onChange={e=>setDraft(d=>({...d,work_phone:e.target.value}))} placeholder="Optional work number"/></Field><Field title="Timezone"><select value={draft.timezone} onChange={e=>setDraft(d=>({...d,timezone:e.target.value}))}>{timezones.includes(draft.timezone)?null:<option value={draft.timezone}>{draft.timezone}</option>}{timezones.map(t=><option key={t}>{t}</option>)}</select></Field><Field title="Preferred language (metadata)"><select value={draft.language} onChange={e=>setDraft(d=>({...d,language:e.target.value}))}>{[['en','English'],['hi','Hindi'],['te','Telugu'],['ta','Tamil'],['kn','Kannada']].map(([value,label])=><option value={value} key={value}>{label}</option>)}</select></Field></div><Field title="About me"><textarea rows={4} maxLength={750} value={draft.biography} onChange={e=>setDraft(d=>({...d,biography:e.target.value}))} placeholder="A short introduction for colleagues; do not include private or medical information."/></Field>
    <div className="profile-colors"><span>Avatar color</span><div>{colors.map(c=><button key={c} type="button" style={{background:c}} className={draft.avatar_color.toUpperCase()===c.toUpperCase()?'selected':''} aria-label={`Use avatar color ${c}`} onClick={()=>setDraft(d=>({...d,avatar_color:c}))}/>)}</div></div>
    <label className="profile-toggle"><input type="checkbox" checked={draft.directory_visible} onChange={e=>setDraft(d=>({...d,directory_visible:e.target.checked}))}/><span><strong>Show my professional profile in the staff directory</strong><small>Disabling this hides your optional professional profile details from colleagues. HR can still administer your employee record.</small></span></label>
    <div className="profile-edit-actions"><button type="submit" disabled={saving} className="profile-primary"><Save size={16}/> {saving?'Saving…':'Save profile changes'}</button><button type="button" className="profile-ghost" disabled={saving} onClick={restoreDraft}><Undo2 size={16}/> Discard unsaved edits</button></div>
   </form><div className="profile-reset"><p>Want to remove optional professional information? This will not remove your login, work email, role, or HR records.</p><button type="button" className="profile-ghost danger" disabled={saving} onClick={()=>void clearOptional()}><Trash2 size={16}/> Delete optional profile details</button></div></section><aside className="profile-card"><div className="profile-card-heading"><h3>Official work details</h3><span>HR managed</span></div><div className="profile-details">{[['Employee code',profile.code],['Official name',profile.name],['Work email',profile.work_email||profile.email],['Role',profile.role],['Department',profile.department],['Designation',profile.designation],['Office',profile.location],['Work mode',profile.work_mode],['Joined',dateLabel(profile.join_date)]].map(([label,value])=><div key={label}><span>{label}</span><strong>{value||'—'}</strong></div>)}</div><div className="profile-note"><LockKeyhole size={19}/> Official employment fields require HR authorization. Profile settings cannot change JWT roles or account passwords.</div><div className="profile-shortcuts"><button onClick={()=>navigate('settings')}><ShieldCheck size={16}/> Password and security <ArrowRight size={16}/></button><button onClick={()=>navigate('privateprofile')}><Phone size={16}/> Private emergency contacts <ArrowRight size={16}/></button></div></aside></div>}
  {tab==='directory'&&<section className="profile-card"><div className="profile-card-heading"><h3>Colleague directory</h3><span>{visible.length} visible</span></div><label className="profile-search"><Search size={17}/><input aria-label="Search professional directory" value={filter} onChange={e=>setFilter(e.target.value)} placeholder="Search by name, team or designation"/></label><div className="profile-directory">{visible.map(p=><article key={p.id}><ProfileAvatar id={p.id} hasPhoto={!!p.has_photo} color={p.avatar_color} name={p.preferred_name||p.name} small revision={pictureRevision}/><div><strong>{p.preferred_name||p.name}</strong><small>{p.designation} · {p.department}</small>{p.headline&&<p>{p.headline}</p>}{p.work_phone&&<small><Phone size={12}/> {p.work_phone}</small>}</div></article>)}{visible.length===0&&<div className="profile-empty">No matching profiles. Colleagues who opted out are not displayed.</div>}</div></section>}
  {tab==='corrections'&&<div className="profile-two-col"><section className="profile-card"><div className="profile-card-heading"><h3>Request an official name correction</h3><span>HR approval required</span></div><p className="profile-helper">This updates your legal/workforce display name only if HR approves it. For work-email changes, contact your HR administrator.</p><form className="profile-form" onSubmit={sendCorrection}><Field title="Requested official name"><input required minLength={2} maxLength={100} value={correction.requested_value} onChange={e=>setCorrection(d=>({...d,requested_value:e.target.value}))}/></Field><Field title="Reason for correction"><textarea rows={4} required minLength={6} maxLength={450} value={correction.reason} onChange={e=>setCorrection(d=>({...d,reason:e.target.value}))}/></Field><button className="profile-primary" disabled={saving}><Mail size={16}/> Submit for HR review</button></form></section><section className="profile-card"><div className="profile-card-heading"><h3>My requests</h3><span>{requests.length}</span></div><div className="profile-request-list">{requests.map(r=><div key={r.id}><strong>{r.requested_value}</strong><span className={'profile-pill '+r.status.toLowerCase()}>{r.status}</span><small>{dateLabel(r.requested_at)} · Official name</small>{r.review_note&&<p>HR note: {r.review_note}</p>}</div>)}{!requests.length&&<div className="profile-empty">No change requests yet.</div>}</div></section></div>}
 </div>
}

export function ProfileManagement({navigate}:{navigate:(page:string)=>void}){
 const [people,setPeople]=useState<Row[]>([]);const [requests,setRequests]=useState<Row[]>([]);
 const [query,setQuery]=useState('');const [status,setStatus]=useState('Pending');const [notes,setNotes]=useState<Record<number,string>>({});
 const [processing,setProcessing]=useState<number|null>(null);const [error,setError]=useState('');const[success,setSuccess]=useState('');const[loading,setLoading]=useState(true);
 const load=useCallback(async()=>{setError('');setLoading(true);try{const [p,r]=await Promise.all([api<Row[]>('/profile/admin/overview'),api<Row[]>('/profile/admin/requests')]);setPeople(p);setRequests(r)}catch(e){setError((e as Error).message)}finally{setLoading(false)}},[]);
 useEffect(()=>{void load()},[load]);
 useRefreshData(load);
 const pending=requests.filter(r=>r.status==='Pending');
 const shown=useMemo(()=>people.filter(p=>`${p.name} ${p.email} ${p.department} ${p.role}`.toLowerCase().includes(query.toLowerCase())),[people,query]);
 async function decide(id:number,decision:'Approved'|'Rejected'){setError('');setSuccess('');setProcessing(id);try{await api(`/profile/admin/requests/${id}/decision`,'POST',{decision,review_note:notes[id]||''});setNotes(old=>({...old,[id]:''}));await load();setSuccess(`Name correction ${decision.toLowerCase()}.`)}catch(e){setError((e as Error).message)}finally{setProcessing(null)}}
 return <div className="profile-center"><header className="profile-hero"><div><div className="profile-eyebrow">PEOPLE MANAGEMENT / PROFILE GOVERNANCE</div><h1>Profile management</h1><p>Review professional profile completeness, handle official name corrections and navigate to existing account and HRIS management.</p></div></header>
 {error&&<Notice text={error} error/>}{success&&<Notice text={success}/>}<div className="profile-metrics"><article><strong>{people.length}</strong><span>Total employee records</span></article><article><strong>{people.filter(p=>p.headline).length}</strong><span>Profiles with headlines</span></article><article><strong>{people.filter(p=>!!p.directory_visible).length}</strong><span>Directory-visible profiles</span></article><article><strong>{pending.length}</strong><span>Corrections awaiting HR</span></article></div>
 <section className="profile-card"><div className="profile-card-heading"><h3>HR management shortcuts</h3><span>Existing secure workflows</span></div><div className="profile-link-grid"><button onClick={()=>navigate('employees')}><Building2 size={20}/><span>Employee HRIS <small>Update official employment fields</small></span><ArrowRight size={17}/></button><button onClick={()=>navigate('accounts')}><LockKeyhole size={20}/><span>Account administration <small>Access, JWT sessions and invitations</small></span><ArrowRight size={17}/></button><button onClick={()=>navigate('orgsettings')}><ShieldCheck size={20}/><span>Organization settings <small>Offices and company defaults</small></span><ArrowRight size={17}/></button></div></section>
 <section className="profile-card"><div className="profile-card-heading"><h3>Professional directory oversight</h3><span>{shown.length} employees</span></div><label className="profile-search"><Search size={17}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search employee, email, department or role"/></label><div className="profile-management-table"><table><thead><tr><th>Employee</th><th>Department</th><th>Role</th><th>Profile status</th><th>Visibility</th></tr></thead><tbody>{shown.map(p=><tr key={p.id}><td><strong>{p.preferred_name||p.name}</strong><small>{p.email}</small></td><td>{p.department}</td><td>{p.role}</td><td>{p.headline?'Configured':'Needs headline'}</td><td><span className={'profile-pill '+(p.directory_visible?'approved':'rejected')}>{p.directory_visible?'Visible':'Hidden'}</span></td></tr>)}</tbody></table>{!shown.length&&<div className="profile-empty">{loading?'Loading profiles…':'No matching employees.'}</div>}</div><p className="profile-helper">Private addresses, personal phone numbers, payroll and account secrets are not shown in this overview.</p></section>
 <section className="profile-card"><div className="profile-card-heading"><h3>Official name-correction requests</h3><select aria-label="Filter requests" value={status} onChange={e=>setStatus(e.target.value)}><option>Pending</option><option>Approved</option><option>Rejected</option><option value="All">All statuses</option></select></div><div className="profile-request-list">{requests.filter(r=>status==='All'||r.status===status).map(r=><article key={r.id} className="profile-review-row"><div><strong>{r.employee_name}</strong><span className={'profile-pill '+r.status.toLowerCase()}>{r.status}</span><small>{r.employee_email} · {dateLabel(r.requested_at)}</small><p><b>Requested name:</b> {r.requested_value}</p><p><b>Reason:</b> {r.reason}</p>{r.review_note&&<p><b>Review note:</b> {r.review_note}</p>}</div>{r.status==='Pending'&&<div className="profile-review-controls"><label>HR review note<input maxLength={450} value={notes[r.id]||''} onChange={e=>setNotes(old=>({...old,[r.id]:e.target.value}))} placeholder="Required for rejection"/></label><button disabled={processing!==null} onClick={()=>void decide(r.id,'Approved')} className="profile-primary"><CheckCircle2 size={16}/> Approve</button><button disabled={processing!==null||(notes[r.id]||'').trim().length<5} onClick={()=>void decide(r.id,'Rejected')} className="profile-ghost danger">Reject</button></div>}</article>)}{!requests.some(r=>status==='All'||r.status===status)&&<div className="profile-empty">No requests in this category.</div>}</div></section>
 </div>
}
