import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import {useCallback,useEffect,useMemo,useState} from 'react';
import {CalendarDays,ChevronLeft,ChevronRight,Clock3,Download,Edit3,Plus,Trash2,X} from 'lucide-react';
import './personal-calendar.css';

type Event={id?:number;day:string;kind:string;title:string;status:string;start_time?:string;notes?:string;personal?:boolean};
type Draft={day:string;start_time:string;title:string;notes:string};
const isoDate=(d:Date)=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
const blank=(day:string):Draft=>({day,start_time:'',title:'',notes:''});
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
async function api<T>(path:string,method='GET',body?:unknown):Promise<T>{
 const token=sessionStorage.getItem('sass_token');
 const response=await hrmFetch(API+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});
 let data:any={};try{data=await response.json()}catch{}
 if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:`Calendar request failed (${response.status})`);
 return data as T;
}
const readable=(day:string)=>new Date(day+'T12:00:00').toLocaleDateString('en-IN',{weekday:'short',day:'numeric',month:'short',year:'numeric'});
function icsEscape(value:string){return value.replace(/\\/g,'\\\\').replace(/\r?\n/g,'\\n').replace(/,/g,'\\,').replace(/;/g,'\\;');}
function downloadIcs(events:Event[]){
 const lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//SASS HRM//Personal Workspace//EN','CALSCALE:GREGORIAN'];
 for(const item of events){
  if(!/^\d{4}-\d{2}-\d{2}$/.test(item.day))continue;
  const dt=item.day.replaceAll('-','');
  const timestamp=item.start_time&&/^\d{2}:\d{2}$/.test(item.start_time)?dt+'T'+item.start_time.replace(':','')+'00':dt;
  lines.push('BEGIN:VEVENT',`UID:${item.personal?'personal':'work'}-${item.id||`${item.kind}-${dt}`}@sass-hrm.local`, `DTSTAMP:${new Date().toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'')}`, `DTSTART${item.start_time?':':';VALUE=DATE:'}${timestamp}`,`SUMMARY:${icsEscape(item.title)}`,`DESCRIPTION:${icsEscape(item.personal?item.notes||'Personal event':`${item.kind} · ${item.status}`)}`,'END:VEVENT');
 }
 lines.push('END:VCALENDAR');
 const ics=lines.join('\r\n')+'\r\n';const blob=new Blob([ics],{type:'text/calendar;charset=utf-8'});const link=document.createElement('a');const uri=URL.createObjectURL(blob);
 try{link.href=uri;link.download='sass-my-calendar.ics';link.click()}finally{window.setTimeout(()=>URL.revokeObjectURL(uri),1500)}
}
export function PersonalCalendar({official}:{official:Event[]}){
 const [nowMonth,setNowMonth]=useState(()=>{const d=new Date();return new Date(d.getFullYear(),d.getMonth(),1)});
 const [personal,setPersonal]=useState<Event[]>([]);const [selected,setSelected]=useState(isoDate(new Date()));
 const [filter,setFilter]=useState('');const[form,setForm]=useState<Draft|null>(null);const[editing,setEditing]=useState<number|null>(null);
 const [saving,setSaving]=useState(false);const[error,setError]=useState('');const[notice,setNotice]=useState('');const[loading,setLoading]=useState(false);
 const reload=useCallback(async()=>{setLoading(true);setError('');try{const items=await api<Event[]>('/calendar/personal');setPersonal(items.map(v=>({...v,kind:'Personal',status:'Private',personal:true}))) }catch(e){setError((e as Error).message)}finally{setLoading(false)}},[]);
 useEffect(()=>{void reload()},[reload]);
 useRefreshData(reload);
 const allEvents=useMemo(()=>[...official,...personal].filter(x=>/^\d{4}-\d{2}-\d{2}$/.test(x.day)).sort((a,b)=>a.day.localeCompare(b.day)||(a.start_time||'').localeCompare(b.start_time||'')),[official,personal]);
 const searchEvents=useMemo(()=>allEvents.filter(x=>[x.title,x.kind,x.status,x.notes].some(v=>String(v||'').toLowerCase().includes(filter.toLowerCase()))),[allEvents,filter]);
 const monthEvents=searchEvents.filter(x=>x.day.startsWith(isoDate(nowMonth).slice(0,7)));
 const selectedEvents=searchEvents.filter(x=>x.day===selected);
 const today=isoDate(new Date());
 const startOffset=(nowMonth.getDay()+6)%7;
 const days=Array.from({length:Math.ceil((new Date(nowMonth.getFullYear(),nowMonth.getMonth()+1,0).getDate()+startOffset)/7)*7},(_,i)=>i-startOffset+1);
 const monthDays=new Date(nowMonth.getFullYear(),nowMonth.getMonth()+1,0).getDate();
 function monthShift(offset:number){const d=new Date(nowMonth.getFullYear(),nowMonth.getMonth()+offset,1);setNowMonth(d);setSelected(isoDate(d))}
 function startEdit(event?:Event){setError('');setNotice('');setEditing(event?.id??null);setForm(event?{day:event.day,title:event.title,start_time:event.start_time||'',notes:event.notes||''}:blank(selected))}
 async function save(ev:React.FormEvent){ev.preventDefault();if(!form||saving)return;setSaving(true);setError('');setNotice('');try{
  await api(editing?`/calendar/personal/${editing}`:'/calendar/personal',editing?'PATCH':'POST',form);
  setForm(null);setNotice(editing?'Personal event updated.':'Personal event added.');setSelected(form.day);setNowMonth(new Date(Number(form.day.slice(0,4)),Number(form.day.slice(5,7))-1,1));await reload();
 }catch(e){setError((e as Error).message)}finally{setSaving(false)}}
 async function remove(event:Event){if(!event.id||!window.confirm(`Remove your personal event “${event.title}”?`))return;setError('');try{await api(`/calendar/personal/${event.id}`,'DELETE');setNotice('Personal event removed.');await reload()}catch(e){setError((e as Error).message)}}
 return <div className="v27-calendar" aria-busy={loading}>
  <div className="v27-cal-intro"><div><div className="eyebrow">TIME / PERSONAL PLANNER</div><h1>My calendar</h1><p>View approved HR dates alongside your private plans. Personal entries are visible only to your signed-in account.</p></div><div className="v27-cal-actions"><button type="button" className="btn outline" onClick={()=>downloadIcs(searchEvents)} disabled={!searchEvents.length}><Download size={16}/> Export .ics</button><button className="btn primary" type="button" onClick={()=>startEdit()}><Plus size={16}/> Add personal event</button></div></div>
  {error&&<div className="data-error-banner" role="alert">{error}</div>}{notice&&<p role="status" className="v27-notice">{notice}</p>}
  <div className="v27-cal-toolbar"><label>Search calendar<input value={filter} onChange={e=>setFilter(e.target.value)} placeholder="Search dates and events"/></label><button type="button" className="btn subtle" onClick={()=>{setNowMonth(new Date(new Date().getFullYear(),new Date().getMonth(),1));setSelected(today)}}>Today</button></div>
  <div className="v27-calendar-layout"><section className="v27-month section-card"><div className="v27-month-head"><div><h2>{nowMonth.toLocaleDateString('en-IN',{month:'long',year:'numeric'})}</h2><p>{monthEvents.length} event{monthEvents.length!==1?'s':''} this month</p></div><div className="v27-month-arrows"><button type="button" aria-label="Previous month" onClick={()=>monthShift(-1)}><ChevronLeft size={19}/></button><button type="button" aria-label="Next month" onClick={()=>monthShift(1)}><ChevronRight size={19}/></button></div></div><div className="v27-day-grid">{['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map(d=><div key={d} className="v27-weekday">{d}</div>)}{days.map((day,i)=>{const actual=new Date(nowMonth.getFullYear(),nowMonth.getMonth(),day),iso=isoDate(actual),isCurrent=day>0&&day<=monthDays;const onDay=searchEvents.filter(x=>x.day===iso);return <button type="button" key={i} onClick={()=>{setSelected(iso);if(!isCurrent)setNowMonth(new Date(actual.getFullYear(),actual.getMonth(),1))}} className={`v27-day ${isCurrent?'':'v27-other'} ${selected===iso?'v27-selected':''} ${today===iso?'v27-today':''}`} aria-label={`${readable(iso)}, ${onDay.length} events`} aria-pressed={selected===iso}><span>{actual.getDate()}</span><div className="v27-dots">{onDay.slice(0,3).map((e,j)=><i key={j} className={e.personal?'v27-personal':'v27-official'}/>)}</div></button>})}</div><div className="v27-cal-legend"><span><i className="v27-official"/> Organization / HR</span><span><i className="v27-personal"/> Private entry</span></div></section>
  <section className="section-card v27-agenda"><div className="v27-agenda-head"><div><h3>{readable(selected)}</h3><p>{selectedEvents.length} event{selectedEvents.length!==1?'s':''}</p></div><button type="button" aria-label="Add event on selected day" title="Add event on this day" onClick={()=>startEdit()}><Plus size={18}/></button></div><div className="v27-agenda-list">{selectedEvents.length?selectedEvents.map((item,i)=><article key={`${item.kind}-${item.id||i}-${item.day}-${i}`} className="v27-agenda-item"><span className={`v27-event-type ${item.personal?'v27-personal-event':''}`}><CalendarDays size={17}/></span><div><strong>{item.title}</strong><small>{item.kind} · {item.status}{item.start_time?` · ${item.start_time}`:''}</small>{item.personal&&item.notes&&<p>{item.notes}</p>}{item.personal&&<div className="v27-agenda-buttons"><button type="button" onClick={()=>startEdit(item)}><Edit3 size={13}/> Edit</button><button type="button" onClick={()=>void remove(item)}><Trash2 size={13}/> Remove</button></div>}</div></article>):<div className="v27-day-empty"><Clock3 size={25}/><strong>No events on this date</strong><p>Add a private reminder or select another day. Existing HR dates appear automatically when recorded.</p><button type="button" className="btn outline" onClick={()=>startEdit()}>Add personal event</button></div>}</div></section></div>
  {form&&<div className="modal-overlay" onMouseDown={e=>{if(e.target===e.currentTarget&&!saving)setForm(null)}}><div className="modal-box v27-event-dialog" role="dialog" aria-modal="true" aria-labelledby="v27-modal-title"><div className="modal-header"><div><span className="eyebrow">PRIVATE CALENDAR</span><h2 id="v27-modal-title">{editing?'Edit personal event':'Add personal event'}</h2><p>Only you can view or edit this personal calendar entry.</p></div><button type="button" className="icon-button" onClick={()=>setForm(null)} disabled={saving} aria-label="Close"><X size={20}/></button></div><form onSubmit={save}><div className="v27-event-fields"><label>Event title<input required minLength={2} maxLength={120} autoFocus value={form.title} onChange={e=>setForm({...form,title:e.target.value})}/></label><label>Date<input required type="date" value={form.day} onChange={e=>setForm({...form,day:e.target.value})}/></label><label>Time (optional)<input type="time" value={form.start_time} onChange={e=>setForm({...form,start_time:e.target.value})}/></label><label>Private notes (optional)<textarea rows={3} maxLength={1000} value={form.notes} onChange={e=>setForm({...form,notes:e.target.value})}/></label></div><div className="modal-footer"><button type="button" className="btn outline" onClick={()=>setForm(null)} disabled={saving}>Cancel</button><button type="submit" className="btn primary" disabled={saving}>{saving?'Saving…':'Save personal event'}</button></div></form></div></div>}
 </div>;
}
