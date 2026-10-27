import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import React, {useEffect,useState} from 'react';
import {AlertCircle,CheckCircle2,Database,Download,UploadCloud,Building2,ShieldCheck,ArrowRight} from 'lucide-react';
import './admin-setup.css';

type Summary={database_engine:string;backend_version?:string;completed:number;total:number;checks:{key:string;label:string;ready:boolean;hint:string}[];counts:Record<string,number>};
type Profile={name:string;legal_name:string;country:string;timezone:string;contact_email:string;website:string};
type EmployeeRow={code:string;name:string;email:string;designation:string;department:string;location:string;work_mode:string;role:string;join_date:string};
type Validation={total:number;valid:number;errors:{row:number;code:string;issues:string[]}[];can_import:boolean};
const fields=['code','name','email','designation','department','location','work_mode','role','join_date'] as const;
const template=fields.join(',')+'\r\n';
const initialProfile:Profile={name:'',legal_name:'',country:'India',timezone:'Asia/Kolkata',contact_email:'',website:''};
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
const FRONTEND_RELEASE='4.5.0';
async function request<T>(path:string,method='GET',body?:unknown):Promise<T>{
 const token=sessionStorage.getItem('sass_token');
 const response=await hrmFetch(API+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{})});
 if(!response.ok){let details:any={};try{details=await response.json()}catch{};
   const detail=typeof details.detail==='string'?details.detail:typeof details.detail?.message==='string'?details.detail.message:`HTTP ${response.status}`;
   throw Error(detail);
 }
 return response.json() as Promise<T>;
}
function parseCSV(text:string):string[][]{
 // RFC-4180 quoting, including commas, escaped quotes and newlines in quoted cells.
 const output:string[][]=[];let row:string[]=[];let current='';let quoted=false;
 const source=text.replace(/^\uFEFF/,'');
 for(let i=0;i<source.length;i++){
  const char=source[i];
  if(char==='"'){if(quoted&&source[i+1]==='"'){current+='"';i++}else quoted=!quoted;}
  else if(char===','&&!quoted){row.push(current);current='';}
  else if((char==='\r'||char==='\n')&&!quoted){row.push(current);if(row.some(value=>value.trim()!==''))output.push(row);row=[];current='';if(char==='\r'&&source[i+1]==='\n')i++;}
  else current+=char;
 }
 if(quoted)throw Error('Unclosed quoted cell in CSV');
 row.push(current);if(row.some(value=>value.trim()!==''))output.push(row);
 return output;
}
function makeDownload(content:string,name:string,mime:string){const blob=new Blob([content],{type:mime});const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),500)}

