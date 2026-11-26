import React,{useCallback,useEffect,useId,useRef,useState} from 'react';
import {Boxes,FolderKanban,Pencil,Plus,Search,Settings2,Trash2} from 'lucide-react';
import {useRefreshData} from './useRefreshData';
import './catalog-workspace.css';

type Kind='products'|'projects';
type Entry={id:number;code:string;name:string;description:string;status:string;category:string|null;owner_id?:number|null;start_date?:string|null;end_date?:string|null};
type Settings={default_status:string;categories:string[]};
type Employee={id:number;name:string};
type Props={kind:Kind;api:<T>(path:string,method?:string,body?:unknown)=>Promise<T>;employees:Employee[];onChanged:()=>void};
type Draft={code:string;name:string;description:string;status:string;category:string;owner_id:string;start_date:string;end_date:string};
type Mode={type:'record';record:Entry|null}|{type:'settings'};
const statuses={products:['Active','Inactive'],projects:['Planned','Active','On Hold','Completed']};
const blank=(defaultStatus:string):Draft=>({code:'',name:'',description:'',status:defaultStatus,category:'',owner_id:'',start_date:'',end_date:''});
const fromEntry=(x:Entry):Draft=>({code:x.code,name:x.name,description:x.description||'',status:x.status,category:x.category||'',owner_id:x.owner_id==null?'':String(x.owner_id),start_date:x.start_date||'',end_date:x.end_date||''});
const msg=(e:unknown)=>e instanceof Error?e.message:String(e);

