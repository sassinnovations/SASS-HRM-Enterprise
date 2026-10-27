import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import React, {useEffect, useState} from 'react';
import {Award, BadgeCheck, BookOpenCheck, ShieldCheck, History} from 'lucide-react';
import './culture-enhancements.css';
type Item=Record<string,any>;

const asArray=(value:unknown):Item[] => Array.isArray(value) ? (value as Item[]) : [];
type Page='performance'|'training'|'recognition';
const BASE=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
async function request(path:string,method='GET',body?:unknown){
 const token=sessionStorage.getItem('sass_token');
 let response:Response;
 try{response=await hrmFetch(BASE+path,{method,headers:{'Content-Type':'application/json',...(token?{'Authorization':`Bearer ${token}`}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{})});}
 catch{throw Error('Backend unavailable. Verify /api/health and MySQL connectivity.');}
 let output:Item={};try{output=await response.json()}catch{}
 if(!response.ok)throw Error(typeof output.detail==='string'?output.detail:`Request failed (${response.status})`);
 return output;
}
const readDate=(date:string)=>date?new Date(date).toLocaleString('en-IN'):'—';
export function CultureEnhancements({page,userId,isHR,goals=[],enrollments=[],recognitions=[]}:{page:Page;userId:number;isHR:boolean;goals:Item[];enrollments:Item[];recognitions:Item[]}){
 const [historyId,setHistoryId]=useState<number|null>(null);
 const [history,setHistory]=useState<Item[]>([]);
 const [verifications,setVerifications]=useState<Item[]>([]);
 const [reactions,setReactions]=useState<Item[]>([]);
 const [selectedEnrollment,setSelectedEnrollment]=useState('');
 const [evidence,setEvidence]=useState('');
 const [reviewNotes,setReviewNotes]=useState<Record<number,string>>({});
 const [loading,setLoading]=useState(false),[error,setError]=useState(''),[info,setInfo]=useState('');
 const refresh=async()=>{
  setError('');
  try{
   if(page==='training')setVerifications(asArray(await request('/culture/training/verifications')));
   if(page==='recognition')setReactions(asArray(await request('/culture/recognition/reactions')));
   if(page==='performance'&&historyId)setHistory(asArray(await request(`/culture/goals/${historyId}/history`)));
  }catch(e){setError((e as Error).message)}
 };
 useEffect(()=>{void refresh()},[page,historyId]);
 useRefreshData(refresh);
 const chooseGoal=async(id:number)=>{setHistoryId(id);setHistory([])};
 const submitEvidence=async(event:React.FormEvent)=>{
  event.preventDefault();setLoading(true);setInfo('');setError('');
  try{await request('/culture/training/verifications','POST',{enrollment_id:Number(selectedEnrollment),evidence_note:evidence});
   setEvidence('');setSelectedEnrollment('');setInfo('Training evidence submitted for HR review; not yet verified.');await refresh();
  }catch(e){setError((e as Error).message)}finally{setLoading(false)}
 };
 const verify=async(id:number,decision:'Verified'|'Rejected')=>{
  setLoading(true);setError('');setInfo('');
  try{await request(`/culture/training/verifications/${id}/decision`,'POST',{decision,note:reviewNotes[id]||''});
   setInfo('Review decision saved.');await refresh();
  }catch(e){setError((e as Error).message)}finally{setLoading(false)}
 };
 const applaud=async(id:number)=>{
  setLoading(true);setInfo('');setError('');
  try{await request(`/culture/recognition/${id}/applaud`,'POST');await refresh()}
  catch(e){setError((e as Error).message)}finally{setLoading(false)}
 };
 const completed=enrollments.filter(x=>x.employee_id===userId&&x.status==='Completed'&&!verifications.some(v=>v.enrollment_id===x.id&&['Pending','Verified'].includes(v.status)));
 return <section className="ce-panel" aria-label="Culture operations">
  <div className="ce-heading"><div><div className="ce-eyebrow">SASS HRM / CULTURE OPERATIONS</div><h3>{page==='performance'?'Goal progress history':page==='training'?'Training completion verification':'Team appreciation'}</h3>
   <p>{page==='performance'?'Every goal progress change is recorded with its actor and timestamp.':page==='training'?'Course completion is employee-reported until HR reviews evidence.':'Colleagues can applaud genuine recognitions; your own recognition cannot be self-applauded.'}</p></div>
   </div>
  {error&&<div role="alert" className="ce-alert">{error}</div>}{info&&<div role="status" className="ce-success">{info}</div>}
  {page==='performance'&&<div className="ce-grid"><div><label className="ce-label" htmlFor="ce-goal">Select a goal</label><select id="ce-goal" value={historyId||''} onChange={e=>void chooseGoal(Number(e.target.value))}><option value="">Select a goal</option>{goals.map(g=><option key={g.id} value={g.id}>{g.employee_name}: {g.title}</option>)}</select><div className="ce-notice"><History size={16}/> These records are read-only; use the goal progress control above to update them.</div></div><div className="ce-records">{historyId ? history.length?history.map(h=><div key={h.id} className="ce-record"><b>{h.old_progress}% → {h.new_progress}%</b><span>{h.actor_name} · {readDate(h.created_at)}</span>{h.note&&<p>{h.note}</p>}</div>):<p>No progress changes recorded for this goal yet.</p>:<p>Select a goal to review its history.</p>}</div></div>}
  {page==='training'&&<><div className="ce-grid"><form onSubmit={submitEvidence} className="ce-form"><h4><BookOpenCheck size={17}/> Submit evidence</h4><label className="ce-label" htmlFor="ce-enrollment">My completed course</label><select required id="ce-enrollment" value={selectedEnrollment} onChange={e=>setSelectedEnrollment(e.target.value)}><option value="">Select a completed course</option>{completed.map(x=><option key={x.id} value={x.id}>{x.course_title}</option>)}</select><label className="ce-label" htmlFor="ce-evidence">Evidence description</label><textarea id="ce-evidence" required minLength={12} maxLength={1500} rows={3} value={evidence} placeholder="Describe training completion evidence; avoid private identity documents" onChange={e=>setEvidence(e.target.value)}/><button className="ce-primary" disabled={loading||!completed.length} type="submit">Request HR verification</button>{!completed.length&&<small>Complete an enrolled course first, or wait for your existing review.</small>}</form>
  <div><h4><ShieldCheck size={17}/> Review status</h4><div className="ce-records">{verifications.length?verifications.map(v=><div className="ce-record" key={v.id}><b>{v.course_title} — {v.status}</b><span>{v.employee_name} · {readDate(v.submitted_at)}</span><p>{v.status==='Pending'?'Awaiting an HR verification decision.':v.status==='Verified'?'HR verified course completion.':'Evidence was rejected. You may resubmit.'}</p>{isHR&&v.status==='Pending'&&v.employee_id!==userId&&<div className="ce-review"><label className="ce-label" htmlFor={`ce-review-${v.id}`}>Human review notes</label><textarea id={`ce-review-${v.id}`} rows={2} minLength={8} value={reviewNotes[v.id]||''} onChange={e=>setReviewNotes(x=>({...x,[v.id]:e.target.value}))}/><div className="ce-buttons"><button className="ce-primary" disabled={loading||(reviewNotes[v.id]||'').trim().length<8} onClick={()=>void verify(v.id,'Verified')}>Verify</button><button className="ce-secondary" disabled={loading||(reviewNotes[v.id]||'').trim().length<8} onClick={()=>void verify(v.id,'Rejected')}>Reject</button></div></div>}</div>):<p>No verification requests yet.</p>}</div></div></div><div className="ce-notice"><ShieldCheck size={16}/> This workflow records HR review; it does not automatically issue accredited certificates.</div></>}
  {page==='recognition'&&<div className="ce-feed">{recognitions.length?recognitions.map(r=>{const entry=reactions.find(x=>x.recognition_id===r.id);const canReact=r.sender_id!==userId&&r.recipient_id!==userId;return <div className="ce-record" key={r.id}><b>{r.recipient_name} — {r.value}</b><p>{r.message}</p><span>From {r.sender_name} · {readDate(r.created_at)}</span><div className="ce-buttons"><button type="button" className="ce-secondary" disabled={!canReact||loading} onClick={()=>void applaud(r.id)}><Award size={15}/>{entry?.mine?'Remove applause':'Applaud'}</button><span><BadgeCheck size={15}/> {entry?.total||0} colleagues applauded</span></div></div>}):<p>No recognition messages yet. Start by recognizing a colleague.</p>}</div>}
 </section>
}
