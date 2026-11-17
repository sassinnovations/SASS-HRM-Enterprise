import React, {useCallback,useEffect,useMemo,useState} from 'react';
import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import {ClipboardCheck,Download,FilePlus2,Package,Search,ShieldCheck,Wrench,AlertTriangle} from 'lucide-react';
import './asset-management.css';

type Rec=Record<string,any>;
type AssetForm={employee_id:string;asset_name:string;serial_number:string;category:string;description:string;
 manufacturer:string;model:string;asset_tag:string;condition_label:string;storage_location:string;
 purchase_date:string;purchase_amount:string;warranty_expiry:string;supplier_name:string;invoice_number:string;
 accessories:string;internal_notes:string;reason:string};
const categoryOptions=['Laptop','Desktop','Mobile','Monitor','Network equipment','Peripheral','Furniture','Access card','Other'];
const conditions=['New','Good','Fair','Damaged','Needs repair'];
const blankForm=():AssetForm=>({employee_id:'',asset_name:'',serial_number:'',category:'Laptop',description:'',
 manufacturer:'',model:'',asset_tag:'',condition_label:'Good',storage_location:'',
 purchase_date:'',purchase_amount:'',warranty_expiry:'',supplier_name:'',invoice_number:'',
 accessories:'',internal_notes:'',reason:''});
const BASE=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
async function api<T=any>(path:string,method='GET',body?:unknown):Promise<T>{
 const token=sessionStorage.getItem('sass_token');
 const response=await hrmFetch(BASE+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});
 let result:any;try{result=await response.json()}catch{result={}};
 if(!response.ok)throw new Error(result?.detail||`Request failed (${response.status})`);
 return result as T;
}
function asForm(row:Rec):AssetForm{return { ...blankForm(),
 employee_id:String(row.employee_id||''),asset_name:row.asset_name||'',serial_number:row.serial_number||'',
 category:row.category||'Other',description:row.description||'',manufacturer:row.manufacturer||'',model:row.model||'',
 asset_tag:row.asset_tag||'',condition_label:row.condition_label||'Good',storage_location:row.storage_location||'',
 purchase_date:row.purchase_date||'',purchase_amount:row.purchase_amount!=null?String(row.purchase_amount):'',
 warranty_expiry:row.warranty_expiry||'',supplier_name:row.supplier_name||'',invoice_number:row.invoice_number||'',
 accessories:row.accessories||'',internal_notes:row.internal_notes||'',reason:''};}
