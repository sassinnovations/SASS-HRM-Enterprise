import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import {useCallback,useEffect,useState} from 'react';
import {CalendarDays, ChevronLeft, ChevronRight, ClipboardList, Plus, Settings2, ShieldCheck, UsersRound} from 'lucide-react';
import './workforce-planning.css';

type Day={day:string;approved_count:number;coverage_warning:boolean;on_leave:{employee_id:number;employee_name:string;department:string;leave_type:string}[];holidays:{name:string;location:string}[]};
type Planner={month:string;scope:string;department:string|null;warning_threshold:number;days:Day[];summary:{approved_requests:number;people_with_leave:number;coverage_warning_days:number}};
type Template={id:number;title:string;guidance:string;priority:string;due_offset_days:number;active:number;created_at:string};
type Assignment={id:number;title:string;employee_name:string;due_date:string;status:string};
type Employee={id:number;name:string;department:string;manager_id?:number;account_active?:number};
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
async function call<T>(path:string,method='GET',body?:unknown):Promise<T>{
 const token=sessionStorage.getItem('sass_token');
 const res=await hrmFetch(API+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});
 const obj=await res.json().catch(()=>null);
 if(!res.ok)throw new Error(typeof obj?.detail==='string'?obj.detail:`Request failed (${res.status})`);
 return obj as T;
}
const dateOnly=(d:Date)=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
const currentMonth=()=>dateOnly(new Date()).slice(0,7);
const moveMonth=(month:string,offset:number)=>{const [y,m]=month.split('-').map(Number);const d=new Date(y,m-1+offset,1);return dateOnly(d).slice(0,7)};

