import {useCallback,useEffect,useState} from 'react';
import type {FormEvent} from 'react';
import {hrmFetch} from './apiTransport';
import {REFRESH_DATA_EVENT} from './useRefreshData';
import './signup-v46.css';

type SignupPolicy={enabled:boolean;allow_employee:boolean;allow_hr_subadmin:boolean;allow_admin:boolean;allowed_email_domain:string;updated_at:string};
const defaultPolicy:SignupPolicy={enabled:true,allow_employee:true,allow_hr_subadmin:true,allow_admin:true,allowed_email_domain:'',updated_at:''};

export function SignupSettingsPanel(){
 const [policy,setPolicy]=useState<SignupPolicy>(defaultPolicy);
 const [loading,setLoading]=useState(true);const [saving,setSaving]=useState(false);
 const [error,setError]=useState('');const [message,setMessage]=useState('');
 const load=useCallback(async()=>{
  setLoading(true);
  try{const token=sessionStorage.getItem('sass_token');
   const r=await hrmFetch(url('/admin/signup-settings'),{headers:{Authorization:`Bearer ${token}`}});
   if(!r.ok)throw Error(`Cannot load registration settings (HTTP ${r.status})`);
   setPolicy(await r.json());setError('');
  }catch(e){setError((e as Error).message)}finally{setLoading(false)}
 },[]);
 useEffect(()=>{void load()},[load]);
 const save=async(e:FormEvent)=>{e.preventDefault();setSaving(true);setError('');setMessage('');
  try{const token=sessionStorage.getItem('sass_token');const r=await hrmFetch(url('/admin/signup-settings'),{method:'PUT',headers:{'Content-Type':'application/json',Authorization:`Bearer ${token}`},body:JSON.stringify(policy)});
   if(!r.ok){const b=await r.json().catch(()=>({detail:'Could not save policy'}));throw Error(typeof b.detail==='string'?b.detail:'Could not save policy')}
   setPolicy(await r.json());setMessage('Saved. The public signup form now follows these settings.');
  }catch(e){setError((e as Error).message)}finally{setSaving(false)}
 };
 const toggle=(name:'enabled'|'allow_employee'|'allow_hr_subadmin'|'allow_admin',value:boolean)=>setPolicy(p=>({...p,[name]:value}));
 return <section className="section-card signup-settings" aria-label="Account signup settings">
  <div className="section-heading"><div><h3>Public sign-up settings</h3><p>Choose which account types applicants can request from the sign-in screen. Approval is required for every role.</p></div></div>
  {error&&<p role="alert" className="sass-form-error">{error}</p>}{message&&<p role="status" className="signup-success">{message}</p>}
  {loading?<p>Loading registration settings…</p>:<form onSubmit={save} className="signup-settings-form">
   <label className="signup-policy-check"><input type="checkbox" checked={policy.enabled} onChange={e=>toggle('enabled',e.target.checked)}/><span><strong>Enable public account requests</strong><small>Switch off to close the signup form without affecting existing accounts.</small></span></label>
   <div className="signup-settings-options">
    {([['allow_employee','Employee'],['allow_hr_subadmin','HR Sub-Admin'],['allow_admin','HR Administrator']] as const).map(([key,label])=><label key={key} className="signup-policy-check"><input type="checkbox" checked={policy[key]} disabled={!policy.enabled} onChange={e=>toggle(key,e.target.checked)}/><span>{label}</span></label>)}
   </div>
   <label className="signup-domain-setting">Company email domain (optional)<input type="text" placeholder="example.com" maxLength={191} value={policy.allowed_email_domain} onChange={e=>setPolicy(p=>({...p,allowed_email_domain:e.target.value}))}/><small>When set, both sign-in and work email must use this domain. This is not proof of email ownership.</small></label>
   <button type="submit" className="btn primary" disabled={saving}>{saving?'Saving…':'Save signup settings'}</button>
   <p className="signup-admin-guidance">An existing HR administrator must independently verify identity and authority before approval. Do not use this form to automatically create administrators.</p>
  </form>}
 </section>
}