const csvCell=(s:unknown)=>{const raw=String(s??'');const safe=/^[\s]*[=+@-]/.test(raw)?"'"+raw:raw;return '"'+safe.replace(/"/g,'""')+'"'};
function downloadCsv(rows:Rec[]){
 const columns=['serial_number','asset_tag','asset_name','category','description','manufacturer','model','condition_label','storage_location','employee_name','status','assigned_at','purchase_date','purchase_amount','warranty_expiry','supplier_name','invoice_number','accessories'];
 const csv='\uFEFF'+[columns.join(','),...rows.map(r=>columns.map(c=>csvCell(r[c])).join(','))].join('\r\n');
 const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
 const link=document.createElement('a');link.href=url;link.download='sass-hrm-asset-inventory.csv';link.click();URL.revokeObjectURL(url);
}

export function AssetManagement({isHR,employees,onChanged}:{isHR:boolean;employees:Rec[];onChanged:()=>void}){
 const [all,setAll]=useState<Rec[]>([]);const[selectedId,setSelectedId]=useState<number|null>(null);
 const [query,setQuery]=useState('');const [filter,setFilter]=useState('All statuses');
 const [mode,setMode]=useState<'view'|'create'|'edit'>('view');const[form,setForm]=useState<AssetForm>(blankForm);
 const [inspections,setInspections]=useState<Rec[]>([]);const[maintenance,setMaintenance]=useState<Rec[]>([]);
 const [inspection,setInspection]=useState({inspected_on:new Date().toISOString().slice(0,10),condition_label:'Good',working_ok:true,accessories_ok:true,security_ok:true,note:''});
 const [maintenanceKind,setMaintenanceKind]=useState('');const[severity,setSeverity]=useState('Medium');
 const [loading,setLoading]=useState(false);const[busy,setBusy]=useState(false);const[error,setError]=useState('');const[success,setSuccess]=useState('');
 const selected=all.find(r=>r.id===selectedId)||null;
 const refresh=useCallback(async()=>{
  setLoading(true);try{setAll(await api<Rec[]>('/assets/registry'));setError('')}catch(e){setError((e as Error).message)}finally{setLoading(false)}
 },[]);
 useEffect(()=>{void refresh()},[refresh]);useRefreshData(refresh);
 const loadRelated=useCallback(async(id:number)=>{
  try{const [checks,cases]=await Promise.all([api<Rec[]>(`/assets/${id}/inspections`),api<Rec[]>(`/assets/${id}/maintenance`)]);setInspections(checks);setMaintenance(cases)}
  catch(e){setError((e as Error).message)}
 },[]);
 useEffect(()=>{if(selectedId!==null)void loadRelated(selectedId);else {setInspections([]);setMaintenance([])}},[selectedId,loadRelated]);
 const filtered=useMemo(()=>all.filter(a=>{
   if(filter!=='All statuses'&&a.status!==filter)return false;
   const text=[a.asset_name,a.serial_number,a.asset_tag,a.category,a.description,a.model,a.employee_name,a.storage_location].join(' ').toLowerCase();
   return text.includes(query.trim().toLowerCase());
  }),[all,query,filter]);
 const setField=(k:keyof AssetForm,value:string)=>setForm(old=>({...old,[k]:value}));
 const edit=(a:Rec)=>{setSelectedId(a.id);setForm(asForm(a));setMode('edit');setError('');setSuccess('')};
 const choose=(a:Rec)=>{setSelectedId(a.id);setMode('view');setError('');setSuccess('')};
 const startAdd=()=>{setForm(blankForm());setMode('create');setError('');setSuccess('')};
 async function save(e:React.FormEvent){e.preventDefault();setBusy(true);setError('');setSuccess('');
  const body:Rec={...form,employee_id:Number(form.employee_id),asset_tag:form.asset_tag||null,
    purchase_date:form.purchase_date||null,purchase_amount:form.purchase_amount?Number(form.purchase_amount):null,
    warranty_expiry:form.warranty_expiry||null};
  try{
   if(mode==='create'){
    const created=await api<{id:number}>('/assets/register','POST',body);setSelectedId(created.id);
    setSuccess('Asset registered, assigned and written to the audit trail.');
   }else if(mode==='edit'&&selectedId!==null){await api(`/assets/${selectedId}/profile`,'PATCH',body);setSuccess('Asset details saved with your reason in the audit trail.')}
   setMode('view');await refresh();onChanged();
  }catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 async function saveInspection(e:React.FormEvent){e.preventDefault();if(selectedId===null)return;setBusy(true);setError('');setSuccess('');
  try{await api(`/assets/${selectedId}/inspections`,'POST',inspection);setSuccess('Condition inspection recorded.');
   setInspection(v=>({...v,note:''}));await Promise.all([loadRelated(selectedId),refresh()]);onChanged();}
  catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 async function createMaintenance(e:React.FormEvent){e.preventDefault();if(selectedId===null)return;setBusy(true);setError('');setSuccess('');
  try{await api(`/assets/${selectedId}/maintenance`,'POST',{maintenance_kind:maintenanceKind,severity});setMaintenanceKind('');
   setSuccess('Maintenance request submitted for HR review.');await loadRelated(selectedId);}
  catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 async function setMaintenanceStatus(id:number,status:string){setBusy(true);setError('');setSuccess('');
  try{await api(`/assets/maintenance/${id}`,'PATCH',{request_status:status});setSuccess('Maintenance case updated.');if(selectedId!==null)await loadRelated(selectedId)}
  catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 const field=(key:keyof AssetForm,label:string,required=false,type='text')=><label key={key}>{label}{required?' *':''}<input type={type} value={form[key]} required={required} min={type==='number'?'0':undefined} step={type==='number'?'0.01':undefined} maxLength={type==='text'?1500:undefined} onChange={e=>setField(key,e.target.value)}/></label>;
 return <section className="am-shell" aria-label="Asset register and requirements">
  <div className="am-toolbar"><div><h3>Asset inventory & requirements</h3><p>Manage descriptions, custody, condition, warranty, inspections and maintenance.</p></div><div className="am-actions">
   {isHR&&<button className="am-primary" type="button" onClick={startAdd}><FilePlus2 size={16}/> Register asset</button>}
   <button type="button" onClick={()=>downloadCsv(filtered)} disabled={!filtered.length}><Download size={16}/> Export visible CSV</button>
  </div></div>
  {error&&<p className="am-alert" role="alert">{error}</p>}{success&&<p className="am-success" role="status">{success}</p>}
  <div className="am-metrics">{[['Total assets',all.length],['Assigned',all.filter(a=>a.status==='Assigned').length],['In maintenance',all.filter(a=>a.status==='Maintenance').length],['Warranty ending in 30 days',all.filter(a=>{if(!a.warranty_expiry)return false;const days=(new Date(a.warranty_expiry).getTime()-Date.now())/86400000;return days>=0&&days<=30}).length]].map(([label,count])=><div key={label}><strong>{count}</strong><span>{label}</span></div>)}</div>
  <div className="am-filters"><label><Search size={16}/> <input aria-label="Search assets" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search asset, serial, category, employee or location"/></label><label>Status <select value={filter} onChange={e=>setFilter(e.target.value)}>{['All statuses','Assigned','Maintenance','Returned'].map(s=><option key={s}>{s}</option>)}</select></label><span>{filtered.length} matching items</span></div>
  <div className="am-table-wrap"><table><thead><tr><th>Asset / serial</th><th>Category</th><th>Custodian</th><th>Location</th><th>Condition</th><th>Status</th><th>Actions</th></tr></thead><tbody>{filtered.map(a=><tr key={a.id}><td><strong>{a.asset_name}</strong><small>{a.serial_number}</small></td><td>{a.category||'Not classified'}</td><td>{a.employee_name}</td><td>{a.storage_location||'Not recorded'}</td><td>{a.condition_label||'Not inspected'}</td><td>{a.status}</td><td><div className="am-row-actions"><button type="button" onClick={()=>choose(a)}>Details</button>{isHR&&<button type="button" onClick={()=>edit(a)}>Edit</button>}</div></td></tr>)}</tbody></table>{!loading&&filtered.length===0&&<p className="am-empty">No assets match these filters. {isHR?'Use Register asset to create the first complete record.':''}</p>}{loading&&<p className="am-empty">Loading asset inventory…</p>}</div>
  {isHR&&mode!=='view'&&<form className="am-card" onSubmit={save}><div className="am-section-title"><h4>{mode==='create'?'Register and assign equipment':'Edit asset requirements'}</h4><button type="button" onClick={()=>setMode('view')}>Cancel</button></div>
    <p className="am-hint">Fields marked * are required. Detailed description should include what the item is, its configuration and intended use. Serial numbers are immutable once registered.</p>
    <div className="am-fields">{mode==='create'&&<label>Assigned employee *<select required value={form.employee_id} onChange={e=>setField('employee_id',e.target.value)}><option value="">Choose employee</option>{employees.filter(e=>e.account_active!==false&&e.account_active!==0).map(e=><option key={e.id} value={e.id}>{e.name} ({e.code})</option>)}</select></label>}
    {field('asset_name','Asset name',true)}{mode==='create'&&field('serial_number','Serial number / unique asset ID',true)}
    <label>Category *<select required value={form.category} onChange={e=>setField('category',e.target.value)}>{categoryOptions.map(v=><option key={v}>{v}</option>)}</select></label>
    <label>Condition *<select required value={form.condition_label} onChange={e=>setField('condition_label',e.target.value)}>{conditions.map(v=><option key={v}>{v}</option>)}</select></label>
    {field('storage_location','Office / storage location',true)}{field('manufacturer','Brand / manufacturer')}{field('model','Model / specification')}{field('asset_tag','Internal asset tag')}
    <label className="am-wide">Asset description *<textarea required minLength={10} maxLength={1500} rows={3} value={form.description} onChange={e=>setField('description',e.target.value)} placeholder="Example: Dell Latitude 5440, 16 GB RAM, 512 GB SSD; office laptop issued for software engineering"/></label>
    {field('purchase_date','Purchase date',false,'date')}{field('purchase_amount','Purchase cost (INR)',false,'number')}{field('warranty_expiry','Warranty expiry date',false,'date')}{field('supplier_name','Vendor / supplier')}{field('invoice_number','Invoice / purchase order reference')}
    <label className="am-wide">Accessories and items issued<textarea rows={2} maxLength={1000} value={form.accessories} onChange={e=>setField('accessories',e.target.value)} placeholder="Charger, mouse, headset, dock, bag, access badge"/></label>
    <label className="am-wide">Internal HR / IT notes<textarea rows={2} maxLength={1500} value={form.internal_notes} onChange={e=>setField('internal_notes',e.target.value)}/></label>
    {mode==='edit'&&<label className="am-wide">Reason for editing *<textarea required minLength={8} maxLength={300} rows={2} value={form.reason} onChange={e=>setField('reason',e.target.value)}/></label>}
    </div><button className="am-primary" type="submit" disabled={busy}><ShieldCheck size={16}/>{busy?'Saving…':mode==='create'?'Register and assign asset':'Save asset changes'}</button></form>}
  {selected&&mode==='view'&&<div className="am-card"><div className="am-section-title"><div><h4><Package size={17}/> {selected.asset_name} — {selected.serial_number}</h4><p>{selected.category||'Legacy record'} · {selected.status} · {selected.employee_name}</p></div>{isHR&&<button type="button" onClick={()=>edit(selected)}>Edit details</button>}</div>
    <div className="am-detail-grid">{[['Description',selected.description||'Add a detailed description'],['Manufacturer / model',[selected.manufacturer,selected.model].filter(Boolean).join(' / ')||'—'],['Condition',selected.condition_label||'Not set'],['Location',selected.storage_location||'Not set'],['Internal tag',selected.asset_tag||'—'],['Accessories',selected.accessories||'—'],['Warranty ends',selected.warranty_expiry||'Not set'],...(isHR?[['Purchase cost',selected.purchase_amount==null?'—':`₹${Number(selected.purchase_amount).toLocaleString('en-IN')}`],['Supplier',selected.supplier_name||'—'],['Invoice reference',selected.invoice_number||'—'],['Internal notes',selected.internal_notes||'—']]:[])].map(([label,value])=><div key={String(label)}><span>{label}</span><strong>{value}</strong></div>)}</div>
    {isHR&&<form className="am-subsection" onSubmit={saveInspection}><h4><ClipboardCheck size={17}/> Asset inspection checklist</h4><div className="am-fields"><label>Inspection date<input type="date" required value={inspection.inspected_on} onChange={e=>setInspection(v=>({...v,inspected_on:e.target.value}))}/></label><label>Observed condition<select value={inspection.condition_label} onChange={e=>setInspection(v=>({...v,condition_label:e.target.value}))}>{conditions.map(x=><option key={x}>{x}</option>)}</select></label></div><div className="am-checks">{([['working_ok','Functional and working'],['accessories_ok','Issued accessories accounted for'],['security_ok','Security and inventory labels checked']] as const).map(([key,label])=><label key={key}><input type="checkbox" checked={inspection[key]} onChange={e=>setInspection(v=>({...v,[key]:e.target.checked}))}/>{label}</label>)}</div><label className="am-note">Inspection findings / checklist evidence *<textarea minLength={5} maxLength={1000} required value={inspection.note} onChange={e=>setInspection(v=>({...v,note:e.target.value}))} rows={2}/></label><button type="submit" disabled={busy}>Save inspection</button></form>}
    <div className="am-subsection"><h4>Inspection history</h4>{inspections.length?inspections.map(s=><div key={s.id} className="am-line"><span>{s.inspected_on}: {s.condition_label}</span><span>Working {s.working_ok?'✓':'✗'} · Accessories {s.accessories_ok?'✓':'✗'} · Security {s.security_ok?'✓':'✗'}{isHR&&s.note?` · ${s.note}`:''}</span></div>):<p className="am-hint">No inspection recorded yet.</p>}</div>
    {selected.status!=='Returned'&&<form className="am-subsection" onSubmit={createMaintenance}><h4><Wrench size={17}/> Report repair or maintenance</h4><div className="am-fields"><label>Problem / maintenance requirement *<input required minLength={5} maxLength={80} value={maintenanceKind} onChange={e=>setMaintenanceKind(e.target.value)} placeholder="Example: Keyboard replacement"/></label><label>Priority<select value={severity} onChange={e=>setSeverity(e.target.value)}>{['Low','Medium','High','Critical'].map(x=><option key={x}>{x}</option>)}</select></label></div><button type="submit" disabled={busy}>Submit maintenance request</button><p className="am-hint">This records a request; HR must separately authorize sending equipment for repair.</p></form>}
    <div className="am-subsection"><h4>Maintenance requests</h4>{maintenance.length?maintenance.map(m=><div key={m.id} className="am-line"><div><strong>#{m.id} {m.maintenance_kind}</strong><span>{m.severity} · {m.request_status}</span></div>{isHR&&['Open','In Progress'].includes(m.request_status)&&<select aria-label={`Status for maintenance ${m.id}`} value={m.request_status} disabled={busy} onChange={e=>void setMaintenanceStatus(m.id,e.target.value)}>{(m.request_status==='Open'?['Open','In Progress','Resolved','Cancelled']:['In Progress','Resolved','Cancelled']).map(x=><option key={x}>{x}</option>)}</select>}</div>):<p className="am-hint">No maintenance requests on this asset.</p>}</div>
   </div>}
  <p className="am-disclaimer"><AlertTriangle size={16}/> Asset profiles and inspections are HR-managed. This inventory does not install device tracking or collect employee activity. Financial and internal fields are visible only to authorized HR administrators.</p>
 </section>;
}
