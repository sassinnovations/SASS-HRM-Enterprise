import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import React, {useEffect,useState} from 'react';
import {AlertCircle,CheckCircle2,Database,UploadCloud,Building2,ShieldCheck,ArrowRight,Settings2,UsersRound,ClipboardCheck} from 'lucide-react';
import {DataQualityImporter} from './DataQualityImporter';
import './data-quality-center.css';
import './admin-setup.css';

type Summary={database_engine:string;backend_version?:string;completed:number;total:number;checks:{key:string;label:string;ready:boolean;hint:string}[];counts:Record<string,number>};
type Profile={name:string;legal_name:string;country:string;timezone:string;contact_email:string;website:string};
const initialProfile:Profile={name:'',legal_name:'',country:'India',timezone:'Asia/Kolkata',contact_email:'',website:''};
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
const FRONTEND_RELEASE='4.8.0';
async function request<T>(path:string,method='GET',body?:unknown):Promise<T>{
 const token=sessionStorage.getItem('sass_token');
 const response=await hrmFetch(API+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{})});
 if(!response.ok){let details:any={};try{details=await response.json()}catch{};
  const detail=typeof details.detail==='string'?details.detail:typeof details.detail?.message==='string'?details.detail.message:`HTTP ${response.status}`;
  throw Error(detail);
 }
 return response.json() as Promise<T>;
}
export function AdminSetupCenter({navigate,onChanged}:{navigate:(page:string)=>void;onChanged:()=>Promise<void>}){
 const[profile,setProfile]=useState<Profile>(initialProfile);const[summary,setSummary]=useState<Summary|null>(null);
 const[busy,setBusy]=useState(false);const[error,setError]=useState('');const[notice,setNotice]=useState('');
 async function load(){try{const [p,s]=await Promise.all([request<Profile|null>('/admin/organization-profile'),request<Summary>('/admin/setup/overview')]);setSummary(s);if(p)setProfile(p)}catch(err){setError((err as Error).message)}}
 useEffect(()=>{load()},[]);
 useRefreshData(load);
 async function save(e:React.FormEvent){e.preventDefault();if(!safeConnection){setError('MySQL backend and release v4.8.0 must be verified before saving records. Run DIAGNOSE_CONNECTION.bat.');return}setBusy(true);setError('');setNotice('');try{
  await request('/admin/organization-profile','PUT',profile);setNotice('Company profile saved and recorded in the audit trail.');await load();
 }catch(err){setError((err as Error).message)}finally{setBusy(false)}}
 const safeConnection=summary?.database_engine==='mysql'&&summary?.backend_version===FRONTEND_RELEASE;
 const staleOrTesting=!!summary&&!safeConnection;
 const control:React.CSSProperties={width:'100%'};
 return <div className="setup-page">
  <div className="setup-hero"><div><span className="eyebrow">SASS HRM / ORGANIZATION ADMINISTRATION</span><h1>Company setup & HRIS import</h1><p>Set up your real organization, check service readiness, and onboard employees with a validated, database-backed import. No sample people or credentials are added.</p></div></div>
  {staleOrTesting&&<div role="alert" className="setup-connection-alert"><AlertCircle size={22}/><div><strong>MySQL backend not verified — writes are paused here</strong><p>This page is connected to {summary?.database_engine?.toUpperCase()||'an unknown database'} · API version {summary?.backend_version||'unreported (older backend)'}. Expected MySQL and API {FRONTEND_RELEASE}. Stop old backend/Vite processes, run the current START_HERE.bat, then DIAGNOSE_CONNECTION.bat. Do not import employee details into a testing database.</p></div></div>}
  {error&&<div role="alert" className="setup-message setup-error"><AlertCircle size={17}/>{error}</div>}
  {notice&&<div role="status" className="setup-message setup-success"><CheckCircle2 size={17}/>{notice}</div>}
  <div className="setup-grid">
   <section className="section-card setup-card"><div className="section-heading"><div><h3>Deployment readiness</h3><p>Each check reflects stored records or current configuration.</p></div><span className="setup-completion">{summary?`${summary.completed}/${summary.total}`:'—'}</span></div>
    <div className="setup-checks">{summary?.checks.map(check=><div key={check.key} className="setup-check"><span className={check.ready?'setup-ready':'setup-pending'}>{check.ready?<CheckCircle2 size={18}/>:<AlertCircle size={18}/>}</span><div><strong>{check.label}</strong><small>{check.ready?'Configured':check.hint}</small>{!check.ready&&({departments:'organization',employees:'employees',leave:'leave',policies:'policies'} as Record<string,string>)[check.key]&&<button type="button" className="setup-fix-link" onClick={()=>navigate(({departments:'organization',employees:'employees',leave:'leave',policies:'policies'} as Record<string,string>)[check.key])}>Open {check.label} <ArrowRight size={13}/></button>}</div></div>)}</div>
    <div className="setup-db"> <Database size={18}/> Database engine: <strong>{summary?.database_engine?.toUpperCase()||'Checking…'}</strong><span className="setup-api-version">API {summary?.backend_version||'legacy'} · Web {FRONTEND_RELEASE}</span>{staleOrTesting&&<span className="setup-db-warning">Not ready — use the verified Docker/MySQL stack.</span>}</div>
   </section>
   <section className="section-card setup-card"><div className="section-heading"><div><h3>Organization profile</h3><p>Official company identity, contact and timezone.</p></div><Building2 size={19}/></div>
    <form onSubmit={save} className="setup-profile-form">
     {([['name','Display name'],['legal_name','Legal registered company name'],['country','Country'],['timezone','Timezone (IANA, e.g. Asia/Kolkata)'],['contact_email','HR contact email'],['website','Company website (https://)']] as [keyof Profile,string][]).map(([key,label])=><label key={key}>{label}<input style={control} value={profile[key]} maxLength={key==='website'?250:180} type={key==='contact_email'?'email':'text'} required={key!=='website'} placeholder={label} onChange={e=>setProfile(x=>({...x,[key]:e.target.value}))}/></label>)}
     <button type="submit" className="btn primary" disabled={busy||!safeConnection}><ShieldCheck size={16}/> {busy?'Saving…':'Save company profile'}</button>
    </form>
   </section>
  </div>
  <section className="section-card setup-card setup-import-hub" aria-label="Company setup configuration">
   <div className="section-heading"><div><h3>Company setup & HRIS settings</h3><p>Configure the organization and review employees before onboarding. Settings are saved to the existing MySQL-backed HRM services.</p></div><Settings2 size={19}/></div>
   <div className="setup-config-grid">
    <button type="button" onClick={()=>navigate('orgsettings')}><Building2 size={19}/><strong>Organization settings</strong><small>Departments, offices, business units and company preferences</small><ArrowRight size={15}/></button>
    <button type="button" onClick={()=>navigate('accounts')}><UsersRound size={19}/><strong>Account provisioning</strong><small>Invite, activate and manage employee accounts and access</small><ArrowRight size={15}/></button>
    <button type="button" onClick={()=>navigate('dataquality')}><ClipboardCheck size={19}/><strong>Data quality center</strong><small>Review validation findings, import issues and monitoring rules</small><ArrowRight size={15}/></button>
    <button type="button" onClick={()=>navigate('audit')}><ShieldCheck size={19}/><strong>Audit trail</strong><small>Review administrative changes and onboarding activity</small><ArrowRight size={15}/></button>
   </div>
  </section>
  <DataQualityImporter onImported={onChanged}/>
  <section className="section-card setup-card"><div className="section-heading"><div><h3>Onboarding steps</h3><p>Complete setup in order before activating imported accounts.</p></div><UploadCloud size={19}/></div>
   <div className="setup-import-nav"><button type="button" onClick={()=>navigate('organization')}>1. Set up departments <ArrowRight size={14}/></button><button type="button" onClick={()=>navigate('employees')}>2. Review employee directory <ArrowRight size={14}/></button><button type="button" onClick={()=>navigate('accounts')}>3. Send account invitations <ArrowRight size={14}/></button><button type="button" onClick={()=>navigate('audit')}>4. Check audit trail <ArrowRight size={14}/></button></div>
  </section>
  <p className="setup-footer-note">Readiness checks are operational indicators—not certifications of security, statutory payroll, or legal compliance. Configure MySQL, SMTP, backups and security controls before using real employee data.</p>
 </div>;
}