type RequestRow={id:number;name:string;email:string;work_email:string;requested_role:string;department:string;designation:string;location:string;work_mode:string;status:string;created_at:string;reviewed_at:string|null;review_note:string|null;employee_id:number|null};
const url=(path:string)=>(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api'+path;
const roleName=(role:string)=>role==='admin'?'HR Administrator':role==='hr_subadmin'?'HR Sub-Admin':'Employee';

export function SignupApprovalQueue(){
 const [rows,setRows]=useState<RequestRow[]>([]);
 const [filter,setFilter]=useState<'Pending'|'Approved'|'Rejected'|'Expired'|'All'>('Pending');
 const [busy,setBusy]=useState<number|null>(null);
 const [error,setError]=useState('');const [notice,setNotice]=useState('');
 const load=useCallback(async()=>{
  try{const token=sessionStorage.getItem('sass_token');if(!token)return;
   const resp=await hrmFetch(url('/admin/signup-requests?status='+filter),{headers:{Authorization:`Bearer ${token}`}});
   if(!resp.ok)throw Error(`Could not load account requests (HTTP ${resp.status})`);
   setRows(await resp.json());setError('');
  }catch(e){setError((e as Error).message)}
 },[filter]);
 useEffect(()=>{void load();window.addEventListener(REFRESH_DATA_EVENT,load);return()=>window.removeEventListener(REFRESH_DATA_EVENT,load)},[load]);
 const review=async(row:RequestRow,decision:'Approved'|'Rejected')=>{
  if(busy!==null)return;
  if(!window.confirm(decision==='Approved'?`Have you VERIFIED ${row.name}'s identity and authorization for ${roleName(row.requested_role)}? Approving grants access to SASS HRM.`:`Reject ${row.name}'s account request?`))return;
  const note=decision==='Approved'&&row.requested_role==='admin'
   ?window.prompt('Provide a brief record of how you verified this administrator applicant and their authorization:')
   :'';
  if(decision==='Approved'&&row.requested_role==='admin'&&(!note||!note.trim()))return;
  setBusy(row.id);setError('');setNotice('');
  try{const token=sessionStorage.getItem('sass_token');
   const res=await hrmFetch(url(`/admin/signup-requests/${row.id}/review`),{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${token}`},body:JSON.stringify({decision,identity_verified:true,review_note:note||''})});
   if(!res.ok){const b=await res.json().catch(()=>({detail:'Request failed'}));throw Error(typeof b.detail==='string'?b.detail:'Unable to review request')}
   setNotice(decision==='Approved'?`${row.name} is now an active SASS HRM account. They can sign in with the password they selected.`:`${row.name}'s request was rejected.`);
   await load();
  }catch(e){setError((e as Error).message)}finally{setBusy(null)}
 };
 return <section className="section-card signup-approval" aria-label="Public account requests">
  <div className="section-heading"><div><h3>Sign-up requests awaiting HR approval</h3><p>Applications submitted from the login page · verify identity before granting any employee or administrator access</p></div>
  <label className="signup-approval-filter">Status <select aria-label="Filter sign-up requests" value={filter} onChange={e=>setFilter(e.target.value as typeof filter)}><option>Pending</option><option>Approved</option><option>Rejected</option><option>Expired</option><option>All</option></select></label></div>
  {notice&&<p role="status" className="signup-success">{notice}</p>}{error&&<p role="alert" className="sass-form-error">{error}</p>}
  <div className="signup-table-wrap"><table><thead><tr><th>Applicant</th><th>Emails</th><th>Requested role</th><th>Work details</th><th>Submitted</th><th>Status / action</th></tr></thead><tbody>
   {rows.map(r=><tr key={r.id}><td><strong>{r.name}</strong><small>Request #{r.id}</small></td><td>{r.email}{r.work_email!==r.email&&<small>{r.work_email}</small>}</td><td>{roleName(r.requested_role)}</td><td>{r.department} · {r.designation}<small>{r.location} · {r.work_mode}</small></td><td>{r.created_at.slice(0,10)}</td><td>{r.status==='Pending'?<div className="signup-review-actions"><button type="button" disabled={busy!==null} className="btn primary" onClick={()=>review(r,'Approved')}>Verify &amp; approve</button><button type="button" disabled={busy!==null} className="btn outline" onClick={()=>review(r,'Rejected')}>Reject</button></div>:<span>{r.status}{r.employee_id&&` · Employee #${r.employee_id}`}</span>}</td></tr>)}
   {!rows.length&&<tr><td colSpan={6} className="signup-no-requests">No {filter==='All'?'':filter.toLowerCase()+' '}account requests found.</td></tr>}
  </tbody></table></div>
  <p className="signup-admin-guidance">The application password is never shown to HR. Requests expire for approval after 14 days. Applicants cannot log in or gain administrator privileges before explicit approval. For public deployment, configure CAPTCHA or an API gateway rate limit.</p>
 </section>
}
