import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import React, {useCallback, useEffect, useState} from 'react';
import {AlertTriangle, ArrowRight, CalendarClock, CheckCircle2, ClipboardCheck, Download, FileLock2, FilePlus2, FolderLock, Trash2, ShieldCheck} from 'lucide-react';
import './operations-extra.css';

type Item=Record<string,any>;
const ROOT=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
const authHeaders=():Record<string,string>=>{const token=sessionStorage.getItem('sass_token');const headers:Record<string,string>={'Content-Type':'application/json'};if(token)headers.Authorization=`Bearer ${token}`;return headers;};
async function request<T=any>(url:string,method='GET',body?:object):Promise<T>{
 const res=await hrmFetch(ROOT+url,{method,headers:authHeaders(),...(body?{body:JSON.stringify(body)}:{})});
 let data:any={};try{data=await res.json()}catch{}
 if(!res.ok)throw new Error((typeof data.detail==='string'?data.detail:Array.isArray(data.detail)?data.detail.map((x:any)=>x.msg).join('; '):`Request failed (${res.status})`));
 return data as T;
}
function Banner({text,error=false}:{text:string;error?:boolean}){return <div role={error?'alert':'status'} className={`ops-banner ${error?'ops-error':'ops-ok'}`}>{error?<AlertTriangle size={17}/>:<CheckCircle2 size={17}/>} {text}</div>}
function Intro({title,detail,icon:Icon}:{title:string;detail:string;icon:React.ElementType}){return <div className="ops-intro"><div className="ops-icon"><Icon size={23}/></div><div><span className="ops-eyebrow">SASS HRM / ENTERPRISE OPERATIONS</span><h1>{title}</h1><p>{detail}</p></div></div>}
function fmtDate(value:string){return value?new Date(value.slice(0,10)+'T12:00:00').toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'}):'—'}

export function AttendanceCorrections({role,employeeId,onChanged}:{role:string;employeeId:number;onChanged?:()=>void}){
 const [rows,setRows]=useState<Item[]>([]);const [form,setForm]=useState({work_day:new Date().toLocaleDateString('en-CA'),proposed_in:'09:30',proposed_out:'18:30',reason:''});
 const [show,setShow]=useState(false);const [saving,setSaving]=useState(false);const [message,setMessage]=useState('');const [error,setError]=useState('');
 const load=useCallback(async()=>{try{setRows(await request<Item[]>('/attendance/corrections'));setError('')}catch(e){setError((e as Error).message)}},[]);
 useEffect(()=>{load()},[load]);
 useRefreshData(load);
 async function submit(e:React.FormEvent){e.preventDefault();setSaving(true);setError('');try{await request('/attendance/corrections','POST',form);setShow(false);setForm(x=>({...x,reason:''}));setMessage('Attendance correction sent for review');await load();onChanged?.()}catch(e){setError((e as Error).message)}finally{setSaving(false)}}
 async function act(row:Item,kind:'Approved'|'Rejected'|'Cancelled'){
  if(kind==='Cancelled'&&!window.confirm('Cancel this pending correction?'))return;
  const note=kind==='Rejected'?(window.prompt('Reason for rejection (optional)')??null):'';
  if(note===null)return;
  setSaving(true);setError('');try{if(kind==='Cancelled')await request(`/attendance/corrections/${row.id}/cancel`,'POST');else await request(`/attendance/corrections/${row.id}/decision`,'POST',{decision:kind,note});setMessage(`Request ${kind.toLowerCase()}`);await load();onChanged?.()}catch(e){setError((e as Error).message)}finally{setSaving(false)}
 }
 const pending=rows.filter(r=>r.status==='Pending').length;
 return <div className="ops-page"><Intro title="Attendance corrections" detail="Request a correction to a past attendance record, or review direct-report requests. Every decision is audited." icon={CalendarClock}/>
  <div className="ops-toolbar"><div><strong>{pending}</strong><span>Awaiting decisions</span></div><div><strong>{rows.length}</strong><span>Visible requests</span></div><button className="ops-button" onClick={()=>setShow(v=>!v)}><FilePlus2 size={16}/> {show?'Close form':'Request correction'}</button></div>
  {error&&<Banner error text={error}/>} {message&&<Banner text={message}/>}
  {show&&<form className="ops-card ops-form" onSubmit={submit}><h3>Correct my attendance</h3><p>Enter same-day check-in and check-out times. Requests are limited to the last 90 days.</p><div className="ops-fields"><label>Date<input required type="date" value={form.work_day} max={new Date().toLocaleDateString('en-CA')} onChange={e=>setForm(x=>({...x,work_day:e.target.value}))}/></label><label>Check in<input required type="time" value={form.proposed_in} onChange={e=>setForm(x=>({...x,proposed_in:e.target.value}))}/></label><label>Check out<input required type="time" value={form.proposed_out} onChange={e=>setForm(x=>({...x,proposed_out:e.target.value}))}/></label></div><label>Reason<textarea required minLength={8} maxLength={500} rows={3} value={form.reason} onChange={e=>setForm(x=>({...x,reason:e.target.value}))}/></label><button className="ops-button" disabled={saving} type="submit">{saving?'Submitting…':'Submit for approval'}</button></form>}
  <section className="ops-card"><div className="ops-card-head"><div><h3>Correction requests</h3><p>{role==='employee'?'Your own requests':'Your requests and authorized team requests'}</p></div></div><div className="ops-table-wrap"><table><thead><tr><th>Employee</th><th>Work date</th><th>Proposed hours</th><th>Reason</th><th>Status</th><th>Action</th></tr></thead><tbody>{rows.map(r=><tr key={r.id}><td>{r.employee_name}</td><td>{fmtDate(r.work_day)}</td><td>{r.proposed_in} – {r.proposed_out}</td><td>{r.reason}</td><td><span className={`ops-pill ${String(r.status).toLowerCase()}`}>{r.status}</span></td><td><div className="ops-actions">{r.status==='Pending'&&(r.employee_id===employeeId?<button disabled={saving} onClick={()=>act(r,'Cancelled')}>Cancel</button>:role!=='employee'?<><button disabled={saving} onClick={()=>act(r,'Approved')}>Approve</button><button disabled={saving} onClick={()=>act(r,'Rejected')}>Reject</button></>:null)}</div></td></tr>)}</tbody></table>{!rows.length&&<p className="ops-empty">No attendance correction requests yet.</p>}</div></section>
 </div>
}

export function DocumentVault({role,employeeId,employees}:{role:string;employeeId:number;employees:Item[]}){
 const [enabled,setEnabled]=useState(false);const [securityInfo,setSecurityInfo]=useState('Secure vault unavailable until HR IT configures encryption and malware scanning.');
 const [rows,setRows]=useState<Item[]>([]);const [target,setTarget]=useState(employeeId);const [category,setCategory]=useState('Employment');const [file,setFile]=useState<File|null>(null);const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [message,setMessage]=useState('');
 const load=useCallback(async()=>{try{setRows(await request<Item[]>('/vault/files'));setError('')}catch(e){setError((e as Error).message)}},[]);
 useEffect(()=>{load();request<{enabled:boolean;message:string}>('/vault/status').then(r=>{setEnabled(r.enabled);setSecurityInfo(r.message)}).catch(()=>{});},[load]);
 useRefreshData(()=>{void load();void request<{enabled:boolean;message:string}>('/vault/status').then(r=>{setEnabled(r.enabled);setSecurityInfo(r.message)}).catch(()=>{});});
 async function upload(e:React.FormEvent){e.preventDefault();if(!file)return;setBusy(true);setError('');setMessage('');try{
   if(file.size>2*1024*1024)throw Error('Maximum file size is 2 MiB');
   const encoded=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]||'');reader.onerror=()=>reject(Error('Could not read file'));reader.readAsDataURL(file)});
   const mime=file.type||(file.name.toLowerCase().endsWith('.txt')?'text/plain':'');
   await request('/vault/files','POST',{employee_id:target,filename:file.name,mime_type:mime,category,data_base64:encoded});
   setFile(null);const input=document.getElementById('sass-vault-file') as HTMLInputElement|null;if(input)input.value='';setMessage('File saved');await load();
 }catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 async function download(r:Item){setError('');try{const res=await hrmFetch(`${ROOT}/vault/files/${r.id}/download`,{headers:authHeaders()});if(!res.ok)throw Error('Download denied or unavailable');const blob=await res.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=r.filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000)}catch(e){setError((e as Error).message)}}
 async function remove(r:Item){if(!window.confirm(`Permanently delete ${r.filename}?`))return;setBusy(true);try{await request(`/vault/files/${r.id}`,'DELETE');setMessage('File permanently deleted');await load()}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 return <div className="ops-page"><Intro title="Private employee file vault" icon={FolderLock} detail="Upload, download and delete your private HR documents. Only you and authorized HR administrators can access them."/>
 <div className="ops-security"><ShieldCheck size={22}/><div><strong>{enabled?'Encrypted storage and malware scanning configured':'Secure document storage is not configured'}</strong><p>{securityInfo} Files are only accessible to their owner and authorized HR. Do not upload real sensitive employee documents until your organization completes an independent security review.</p></div></div>
 {error&&<Banner error text={error}/>} {message&&<Banner text={message}/>}
 <form className="ops-card ops-form" onSubmit={upload}><h3>Upload a document</h3><div className="ops-fields">
 {role==='admin'&&<label>Employee<select value={target} onChange={e=>setTarget(Number(e.target.value))}>{employees.map(p=><option key={p.id} value={p.id}>{p.name} · {p.code}</option>)}</select></label>}
 <label>Category<select value={category} onChange={e=>setCategory(e.target.value)}>{['Employment','Education','Identity','Payroll','Other'].map(x=><option key={x}>{x}</option>)}</select></label>
 <label>File (PDF, PNG, JPEG, TXT · max 2 MiB)<input id="sass-vault-file" disabled={!enabled} required type="file" accept=".pdf,.png,.jpg,.jpeg,.txt" onChange={e=>setFile(e.target.files?.[0]||null)}/></label></div>
 <button className="ops-button" type="submit" disabled={busy||!file||!enabled}><FilePlus2 size={16}/> {busy?'Uploading…':'Upload document'}</button></form>
 <section className="ops-card"><div className="ops-card-head"><div><h3>Stored files</h3><p>{rows.length} files available to this account</p></div></div><div className="ops-table-wrap"><table><thead><tr><th>Document</th><th>Employee</th><th>Category</th><th>Size</th><th>Added</th><th>Actions</th></tr></thead><tbody>{rows.map(r=><tr key={r.id}><td><FileLock2 size={16}/> {r.filename}</td><td>{r.employee_name}</td><td>{r.category}</td><td>{Math.ceil(r.byte_count/1024)} KiB</td><td>{fmtDate(r.created_at)}</td><td><div className="ops-actions"><button onClick={()=>download(r)}><Download size={15}/> Download</button><button disabled={busy} onClick={()=>remove(r)}><Trash2 size={15}/> Delete</button></div></td></tr>)}</tbody></table>{!rows.length&&<p className="ops-empty">No files have been uploaded.</p>}</div></section></div>
}

