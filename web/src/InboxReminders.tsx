import {useCallback,useEffect,useRef,useState} from 'react';
import {Check,Plus,StickyNote} from 'lucide-react';
import {useRefreshData} from './useRefreshData';

type Api=<T>(path:string,method?:string,body?:unknown)=>Promise<T>;
export const reminderViews={open:'Open',due:'Due now',upcoming:'Upcoming',done:'Completed',all:'All reminders'} as const;
export type ReminderView=keyof typeof reminderViews;
type Reminder={id:number;title:string;body:string;due_date:string|null;is_done:number};
type Draft={title:string;body:string;due_date:string};
const blank:Draft={title:'',body:'',due_date:''};
const path='/workspace/inbox/reminders';
const pageSize=20;
const asDraft=(item:Reminder):Draft=>({title:item.title,body:item.body,due_date:item.due_date||''});
const payload=(draft:Draft)=>({...draft,due_date:draft.due_date||null});
const localDay=()=>{
 const now=new Date();
 return [now.getFullYear(),now.getMonth()+1,now.getDate()].map((part,i)=>String(part).padStart(i===0?4:2,'0')).join('-');
};

export function InboxReminders({api,initialView}:{api:Api;initialView:ReminderView}){
 const [items,setItems]=useState<Reminder[]>([]);
 const [status,setStatus]=useState<ReminderView>(initialView);
 const [lastDefault,setLastDefault]=useState(initialView);
 const [page,setPage]=useState(0);
 const [hasMore,setHasMore]=useState(false);
 const [editing,setEditing]=useState<number|null>(null);
 const [draft,setDraft]=useState<Draft|null>(null);
 const [deleteId,setDeleteId]=useState<number|null>(null);
 const [error,setError]=useState('');
 const [notice,setNotice]=useState('');
 const [busy,setBusy]=useState(false);
 const [loading,setLoading]=useState(false);
 const generation=useRef(0);
 const editor=useRef<HTMLInputElement>(null);
 // Keep an unsaved reminder form open when the user changes display settings.
 if(initialView!==lastDefault){setLastDefault(initialView);setStatus(initialView);setPage(0);setDeleteId(null)}
 const load=useCallback(async()=>{
  const request=++generation.current;
  setLoading(true);
  try{
   const result=await api<{items:Reminder[];has_more:boolean}>(path+'?'+new URLSearchParams({status,as_of:localDay(),limit:String(pageSize),offset:String(page*pageSize)}));
   if(request!==generation.current)return;
   if(!result.items.length&&page>0){setPage(page-1);return}
   setItems(result.items);setHasMore(result.has_more);
  }catch(e){if(request===generation.current)setError((e as Error).message)}
  finally{if(request===generation.current)setLoading(false)}
 },[api,status,page]);
 useEffect(()=>{void load();return()=>{generation.current++}},[load]);
 useRefreshData(load);
 const editingOpen=draft!==null;
 useEffect(()=>{if(editingOpen)editor.current?.focus()},[editingOpen,editing]);
 async function run(action:()=>Promise<unknown>,message:string,close=false){
  setBusy(true);setError('');setNotice('');
  try{
   await action();
   if(close){setDraft(null);setEditing(null)}
   setDeleteId(null);setNotice(message);
   await load();
  }catch(e){setError((e as Error).message)}
  finally{setBusy(false)}
 }
 return <section className="wc-panel wc-reminders" aria-labelledby="wc-reminders-heading" aria-busy={loading||busy}>
  <div className="wc-toolbar wc-reminder-head"><div><h3 id="wc-reminders-heading">Personal reminders</h3><p>Private to your account. Due dates help you prioritize here; reminders don’t send messages.</p></div>
  <button type="button" className="wc-primary" disabled={busy} onClick={()=>{setEditing(null);setDraft({...blank});setDeleteId(null)}}><Plus size={16}/> Add reminder</button></div>
  {error&&<div className="wc-error" role="alert">{error}</div>}
  {notice&&<div className="wc-success" role="status">{notice}</div>}
  {draft&&<form className="wc-reminder-form" onSubmit={e=>{
   e.preventDefault();
   if(!draft.title.trim()){setError('Enter a reminder title.');return}
   const request=editing===null?()=>api(path,'POST',payload(draft)):()=>api(path+'/'+editing,'PUT',payload(draft));
   void run(request,editing===null?'Reminder added. Switch to All reminders if it is hidden by your current filter.':'Reminder updated.',true);
  }}>
   <h4>{editing===null?'New reminder':'Edit reminder'}</h4>
   <label className="wc-field">Title<input ref={editor} maxLength={120} required value={draft.title} disabled={busy} onChange={e=>setDraft({...draft,title:e.target.value})}/></label>
   <label className="wc-field">Notes (optional)<textarea rows={3} maxLength={1200} value={draft.body} disabled={busy} onChange={e=>setDraft({...draft,body:e.target.value})}/></label>
   <label className="wc-field">Due date (optional)<input type="date" value={draft.due_date} disabled={busy} onChange={e=>setDraft({...draft,due_date:e.target.value})}/></label>
   <div className="wc-alert-actions"><button className="wc-outline" type="submit" disabled={busy}>{busy?'Saving…':'Save reminder'}</button><button className="wc-outline" type="button" disabled={busy} onClick={()=>{setDraft(null);setEditing(null)}}>Cancel</button></div>
  </form>}
  <div className="wc-toolbar">
   <div className="wc-tabs wc-reminder-tabs" aria-label="Reminder views">{(Object.entries(reminderViews) as [ReminderView,string][]).map(([value,label])=><button className={status===value?'active':''} key={value} type="button" aria-pressed={status===value} disabled={busy} onClick={()=>{setStatus(value);setPage(0);setDeleteId(null);setError('')}}>{label}</button>)}</div>
   {status==='due'&&<small>Open reminders due today or earlier.</small>}
   {status==='upcoming'&&<small>Open reminders due after today.</small>}
  </div>
  <div className="wc-alerts">{items.length?items.map(item=><article key={item.id} className={'wc-alert '+(item.is_done?'read':'')}>
   <span className="wc-alert-icon" aria-hidden>{item.is_done?<Check size={17}/>:<StickyNote size={17}/>}</span>
   <div><strong>{item.title}</strong>{item.body&&<p>{item.body}</p>}<small>{item.is_done?'Completed':'Open'}{item.due_date?' · Due '+item.due_date:''}</small>{!item.is_done&&item.due_date&&item.due_date<=localDay()&&<span className="wc-reminder-due">{item.due_date===localDay()?'Due today':'Overdue'}</span>}</div>
   <div className="wc-alert-actions">
    {deleteId===item.id?<><span>Delete this reminder?</span><button type="button" className="wc-outline wc-danger" disabled={busy} onClick={()=>void run(()=>api(path+'/'+item.id,'DELETE'),'Reminder deleted.',editing===item.id)}>Confirm deletion</button><button type="button" className="wc-outline" disabled={busy} onClick={()=>setDeleteId(null)}>Keep reminder</button></>:<>
     <button type="button" className="wc-outline" disabled={busy||loading||editing===item.id} onClick={()=>void run(()=>api(path+'/'+item.id+'/completion','PATCH',{is_done:!item.is_done}),item.is_done?'Reminder reopened.':'Reminder completed.')}>{item.is_done?'Reopen':'Complete'}</button>
     <button type="button" className="wc-outline" disabled={busy||loading} onClick={()=>{setDeleteId(null);setEditing(item.id);setDraft(asDraft(item))}}>Edit</button>
     <button type="button" className="wc-outline wc-danger" disabled={busy||loading} onClick={()=>setDeleteId(item.id)}>Delete</button>
    </>}
   </div>
  </article>):<div className="wc-empty">{loading?'Loading reminders…':'No reminders in this view.'}</div>}</div>
  {(page>0||hasMore)&&<div className="wc-alert-actions wc-pagination"><button className="wc-outline" disabled={busy||loading||page===0} onClick={()=>{setPage(page-1);setDeleteId(null)}}>Previous reminders</button><small>Page {page+1}</small><button className="wc-outline" disabled={busy||loading||!hasMore} onClick={()=>{setPage(page+1);setDeleteId(null)}}>Next reminders</button></div>}
 </section>
}
