import {useCallback,useEffect,useMemo,useState} from 'react';
import {ArrowRight,CheckCircle2,Database,Download,FileSpreadsheet,FileUp,Search,Settings2,ShieldCheck,AlertTriangle,Trash2,Pencil} from 'lucide-react';
import {hrmFetch} from './apiTransport';
import './excel-data-center.css';

type Dataset={key:string;name:string;feature:string;columns:string[];importable:boolean;note:string;import_fields:string[]};
type Feature={key:string;name:string;domain:string;url:string;settings:string;datasets:string[];management:string};
type Catalog={features:Feature[];datasets:Dataset[];import_limit:number;export_limit:number;existing_imports:{feature:string;page:string;label:string}[];caveat:string};
type Preview={module:string;valid_rows:number;errors:{row:number;message:string}[];sample:Record<string,unknown>[];preview_token:string|null;note:string};
type MasterRecord={id:number;[key:string]:string|number|boolean|null};
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
function headers(){const token=sessionStorage.getItem('sass_token');return token?{Authorization:`Bearer ${token}`}:{}}
async function api<T>(path:string,method='GET',payload?:unknown):Promise<T>{
 const response=await hrmFetch(API+path,{method,headers:{...headers(),...(payload===undefined?{}:{'Content-Type':'application/json'})},
  ...(payload===undefined?{}:{body:JSON.stringify(payload)}),cache:'no-store'});
 const result=await response.json().catch(()=>null);
 if(!response.ok)throw Error(typeof result?.detail==='string'?result.detail:`The request failed (HTTP ${response.status})`);
 return result as T;
}
async function download(path:string,filename:string){
 const response=await hrmFetch(API+path,{headers:headers(),cache:'no-store'});
 if(!response.ok){const result=await response.json().catch(()=>null);throw Error(typeof result?.detail==='string'?result.detail:`Download failed (HTTP ${response.status})`)}
 const blob=await response.blob();const url=URL.createObjectURL(blob);
 const link=document.createElement('a');link.href=url;link.download=filename;document.body.appendChild(link);link.click();link.remove();
 window.setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function fileBase64(file:File):Promise<string>{
 const dataUrl=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result||''));reader.onerror=()=>reject(Error('Could not read the selected file'));reader.readAsDataURL(file)});
 return dataUrl.split(',')[1]||'';
}
const MASTER_FIELDS:Record<string,{key:string;title:string;settings:string;get:string;post:string;fields:string[];required:string[];description:string}>={
 office_locations:{key:'office_locations',title:'Office directory',settings:'orgsettings',get:'/admin/organization/offices',post:'/admin/organization/offices',fields:['code','name','city','country','address','timezone','is_active'],required:['code','name','city','country','timezone'],description:'Office deletion is blocked if employees, shifts, jobs or other records use this location.'},
 service_categories:{key:'service_categories',title:'Service types',settings:'talentsettings',get:'/request-desk/categories?include_archived=true',post:'/request-desk/categories',fields:['name','description'],required:['name'],description:'Archive a service type before deleting. Categories with existing requests cannot be deleted.'},
 hr_task_templates:{key:'hr_task_templates',title:'HR task templates',settings:'workflowsettings',get:'/workforce/task-templates?include_archived=true',post:'/workforce/task-templates',fields:['title','guidance','priority','due_offset_days'],required:['title','due_offset_days'],description:'Archive before deleting. Templates linked to assigned tasks cannot be deleted.'},
};
function MasterCatalogManager({selected,navigate}:{selected:string;navigate:(key:string)=>void}){
 const spec=MASTER_FIELDS[selected];
 const [records,setRecords]=useState<MasterRecord[]>([]);const [editing,setEditing]=useState<MasterRecord|null>(null);
 const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');
 const reload=useCallback(async()=>{if(!spec)return;try{setRecords(await api<MasterRecord[]>(spec.get))}catch(e){setError((e as Error).message)}},[spec]);
 useEffect(()=>{setEditing(null);setError('');void reload()},[reload]);
 if(!spec)return null;
 const initial=():MasterRecord=>({id:0,...Object.fromEntries(spec.fields.map(f=>[f,f==='is_active'?true:f==='priority'?'Normal':f==='due_offset_days'?3:f==='timezone'?'Asia/Kolkata':'' ]))});
 const write=async(job:()=>Promise<unknown>,message:string)=>{setBusy(true);setError('');setNotice('');try{await job();setNotice(message);setEditing(null);await reload()}catch(e){setError((e as Error).message)}finally{setBusy(false)}};
 const save=()=>{if(!editing)return;const data=Object.fromEntries(spec.fields.map(f=>[f,editing[f]]));
  if(selected==='hr_task_templates')data.due_offset_days=Number(data.due_offset_days);
  if(selected==='office_locations')data.is_active=Boolean(data.is_active);
  const isUpdate=Boolean(editing.id);
  void write(()=>api(spec.post+(isUpdate?`/${editing.id}`:''),isUpdate?'PUT':'POST',data),isUpdate?'Record updated with audit trail.':'Record created with audit trail.');
 };
 const changeState=(record:MasterRecord)=>{const active=!Boolean(record.active);
  if(!window.confirm(`${active?'Restore':'Archive'} ${String(record.name||record.title)}?`))return;
  const path=selected==='service_categories'?`/request-desk/categories/${record.id}/state`:`/workforce/task-templates/${record.id}`;
  void write(()=>api(path,'PATCH',{active}),active?'Record restored.':'Record archived.');
 };
 const remove=(record:MasterRecord)=>{const reason=window.prompt(`Reason for deleting ${String(record.name||record.title)} (5+ characters):`);
  if(reason===null)return;
  if(reason.trim().length<5){setError('A deletion reason of at least five characters is required.');return}
  if(!window.confirm(`Permanently delete ${String(record.name||record.title)}? Linked records will be protected by the server.`))return;
  void write(()=>api(spec.post+`/${record.id}`,'DELETE',{confirm:'DELETE',reason:reason.trim()}),'Record deleted after backend dependency checks.');
 };
 return <section className="exc-panel exc-manager"><div className="exc-section-head"><div><h2>{spec.title} · Add / Edit / Archive / Delete</h2><p>{spec.description}</p></div><div className="exc-buttons"><button type="button" disabled={busy} onClick={()=>setEditing(initial())}>Add manually</button><button type="button" onClick={()=>navigate(spec.settings)}><Settings2 size={14}/> Settings</button></div></div>
 {error&&<div className="exc-alert exc-error" role="alert">{error}</div>}{notice&&<div className="exc-alert exc-good" role="status">{notice}</div>}
 {editing&&<div className="exc-editbox"><h3>{editing.id?`Edit record #${editing.id}`:'Add master record'}</h3><div className="exc-editgrid">{spec.fields.map(field=><label key={field}>{field.replaceAll('_',' ')}{field==='is_active'?<select value={editing[field]?'true':'false'} onChange={e=>setEditing(o=>o?{...o,[field]:e.target.value==='true'}:o)}><option value="true">Active</option><option value="false">Inactive</option></select>:field==='priority'?<select value={String(editing[field]||'Normal')} onChange={e=>setEditing(o=>o?{...o,[field]:e.target.value}:o)}><option>Low</option><option>Normal</option><option>High</option></select>:<input type={field==='due_offset_days'?'number':'text'} min={field==='due_offset_days'?0:undefined} max={field==='due_offset_days'?365:undefined} maxLength={field==='guidance'?1000:field==='description'?700:500} required={spec.required.includes(field)} value={String(editing[field]??'')} onChange={e=>setEditing(o=>o?{...o,[field]:e.target.value}:o)}/>}</label>)}</div><div className="exc-buttons"><button type="button" disabled={busy} onClick={()=>setEditing(null)}>Cancel</button><button type="button" disabled={busy||spec.required.some(f=>!String(editing[f]??'').trim())} className="exc-primary" onClick={save}>Save to HRM</button></div></div>}
 <div className="exc-manager-list">{records.map(record=><article key={record.id}><div><strong>{String(record.name||record.title||record.code||record.id)}</strong><small>ID #{record.id} {record.active!==undefined?`· ${record.active?'Active':'Archived'}`:''}</small></div><div className="exc-buttons"><button disabled={busy} type="button" onClick={()=>setEditing(record)}><Pencil size={14}/> Edit</button>{record.active!==undefined&&<button type="button" disabled={busy} onClick={()=>changeState(record)}>{record.active?'Archive':'Restore'}</button>}<button disabled={busy} type="button" onClick={()=>remove(record)}><Trash2 size={14}/> Delete</button></div></article>)}{!records.length&&<small>No existing records, or the catalog has not loaded yet.</small>}</div></section>;
}

export function ExcelDataCenter({navigate}:{navigate:(key:string)=>void}){
 const [catalog,setCatalog]=useState<Catalog|null>(null);
 const [query,setQuery]=useState('');const [domain,setDomain]=useState('All');
 const [selected,setSelected]=useState('office_locations');const [file,setFile]=useState<File|null>(null);
 const [fileContent,setFileContent]=useState<string|null>(null);const [preview,setPreview]=useState<Preview|null>(null);
 const [exportRows,setExportRows]=useState(1000);const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');const [notice,setNotice]=useState('');
 const load=useCallback(async()=>{try{setCatalog(await api<Catalog>('/admin/excel/catalog'))}catch(e){setError((e as Error).message)}},[]);
 useEffect(()=>{void load()},[load]);
 const domains=useMemo(()=>['All',...new Set((catalog?.features||[]).map(f=>f.domain))],[catalog]);
 const filtered=useMemo(()=>catalog?.features.filter(f=>(domain==='All'||domain===f.domain)&&
  [f.name,f.key,f.domain,...f.datasets].join(' ').toLowerCase().includes(query.trim().toLowerCase()))||[],[catalog,domain,query]);
 const withBusy=async(action:()=>Promise<void>)=>{setBusy(true);setError('');setNotice('');try{await action()}catch(e){setError((e as Error).message)}finally{setBusy(false)}};
 const exportOne=(d:Dataset)=>void withBusy(async()=>{await download(`/admin/excel/export/${d.key}.xlsx?limit=${exportRows}`,`sass-hrm-${d.key}.xlsx`);setNotice(`Downloaded ${d.name} workbook (maximum ${exportRows} rows).`)});
 const exportAll=()=>void withBusy(async()=>{await download(`/admin/excel/database.xlsx?limit=${Math.min(exportRows,2000)}`,'sass-hrm-curated-database.xlsx');setNotice('Downloaded reviewed database workbook. This is not a full MySQL backup.');});
 const template=(d:Dataset)=>void withBusy(async()=>{await download(`/admin/excel/template/${d.key}.xlsx`,`sass-hrm-${d.key}-template.xlsx`);setNotice('Blank import template downloaded.')});
 const chooseFile=(next:File|null)=>{setFile(next);setFileContent(null);setPreview(null);setNotice('');setError('')};
 const review=()=>void withBusy(async()=>{
  if(!file)throw Error('Select an Excel or CSV file first');
  if(file.size>2*1024*1024)throw Error('Maximum import file size is 2 MB');
  const binary=await fileBase64(file);
  const response=await api<Preview>(`/admin/excel/import/${selected}/preview`,'POST',{filename:file.name,file_base64:binary});
  setFileContent(binary);setPreview(response);setNotice(response.errors.length?'Correct the spreadsheet and preview it again.':'Preview completed; nothing has been saved yet.');
 });
 const confirm=()=>void withBusy(async()=>{
  if(!preview?.preview_token||!file||!fileContent)throw Error('Run a clean preview first');
  if(!window.confirm(`Create ${preview.valid_rows} NEW records in ${selected}? Existing records will not be edited or deleted.`))return;
  const result=await api<{created:number}>(`/admin/excel/import/${selected}/commit`,'POST',{filename:file.name,file_base64:fileContent,preview_token:preview.preview_token});
  setNotice(`Created ${result.created} records successfully. Reopen the owning feature to edit or archive them.`);
  setPreview(null);setFileContent(null);setFile(null);
 });
 const selectedDataset=catalog?.datasets.find(d=>d.key===selected);
 return <section className="exc-page">
  <header className="exc-heading"><div><span className="exc-eyebrow">SASS HRM / ADMINISTRATOR DATA OPERATIONS</span><h1>Excel & module data center</h1><p>Export curated MySQL worksheets, download Excel templates, create approved master records by previewed import, and open the correct module for Edit, Delete and Settings.</p></div><button type="button" onClick={()=>navigate('settingscenter')}><Settings2 size={16}/> Administration settings</button></header>
  <div className="exc-banner"><ShieldCheck size={20}/><span>Administrator access is checked on the server. Imports cannot overwrite existing records or bypass employee, payroll, audit, recruitment or approval rules. Exports are row-limited and audited.</span></div>
  {error&&<div role="alert" className="exc-alert exc-error"><AlertTriangle size={17}/>{error}</div>}{notice&&<div role="status" className="exc-alert exc-good"><CheckCircle2 size={17}/>{notice}</div>}
  <div className="exc-top-grid"><article className="exc-panel"><div className="exc-panel-header"><Database size={21}/><h2>Download database sheets</h2></div><p>One Excel workbook with 26 reviewed, non-secret table views. Includes a scope/limitations worksheet. Not a raw database dump or a backup.</p><label>Maximum rows per dataset <input type="number" value={exportRows} min={1} max={2000} onChange={e=>setExportRows(Math.max(1,Math.min(2000,Number(e.target.value)||1)))}/></label><button className="exc-primary" type="button" disabled={busy} onClick={exportAll}><Download size={16}/> Download database workbook (.xlsx)</button></article>
   <article className="exc-panel"><div className="exc-panel-header"><FileUp size={21}/><h2>Bulk-create master records</h2></div><p>Choose a supported catalog and upload its exact template. Every row is validated and must pass an explicit preview and confirmation before any insert.</p><label>Dataset<select value={selected} onChange={e=>{setSelected(e.target.value);chooseFile(null)}}>{catalog?.datasets.filter(d=>d.importable).map(d=><option value={d.key} key={d.key}>{d.name}</option>)}</select></label><div className="exc-row">{selectedDataset&&<button type="button" disabled={busy} onClick={()=>template(selectedDataset)}><Download size={15}/> Blank template</button>}<label className="exc-file">Excel / CSV<input aria-label="Excel or CSV file" type="file" accept=".xlsx,.csv" onChange={e=>chooseFile(e.target.files?.[0]||null)}/></label></div><small>{file?`${file.name} · ${(file.size/1024).toFixed(0)} KB`:'CSV and XLSX, up to 500 non-empty rows, 2 MB file limit'}</small><button type="button" className="exc-primary" disabled={busy||!file} onClick={review}>Validate & preview import</button>
    {preview&&<div className="exc-preview"><strong>{preview.errors.length?'Import rejected':`${preview.valid_rows} new rows ready for review`}</strong>{preview.errors.map((e,i)=><p key={`${e.row}-${i}`}>Row {e.row}: {e.message}</p>)}{!preview.errors.length&&<><pre>{JSON.stringify(preview.sample,null,2)}</pre><button type="button" className="exc-primary" disabled={busy} onClick={confirm}>Confirm create-only import</button></>}</div>}</article></div>
  <MasterCatalogManager selected={selected} navigate={navigate}/>
  <section className="exc-panel"><div className="exc-section-head"><div><h2><FileSpreadsheet size={21}/> Excel exports by module</h2><p>Download individual, approved table views. Edit and Delete are performed in each module using its current record relationships and safeguards.</p></div></div><div className="exc-datasets">{catalog?.datasets.map(d=><article key={d.key} className="exc-dataset"><div><strong>{d.name}</strong><small>{d.columns.length} reviewed columns · {d.importable?'Validated create-only import':'Export only'}</small>{d.note&&<small>{d.note}</small>}</div><div className="exc-buttons"><button type="button" disabled={busy} onClick={()=>exportOne(d)}><Download size={14}/> Excel</button><button type="button" onClick={()=>navigate(d.feature)}><Pencil size={14}/> Manage</button></div></article>)}</div></section>
  <section className="exc-panel"><div className="exc-section-head"><div><h2>Existing specialized Excel imports</h2><p>These workflows have their own validations and must not be replaced by a generic spreadsheet writer.</p></div></div><div className="exc-shortcuts">{catalog?.existing_imports.map(item=><button key={item.page} type="button" onClick={()=>navigate(item.page)}>{item.label}<ArrowRight size={15}/></button>)}</div></section>
  <section className="exc-panel"><div className="exc-section-head"><div><h2>Find any HRM feature</h2><p>Browse all 73 established feature screens. Edit/Delete buttons lead to their owning feature when permitted; they do not delete entire database tables.</p></div><div className="exc-filter"><Search size={15}/><input type="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search modules or datasets"/></div><select aria-label="Filter by workstream" value={domain} onChange={e=>setDomain(e.target.value)}>{domains.map(d=><option key={d} value={d}>{d}</option>)}</select></div><div className="exc-features">{filtered.map(feature=><article key={feature.key}><div><strong>{feature.name}</strong><small>{feature.domain}</small><small>{feature.datasets.length?`Export: ${feature.datasets.join(', ')}`:'Module-specific workflow: no generic Excel dataset'}</small></div><div className="exc-buttons"><button type="button" onClick={()=>navigate(feature.key)}><Pencil size={14}/> Manage / edit</button>{feature.settings&&feature.settings!==feature.key&&<button type="button" onClick={()=>navigate(feature.settings)}><Settings2 size={14}/> Settings</button>}{feature.datasets.map(key=><button type="button" key={key} disabled={busy} onClick={()=>{const dataset=catalog?.datasets.find(d=>d.key===key);if(dataset)exportOne(dataset)}}><Download size={14}/> {key}</button>)}</div></article>)}{!filtered.length&&<p>No matching features.</p>}</div></section>
  <p className="exc-foot"><Trash2 size={16}/> For deletion or archiving, open the owning HRM feature. Historical payroll, approvals, identity and audit records are intentionally not exposed to generic spreadsheet deletion.</p>
 </section>;
}
