import {useCallback,useEffect,useState} from 'react';
import {AlertCircle,ArrowRight,KeyRound,LockKeyhole,ShieldCheck,Users,Clock3} from 'lucide-react';
import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import './account-security-center.css';

type PersonalRecord={id:number;created_at:string};
type PersonalData={events:PersonalRecord[];retention_days:number;session_hours:number;note:string};
type Account={id:number;code:string;name:string;email:string;role:string;account_active:number;last_login:string|null;successful_logins:number};
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
async function api<T>(path:string,method='GET'):Promise<T>{
  const token=sessionStorage.getItem('sass_token');
  const response=await hrmFetch(API+path,{method,headers:{Authorization:`Bearer ${token||''}`}});
  let payload:any=null;try{payload=await response.json()}catch{}
  if(!response.ok)throw new Error(typeof payload?.detail==='string'?payload.detail:`Request failed (${response.status})`);
  return payload as T;
}
const niceDate=(stamp:string|null)=>{
 if(!stamp)return 'No recorded sign-ins';
 const d=new Date(stamp);return isNaN(d.getTime())?stamp:d.toLocaleString('en-IN',{dateStyle:'medium',timeStyle:'short'});
};
export function AccountSecurityCenter({mode,navigate,onRevoke}:{mode:'me'|'admin';navigate:(page:string)=>void;onRevoke:()=>void}){
 const [mine,setMine]=useState<PersonalData|null>(null);
 const [accounts,setAccounts]=useState<Account[]>([]);
 const [term,setTerm]=useState('');const [query,setQuery]=useState('');
 const [status,setStatus]=useState('all');
 const [error,setError]=useState('');const [loading,setLoading]=useState(false);
 const [revoking,setRevoking]=useState(false);
 const load=useCallback(async()=>{
  setLoading(true);setError('');
  try{if(mode==='me')setMine(await api<PersonalData>('/security/me/activity'));
  else{const params=new URLSearchParams({q:query,status,limit:'100'});
   const result=await api<{items:Account[]}>(`/security/admin/activity?${params}`);setAccounts(result.items);}}
  catch(e){setError((e as Error).message)}finally{setLoading(false)}
 },[mode,query,status]);
 useEffect(()=>{void load()},[load]);useRefreshData(load);
 const revoke=async()=>{
  if(!window.confirm('Sign out every session, including this browser? You will need to sign in again.'))return;
  setRevoking(true);setError('');
  try{await api('/security/me/revoke-all','POST');onRevoke()}
  catch(e){setError((e as Error).message);setRevoking(false)}
 };
 return <section className="sec-center" aria-busy={loading}>
  <div className="sec-head"><span className="sec-label">SASS HRM / IDENTITY SECURITY</span><h1>{mode==='me'?'My Account Security':'Administrator Sign-in Review'}</h1><p>{mode==='me'?'Review your successful sign-ins and revoke your active sessions.':'Review recent successful sign-in activity and accounts needing a login setup.'}</p></div>
  {error&&<div className="sec-error" role="alert"><AlertCircle size={18}/>{error}</div>}
  {mode==='me'?<div className="sec-layout">
   <div className="sec-panel"><div className="sec-panel-title"><Clock3 size={21}/><h2>Successful sign-ins</h2></div><p>Up to your 30 most recent successful sign-ins. Dates display in your browser's timezone.</p>
   <div className="sec-history">{mine?.events.length?mine.events.map((e,i)=><div key={e.id} className="sec-event"><span className="sec-event-dot"/><div><strong>{niceDate(e.created_at)}</strong><small>{i===0?'Most recent sign-in':'Successful sign-in'}</small></div></div>):<p>No login activity has been recorded yet.</p>}</div>
   <small className="sec-note">A record older than {mine?.retention_days||180} days is removed when you next sign in. Older activity may be unavailable.</small></div>
   <div className="sec-panel"><div className="sec-panel-title"><ShieldCheck size={21}/><h2>Session controls</h2></div><p>Normal sign-in sessions expire after eight hours. For security, sign out other browsers when you suspect unauthorized account use.</p>
   <button type="button" className="sec-danger" onClick={()=>void revoke()} disabled={revoking}>{revoking?'Signing out…':'Sign out all sessions'}</button>
   <div className="sec-links"><button onClick={()=>navigate('settings')}><KeyRound size={16}/> Password & workspace settings <ArrowRight size={15}/></button><button onClick={()=>navigate('profile')}><Users size={16}/> My profile <ArrowRight size={15}/></button></div>
   <p className="sec-note">SASS HRM records successful login timestamps only—not passwords, IP addresses, exact device locations, or browser fingerprints. MFA and enterprise SSO are not yet implemented.</p></div>
  </div>:<div className="sec-panel"><div className="sec-panel-title"><LockKeyhole size={20}/><h2>Account sign-in activity</h2></div><p>Read-only administrator review. Manage account creation, suspensions, and password resets from Account Provisioning.</p>
   <form className="sec-filters" onSubmit={e=>{e.preventDefault();setQuery(term)}}><input aria-label="Find account" value={term} maxLength={100} onChange={e=>setTerm(e.target.value)} placeholder="Search name, staff ID or sign-in email"/><select aria-label="Account status" value={status} onChange={e=>setStatus(e.target.value)}><option value="all">All accounts</option><option value="active">Active</option><option value="inactive">Inactive</option><option value="never">No recorded sign-in</option></select><button type="submit">Search accounts</button></form>
   <div className="sec-table-wrap"><table><thead><tr><th>Employee</th><th>Role</th><th>State</th><th>Last successful sign-in</th><th>Recorded sign-ins</th></tr></thead><tbody>{accounts.length?accounts.map(a=><tr key={a.id}><td><strong>{a.name}</strong><small>{a.code}</small></td><td>{a.role}</td><td>{a.account_active?'Active':'Inactive'}</td><td>{niceDate(a.last_login)}</td><td>{a.successful_logins}</td></tr>):<tr><td colSpan={5}>No matching accounts.</td></tr>}</tbody></table></div>
   {accounts.length===100&&<p className="sec-note">Showing the first 100 results. Narrow your search to find a specific account.</p>}
   <div className="sec-links"><button onClick={()=>navigate('accounts')}>Open Account Provisioning <ArrowRight size={15}/></button><button onClick={()=>navigate('audit')}>Open Audit Trail <ArrowRight size={15}/></button></div>
   <p className="sec-note">This page records successful sign-ins only. It cannot determine the exact device, the user's physical location, or all currently open sessions. Login history begins when this upgrade is installed.</p>
  </div>}
 </section>
}