export function AdminSetupCenter({navigate,onChanged}:{navigate:(page:string)=>void;onChanged:()=>Promise<void>}){
 const[profile,setProfile]=useState<Profile>(initialProfile);const[summary,setSummary]=useState<Summary|null>(null);
 const[records,setRecords]=useState<EmployeeRow[]>([]);const[validation,setValidation]=useState<Validation|null>(null);
 const[busy,setBusy]=useState(false);const[error,setError]=useState('');const[notice,setNotice]=useState('');
 async function load(){try{const [p,s]=await Promise.all([request<Profile|null>('/admin/organization-profile'),request<Summary>('/admin/setup/overview')]);setSummary(s);if(p)setProfile(p)}catch(err){setError((err as Error).message)}}
 useEffect(()=>{load()},[]);
 useRefreshData(load);
 async function save(e:React.FormEvent){e.preventDefault();if(!safeConnection){setError('MySQL backend and release v4.5.0 must be verified before saving records. Run DIAGNOSE_CONNECTION.bat.');return}setBusy(true);setError('');setNotice('');try{
  await request('/admin/organization-profile','PUT',profile);setNotice('Company profile saved and recorded in the audit trail.');await load();
 }catch(err){setError((err as Error).message)}finally{setBusy(false)}}
 async function fileSelected(file?:File){setValidation(null);setRecords([]);setError('');setNotice('');if(!file)return;
  try{if(file.size>250_000)throw Error('Maximum file size is 250 KB. Import up to 250 employees at a time.');
   const contents=parseCSV(await file.text());if(!contents.length)throw Error('CSV is empty');
   const header=contents.shift()!.map(x=>x.trim().toLowerCase());
   if(header.length!==fields.length||fields.some((f,i)=>header[i]!==f))throw Error('CSV columns must match the downloaded template in the same order');
   if(contents.length<1||contents.length>250)throw Error('Add 1 to 250 employees per CSV');
   const parsed=contents.map((line,i)=>{if(line.length!==fields.length)throw Error(`Row ${i+2}: expected ${fields.length} columns`);
    return Object.fromEntries(line.map((value,j)=>[fields[j],value.trim()])) as EmployeeRow});
   setRecords(parsed);setNotice(`Parsed ${parsed.length} employee record(s). Select Preview validation before committing.`);
  }catch(err){setError((err as Error).message)}}
 async function preview(){if(!safeConnection){setError('Database not verified. Run DIAGNOSE_CONNECTION.bat before importing.');return}setBusy(true);setError('');try{setValidation(await request<Validation>('/admin/employees/import/preview','POST',{records}));setNotice('Validation completed. No records have been written yet.')}catch(err){setError((err as Error).message)}finally{setBusy(false)}}
 async function commit(){if(!safeConnection||!validation?.can_import)return; if(!window.confirm(`Create ${records.length} inactive employee records? You will need to send secure invitations separately.`))return;
  setBusy(true);setError('');try{const result=await request<{message:string;created:number}>('/admin/employees/import/commit','POST',{records,confirm:'IMPORT'});
   setNotice(`${result.created} employee accounts created. ${result.message}`);setValidation(null);setRecords([]);await load();await onChanged();
  }catch(err){setError((err as Error).message);setValidation(null)}finally{setBusy(false)}}
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
  <section className="section-card setup-card"><div className="section-heading"><div><h3>Employee import</h3><p>Review employee records before committing them. All new accounts remain inactive until individual activation.</p></div><button className="btn outline" onClick={()=>makeDownload(template,'sass-hrm-employee-template.csv','text/csv;charset=utf-8')}><Download size={16}/> Download CSV template</button></div>
   <div className="setup-import-info"><ShieldCheck size={19}/> Employee files are processed in your browser for preview, and records are saved only after administrator confirmation. No passwords should appear in the CSV.</div>
   <div className="setup-import-controls"><label className="setup-file-label"><UploadCloud size={19}/> Choose an employee CSV<input aria-label="Select employee CSV" type="file" accept=".csv,text/csv" onChange={e=>{fileSelected(e.target.files?.[0]);e.currentTarget.value=''}}/></label><button className="btn outline" disabled={busy||!safeConnection||!records.length} onClick={preview}>Preview validation</button><button className="btn primary" disabled={busy||!safeConnection||!validation?.can_import} onClick={commit}>Import {validation?.valid||records.length} employees <ArrowRight size={15}/></button></div>
   {records.length>0&&<p className="setup-preview-count">{records.length} records loaded from CSV · no changes saved yet</p>}
   {validation&&<div className="setup-validation"><strong>{validation.valid} valid / {validation.total} total rows</strong>{validation.errors.length>0?<div className="setup-validation-errors">{validation.errors.map(e=><p key={e.row}>Row {e.row} ({e.code}): {e.issues.join('; ')}</p>)}</div>:<p>All rows passed current database and input validation. Revalidation occurs when you import.</p>}</div>}
   <div className="setup-import-nav"><button onClick={()=>navigate('organization')}>1. Set up departments <ArrowRight size={14}/></button><button onClick={()=>navigate('employees')}>2. Review employee directory <ArrowRight size={14}/></button><button onClick={()=>navigate('accounts')}>3. Send account invitations <ArrowRight size={14}/></button><button onClick={()=>navigate('audit')}>4. Check audit trail <ArrowRight size={14}/></button></div>
  </section>
  <p className="setup-footer-note">Readiness checks are operational indicators—not certifications of security, statutory payroll, or legal compliance. Configure MySQL, SMTP, backups and security controls before using real employee data.</p>
 </div>;
}