export function LeaveCoveragePlanner({isHR}:{isHR:boolean}){
 const [month,setMonth]=useState(currentMonth());
 const [dept,setDept]=useState('');
 const [threshold,setThreshold]=useState(2);
 const [data,setData]=useState<Planner|null>(null);
 const [error,setError]=useState('');
 const [notice,setNotice]=useState('');
 const [busy,setBusy]=useState(false);
 const [showSettings,setShowSettings]=useState(false);
 const load=useCallback(async()=>{
  setBusy(true);setError('');
  try{const out=await call<Planner>(`/workforce/leave-coverage?month=${month}${dept?`&department=${encodeURIComponent(dept)}`:''}`);setData(out);setThreshold(out.warning_threshold)}
  catch(e){setError((e as Error).message)}finally{setBusy(false)}
 },[month,dept]);
 useEffect(()=>{void load()},[load]);
 useRefreshData(load);
 const offset=new Date(`${month}-01T12:00:00`).getDay();
 const mondayOffset=(offset+6)%7;
 const monthLabel=new Date(`${month}-01T12:00:00`).toLocaleDateString('en-IN',{month:'long',year:'numeric'});
 const save=async()=>{
  setBusy(true);setError('');setNotice('');
  try{await call('/workforce/leave-coverage/settings','PUT',{warning_threshold:Number(threshold)});setNotice('Coverage threshold saved. Warnings are advisory and do not reject leave.');await load()}
  catch(e){setError((e as Error).message)}finally{setBusy(false)}
 };
 return <section className="wf-page">
  <header className="wf-header"><div><small>WORKFORCE / PLANNING</small><h1>Team leave & coverage planner</h1><p>Approved leave and office holidays in one calendar. Leave reasons and private information are never shown.</p></div><div className="wf-toolbar">{isHR&&<button onClick={()=>setShowSettings(v=>!v)}><Settings2 size={16}/> Coverage settings</button>}</div></header>
  <div className="wf-cards"><article><CalendarDays size={19}/><span>Approved leave requests</span><strong>{data?.summary.approved_requests??'—'}</strong></article><article><UsersRound size={19}/><span>People taking leave</span><strong>{data?.summary.people_with_leave??'—'}</strong></article><article><ShieldCheck size={19}/><span>Coverage warning days</span><strong>{data?.summary.coverage_warning_days??'—'}</strong></article></div>
  {showSettings&&isHR&&<div className="wf-panel"><h3>Coverage warning settings</h3><p>Highlight a day when the visible approved absences meet this threshold. This is an advisory alert, not an automated staffing decision.</p><div className="wf-form-row"><label>Absence warning threshold<input type="number" min={1} max={50} value={threshold} onChange={e=>setThreshold(Number(e.target.value))}/></label><button className="wf-primary" disabled={busy||threshold<1||threshold>50} onClick={()=>void save()}>Save settings</button></div></div>}
  <div className="wf-panel"><div className="wf-calendar-top"><div className="wf-month-nav"><button aria-label="Previous month" onClick={()=>setMonth(v=>moveMonth(v,-1))}><ChevronLeft size={18}/></button><h2>{monthLabel}</h2><button aria-label="Next month" onClick={()=>setMonth(v=>moveMonth(v,1))}><ChevronRight size={18}/></button></div><div className="wf-form-row">{isHR&&<label>Department (optional)<input value={dept} maxLength={100} onChange={e=>setDept(e.target.value)} placeholder="Exact department name"/></label>}<button onClick={()=>{setMonth(currentMonth());setDept('')}}>Current month</button></div></div>
   {data&&<p className="wf-muted">Visibility: {data.scope} · Warning threshold: {data.warning_threshold} approved absences</p>}
   <div className="wf-calendar-grid">{['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map(x=><strong className="wf-weekday" key={x}>{x}</strong>)}{Array.from({length:mondayOffset},(_,i)=><div className="wf-filler" key={`f${i}`}/>)}{data?.days.map(d=><div className={`wf-day ${d.coverage_warning?'wf-warning':''}`} key={d.day}><b>{Number(d.day.slice(-2))}</b>{d.holidays.map((h,i)=><small className="wf-holiday" key={i}>{h.name}</small>)}{d.on_leave.slice(0,3).map(p=><small key={p.employee_id} title={`${p.employee_name} · ${p.leave_type}`}>{p.employee_name}</small>)}{d.on_leave.length>3&&<small>+{d.on_leave.length-3} more</small>}{d.coverage_warning&&<em>Review coverage</em>}</div>)}</div>
  </div>
  {error&&<p className="wf-error" role="alert">{error}</p>}{notice&&<p className="wf-notice" role="status">{notice}</p>}
  <p className="wf-disclaimer"><ShieldCheck size={16}/> Employees see only their approved absences; managers see direct-report coverage; HR administrators can review organization coverage. This planner does not grant leave approval rights.</p>
 </section>;
}

export function HRTaskTemplates({isHR,userId,employees}:{isHR:boolean;userId:number;employees:Employee[]}){
 const [items,setItems]=useState<Template[]>([]);
 const [assignments,setAssignments]=useState<Assignment[]>([]);
 const [archived,setArchived]=useState(false);
 const [title,setTitle]=useState('');const [guidance,setGuidance]=useState('');
 const [priority,setPriority]=useState('Normal');const [days,setDays]=useState(3);
 const [selected,setSelected]=useState('');const [emp,setEmp]=useState('');const [start,setStart]=useState(dateOnly(new Date()));
 const [search,setSearch]=useState('');const [error,setError]=useState('');const [notice,setNotice]=useState('');const [busy,setBusy]=useState(false);
 const load=useCallback(async()=>{setError('');try{
  const [templates,existing]=await Promise.all([call<Template[]>(`/workforce/task-templates${archived?'?include_archived=true':''}`),call<Assignment[]>('/workforce/task-templates/assignments')]);
  setItems(templates);setAssignments(existing);
 }catch(e){setError((e as Error).message)}},[archived]);
 useEffect(()=>{void load()},[load]);
 useRefreshData(load);
 const act=async(fn:()=>Promise<unknown>,success:string)=>{setBusy(true);setError('');setNotice('');try{await fn();setNotice(success);await load()}catch(e){setError((e as Error).message)}finally{setBusy(false)}};
 const eligibleEmployees=employees.filter(e=>e.account_active!==0&&(isHR||e.id===userId||e.manager_id===userId));
 const filtered=items.filter(x=>[x.title,x.guidance,x.priority].join(' ').toLowerCase().includes(search.toLowerCase()));
 return <section className="wf-page"><header className="wf-header"><div><small>TALENT / REUSABLE WORK</small><h1>HR task templates</h1><p>Standardize repeatable HR assignments. Every assignment creates a real task with a due date, owner and audit record.</p></div><div className="wf-toolbar"></div></header>
 {isHR&&<div className="wf-panel"><h3>Create a reusable template</h3><div className="wf-form-grid"><label>Task title<input value={title} maxLength={160} onChange={e=>setTitle(e.target.value)} placeholder="Conduct new hire check-in"/></label><label>Priority<select value={priority} onChange={e=>setPriority(e.target.value)}>{['Low','Normal','High'].map(x=><option key={x}>{x}</option>)}</select></label><label>Due after (days)<input type="number" min={0} max={365} value={days} onChange={e=>setDays(Number(e.target.value))}/></label></div><label className="wf-long-field">Instructions (stored as the task's initial comment)<textarea rows={2} maxLength={1000} value={guidance} onChange={e=>setGuidance(e.target.value)}/></label><button className="wf-primary" disabled={busy||title.trim().length<4||days<0||days>365} onClick={()=>void act(()=>call('/workforce/task-templates','POST',{title,guidance,priority,due_offset_days:days}),'Task template created.')}><Plus size={16}/> Create template</button></div>}
 <div className="wf-panel"><div className="wf-panel-title"><div><h3>Template library</h3><p>HR administrators manage template availability. Managers can assign active templates to their teams.</p></div><label>Find template<input type="search" placeholder="Search templates" value={search} onChange={e=>setSearch(e.target.value)}/></label></div>{isHR&&<label className="wf-inline"><input type="checkbox" checked={archived} onChange={e=>setArchived(e.target.checked)}/> Show archived templates</label>}
 <div className="wf-list">{filtered.length?filtered.map(t=><div className="wf-list-row" key={t.id}><div><strong>{t.title}</strong><p>{t.guidance||'No additional instructions'}</p><small>{t.priority} priority · Due {t.due_offset_days} day(s) after assignment start</small></div><div className="wf-toolbar">{!t.active&&<span className="wf-tag">Archived</span>}{isHR&&<button disabled={busy} onClick={()=>void act(()=>call(`/workforce/task-templates/${t.id}`,'PATCH',{active:!t.active}),'Template availability updated.')}>{t.active?'Archive':'Restore'}</button>}</div></div>):<p className="wf-muted">No templates match this search.</p>}</div></div>
 <div className="wf-panel"><h3>Assign a template</h3><div className="wf-form-grid"><label>Template<select value={selected} onChange={e=>setSelected(e.target.value)}><option value="">Select active template</option>{items.filter(t=>t.active).map(t=><option key={t.id} value={t.id}>{t.title}</option>)}</select></label><label>Employee<select value={emp} onChange={e=>setEmp(e.target.value)}><option value="">Select employee</option>{eligibleEmployees.map(e=><option key={e.id} value={e.id}>{e.name} · {e.department}</option>)}</select></label><label>Start date<input type="date" min={dateOnly(new Date())} value={start} onChange={e=>setStart(e.target.value)}/></label></div><button className="wf-primary" disabled={busy||!selected||!emp||!start} onClick={()=>void act(()=>call(`/workforce/task-templates/${selected}/assign`,'POST',{employee_id:Number(emp),start_date:start}),'HR task assigned; employee notified.') }><ClipboardList size={16}/> Assign task</button><p className="wf-muted">Managers may only assign tasks within their authorized team. Duplicate assignments for the same template, employee and start date are blocked.</p></div>
 <div className="wf-panel"><h3>Recent template assignments</h3><div className="wf-list">{assignments.length?assignments.map(a=><div className="wf-list-row" key={a.id}><div><strong>{a.title}</strong><small>{a.employee_name} · Due {a.due_date}</small></div><span className="wf-tag">{a.status}</span></div>):<p className="wf-muted">No template assignments yet.</p>}</div></div>
 {error&&<p className="wf-error" role="alert">{error}</p>}{notice&&<p className="wf-notice" role="status">{notice}</p>}
 </section>;
}