export function ReadinessCenter({navigate}:{navigate:(key:string)=>void}){
 const [data,setData]=useState<{active_employees:number;total_open_items:number;issues:Item[];disclaimer:string}|null>(null);const [error,setError]=useState('');
 const load=useCallback(async()=>{try{setData(await request('/admin/readiness'));setError('')}catch(e){setError((e as Error).message)}},[]);
 useEffect(()=>{load()},[load]);
 useRefreshData(load);
 return <div className="ops-page"><Intro title="HR operations center" detail="An actionable overview of workforce data quality and pending administrative work, based on current HR records." icon={ClipboardCheck}/>
 {error&&<Banner error text={error}/>}<div className="ops-toolbar"><div><strong>{data?.active_employees??'—'}</strong><span>Active employees</span></div><div><strong>{data?.total_open_items??'—'}</strong><span>Outstanding items</span></div></div>
 <div className="ops-grid">{data?.issues.map(item=><article className="ops-card ops-readiness" key={item.key}><div className="ops-card-head"><h3>{item.title}</h3><span className={`ops-bubble ${item.count?'ops-warning':''}`}>{item.count}</span></div><p>{item.detail}</p><button className="ops-link" onClick={()=>navigate(item.route)}>Open related module <ArrowRight size={16}/></button></article>)}</div>
 {data&&<div className="ops-security"><ShieldCheck size={20}/><p>{data.disclaimer}</p></div>}</div>
}
