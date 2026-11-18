import {useCallback,useEffect,useState} from 'react';
import {CheckCircle2,Download,FileSpreadsheet,Settings2,ShieldCheck,UploadCloud} from 'lucide-react';
import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';

const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api/admin/data-quality/import';
const ROOT_API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
const FRONTEND_RELEASE='4.8.0';
const FIELDS=['code','name','email','designation','department','location','join_date','role','work_mode'] as const;
type FieldName=typeof FIELDS[number];
type ImportSettings={mapping:Record<FieldName,string>;duplicate_mode:'reject'|'skip';date_format:'YYYY-MM-DD'|'DD/MM/YYYY'|'MM/DD/YYYY';sheet_name:string;default_role:'employee'|'manager';default_work_mode:'On-site'|'Hybrid'|'Remote';trim_values:boolean;skip_blank_rows:boolean;max_rows:number};
type Preview={columns:string[];total:number;valid:number;skipped:number;errors:{row:number;issues:string[]}[];error_count:number;sample:{row:number;code:string;name:string;department:string}[];preview_token:string};
type History={id:number;filename:string;source_rows:number;created_rows:number;duplicate_rows:number;actor_id:number;created_at:string};
const INITIAL:ImportSettings={mapping:Object.fromEntries(FIELDS.map(f=>[f,f])) as Record<FieldName,string>,duplicate_mode:'reject',date_format:'YYYY-MM-DD',sheet_name:'',default_role:'employee',default_work_mode:'On-site',trim_values:true,skip_blank_rows:true,max_rows:1000};
const ALIASES:Partial<Record<FieldName,string[]>>={code:['employee_code','staff_code','employee id','emp_code'],name:['employee_name','official_name','full_name','full name'],email:['work_email','email_address','official_email'],designation:['job_title','position'],department:['team','business_unit'],location:['office','office_location'],join_date:['date_of_joining','joining_date','doj'],role:['access_role'],work_mode:['working_mode']};
const NAMES:Record<FieldName,string>={code:'Employee code',name:'Official name',email:'Work email',designation:'Designation',department:'Department',location:'Office / location',join_date:'Joining date',role:'Account role',work_mode:'Work mode'};
function token(){return sessionStorage.getItem('sass_token')||''}
async function get<T>(path:string):Promise<T>{
 const res=await hrmFetch(API+path,{headers:{Authorization:`Bearer ${token()}`},cache:'no-store'});
 const body=await res.json().catch(()=>null);
 if(!res.ok)throw Error(typeof body?.detail==='string'?body.detail:`Request failed (${res.status})`);
 return body as T;
}
async function sendJson<T>(path:string,body:unknown):Promise<T>{
 const res=await hrmFetch(API+path,{method:'PUT',headers:{Authorization:`Bearer ${token()}`,'Content-Type':'application/json'},body:JSON.stringify(body)});
 const output=await res.json().catch(()=>null);
 if(!res.ok)throw Error(typeof output?.detail==='string'?output.detail:`Request failed (${res.status})`);
 return output as T;
}
async function sendFile<T>(path:string,file:File,headers:Record<string,string>={}):Promise<T>{
 const res=await hrmFetch(API+path,{method:'POST',headers:{Authorization:`Bearer ${token()}`,'x-filename':encodeURIComponent(file.name),...headers},body:file,cache:'no-store'});
 const output=await res.json().catch(()=>null);
 if(!res.ok)throw Error(typeof output?.detail==='string'?output.detail:`Request failed (${res.status})`);
 return output as T;
}
export function DataQualityImporter({onImported}:{onImported?:()=>Promise<void>}={}){
 const [expanded,setExpanded]=useState(false);
 const [settings,setSettings]=useState<ImportSettings>(INITIAL);
 const [file,setFile]=useState<File|null>(null);
 const [columns,setColumns]=useState<string[]>([]);
 const [preview,setPreview]=useState<Preview|null>(null);
 const [history,setHistory]=useState<History[]>([]);
 const [confirm,setConfirm]=useState('');
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const [message,setMessage]=useState('');
 const [safeConnection,setSafeConnection]=useState(false);
 const [connectionChecked,setConnectionChecked]=useState(false);
 const replacePreview=(p:Preview|null)=>{setPreview(p);if(!p)setConfirm('')};
 const validation=preview?{can_import:!preview.error_count&&Boolean(preview.preview_token)&&preview.valid>0&&confirm==='IMPORT'}:null;
 const refresh=useCallback(async()=>{
  try{
   const [saved,imports]=await Promise.all([get<ImportSettings>('/settings'),get<History[]>('/history')]);
   setSettings(saved);setHistory(imports);
   const overviewRes=await hrmFetch(ROOT_API+'/admin/setup/overview',{headers:{Authorization:`Bearer ${token()}`},cache:'no-store'});
   const overview=await overviewRes.json().catch(()=>null);
   setSafeConnection(overviewRes.ok&&overview?.database_engine==='mysql'&&overview?.backend_version===FRONTEND_RELEASE);
  }catch(e){setError((e as Error).message);setSafeConnection(false)}
  finally{setConnectionChecked(true)}
 },[]);
 useEffect(()=>{void refresh()},[refresh]);useRefreshData(refresh);
 const run=async(job:()=>Promise<void>)=>{setError('');setMessage('');setBusy(true);try{await job()}catch(e){setError((e as Error).message)}finally{setBusy(false)}};
 const edit=(patch:Partial<ImportSettings>)=>{setSettings(s=>({...s,...patch}));replacePreview(null);setConfirm('')};
 const inspect=()=>void run(async()=>{
  if(!file)throw Error('Choose a CSV or XLSX file first.');
  if(!safeConnection)throw Error('MySQL backend and release v4.8.0 must be verified before importing. Run DIAGNOSE_CONNECTION.bat.');
  const result=await sendFile<{columns:string[];file_rows:number}>('/columns',file);
  setColumns(result.columns);setSettings(current=>{const next={...current.mapping};for(const field of FIELDS){if(result.columns.some(h=>h.toLowerCase()===next[field].toLowerCase()))continue;const match=result.columns.find(h=>[field,...(ALIASES[field]||[])].some(alias=>alias.toLowerCase()===h.toLowerCase()));if(match)next[field]=match}return {...current,mapping:next}});replacePreview(null);setConfirm('');setMessage(`${result.columns.length} columns found; ${result.file_rows} worksheet rows. Check your column mapping and preview.`);
 });
 const save=()=>void run(async()=>{
  if(!safeConnection)throw Error('MySQL backend and release v4.8.0 must be verified before importing. Run DIAGNOSE_CONNECTION.bat.');
  await sendJson('/settings',settings);replacePreview(null);setConfirm('');setMessage('Import settings saved and audited. Preview your file with these settings.');
 });
 const preflight=()=>void run(async()=>{
  if(!file)throw Error('Choose a CSV or XLSX file first.');
  if(!safeConnection)throw Error('MySQL backend and release v4.8.0 must be verified before importing. Run DIAGNOSE_CONNECTION.bat.');
  // Save first so the backend preview and confirmation use exactly these choices.
  await sendJson('/settings',settings);
  const p=await sendFile<Preview>('/preview',file);
  replacePreview(p);setConfirm('');setMessage(p.error_count?`${p.error_count} validation issues. Nothing was imported.`:`Preview ready: ${p.valid} new records, ${p.skipped} duplicates skipped.`);
 });
 const commit=()=>void run(async()=>{
  if(!safeConnection||!validation?.can_import||!file||!preview?.preview_token||preview.error_count||confirm!=='IMPORT')throw Error('Preview successfully and type IMPORT before continuing.');
  const result=await sendFile<{created:number;skipped:number;message:string}>('/commit',file,{'x-import-preview-token':preview.preview_token,'x-import-confirm':'IMPORT'});
  setMessage(`${result.created} inactive employee accounts created; ${result.skipped} duplicates skipped. Invite employees separately in Account Provisioning.`);
  replacePreview(null);setConfirm('');setFile(null);setColumns([]);
  setHistory(await get<History[]>('/history'));
  if(onImported)await onImported();
 });
 const downloadTemplate=()=>void run(async()=>{
  const resp=await hrmFetch(API+'/template.csv',{headers:{Authorization:`Bearer ${token()}`},cache:'no-store'});
  if(!resp.ok)throw Error('Could not download the import template.');
  const u=URL.createObjectURL(await resp.blob());
  const a=document.createElement('a');a.href=u;a.download='sass-hrm-employee-import-template.csv';document.body.append(a);a.click();a.remove();URL.revokeObjectURL(u);
 });
 return <section className="dq-panel dq-import" aria-label="Employee HRIS import settings">
  <div className="dq-import-heading"><div><h2>Employee HRIS import & settings</h2><p>Import employee master data from CSV or Excel. All uploads are previewed first; existing employees are never overwritten and new accounts remain inactive.</p></div><button type="button" aria-expanded={expanded} onClick={()=>setExpanded(s=>!s)}><UploadCloud size={16}/>{expanded?'Close importer':'Open importer'}</button></div>
  {connectionChecked&&!safeConnection&&<div role="alert" className="dq-alert error">MySQL backend not verified — import is paused. Expected MySQL and API {FRONTEND_RELEASE}. Run DIAGNOSE_CONNECTION.bat before uploading employee records.</div>}
  {expanded&&<div className="dq-import-content">
   <div className="dq-import-toolbar"><button type="button" disabled={busy} onClick={downloadTemplate}><Download size={16}/> Download saved CSV template</button><span>Administrator only · Max file size 10 MB · CSV/XLSX</span></div>
   <div className="dq-import-settings"><h3><Settings2 size={17}/> Import validation & defaults</h3><div className="dq-policy-grid">
    <label>Duplicate employees<select value={settings.duplicate_mode} onChange={e=>edit({duplicate_mode:e.target.value as ImportSettings['duplicate_mode']})}><option value="reject">Reject entire import</option><option value="skip">Skip existing or repeated records</option></select></label>
    <label>Joining date format<select value={settings.date_format} onChange={e=>edit({date_format:e.target.value as ImportSettings['date_format']})}><option>YYYY-MM-DD</option><option>DD/MM/YYYY</option><option>MM/DD/YYYY</option></select></label>
    <label>Default access role<select value={settings.default_role} onChange={e=>edit({default_role:e.target.value as ImportSettings['default_role']})}><option value="employee">Employee</option><option value="manager">Manager</option></select></label>
    <label>Default work mode<select value={settings.default_work_mode} onChange={e=>edit({default_work_mode:e.target.value as ImportSettings['default_work_mode']})}>{(['On-site','Hybrid','Remote'] as const).map(v=><option key={v}>{v}</option>)}</select></label>
    <label>Excel worksheet name <small>(blank = first sheet)</small><input value={settings.sheet_name} maxLength={100} onChange={e=>edit({sheet_name:e.target.value})} placeholder="First worksheet"/></label>
    <label>Max imported rows (1–5000)<input type="number" value={settings.max_rows} min={1} max={5000} onChange={e=>edit({max_rows:Number(e.target.value)})}/></label>
   </div><div className="dq-import-toggles"><label><input type="checkbox" checked={settings.trim_values} onChange={e=>edit({trim_values:e.target.checked})}/> Trim whitespace</label><label><input type="checkbox" checked={settings.skip_blank_rows} onChange={e=>edit({skip_blank_rows:e.target.checked})}/> Ignore blank rows</label></div>
   <h3>Excel / CSV column mapping</h3><p>Choose the worksheet column corresponding to each employee field. Fields marked * are required; role and work mode can use the defaults above.</p>
   <div className="dq-policy-grid">{FIELDS.map(key=><label key={key}>{NAMES[key]}{!['role','work_mode'].includes(key)?' *':''}{columns.length?<select value={settings.mapping[key]} onChange={e=>edit({mapping:{...settings.mapping,[key]:e.target.value}})}><option value="">{!['role','work_mode'].includes(key)?'Select required column':'Use default'}</option>{columns.map(name=><option key={name} value={name}>{name}</option>)}{!columns.includes(settings.mapping[key])&&<option value={settings.mapping[key]}>{settings.mapping[key]} (not found)</option>}</select>:<input value={settings.mapping[key]} maxLength={100} onChange={e=>edit({mapping:{...settings.mapping,[key]:e.target.value}})} placeholder={key}/>}</label>)}</div>
   <button type="button" disabled={busy||!safeConnection||!Number.isInteger(settings.max_rows)||settings.max_rows<1||settings.max_rows>5000} onClick={save}>Save import settings</button>
   </div>
   <div className="dq-import-upload"><h3><FileSpreadsheet size={17}/> Upload & preview</h3><label>Select employee workbook <input type="file" accept=".csv,.xlsx" onChange={e=>{setFile(e.target.files?.[0]||null);replacePreview(null);setColumns([]);setConfirm('')}}/></label><div className="dq-actions"><button disabled={!file||busy||!safeConnection} onClick={inspect}>Inspect columns</button><button className="dq-primary" disabled={!file||busy||!safeConnection} onClick={preflight}>Preview & validate</button></div>
   {preview&&<div className="dq-import-preview"><h3>Import preview</h3><div className="dq-import-summary"><span>Total: <strong>{preview.total}</strong></span><span>Ready: <strong>{preview.valid}</strong></span><span>Skipped: <strong>{preview.skipped}</strong></span><span>Errors: <strong>{preview.error_count}</strong></span></div>{preview.error_count>0&&<div role="alert" className="dq-alert error">No rows can be imported until errors are corrected. {preview.errors.slice(0,20).map(e=><p key={e.row}>Row {e.row}: {e.issues.join('; ')}</p>)}</div>}
   {preview.sample.length>0&&<div className="dq-import-table"><table><thead><tr><th>Excel row</th><th>Code</th><th>Employee</th><th>Department</th></tr></thead><tbody>{preview.sample.map(r=><tr key={r.row}><td>{r.row}</td><td>{r.code}</td><td>{r.name}</td><td>{r.department}</td></tr>)}</tbody></table></div>}
   {!preview.error_count&&preview.preview_token&&<div className="dq-import-confirm"><p><ShieldCheck size={16}/> This creates inactive HRIS accounts. Existing employees are not updated. Confirm after reviewing the data.</p><label>Type IMPORT to confirm<input value={confirm} onChange={e=>setConfirm(e.target.value)} placeholder="IMPORT" autoComplete="off"/></label><button className="dq-primary" disabled={busy||!safeConnection||!validation?.can_import} onClick={commit}>Import {preview.valid} employee records</button></div>}
   </div>}</div>
   <div className="dq-import-history"><h3><CheckCircle2 size={17}/> Recent import history</h3>{history.length?<div className="dq-import-table"><table><thead><tr><th>File</th><th>Rows</th><th>Created</th><th>Skipped</th><th>Imported at</th></tr></thead><tbody>{history.map(r=><tr key={r.id}><td>{r.filename}</td><td>{r.source_rows}</td><td>{r.created_rows}</td><td>{r.duplicate_rows}</td><td>{r.created_at.slice(0,19).replace('T',' ')}</td></tr>)}</tbody></table></div>:<p>No import history yet.</p>}</div>
  </div>}
  {error&&<div role="alert" className="dq-alert error">{error}</div>}{message&&<div role="status" className="dq-alert success">{message}</div>}
 </section>;
}
