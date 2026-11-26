import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import {useEffect,useMemo,useState} from 'react';
import {CalendarDays,ChevronLeft,ChevronRight,Clock3,Copy,Download,Edit3,List,Plus,Settings2,Tag,Trash2,X} from 'lucide-react';
import './personal-calendar.css';

const colors=['blue','green','violet','amber','rose'] as const;
type CategoryColor=typeof colors[number];
type Category={id:number;name:string;color:CategoryColor;event_count:number};
type CategoryDraft={name:string;color:CategoryColor};
const blankCategory:CategoryDraft={name:'',color:'blue'};
type Event={id?:number;day:string;kind:string;title:string;status:string;start_time?:string;notes?:string;personal?:boolean;category_id?:number|null;category_name?:string|null;category_color?:CategoryColor|null};
type Draft={day:string;start_time:string;title:string;notes:string;category_id:number|null};
type CalendarView='month'|'agenda';
type AgendaDays=7|14|30;
type Preferences={preferred_view:CalendarView;agenda_days:AgendaDays;week_start:'monday'|'sunday';visibility:'all'|'official'|'personal';default_start_time:string;include_private_export:boolean};
const defaults:Preferences={preferred_view:'month',agenda_days:14,week_start:'monday',visibility:'all',default_start_time:'',include_private_export:false};
const weekdays=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
const isoDate=(d:Date)=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
const monthOf=(day:string)=>new Date(day.slice(0,7)+'-01T12:00:00');
function shiftDays(day:string,count:number){
 const date=new Date(day+'T12:00:00');
 date.setDate(date.getDate()+count);
 return isoDate(date);
}
const supportedDate=(day:string)=>/^\d{4}-\d{2}-\d{2}$/.test(day)&&day>='1901-01-01'&&day<='9998-12-31';
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
async function api<T>(path:string,method='GET',body?:unknown,signal?:AbortSignal):Promise<T>{
 const token=sessionStorage.getItem('sass_token');
 const response=await hrmFetch(API+path,{method,signal,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});
 let data:any={};try{data=await response.json()}catch{}
 if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:`Calendar request failed (${response.status})`);
 return data as T;
}
const readable=(day:string)=>new Date(day+'T12:00:00').toLocaleDateString('en-IN',{weekday:'short',day:'numeric',month:'short',year:'numeric'});
function icsEscape(value:string){return value.replace(/\\/g,'\\\\').replace(/\r\n?|\n/g,'\\n').replace(/,/g,'\\,').replace(/;/g,'\\;');}
function downloadIcs(events:Event[]){
 const lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//SASS HRM//Personal Workspace//EN','CALSCALE:GREGORIAN'];
 for(const [index,item] of events.entries()){
  if(!/^\d{4}-\d{2}-\d{2}$/.test(item.day))continue;
  const dt=item.day.replaceAll('-','');
  const timestamp=item.start_time&&/^\d{2}:\d{2}$/.test(item.start_time)?dt+'T'+item.start_time.replace(':','')+'00':dt;
  lines.push('BEGIN:VEVENT',`UID:${item.personal?'personal':'work'}-${item.personal&&item.id?item.id:`${dt}-${index}`}@sass-hrm.local`, `DTSTAMP:${new Date().toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'')}`, `DTSTART${item.start_time?':':';VALUE=DATE:'}${timestamp}`,`SUMMARY:${icsEscape(item.title)}`,`DESCRIPTION:${icsEscape(item.personal?item.notes||'Personal event':`${item.kind} · ${item.status}`)}`);
  if(item.personal&&item.category_name)lines.push(`CATEGORIES:${icsEscape(item.category_name)}`);
  lines.push('END:VEVENT');
 }
 lines.push('END:VCALENDAR');
 const ics=lines.join('\r\n')+'\r\n';const blob=new Blob([ics],{type:'text/calendar;charset=utf-8'});const link=document.createElement('a');const uri=URL.createObjectURL(blob);
 try{link.href=uri;link.download='sass-my-calendar.ics';link.click()}finally{window.setTimeout(()=>URL.revokeObjectURL(uri),1500)}
}
export function PersonalCalendar({official}:{official:Event[]}){
 const today=isoDate(new Date());
 const [month,setMonth]=useState(()=>monthOf(today));
 const [selected,setSelected]=useState(today);
 const [personal,setPersonal]=useState<Event[]>([]);
 const [officialRange,setOfficialRange]=useState<{start:string;end:string;events:Event[]}|null>(null);
 const [officialLoading,setOfficialLoading]=useState(false);
 const [officialError,setOfficialError]=useState('');
 const [categories,setCategories]=useState<Category[]>([]);
 const [categoryScope,setCategoryScope]=useState('all');
 const [categoryOpen,setCategoryOpen]=useState(false);
 const [categoryDraft,setCategoryDraft]=useState<CategoryDraft>(blankCategory);
 const [categoryEditing,setCategoryEditing]=useState<number|null>(null);
 const [categoryError,setCategoryError]=useState('');
 const [categoryLoadError,setCategoryLoadError]=useState('');
 const [categoryLoading,setCategoryLoading]=useState(false);
 const [preferences,setPreferences]=useState<Preferences>(defaults);
 const [settings,setSettings]=useState<Preferences|null>(null);
 const [viewOverride,setViewOverride]=useState<CalendarView|null>(null);
 const [rangeOverride,setRangeOverride]=useState<AgendaDays|null>(null);
 const view=viewOverride??preferences.preferred_view??'month';
 const agendaDays=rangeOverride??preferences.agenda_days??14;
 const [prefsReady,setPrefsReady]=useState(false);
 const [filter,setFilter]=useState('');
 const [eventScope,setEventScope]=useState<Preferences['visibility']|null>(null);
 const visibility=eventScope??preferences.visibility;
 const [form,setForm]=useState<Draft|null>(null);
 const [editing,setEditing]=useState<number|null>(null);
 const [saving,setSaving]=useState(false);
 const [removing,setRemoving]=useState<number|null>(null);
 const [entryError,setEntryError]=useState('');
 const [prefsError,setPrefsError]=useState('');
 const [loadError,setLoadError]=useState('');
 const [notice,setNotice]=useState('');
 const [loading,setLoading]=useState(false);
 const [revision,setRevision]=useState(0);
 const monthStart=preferences.week_start==='sunday'?0:1;
 const offset=(month.getDay()-monthStart+7)%7;
 const monthLength=new Date(month.getFullYear(),month.getMonth()+1,0).getDate();
 const gridLength=Math.ceil((monthLength+offset)/7)*7;
 const agendaEnd=shiftDays(selected,agendaDays-1);
 const rangeStart=view==='agenda'?selected:isoDate(new Date(month.getFullYear(),month.getMonth(),1-offset));
 const rangeEnd=view==='agenda'?agendaEnd:isoDate(new Date(month.getFullYear(),month.getMonth(),gridLength-offset));
 useEffect(()=>{
  const controller=new AbortController();
  setLoading(true);setLoadError('');
  api<Event[]>(`/calendar/personal?start=${rangeStart}&end=${rangeEnd}`,'GET',undefined,controller.signal)
   .then(items=>{if(!controller.signal.aborted)setPersonal(items.map(v=>({...v,kind:'Personal',status:'Private',personal:true})))})
   .catch(e=>{if(!controller.signal.aborted){setPersonal([]);setLoadError(e.message)}})
   .finally(()=>{if(!controller.signal.aborted)setLoading(false)});
  return ()=>controller.abort();
 },[rangeStart,rangeEnd,revision]);
 useEffect(()=>{
  const controller=new AbortController();
  setOfficialLoading(true);setOfficialError('');
  api<Event[]>(`/calendar/me?start=${rangeStart}&end=${rangeEnd}`,'GET',undefined,controller.signal)
   .then(events=>{if(!controller.signal.aborted)setOfficialRange({start:rangeStart,end:rangeEnd,events})})
   .catch(()=>{if(!controller.signal.aborted){setOfficialRange(null);setOfficialError('Could not refresh HR dates. Some dates may be missing.')}})
   .finally(()=>{if(!controller.signal.aborted)setOfficialLoading(false)});
  return ()=>controller.abort();
 },[rangeStart,rangeEnd,revision]);
 useEffect(()=>{
  if(prefsReady)return;
  const controller=new AbortController();
  api<Preferences>('/calendar/preferences','GET',undefined,controller.signal)
   .then(saved=>{if(!controller.signal.aborted){setPreferences(saved);setPrefsError('');setPrefsReady(true)}})
   .catch(e=>{if(!controller.signal.aborted)setPrefsError(e.message)});
  return ()=>controller.abort();
 },[prefsReady,revision]);
 useEffect(()=>{
  const controller=new AbortController();
  setCategoryLoading(true);setCategoryLoadError('');
  api<Category[]>('/calendar/categories','GET',undefined,controller.signal)
   .then(items=>{if(!controller.signal.aborted){
    setCategories(items);
    setCategoryScope(current=>current==='all'||current==='none'||items.some(category=>String(category.id)===current)?current:'all');
   }})
   .catch(e=>{if(!controller.signal.aborted)setCategoryLoadError(e.message)})
   .finally(()=>{if(!controller.signal.aborted)setCategoryLoading(false)});
  return ()=>controller.abort();
 },[revision]);
 const reload=()=>setRevision(r=>r+1);
 useRefreshData(reload);
 const officialEvents=officialRange?.start===rangeStart&&officialRange.end===rangeEnd?officialRange.events:official;
 const pending=loading||officialLoading;
 const searchEvents=useMemo(()=>{
  const query=filter.trim().toLowerCase();
  return [
   ...(visibility==='personal'?[]:officialEvents),
   ...(visibility==='official'?[]:personal),
  ].filter(event=>/^\d{4}-\d{2}-\d{2}$/.test(event.day) &&
   (visibility==='official'||categoryScope==='all'||(event.personal&&(categoryScope==='none'?!event.category_id:String(event.category_id)===categoryScope))) &&
   [event.day,event.title,event.kind,event.status,event.category_name,event.notes].some(value=>String(value??'').toLowerCase().includes(query)))
   .sort((a,b)=>a.day.localeCompare(b.day)||(a.start_time||'').localeCompare(b.start_time||''));
 },[officialEvents,personal,filter,visibility,categoryScope]);
 const monthEvents=searchEvents.filter(x=>x.day.startsWith(isoDate(month).slice(0,7)));
 const agendaEvents=searchEvents.filter(x=>x.day>=selected&&x.day<=agendaEnd);
 const agendaGroups=agendaEvents.reduce((groups,item)=>{
  const group=groups.get(item.day)??[];group.push(item);groups.set(item.day,group);return groups;
 },new Map<string,Event[]>());
 const exportEvents=(view==='agenda'?agendaEvents:monthEvents).filter(x=>!x.personal||preferences.include_private_export);
 const hasFilters=!!filter.trim()||visibility!=='all'||categoryScope!=='all';
 const selectedEvents=searchEvents.filter(x=>x.day===selected);
 const days=Array.from({length:gridLength},(_,index)=>index-offset+1);
 const headings=weekdays.map((_,index)=>weekdays[(index+monthStart)%7]);
 function jump(day:string){
  if(!supportedDate(day))return;
  setSelected(day);setMonth(monthOf(day));
 }
 function shift(offsetMonths:number){
  const target=new Date(month.getFullYear(),month.getMonth()+offsetMonths,1);
  jump(isoDate(target));
 }
 function clearFilters(){
  setFilter('');setEventScope('all');setCategoryScope('all');
 }
 function startEntry(event?:Event,copy=false,day=selected){
  setEntryError('');setNotice('');
  setEditing(copy?null:event?.id??null);
  setForm(event?{day:event.day,start_time:event.start_time||'',title:event.title,notes:event.notes||'',category_id:event.category_id??null}:
   {day,start_time:preferences.default_start_time,title:'',notes:'',category_id:categories.find(c=>String(c.id)===categoryScope)?.id??null});
 }
 async function saveEntry(ev:React.FormEvent){
  ev.preventDefault();if(!form||saving)return;
  setSaving(true);setEntryError('');setNotice('');
  try{
   await api(editing?`/calendar/personal/${editing}`:'/calendar/personal',editing?'PATCH':'POST',form);
   setForm(null);setNotice(editing?'Personal event updated.':'Personal event added.');
   if(visibility==='official')setEventScope('all');
   if(categoryScope!=='all'&&(form.category_id===null?'none':String(form.category_id))!==categoryScope)setCategoryScope('all');
   setFilter('');
   if(view!=='agenda'||form.day<selected||form.day>agendaEnd)jump(form.day);
   reload();
  }catch(e){setEntryError((e as Error).message)}
  finally{setSaving(false)}
 }
 async function remove(event:Event){
  if(!event.id||removing!==null||!window.confirm(`Remove your personal event “${event.title}”?`))return;
  setRemoving(event.id);setLoadError('');setNotice('');
  try{
   await api(`/calendar/personal/${event.id}`,'DELETE');
   setPersonal(items=>items.filter(x=>x.id!==event.id));
   setNotice('Personal event removed.');reload();
  }catch(e){setLoadError((e as Error).message)}
  finally{setRemoving(null)}
 }
 async function savePreferences(ev:React.FormEvent){
  ev.preventDefault();if(!settings||saving)return;
  setSaving(true);setPrefsError('');setNotice('');
  try{
   setPreferences(await api<Preferences>('/calendar/preferences','PUT',settings));
   setSettings(null);setEventScope(null);setViewOverride(null);setRangeOverride(null);setPrefsReady(true);setNotice('Calendar settings saved.');
  }catch(e){setPrefsError((e as Error).message)}
  finally{setSaving(false)}
 }
 function showCategories(){
  setCategoryOpen(true);setCategoryEditing(null);setCategoryDraft(blankCategory);setCategoryError('');
 }
 function editCategory(item:Category){
  setCategoryDraft({name:item.name,color:item.color});setCategoryEditing(item.id);setCategoryError('');
 }
 function resetCategoryForm(){
  setCategoryDraft(blankCategory);setCategoryEditing(null);setCategoryError('');
 }
 async function saveCategory(ev:React.FormEvent){
  ev.preventDefault();
  if(saving)return;
  setSaving(true);setCategoryError('');setNotice('');
  try{
   await api(categoryEditing?`/calendar/categories/${categoryEditing}`:'/calendar/categories',categoryEditing?'PATCH':'POST',categoryDraft);
   setNotice(categoryEditing?'Category updated.':'Category added.');
   resetCategoryForm();reload();
  }catch(e){setCategoryError((e as Error).message)}
  finally{setSaving(false)}
 }
 async function removeCategory(item:Category){
  if(saving||!window.confirm(`Delete the category “${item.name}”? Its events will stay in your calendar without a category.`))return;
  setSaving(true);setCategoryError('');setNotice('');
  try{
   await api(`/calendar/categories/${item.id}`,'DELETE');
   if(categoryEditing===item.id)resetCategoryForm();
   if(categoryScope===String(item.id))setCategoryScope('all');
   setNotice('Category deleted. Its events were kept.');reload();
  }catch(e){setCategoryError((e as Error).message)}
  finally{setSaving(false)}
 }
 function eventCard(item:Event,i:number){
  return <article key={`${item.kind}-${item.id||i}-${item.day}-${i}`} className="v27-agenda-item">
      <span className={`v27-event-type ${item.personal?'v27-personal-event':''}`}><CalendarDays size={17}/></span>
      <div><strong>{item.title}</strong><small>{item.kind} · {item.status}{item.start_time?` · ${item.start_time}`:''}</small>
       {item.personal&&item.category_name&&<span className={`v27-category-badge v27-tint-${item.category_color??'blue'}`}><i/>{item.category_name}</span>}
       {item.personal&&item.notes&&<p>{item.notes}</p>}
       {item.personal&&<div className="v27-agenda-buttons">
        <button type="button" onClick={()=>startEntry(item)}><Edit3 size={13}/> Edit</button>
        <button type="button" onClick={()=>startEntry(item,true)}><Copy size={13}/> Duplicate</button>
        <button type="button" disabled={removing!==null} onClick={()=>void remove(item)}><Trash2 size={13}/> Delete</button>
       </div>}
      </div></article>;
 }
 function emptyState(scope:string){
  return <div className="v27-day-empty"><Clock3 size={25}/>
   <strong>{pending?'Loading calendar…':loadError?'Calendar could not be loaded':hasFilters?`No events match your filters ${scope}`:`No events ${scope}`}</strong>
   <p>{pending?'Fetching the selected dates.':loadError?'Retry or choose a different date.':hasFilters?'Clear the filters to show all dates and events in this view.':'Add a private entry or choose other dates. HR events appear automatically.'}</p>
   {!pending&&<div className="v27-empty-actions">{hasFilters&&<button type="button" className="btn outline" onClick={clearFilters}>Clear filters</button>}<button type="button" className="btn outline" onClick={()=>startEntry()}>Add personal event</button></div>}
  </div>;
 }
 return <div className="v27-calendar" aria-busy={pending}>
  <div className="v27-cal-intro">
   <div><div className="eyebrow">TIME / PERSONAL PLANNER</div><h1>My calendar</h1><p>View read-only HR dates alongside your private plans. Only your signed-in account can open personal entries.</p></div>
   <div className="v27-cal-actions">
    <button type="button" className="btn outline" onClick={()=>{setPrefsError('');setSettings(preferences)}} disabled={!prefsReady}><Settings2 size={16}/> Calendar settings</button>
    <button type="button" className="btn outline" onClick={showCategories}><Tag size={16}/> Manage categories</button>
    <button type="button" title={preferences.include_private_export?'Export matching events, including private notes':'Export matching HR events only; private entries are excluded'} className="btn outline" onClick={()=>downloadIcs(exportEvents)} disabled={!exportEvents.length||pending}><Download size={16}/> {view==='agenda'?'Export this period':'Export this month'}</button>
    <button className="btn primary" type="button" onClick={()=>startEntry()}><Plus size={16}/> Add personal event</button>
   </div>
  </div>
  {(loadError||officialError||(!prefsReady&&prefsError))&&<div className="data-error-banner" role="alert">{loadError||officialError||prefsError} <button type="button" className="btn outline" onClick={reload}>Retry</button></div>}
  {notice&&<p role="status" className="v27-notice">{notice}</p>}
  <div className="v27-cal-view-bar">
   <div className="v27-layout-switch" role="group" aria-label="Calendar view">
    <button type="button" aria-pressed={view==='month'} onClick={()=>setViewOverride('month')}><CalendarDays size={17}/> Month</button>
    <button type="button" aria-pressed={view==='agenda'} onClick={()=>setViewOverride('agenda')}><List size={17}/> Agenda</button>
   </div>
   <span>{view==='agenda'?'Browse upcoming dates in order.':'Select a date to view or add events.'}</span>
  </div>
  <div className="v27-cal-toolbar">
   <label>Search calendar<input value={filter} onChange={e=>setFilter(e.target.value)} placeholder="Search dates and events"/></label>
   <label className="v27-view-scope">Event filter<select value={visibility} onChange={e=>setEventScope(e.target.value as Preferences['visibility'])}><option value="all">All events</option><option value="official">HR events</option><option value="personal">Personal events</option></select></label>
   <label className="v27-view-scope">Category filter<select value={categoryScope} disabled={visibility==='official'} onChange={e=>setCategoryScope(e.target.value)}><option value="all">All categories</option><option value="none">Uncategorized</option>{categories.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
   <label className="v27-date-jump">{view==='agenda'?'Agenda start':'Go to date'}<input type="date" min="1901-01-01" max="9998-12-31" value={selected} onChange={e=>jump(e.target.value)}/></label>
   <button type="button" className="btn subtle" onClick={()=>jump(today)}>Today</button>
  </div>
  {view==='month'?<div className="v27-calendar-layout">
   <section className="v27-month section-card">
    <div className="v27-month-head">
     <div><h2>{month.toLocaleDateString('en-IN',{month:'long',year:'numeric'})}</h2><p>{monthEvents.length} event{monthEvents.length!==1?'s':''} this month</p></div>
     <div className="v27-month-arrows"><button type="button" aria-label="Previous month" onClick={()=>shift(-1)}><ChevronLeft size={19}/></button><button type="button" aria-label="Next month" onClick={()=>shift(1)}><ChevronRight size={19}/></button></div>
    </div>
    <div className="v27-day-grid">
     {headings.map(d=><div key={d} className="v27-weekday">{d}</div>)}
     {days.map(day=>{
      const actual=new Date(month.getFullYear(),month.getMonth(),day),iso=isoDate(actual),isCurrent=day>0&&day<=monthLength;
      const onDay=searchEvents.filter(x=>x.day===iso);
      return <button type="button" key={iso} onClick={()=>jump(iso)} className={`v27-day ${isCurrent?'':'v27-other'} ${selected===iso?'v27-selected':''} ${today===iso?'v27-today':''}`} aria-label={`${readable(iso)}, ${onDay.length} events`} aria-pressed={selected===iso}><span>{actual.getDate()}</span><div className="v27-dots">{onDay.slice(0,3).map((e,j)=><i key={j} className={e.personal?`v27-personal ${e.category_color?`v27-tint-${e.category_color}`:''}`:'v27-official'}/>)}</div></button>;
     })}
    </div>
    <div className="v27-cal-legend"><span><i className="v27-official"/> Organization / HR (read-only)</span><span><i className="v27-personal"/> Private entry</span></div>
   </section>
   <section className="section-card v27-agenda">
    <div className="v27-agenda-head"><div><h3>{readable(selected)}</h3><p>{selectedEvents.length} event{selectedEvents.length!==1?'s':''}</p></div><button type="button" aria-label="Add event on selected day" onClick={()=>startEntry()}><Plus size={18}/></button></div>
    <div className="v27-agenda-list">
     {selectedEvents.length?selectedEvents.map(eventCard):emptyState('on this date')}
    </div>
   </section>
  </div>:<section className="section-card v27-agenda-range" aria-labelledby="v27-agenda-title">
   <div className="v27-agenda-range-header">
    <div><span className="eyebrow">UPCOMING SCHEDULE</span><h2 id="v27-agenda-title">Agenda</h2><p><time dateTime={selected}>{readable(selected)}</time> to <time dateTime={agendaEnd}>{readable(agendaEnd)}</time> · {agendaEvents.length} {agendaEvents.length===1?'event':'events'}</p></div>
    <div className="v27-agenda-range-tools">
     <label>Show next<select value={agendaDays} onChange={e=>setRangeOverride(Number(e.target.value) as AgendaDays)}><option value={7}>7 days</option><option value={14}>14 days</option><option value={30}>30 days</option></select></label>
     <div className="v27-month-arrows"><button type="button" aria-label="Previous agenda period" disabled={!supportedDate(shiftDays(selected,-agendaDays))} onClick={()=>jump(shiftDays(selected,-agendaDays))}><ChevronLeft size={19}/></button><button type="button" aria-label="Next agenda period" disabled={!supportedDate(shiftDays(selected,agendaDays))} onClick={()=>jump(shiftDays(selected,agendaDays))}><ChevronRight size={19}/></button></div>
    </div>
   </div>
   {agendaEvents.length?<div className="v27-agenda-groups">{[...agendaGroups].map(([day,events])=><section className="v27-agenda-group" key={day}>
    <div className="v27-agenda-head"><div><h3><time dateTime={day}>{readable(day)}</time></h3><p>{day===today?'Today · ':''}{events.length} {events.length===1?'event':'events'}</p></div><button type="button" aria-label={`Add event on ${readable(day)}`} onClick={()=>startEntry(undefined,false,day)}><Plus size={18}/></button></div>
    <div className="v27-agenda-range-list">{events.map(eventCard)}</div>
   </section>)}</div>:emptyState('in this period')}
  </section>}
  {form&&<div className="modal-overlay" onMouseDown={e=>{if(e.target===e.currentTarget&&!saving)setForm(null)}}>
   <div className="modal-box v27-event-dialog" role="dialog" aria-modal="true" aria-labelledby="v27-modal-title" onKeyDown={e=>{if(e.key==='Escape'&&!saving)setForm(null)}}>
    <div className="modal-header"><div><span className="eyebrow">PRIVATE CALENDAR</span><h2 id="v27-modal-title">{editing?'Edit personal event':'Add personal event'}</h2><p>Only you can view or edit this personal entry.</p></div><button type="button" className="icon-button" onClick={()=>setForm(null)} disabled={saving} aria-label="Close"><X size={20}/></button></div>
    <form onSubmit={saveEntry}><div className="v27-event-fields">
     {entryError&&<div className="data-error-banner" role="alert">{entryError}</div>}
     <label>Event title<input required minLength={2} maxLength={120} autoFocus value={form.title} onChange={e=>setForm({...form,title:e.target.value})}/></label>
     <label>Date<input required type="date" min="1901-01-01" max="9998-12-31" value={form.day} onChange={e=>setForm({...form,day:e.target.value})}/></label>
     <label>Time (optional)<input type="time" value={form.start_time} onChange={e=>setForm({...form,start_time:e.target.value})}/></label>
     <label>Personal category<select value={form.category_id??''} disabled={categoryLoading||!!categoryLoadError} onChange={e=>setForm({...form,category_id:e.target.value?Number(e.target.value):null})}><option value="">No category</option>{categories.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
     {categoryLoadError&&<small>Categories could not be loaded. You can still save the event.</small>}
     <label>Private notes (optional)<textarea rows={3} maxLength={1000} value={form.notes} onChange={e=>setForm({...form,notes:e.target.value})}/></label>
    </div><div className="modal-footer"><button type="button" className="btn outline" onClick={()=>setForm(null)} disabled={saving}>Cancel</button><button type="submit" className="btn primary" disabled={saving}>{saving?'Saving…':'Save personal event'}</button></div></form>
   </div>
  </div>}
  {categoryOpen&&<div className="modal-overlay" onMouseDown={e=>{if(e.target===e.currentTarget&&!saving)setCategoryOpen(false)}}>
   <div className="modal-box v27-event-dialog" role="dialog" aria-modal="true" aria-labelledby="v27-categories-title" onKeyDown={e=>{if(e.key==='Escape'&&!saving)setCategoryOpen(false)}}>
    <div className="modal-header"><div><span className="eyebrow">MY CALENDAR SETTINGS</span><h2 id="v27-categories-title">Personal event categories</h2><p>Group your private events. Categories never change HR dates.</p></div><button type="button" className="icon-button" onClick={()=>setCategoryOpen(false)} disabled={saving} aria-label="Close"><X size={20}/></button></div>
    <div className="v27-category-list">
     {categoryLoadError&&<div className="data-error-banner" role="alert">{categoryLoadError} <button type="button" className="btn outline" onClick={reload}>Retry</button></div>}
     {categories.map(item=><article className="v27-category-row" key={item.id}><div><span className={`v27-category-badge v27-tint-${item.color}`}><i/>{item.name}</span><small>{item.event_count} event{item.event_count===1?'':'s'}</small></div><div className="v27-agenda-buttons"><button type="button" disabled={saving} onClick={()=>editCategory(item)} aria-label={`Edit category ${item.name}`}><Edit3 size={14}/> Edit</button><button type="button" disabled={saving} onClick={()=>void removeCategory(item)} aria-label={`Delete category ${item.name}`}><Trash2 size={14}/> Delete</button></div></article>)}
     {!categories.length&&!categoryLoadError&&<p className="v27-category-empty">{categoryLoading?'Loading categories…':'No personal categories yet. Add one below.'}</p>}
    </div>
    <form onSubmit={saveCategory}><div className="v27-event-fields">
     <h3>{categoryEditing?'Edit category':'Add a category'}</h3>
     {categoryError&&<div className="data-error-banner" role="alert">{categoryError}</div>}
     <label>Category name<input required minLength={2} maxLength={48} autoFocus value={categoryDraft.name} onChange={e=>setCategoryDraft({...categoryDraft,name:e.target.value})}/></label>
     <label>Category color<select value={categoryDraft.color} onChange={e=>setCategoryDraft({...categoryDraft,color:e.target.value as CategoryColor})}>{colors.map(color=><option key={color} value={color}>{color.charAt(0).toUpperCase()+color.slice(1)}</option>)}</select></label>
    </div><div className="modal-footer">{categoryEditing&&<button type="button" className="btn outline" onClick={resetCategoryForm} disabled={saving}>Cancel edit</button>}<button type="submit" className="btn primary" disabled={saving}>{saving?'Saving…':categoryEditing?'Save category':'Add category'}</button></div></form>
   </div>
  </div>}
  {settings&&<div className="modal-overlay" onMouseDown={e=>{if(e.target===e.currentTarget&&!saving)setSettings(null)}}>
   <div className="modal-box v27-event-dialog" role="dialog" aria-modal="true" aria-labelledby="v27-settings-title" onKeyDown={e=>{if(e.key==='Escape'&&!saving)setSettings(null)}}>
    <div className="modal-header"><div><span className="eyebrow">PERSONAL PREFERENCES</span><h2 id="v27-settings-title">Calendar settings</h2><p>Applies only to your account.</p></div><button type="button" className="icon-button" onClick={()=>setSettings(null)} disabled={saving} aria-label="Close"><X size={20}/></button></div>
    <form onSubmit={savePreferences}><div className="v27-event-fields">
     {prefsError&&<div className="data-error-banner" role="alert">{prefsError}</div>}
     <label>Default calendar view<select autoFocus value={settings.preferred_view} onChange={e=>setSettings({...settings,preferred_view:e.target.value as CalendarView})}><option value="month">Month</option><option value="agenda">Agenda</option></select></label>
     <label>Default agenda period<select value={settings.agenda_days} onChange={e=>setSettings({...settings,agenda_days:Number(e.target.value) as AgendaDays})}><option value={7}>7 days</option><option value={14}>14 days</option><option value={30}>30 days</option></select></label>
     <label>Week starts on<select value={settings.week_start} onChange={e=>setSettings({...settings,week_start:e.target.value as Preferences['week_start']})}><option value="monday">Monday</option><option value="sunday">Sunday</option></select></label>
     <label>Show events<select value={settings.visibility} onChange={e=>setSettings({...settings,visibility:e.target.value as Preferences['visibility']})}><option value="all">HR and personal events</option><option value="official">HR events only</option><option value="personal">Personal events only</option></select></label>
     <label>Default personal event time (optional)<input type="time" value={settings.default_start_time} onChange={e=>setSettings({...settings,default_start_time:e.target.value})}/></label>
     <label className="v27-export-preference"><input type="checkbox" checked={settings.include_private_export} onChange={e=>setSettings({...settings,include_private_export:e.target.checked})}/> Include private events and notes in calendar exports</label>
     <small>Leave this off when sharing your calendar file with others.</small>
    </div><div className="modal-footer"><button type="button" className="btn outline" onClick={()=>setSettings(defaults)} disabled={saving}>Reset defaults</button><button type="submit" className="btn primary" disabled={saving}>{saving?'Saving…':'Save settings'}</button></div></form>
   </div>
  </div>}
 </div>;
}
