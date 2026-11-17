import React, {useCallback,useEffect,useRef,useState} from 'react';
import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import {Camera, Fingerprint, ScanEye, ClipboardPen, ShieldCheck, Eye, Trash2} from 'lucide-react';
import './attendance-modalities.css';

type Row=Record<string,any>;
type Methods={manual_enabled:boolean;photo_enabled:boolean;fingerprint_enabled:boolean;iris_enabled:boolean;photo_retention_days:number;photo_notice:string;device_notice:string};
const ROOT=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
const auth=():Record<string,string>=>{const token=sessionStorage.getItem('sass_token');return token?{'Authorization':`Bearer ${token}`}:{}};
async function api<T>(path:string,init:RequestInit={}):Promise<T>{
 const response=await hrmFetch(ROOT+path,{...init,headers:{...auth(),...(init.headers||{})}});
 if(!response.ok){let detail=`Request failed (${response.status})`;try{const data=await response.json();if(typeof data.detail==='string')detail=data.detail;else if(Array.isArray(data.detail))detail=data.detail.map((x:any)=>x.msg).join('; ')}catch{}throw new Error(detail)}
 return response.json() as Promise<T>;
}
const localDay=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`};

export function AttendanceModalities({isHR,employees,onChanged}:{isHR:boolean;employees:Row[];onChanged?:()=>void}){
 const video=useRef<HTMLVideoElement|null>(null);
 const stream=useRef<MediaStream|null>(null);
 const [methods,setMethods]=useState<Methods|null>(null);
 const [events,setEvents]=useState<Row[]>([]);
 const [cameraOn,setCameraOn]=useState(false);
 const [consent,setConsent]=useState(false);
 const [photoAction,setPhotoAction]=useState<'check-in'|'check-out'>('check-in');
 const [manual,setManual]=useState({employee_id:'',work_day:localDay(),check_in:'09:30',check_out:'',reason:''});
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');const [message,setMessage]=useState('');
 const [photoUrl,setPhotoUrl]=useState('');
 const load=useCallback(async()=>{
  try{const [m,e]=await Promise.all([api<Methods>('/attendance/methods'),api<Row[]>('/attendance/capture-events')]);setMethods(m);setEvents(e)}
  catch(e){setError((e as Error).message)}
 },[]);
 useEffect(()=>{void load()},[load]);
 useRefreshData(load);
 useEffect(()=>{if(cameraOn&&video.current&&stream.current){video.current.srcObject=stream.current;void video.current.play().catch(()=>{})}},[cameraOn]);
 useEffect(()=>()=>{stream.current?.getTracks().forEach(t=>t.stop());stream.current=null},[]);
 useEffect(()=>()=>{if(photoUrl)URL.revokeObjectURL(photoUrl)},[photoUrl]);
 const stopCamera=()=>{stream.current?.getTracks().forEach(t=>t.stop());stream.current=null;if(video.current)video.current.srcObject=null;setCameraOn(false)};
 async function startCamera(){setError('');setMessage('');try{
  if(!navigator.mediaDevices?.getUserMedia)throw Error('Camera unavailable. Use HTTPS or localhost, allow camera access, or use manual attendance.');
  stopCamera();stream.current=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user',width:{ideal:640}},audio:false});setCameraOn(true);
 }catch(err){setError((err as Error).message)}}
 async function submitPhoto(){setError('');setMessage('');if(!consent){setError('Confirm your consent before submitting a photo.');return}
  if(!video.current||!video.current.videoWidth){setError('Camera is not ready. Start the camera and wait for the preview.');return}
  setBusy(true);
  try{
   const canvas=document.createElement('canvas');canvas.width=Math.min(video.current.videoWidth,640);canvas.height=Math.round(video.current.videoHeight*canvas.width/video.current.videoWidth);
   canvas.getContext('2d')?.drawImage(video.current,0,0,canvas.width,canvas.height);
   const blob=await new Promise<Blob>((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(Error('Unable to capture photo')),'image/jpeg',0.78));
   const result=await api<{message:string}>(`/attendance/photo?action=${photoAction}&consent=true`,{method:'POST',headers:{'Content-Type':'image/jpeg'},body:blob});
   setMessage(result.message);setConsent(false);stopCamera();await load();onChanged?.();
  }catch(err){setError((err as Error).message)}finally{setBusy(false)}
 }
 async function submitManual(e:React.FormEvent){e.preventDefault();setError('');setMessage('');setBusy(true);
  try{const result=await api<{message:string}>('/attendance/manual',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({employee_id:Number(manual.employee_id),work_day:manual.work_day,check_in:manual.check_in,check_out:manual.check_out||null,reason:manual.reason})});
   setMessage(result.message);setManual(x=>({...x,reason:''}));await load();onChanged?.();
  }catch(err){setError((err as Error).message)}finally{setBusy(false)}
 }
 async function viewPhoto(id:number){setError('');try{
  const response=await hrmFetch(`${ROOT}/attendance/photo-evidence/${id}`,{headers:auth()});
  if(!response.ok)throw Error(`Photo unavailable (${response.status}). It may have expired or be restricted.`);
  setPhotoUrl(URL.createObjectURL(await response.blob()));
 }catch(err){setError((err as Error).message)}}
 async function deletePhoto(id:number){if(!window.confirm('Remove this photo evidence permanently? Attendance times and audit history will remain.'))return;
  setBusy(true);setError('');try{await api(`/attendance/photo-evidence/${id}`,{method:'DELETE'});setMessage('Photo evidence removed; attendance remains recorded.');setPhotoUrl('');await load()}catch(err){setError((err as Error).message)}finally{setBusy(false)}}
 return <div className="attm-root">
  <div className="attm-heading"><ShieldCheck size={21}/><div><h2>Attendance capture methods</h2><p>Manual entry, camera-assisted photo evidence, and external fingerprint/iris devices.</p></div></div>
  {error&&<div className="attm-error" role="alert">{error}</div>}{message&&<div className="attm-success" role="status">{message}</div>}
  <div className="attm-grid">
   <section className="attm-card"><h3><Camera size={18}/> Photo check-in / check-out</h3>
    <p>Take a current camera photo for attendance evidence. This does <strong>not</strong> perform facial recognition or identity matching.</p>
    <span className="attm-status">{methods?.photo_enabled?'Encrypted photo capture is configured':'Not enabled: HR IT must configure encrypted storage'}</span>
    {methods?.photo_enabled&&<>
     <label className="attm-field">Action<select value={photoAction} onChange={e=>setPhotoAction(e.target.value as 'check-in'|'check-out')}><option value="check-in">Check in</option><option value="check-out">Check out</option></select></label>
     <div className="attm-preview">{cameraOn?<video ref={video} playsInline muted autoPlay aria-label="Live camera preview"/>:<div>Camera preview is off</div>}</div>
     <div className="attm-buttons"><button type="button" onClick={()=>cameraOn?stopCamera():void startCamera()} disabled={busy}>{cameraOn?'Stop camera':'Start camera'}</button></div>
     <label className="attm-consent"><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/><span>I consent to submit this photo for attendance evidence. I understand it is encrypted, access-restricted and retained for up to {methods.photo_retention_days} days; I may use the manual/correction process instead.</span></label>
     <button className="attm-primary" type="button" disabled={busy||!consent||!cameraOn} onClick={()=>void submitPhoto()}>{busy?'Saving…':'Capture photo and '+(photoAction==='check-in'?'check in':'check out')}</button>
    </>}
   </section>
   <section className="attm-card"><h3><Fingerprint size={18}/> Fingerprint device</h3>
    <p>A compatible scanner verifies the employee <strong>on the device</strong>, then sends a signed attendance event. No fingerprints or templates are uploaded to SASS HRM.</p>
    <span className="attm-status">{methods?.fingerprint_enabled?'Device gateway enabled — connect and test your scanner':'Hardware gateway not configured'}</span>
    <h3 className="attm-sub"><ScanEye size={18}/> Iris device</h3>
    <p>Compatible iris scanners use the same verified-event gateway; browser webcams do not scan irises.</p>
    <span className="attm-status">{methods?.iris_enabled?'Device gateway enabled — connect and test your scanner':'Hardware gateway not configured'}</span>
   </section>
  </div>
  {isHR&&<section className="attm-card"><h3><ClipboardPen size={18}/> HR manual attendance entry</h3><p>Only HR administrators can create a missing entry. Existing entries require the approved Attendance Corrections workflow.</p>
   <form onSubmit={e=>void submitManual(e)}><div className="attm-form-grid">
    <label className="attm-field">Employee<select required value={manual.employee_id} onChange={e=>setManual(x=>({...x,employee_id:e.target.value}))}><option value="">Select employee</option>{employees.map(e=><option key={e.id} value={e.id}>{e.name} ({e.code})</option>)}</select></label>
    <label className="attm-field">Work date<input required type="date" max={localDay()} value={manual.work_day} onChange={e=>setManual(x=>({...x,work_day:e.target.value}))}/></label>
    <label className="attm-field">Check in<input required type="time" value={manual.check_in} onChange={e=>setManual(x=>({...x,check_in:e.target.value}))}/></label>
    <label className="attm-field">Check out (optional)<input type="time" value={manual.check_out} onChange={e=>setManual(x=>({...x,check_out:e.target.value}))}/></label>
   </div><label className="attm-field">Reason for manual entry<textarea minLength={8} maxLength={500} required value={manual.reason} onChange={e=>setManual(x=>({...x,reason:e.target.value}))} placeholder="Explain why a manual attendance record is needed"/></label>
   <button className="attm-primary" type="submit" disabled={busy||!manual.employee_id}>{busy?'Saving…':'Save manual attendance'}</button></form>
  </section>}
  <section className="attm-card"><div className="attm-row"><h3>Attendance capture history</h3><p>Use the workspace Refresh data button to update history.</p></div>
   <div className="attm-table-scroll"><table><thead><tr><th>Employee</th><th>Date</th><th>Action</th><th>Method</th><th>Device</th><th>Evidence</th></tr></thead><tbody>
    {events.map(e=><tr key={e.id}><td>{e.employee_name}</td><td>{e.work_day}</td><td>{e.event_type}</td><td>{e.method}</td><td>{e.device_id||'—'}</td><td>{e.has_photo?<span className="attm-buttons"><button type="button" onClick={()=>void viewPhoto(e.id)}><Eye size={14}/> View</button><button type="button" disabled={busy} onClick={()=>void deletePhoto(e.id)}><Trash2 size={14}/> Remove photo</button></span>:'—'}</td></tr>)}
   </tbody></table>{!events.length&&<p>No additional attendance capture events yet.</p>}</div>
   {photoUrl&&<div className="attm-evidence"><p>Private photo evidence preview</p><img src={photoUrl} alt="Attendance check-in evidence"/><button type="button" onClick={()=>setPhotoUrl('')}>Close preview</button></div>}
  </section>
  <p className="attm-privacy">Manual check-in/out remains available above. Device enrollment, liveness checks and template management stay with your certified device vendor. HR must obtain appropriate notice and consent or another valid legal basis before enabling biometric devices.</p>
 </div>;
}