export default function CatalogWorkspace(props:Props){
 const {kind,api,employees,onChanged}=props;
 const noun=kind==='products'?'Product':'Project', title=noun+'s', path='/catalog/'+kind;
 const icon=kind==='products'?<Boxes size={25} aria-hidden="true"/>:<FolderKanban size={25} aria-hidden="true"/>;
 const uid=useId(), editorId=uid+'editor', confirmId=uid+'confirm', confirmHelpId=uid+'confirm-help';
 const [rows,setRows]=useState<Entry[]>([]),[settings,setSettings]=useState<Settings|null>(null);
 const [loading,setLoading]=useState(true),[loadError,setLoadError]=useState('');
 const [error,setError]=useState(''),[notice,setNotice]=useState(''),[saving,setSaving]=useState(false);
 const [query,setQuery]=useState(''),[status,setStatus]=useState(''),[category,setCategory]=useState('');
 const [mode,setMode]=useState<Mode|null>(null),[draft,setDraft]=useState<Draft>(blank(statuses[kind][0]));
 const [categoryText,setCategoryText]=useState(''),[defaultStatus,setDefaultStatus]=useState(statuses[kind][0]);
 const [remove,setRemove]=useState<Entry|null>(null);
 const dialog=useRef<HTMLDialogElement>(null),editor=useRef<HTMLHeadingElement>(null),deleteTrigger=useRef<HTMLElement|null>(null);
 const addButton=useRef<HTMLButtonElement>(null),settingsButton=useRef<HTMLButtonElement>(null),editTrigger=useRef<HTMLElement|null>(null);
 const loadId=useRef(0);

 const reload=useCallback(async()=>{
  const id=++loadId.current;
  setLoading(true);setLoadError('');
  try{
   const [items,prefs]=await Promise.all([api<Entry[]>(path),api<Settings>(path+'/settings')]);
   if(id===loadId.current){setRows(items);setSettings(prefs);}
  }catch(e){if(id===loadId.current)setLoadError(msg(e));}
  finally{if(id===loadId.current)setLoading(false);}
 },[api,path]);
 useEffect(()=>{void reload();return ()=>{loadId.current++;};},[reload]);
 useRefreshData(reload);
 useEffect(()=>{if(mode)editor.current?.focus();},[mode]);
 useEffect(()=>{
  const node=dialog.current;
  if(remove&&!node?.open)node?.showModal();
  if(!remove&&node?.open)node.close();
 },[remove]);

 const showEditor=(record:Entry|null,trigger:HTMLElement|null)=>{
  editTrigger.current=trigger;setNotice('');setError('');setDraft(record?fromEntry(record):blank(settings?.default_status||statuses[kind][0]));
  setMode({type:'record',record});
 };
 const showSettings=()=>{
  if(!settings)return;
  setNotice('');setError('');setCategoryText(settings.categories.join('\n'));setDefaultStatus(settings.default_status);setMode({type:'settings'});
 };
 const closeEditor=()=>{
  const trigger=mode?.type==='settings'?settingsButton.current:editTrigger.current||addButton.current;
  setMode(null);setError('');requestAnimationFrame(()=>trigger?.focus());
 };
 const closeRemove=(fallback=false)=>{
  setRemove(null);setError('');
  requestAnimationFrame(()=>(!fallback&&deleteTrigger.current?.isConnected?deleteTrigger.current:addButton.current)?.focus());
 };
 const patch=(name:keyof Draft,value:string)=>setDraft(prev=>({...prev,[name]:value}));
 const saveRecord=async(event:React.FormEvent)=>{
  event.preventDefault();if(saving||mode?.type!=='record')return;
  if(!draft.code.trim()||!draft.name.trim()){setError('Enter a code and name.');return;}
  if(draft.start_date&&draft.end_date&&draft.end_date<draft.start_date){setError('The end date must be on or after the start date.');return;}
  setSaving(true);setError('');
  try{
   const body={code:draft.code.trim(),name:draft.name.trim(),description:draft.description.trim(),status:draft.status,category:draft.category.trim(),
    ...(kind==='projects'?{owner_id:draft.owner_id?Number(draft.owner_id):null,start_date:draft.start_date||null,end_date:draft.end_date||null}:{})};
   await api(path+(mode.record?'/'+mode.record.id:''),mode.record?'PUT':'POST',body);
   const content=noun+(mode.record?' updated.':' added.');
   closeEditor();setNotice(content);await reload();onChanged();
  }catch(e){setError(msg(e));}
  finally{setSaving(false);}
 };
 const saveSettings=async(event:React.FormEvent)=>{
  event.preventDefault();if(saving)return;
  const distinct=new Set<string>();
  const categories=categoryText.split('\n').map(x=>x.trim()).filter(Boolean).filter(x=>{
   const key=x.toLocaleLowerCase();if(distinct.has(key))return false;distinct.add(key);return true;
  });
  setSaving(true);setError('');
  try{
   await api(path+'/settings','PUT',{default_status:defaultStatus,categories});
   closeEditor();setNotice(noun+' settings saved.');await reload();onChanged();
  }catch(e){setError(msg(e));}
  finally{setSaving(false);}
 };
 const deleteRecord=async()=>{
  if(!remove||saving)return;
  setSaving(true);setError('');
  try{
   await api(path+'/'+remove.id,'DELETE');
   closeRemove(true);setNotice(noun+' deleted from the register.');await reload();onChanged();
  }catch(e){setError(msg(e));}
  finally{setSaving(false);}
 };
 const categories=[...new Set([...(settings?.categories||[]),...rows.map(x=>x.category||'').filter(Boolean)])].sort((a,b)=>a.localeCompare(b));
 const editCategories=[...new Set([...(settings?.categories||[]),...(draft.category?[draft.category]:[])])];
 const visible=rows.filter(row=>{
  const q=query.trim().toLowerCase();
  return (!q||[row.name,row.code,row.category,row.description].some(x=>x?.toLowerCase().includes(q)))&&(!status||row.status===status)&&(!category||row.category===category);
 });
 const nameFor=(id?:number|null)=>id==null?'Unassigned':employees.find(e=>Number(e.id)===Number(id))?.name||'Employee #'+id;

 return <section className="cw" aria-label={title} aria-busy={loading||saving}>
  <header className="cw-banner">
   <div className="cw-title">{icon}<div><p className="cw-kicker">Administration register</p><h1>{title}</h1><p>{kind==='products'?'Manage your product catalog. Employee equipment is managed separately in Asset Management.':'Manage internal project records, owners and schedules.'}</p></div></div>
   <div className="cw-actions">
    <button type="button" className="cw-button" ref={settingsButton} disabled={!settings||saving||Boolean(mode)} onClick={showSettings}><Settings2 size={17} aria-hidden="true"/>{noun} settings</button>
    <button type="button" className="cw-button cw-primary" ref={addButton} disabled={!settings||saving||Boolean(mode)} onClick={e=>showEditor(null,e.currentTarget)}><Plus size={18} aria-hidden="true"/>Add {noun.toLowerCase()}</button>
   </div>
  </header>
  {notice&&<p className="cw-notice" role="status">{notice}</p>}
  {loadError&&<div className="cw-error" role="alert"><span>{loadError}</span><button type="button" className="cw-button" onClick={()=>void reload()}>Retry</button></div>}
  {mode&&<section className="cw-editor cw-card" aria-labelledby={editorId}>
   <h2 id={editorId} tabIndex={-1} ref={editor}>{mode.type==='settings'?noun+' settings':(mode.record?'Edit ':'Add ')+noun.toLowerCase()}</h2>
   {error&&<p className="cw-error" role="alert">{error}</p>}
   {mode.type==='settings'?<form onSubmit={saveSettings}>
    <div className="cw-grid">
     <label>Default status<select aria-label="Default status" value={defaultStatus} onChange={e=>setDefaultStatus(e.target.value)}>{statuses[kind].map(x=><option key={x}>{x}</option>)}</select></label>
     <label>Categories (one per line)<textarea aria-label="Categories (one per line)" rows={5} value={categoryText} onChange={e=>setCategoryText(e.target.value)} maxLength={3200}/><small>Categories are offered when adding or editing {title.toLowerCase()}.</small></label>
    </div>
    <div className="cw-actions"><button type="submit" className="cw-button cw-primary" disabled={saving}>{saving?'Saving…':'Save settings'}</button><button type="button" className="cw-button" disabled={saving} onClick={closeEditor}>Cancel</button></div>
   </form>:<form onSubmit={saveRecord}>
    <div className="cw-grid">
     <label>Code<input required value={draft.code} maxLength={48} pattern="[A-Za-z0-9][A-Za-z0-9_.\-]{0,47}" title="Letters and numbers; periods, underscores and dashes can follow the first character" onChange={e=>patch('code',e.target.value)}/></label>
     <label>Name<input required value={draft.name} maxLength={160} onChange={e=>patch('name',e.target.value)}/></label>
     <label>Status<select aria-label="Status" value={draft.status} onChange={e=>patch('status',e.target.value)}>{statuses[kind].map(x=><option key={x}>{x}</option>)}</select></label>
     <label>Category<select aria-label="Category" value={draft.category} onChange={e=>patch('category',e.target.value)}><option value="">Uncategorized</option>{editCategories.map(x=><option key={x}>{x}</option>)}</select></label>
     {kind==='projects'&&<>
      <label>Project owner<select aria-label="Project owner" value={draft.owner_id} onChange={e=>patch('owner_id',e.target.value)}>
       <option value="">Unassigned</option>
       {draft.owner_id&&!employees.some(x=>String(x.id)===draft.owner_id)&&<option value={draft.owner_id}>{nameFor(Number(draft.owner_id))}</option>}
       {employees.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}
      </select></label>
      <label>Start date<input type="date" value={draft.start_date} onChange={e=>patch('start_date',e.target.value)}/></label>
      <label>End date<input type="date" min={draft.start_date||undefined} value={draft.end_date} onChange={e=>patch('end_date',e.target.value)}/></label>
     </>}
     <label className="cw-span">Description<textarea rows={3} maxLength={3000} value={draft.description} onChange={e=>patch('description',e.target.value)}/></label>
    </div>
    <div className="cw-actions"><button type="submit" className="cw-button cw-primary" disabled={saving}>{saving?'Saving…':'Save '+noun.toLowerCase()}</button><button type="button" className="cw-button" disabled={saving} onClick={closeEditor}>Cancel</button></div>
   </form>}
  </section>}
  <section className="cw-card" aria-label={noun+' register'}>
   <div className="cw-filters">
    <label><span><Search size={15} aria-hidden="true"/>Search {title.toLowerCase()}</span><input type="search" placeholder="Name, code or description" value={query} onChange={e=>setQuery(e.target.value)}/></label>
    <label>Filter by status<select aria-label="Filter by status" value={status} onChange={e=>setStatus(e.target.value)}><option value="">All statuses</option>{statuses[kind].map(x=><option key={x}>{x}</option>)}</select></label>
    <label>Filter by category<select aria-label="Filter by category" value={category} onChange={e=>setCategory(e.target.value)}><option value="">All categories</option>{categories.map(x=><option key={x}>{x}</option>)}</select></label>
   </div>
   <p className="cw-count" aria-live="polite">{loading?'Loading '+title.toLowerCase()+'…':visible.length+' of '+rows.length+' '+title.toLowerCase()}</p>
   {visible.length>0?<div className="cw-table-scroll" role="region" aria-label={title+' table'} tabIndex={0}><table>
    <thead><tr><th scope="col">Code</th><th scope="col">Name</th><th scope="col">Category</th><th scope="col">Status</th>{kind==='projects'&&<><th scope="col">Owner</th><th scope="col">Schedule</th></>}<th scope="col">Actions</th></tr></thead>
    <tbody>{visible.map(row=><tr key={row.id}><td>{row.code}</td><th scope="row">{row.name}{row.description&&<small>{row.description}</small>}</th><td>{row.category||'Uncategorized'}</td><td><span className="cw-status" data-status={row.status}>{row.status}</span></td>
     {kind==='projects'&&<><td>{nameFor(row.owner_id)}</td><td>{row.start_date||row.end_date?(row.start_date||'No start')+' → '+(row.end_date||'No end'):'Not scheduled'}</td></>}
     <td><div className="cw-row-actions"><button type="button" className="cw-button" disabled={saving||Boolean(mode)} aria-label={'Edit '+row.name} onClick={e=>showEditor(row,e.currentTarget)}><Pencil size={14} aria-hidden="true"/>Edit</button><button type="button" className="cw-button cw-danger" disabled={saving||Boolean(mode)} aria-label={'Delete '+row.name} onClick={e=>{deleteTrigger.current=e.currentTarget;setNotice('');setError('');setRemove(row);}}><Trash2 size={14} aria-hidden="true"/>Delete</button></div></td>
    </tr>)}</tbody>
   </table></div>:!loading&&!loadError&&<p className="cw-empty">{rows.length?'No records match those filters.':'No '+title.toLowerCase()+' yet. Use Add '+noun.toLowerCase()+' to create the first record.'}</p>}
  </section>
  <dialog ref={dialog} className="cw-dialog" aria-labelledby={confirmId} aria-describedby={confirmHelpId} onCancel={e=>{e.preventDefault();if(!saving)closeRemove();}}>
   {remove&&<><h2 id={confirmId}>Delete {noun.toLowerCase()}?</h2><p id={confirmHelpId}><strong>{remove.name}</strong> ({remove.code}) will no longer appear in the register.</p>{error&&<p className="cw-error" role="alert">{error}</p>}<div className="cw-actions"><button type="button" className="cw-button" autoFocus disabled={saving} onClick={()=>closeRemove()}>Keep record</button><button type="button" className="cw-button cw-danger-solid" disabled={saving} onClick={()=>void deleteRecord()}>{saving?'Deleting…':'Confirm delete'}</button></div></>}
  </dialog>
 </section>;
}
