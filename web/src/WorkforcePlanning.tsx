import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import {useCallback,useEffect,useRef,useState} from 'react';
import {CalendarDays, ChevronLeft, ChevronRight, ClipboardList, Plus, Settings2, ShieldCheck, UsersRound} from 'lucide-react';
import './workforce-planning.css';

type Day={day:string;approved_count:number;coverage_warning:boolean;on_leave:{employee_id:number;employee_name:string;department:string;leave_type:string|null}[];holidays:{name:string;location:string}[]};
type CoverageDraft={label:string;primary_employee_id:string;backup_employee_id:string;starts_on:string;ends_on:string;status:'Planned'|'Confirmed';notes:string};
type CoveragePlan=Omit<CoverageDraft,'primary_employee_id'|'backup_employee_id'|'notes'>&{id:number;primary_employee_id:number;backup_employee_id:number;primary_name:string;backup_name:string;revision:number;notes?:string;is_mine:boolean;backup_on_leave?:boolean;parallel_backup_days?:string[];backup_leave_days?:string[]};
type CoveragePreferences={default_department:string|null;show_holidays:boolean;plan_status:'All'|CoverageDraft['status'];my_assignments_only:boolean};
const defaultCoveragePreferences:CoveragePreferences={default_department:null,show_holidays:true,plan_status:'All',my_assignments_only:false};
type Planner={month:string;scope:string;department:string|null;warning_threshold:number;weekdays_only:boolean;days:Day[];manual_plans:CoveragePlan[];staff_choices:{id:number;name:string;department:string}[];summary:{approved_requests:number;people_with_leave:number;coverage_warning_days:number}};
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
const coverageDateLabel=(day:string)=>new Date(`${day}T12:00:00`).toLocaleDateString('en-IN',
 {weekday:'short',day:'numeric',month:'short',year:'numeric'});


export function LeaveCoveragePlanner({isHR}:{isHR:boolean}){
 const [month,setMonth]=useState(currentMonth);
 const [dept,setDept]=useState('');
 const [threshold,setThreshold]=useState('2');
 const [weekdaysOnly,setWeekdaysOnly]=useState(false);
 const [data,setData]=useState<Planner|null>(null);
 const [error,setError]=useState('');
 const [notice,setNotice]=useState('');
 const [loading,setLoading]=useState(false);
 const [saving,setSaving]=useState(false);
 const [showSettings,setShowSettings]=useState(false);
 const [draft,setDraft]=useState<CoverageDraft|null>(null);
 const [edit,setEdit]=useState<{id:number;revision:number}|null>(null);
 const [prefs,setPrefs]=useState<CoveragePreferences>(defaultCoveragePreferences);
 const [prefDraft,setPrefDraft]=useState<CoveragePreferences|null>(null);
 const [prefError,setPrefError]=useState('');
 const [prefsLoading,setPrefsLoading]=useState(true);
 const [reviewDate,setReviewDate]=useState(()=>dateOnly(new Date()));
 const [warningsOnly,setWarningsOnly]=useState(false);
 const reviewRef=useRef<HTMLElement>(null);
 const planTitleRef=useRef<HTMLInputElement>(null);
 const editingPlan=!!draft;
 useEffect(()=>{if(editingPlan)planTitleRef.current?.focus()},[editingPlan]);
 const generation=useRef(0);
 useEffect(()=>{
  let current=true;
  call<CoveragePreferences>('/workforce/leave-coverage/preferences').then(out=>{
   if(current){setPrefs(out);if(isHR)setDept(out.default_department||'');setPrefError('')}
  }).catch(()=>{if(current)setPrefError('Could not load your settings. Default planner filters are shown.')})
  .finally(()=>{if(current)setPrefsLoading(false)});
  return ()=>{current=false};
 },[isHR]);
 const load=useCallback(async()=>{
  if(prefsLoading)return;
  const request=++generation.current;
  setLoading(true);setError('');
  try{
   const out=await call<Planner>(`/workforce/leave-coverage?month=${month}${dept?`&department=${encodeURIComponent(dept)}`:''}`);
   if(request===generation.current)setData(out);
  }catch(e){if(request===generation.current)setError((e as Error).message)}
  finally{if(request===generation.current)setLoading(false)}
 },[month,dept,prefsLoading]);
 useEffect(()=>{void load();return ()=>{generation.current++}},[load]);
 useRefreshData(load);
 const visible=data?.month===month&&(data.department||'')===dept?data:null;
 const plans=(visible?.manual_plans||[]).filter(p=>(prefs.plan_status==='All'||p.status===prefs.plan_status)&&
  (!prefs.my_assignments_only||p.is_mine));
 const dayReviews=(visible?.days||[]).map(day=>{
  const active=plans.filter(p=>p.starts_on<=day.day&&p.ends_on>=day.day);
  const backupConflict=active.some(p=>p.parallel_backup_days?.includes(day.day)||p.backup_leave_days?.includes(day.day));
  return {day,plans:active,warning:day.coverage_warning||backupConflict,backupConflict};
 });
 const warningDays=dayReviews.filter(d=>d.warning).length;
 const filteredReview=warningsOnly?dayReviews.filter(d=>d.warning):dayReviews;
 const selectedReview=filteredReview.find(d=>d.day.day===reviewDate)??filteredReview[0];
 const openReview=(day:string,warning:boolean)=>{
  setReviewDate(day);
  if(!warning)setWarningsOnly(false);
  reviewRef.current?.scrollIntoView({block:'nearest'});
 };
 const staff=visible?.staff_choices||[];
 const canEdit=visible?.scope==='organization'||visible?.scope==='team';
 const departments=Array.from(new Set((data?.staff_choices||[]).map(person=>person.department).filter(Boolean))).sort();
 const offset=new Date(`${month}-01T12:00:00`).getDay();
 const mondayOffset=(offset+6)%7;
 const monthLabel=new Date(`${month}-01T12:00:00`).toLocaleDateString('en-IN',{month:'long',year:'numeric'});
 const busy=saving||loading||prefsLoading;
 const savePreferences=async()=>{
  if(!prefDraft||busy)return;
  setSaving(true);setPrefError('');setNotice('');
  try{
   const out=await call<CoveragePreferences>('/workforce/leave-coverage/preferences','PUT',prefDraft);
   setPrefs(out);setDept(out.default_department||'');setPrefDraft(null);setNotice('Your planner settings were saved.');
  }catch(e){setPrefError((e as Error).message)}finally{setSaving(false)}
 };
 const saveSettings=async(nextThreshold:number,nextWeekdays:boolean)=>{
  if(busy||!Number.isInteger(nextThreshold)||nextThreshold<1||nextThreshold>50)return;
  setSaving(true);setError('');setNotice('');
  try{
   await call('/workforce/leave-coverage/settings','PUT',{warning_threshold:nextThreshold,weekdays_only:nextWeekdays});
   setThreshold(String(nextThreshold));setWeekdaysOnly(nextWeekdays);setShowSettings(false);
   setNotice('Coverage settings saved. Warnings do not reject leave.');await load();
  }catch(e){setError((e as Error).message)}finally{setSaving(false)}
 };
 const beginPlan=(chosenDay?:string)=>{
  const day=chosenDay||(month===currentMonth()?dateOnly(new Date()):`${month}-01`);
  setEdit(null);setDraft({label:'',primary_employee_id:'',backup_employee_id:'',starts_on:day,ends_on:day,status:'Planned',notes:''});
  setNotice('');setError('');
 };
 const editPlan=(p:CoveragePlan)=>{
  setEdit({id:p.id,revision:p.revision});
  setDraft({label:p.label,primary_employee_id:String(p.primary_employee_id),backup_employee_id:String(p.backup_employee_id),
   starts_on:p.starts_on,ends_on:p.ends_on,status:p.status,notes:p.notes||''});
  setNotice('');setError('');
 };
 const updateDraft=(patch:Partial<CoverageDraft>)=>setDraft(old=>old?{...old,...patch}:old);
 const savePlan=async()=>{
  if(busy||!draft||!draft.label.trim()||!draft.primary_employee_id||!draft.backup_employee_id||draft.primary_employee_id===draft.backup_employee_id)return;
  setSaving(true);setError('');setNotice('');
  try{
   await call('/workforce/leave-coverage/plans'+(edit?`/${edit.id}`:''),edit?'PUT':'POST',{
    ...draft,primary_employee_id:Number(draft.primary_employee_id),backup_employee_id:Number(draft.backup_employee_id),
    ...(edit?{revision:edit.revision}:{})
   });
   const mayBeFiltered=prefs.plan_status!=='All'||prefs.my_assignments_only;
  setNotice((edit?'Coverage plan updated.':'Coverage plan added.')+(mayBeFiltered?' Your personal filters may hide it from this view.':''));
  setEdit(null);setDraft(null);
   const starts=draft.starts_on.slice(0,7),ends=draft.ends_on.slice(0,7);
   const changedMonth=month<starts||month>ends;
   const changedDepartment=!!dept&&staff.find(p=>p.id===Number(draft.primary_employee_id))?.department!==dept;
   if(changedMonth)setMonth(starts);
   if(changedDepartment)setDept('');
   if(!changedMonth&&!changedDepartment)await load();
  }catch(e){setError((e as Error).message)}finally{setSaving(false)}
 };
 const removePlan=async(p:CoveragePlan)=>{
  if(!window.confirm(`Delete the coverage plan “${p.label}”? Approved leave will not change.`))return;
  setSaving(true);setError('');setNotice('');
  try{
   await call(`/workforce/leave-coverage/plans/${p.id}`,'DELETE',{confirm:'DELETE',revision:p.revision});
   if(edit?.id===p.id){setEdit(null);setDraft(null)}
   setNotice('Coverage plan deleted.');await load();
  }catch(e){setError((e as Error).message)}finally{setSaving(false)}
 };
 const staffOptions=(selected:string)=> <>
  <option value="">Choose employee</option>
  {selected&&!staff.some(person=>String(person.id)===selected)&&<option value={selected}>Previously assigned (inactive)</option>}
  {staff.map(person=><option key={person.id} value={person.id}>{person.name} · {person.department}</option>)}
 </>;
 return <section className="wf-page">
  <header className="wf-header"><div><small>WORKFORCE / PLANNING</small><h1>Team leave & coverage planner</h1><p>See approved absences, holidays, and backup assignments without changing leave records.</p></div><div className="wf-toolbar">
   <button type="button" aria-expanded={!!prefDraft} disabled={busy} onClick={()=>setPrefDraft(p=>p?null:{...prefs})}><Settings2 size={16}/> My planner settings</button>
   {isHR&&<button type="button" aria-expanded={showSettings} disabled={!visible||saving} onClick={()=>{if(visible){setThreshold(String(visible.warning_threshold));setWeekdaysOnly(visible.weekdays_only);setShowSettings(v=>!v)}}}><Settings2 size={16}/> Coverage settings</button>}
  </div></header>
  <div className="wf-cards wf-coverage-cards"><article><CalendarDays size={19}/><span>Approved leave requests</span><strong>{visible?.summary.approved_requests??'—'}</strong></article><article><UsersRound size={19}/><span>People taking leave</span><strong>{visible?.summary.people_with_leave??'—'}</strong></article><article><ClipboardList size={19}/><span>{canEdit?'Manual coverage plans':'My coverage plans'}</span><strong>{visible?plans.length:'—'}</strong></article><article><ShieldCheck size={19}/><span>Coverage warning days</span><strong>{visible?.summary.coverage_warning_days??'—'}</strong></article></div>
  {prefError&&<p className="wf-error" role="alert">{prefError}</p>}
  {error&&<p className="wf-error" role="alert">{error} <button type="button" disabled={busy} onClick={()=>void load()}>Refresh planner</button></p>}{notice&&<p className="wf-notice" role="status">{notice}</p>}
  {prefDraft&&<form className="wf-panel" onSubmit={e=>{e.preventDefault();void savePreferences()}}>
   <h3>My planner settings</h3><p>These display options are saved to your account. They do not change anyone else's view or any leave record.</p>
   <div className="wf-form-row">
    {isHR&&<label>Default department<select aria-label="Default department" value={prefDraft.default_department||''} onChange={e=>setPrefDraft({...prefDraft,default_department:e.target.value||null})}><option value="">All departments</option>{departments.map(d=><option key={d}>{d}</option>)}</select></label>}
    <label>Plan status filter<select aria-label="Plan status filter" value={prefDraft.plan_status} onChange={e=>setPrefDraft({...prefDraft,plan_status:e.target.value as CoveragePreferences['plan_status']})}><option>All</option><option>Planned</option><option>Confirmed</option></select></label>
    <label className="wf-coverage-toggle"><input type="checkbox" checked={prefDraft.show_holidays} onChange={e=>setPrefDraft({...prefDraft,show_holidays:e.target.checked})}/> Show holidays</label>
    {canEdit&&<label className="wf-coverage-toggle"><input type="checkbox" checked={prefDraft.my_assignments_only} onChange={e=>setPrefDraft({...prefDraft,my_assignments_only:e.target.checked})}/> My assignments only</label>}
   </div>
   <div className="wf-form-row">
    <button className="wf-primary" disabled={busy}>Save my planner settings</button>
    <button type="button" disabled={busy} onClick={()=>setPrefDraft({...defaultCoveragePreferences})}>Use planner defaults</button>
    <button type="button" disabled={saving} onClick={()=>setPrefDraft(null)}>Cancel</button>
   </div>
  </form>}
  {showSettings&&isHR&&<form className="wf-panel" onSubmit={e=>{e.preventDefault();void saveSettings(Number(threshold),weekdaysOnly)}}>
   <h3>Coverage warning settings</h3><p>Highlight days when visible approved absences meet the threshold. A warning never blocks a leave request.</p>
   <div className="wf-form-row"><label>Absence warning threshold<input required type="number" min={1} max={50} step={1} value={threshold} onChange={e=>setThreshold(e.target.value)}/></label>
    <label className="wf-coverage-toggle"><input type="checkbox" checked={weekdaysOnly} onChange={e=>setWeekdaysOnly(e.target.checked)}/> Warn only Monday–Friday</label>
    <button className="wf-primary" disabled={busy}>Save settings</button>
    <button type="button" disabled={busy} onClick={()=>{setThreshold('2');setWeekdaysOnly(false)}}>Use defaults</button>
   </div>
  </form>}
  <div className="wf-panel"><div className="wf-calendar-top"><div className="wf-month-nav">
   <button type="button" aria-label="Previous month" disabled={saving||month<='2000-01'} onClick={()=>setMonth(v=>moveMonth(v,-1))}><ChevronLeft size={18}/></button>
   <h2>{monthLabel}</h2><button type="button" aria-label="Next month" disabled={saving||month>='2100-12'} onClick={()=>setMonth(v=>moveMonth(v,1))}><ChevronRight size={18}/></button>
   </div><div className="wf-form-row">
    {isHR&&<label>Department<select value={dept} disabled={saving} onChange={e=>setDept(e.target.value)}><option value="">All departments</option>{departments.map(d=><option key={d}>{d}</option>)}</select></label>}
    <button type="button" disabled={saving} onClick={()=>{setMonth(currentMonth());setDept('');setReviewDate(dateOnly(new Date()))}}>Current month</button>
   </div></div>
   {(loading||prefsLoading)&&!visible&&<p className="wf-muted" role="status">Loading coverage…</p>}
   {visible&&<p className="wf-muted">Visibility: {visible.scope}{canEdit&&` · Warning threshold: ${visible.warning_threshold} approved absences${visible.weekdays_only?' (Monday–Friday)':''}`}</p>}
   <div className="wf-calendar-grid">{['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map(x=><strong className="wf-weekday" key={x}>{x}</strong>)}{Array.from({length:mondayOffset},(_,i)=><div className="wf-filler" key={`f${i}`}/>)}{dayReviews.map(({day:d,plans:activePlans,warning,backupConflict})=>
    <div className={`wf-day ${warning?'wf-warning':''}`} key={d.day}>
     <button className="wf-day-select" type="button" aria-label={`Review coverage for ${d.day}`} aria-pressed={selectedReview?.day.day===d.day}
      onClick={()=>openReview(d.day,warning)}>{Number(d.day.slice(-2))}</button>
     {prefs.show_holidays&&d.holidays.map((h,i)=><small className="wf-holiday" key={i}>{h.name}</small>)}
     {d.on_leave.slice(0,3).map(p=><small key={p.employee_id} title={p.leave_type?`${p.employee_name} · ${p.leave_type}`:p.employee_name}>{p.employee_name}</small>)}
     {d.on_leave.length>3&&<small>+{d.on_leave.length-3} more</small>}
     {activePlans.length>0&&<span className="wf-day-plan">{activePlans.length} {activePlans.length===1?'plan':'plans'}</span>}
     {d.coverage_warning&&<em>Review coverage</em>}
     {backupConflict&&<em>Backup conflict</em>}
    </div>
   )}</div>
  </div>
  {visible&&<section className="wf-panel" id="coverage-day-review" ref={reviewRef} aria-labelledby="coverage-day-heading">
   <div className="wf-panel-title"><div><h3 id="coverage-day-heading">Daily coverage review</h3><p>Approved absences and manual backup plans are listed separately. A backup warning never changes a leave record.</p></div>
    {canEdit&&<label className="wf-inline"><input type="checkbox" checked={warningsOnly} onChange={e=>setWarningsOnly(e.target.checked)}/> Warning days only</label>}
   </div>
   {canEdit&&<p className="wf-muted" role="status">{warningDays} {warningDays===1?'day needs':'days need'} review under the current filters.</p>}
   {selectedReview?<><div className="wf-form-row"><label>Review date<select aria-label="Review date" value={selectedReview.day.day} onChange={e=>setReviewDate(e.target.value)}>
    {filteredReview.map(({day,warning})=><option key={day.day} value={day.day}>{coverageDateLabel(day.day)}{warning?' · Review':''}</option>)}
   </select></label>
    {canEdit&&<button type="button" className="wf-primary" disabled={busy||!!draft} onClick={()=>beginPlan(selectedReview.day.day)}><Plus size={16}/> Add plan for this day</button>}
   </div>
   {selectedReview.day.coverage_warning&&<p className="wf-coverage-conflict">The approved-absence threshold was reached on this date.</p>}
   <div className="wf-coverage-review-columns">
    <div><h4>Approved absences ({selectedReview.day.approved_count})</h4>
     {selectedReview.day.on_leave.length?<ul>{selectedReview.day.on_leave.map(p=><li key={p.employee_id}>{p.employee_name}{p.leave_type? ` · ${p.leave_type}`:''}</li>)}</ul>:<p>No approved absences in this view.</p>}
     {prefs.show_holidays&&selectedReview.day.holidays.length>0&&<div><h4>Office holidays</h4>
      <ul>{selectedReview.day.holidays.map((h,i)=><li key={i}>{h.name} · {h.location}</li>)}</ul></div>}
    </div>
    <div><h4>Manual backup plans ({selectedReview.plans.length})</h4>
     {selectedReview.plans.length?<ul>{selectedReview.plans.map(p=><li key={p.id}>
      <a href={`#coverage-plan-${p.id}`}>{p.label}</a> · Backup: {p.backup_name} · {p.status}
      {p.backup_leave_days?.includes(selectedReview.day.day)&&<span className="wf-day-conflict">Backup on approved leave this day</span>}
      {p.parallel_backup_days?.includes(selectedReview.day.day)&&<span className="wf-day-conflict">Backup booked on multiple plans this day</span>}
     </li>)}</ul>:<p>No manual plans match this date and your filters.</p>}
    </div>
   </div></>:<p className="wf-muted">No warning days under the current filters.</p>}
  </section>}

  {visible&&<div className="wf-panel" id="coverage-plans">
   <div className="wf-panel-title"><div><h3>{canEdit?'Manual coverage plans':'My coverage assignments'}</h3><p>{canEdit?'Assign backups and record handovers. These plans do not approve or cancel leave.':'See where you are named as the primary or backup employee.'}</p></div>
    {canEdit&&<button type="button" className="wf-primary" disabled={busy||!!draft} onClick={()=>beginPlan()}><Plus size={16}/> Add coverage plan</button>}
   </div>
   {(prefs.plan_status!=='All'||(canEdit&&prefs.my_assignments_only))&&<p className="wf-muted">Plan filters: {prefs.plan_status==='All'?'All statuses':prefs.plan_status}{canEdit&&prefs.my_assignments_only?' · My assignments only':''}</p>}
   {canEdit&&draft&&<form className="wf-coverage-form" onSubmit={e=>{e.preventDefault();void savePlan()}}>
    <h3>{edit?'Edit coverage plan':'Add a manual coverage plan'}</h3>
    <label className="wf-long-field">Plan title<input ref={planTitleRef} required maxLength={100} value={draft.label} onChange={e=>updateDraft({label:e.target.value})} placeholder="Example: Payroll approval backup"/></label>
    <div className="wf-form-grid">
     <label>Primary employee<select required value={draft.primary_employee_id} onChange={e=>updateDraft({primary_employee_id:e.target.value})}>{staffOptions(draft.primary_employee_id)}</select></label>
     <label>Backup employee<select required value={draft.backup_employee_id} onChange={e=>updateDraft({backup_employee_id:e.target.value})}>{staffOptions(draft.backup_employee_id)}</select></label>
     <label>Status<select aria-label="Status" value={draft.status} onChange={e=>updateDraft({status:e.target.value as CoverageDraft['status']})}><option>Planned</option><option>Confirmed</option></select></label>
     <label>From<input required type="date" min="2000-01-01" max="2100-12-31" value={draft.starts_on} onChange={e=>{const start=e.target.value;updateDraft({starts_on:start,...(start>draft.ends_on?{ends_on:start}:{})})}}/></label>
     <label>Through<input required type="date" min={draft.starts_on||'2000-01-01'} max="2100-12-31" value={draft.ends_on} onChange={e=>updateDraft({ends_on:e.target.value})}/></label>
    </div>
    <label className="wf-long-field">Handover notes (HR and managers only)<textarea rows={2} maxLength={500} value={draft.notes} onChange={e=>updateDraft({notes:e.target.value})} placeholder="Work handover only. Do not enter private leave information."/></label>
    <div className="wf-toolbar"><button className="wf-primary" disabled={busy||!draft.label.trim()||!draft.primary_employee_id||!draft.backup_employee_id||draft.primary_employee_id===draft.backup_employee_id}>{edit?'Save plan changes':'Save coverage plan'}</button>
     <button type="button" disabled={saving} onClick={()=>{setDraft(null);setEdit(null)}}>Cancel</button></div>
   </form>}
   <div className="wf-list">{plans.length?plans.map(p=><div className="wf-list-row" id={`coverage-plan-${p.id}`} key={p.id}><div><strong>{p.label}</strong>
    <p>{p.primary_name} · Backup: {p.backup_name}</p><small>{p.starts_on}{p.ends_on!==p.starts_on?` to ${p.ends_on}`:''}</small>
    {p.backup_on_leave&&<p className="wf-coverage-conflict"><strong>Backup has approved leave during this plan.</strong> Consider selecting someone else.</p>}
    {!!p.parallel_backup_days?.length&&<p className="wf-coverage-conflict"><strong>Backup booked on multiple plans.</strong> Review {p.parallel_backup_days.length===1?'the flagged date':'the flagged dates'} in this month.</p>}
    {p.notes&&<p className="wf-coverage-notes">{p.notes}</p>}
   </div><div className="wf-toolbar"><span className="wf-tag">{p.status}</span>{canEdit&&<>
    <button type="button" disabled={busy||!!draft} onClick={()=>editPlan(p)} aria-label={`Edit ${p.label}`}>Edit</button>
    <button type="button" disabled={busy} onClick={()=>void removePlan(p)} aria-label={`Delete ${p.label}`}>Delete</button></>}</div></div>):<p className="wf-muted">No coverage plans for this month and scope.</p>}</div>
  </div>}
  <p className="wf-disclaimer"><ShieldCheck size={16}/> Employees see their own approved absences and coverage assignments. Managers work within their direct-report scope. HR administrators can plan across departments. Private leave reasons are never shown.</p>
 </section>;
}

export function HRTaskTemplates({isHR,userId,employees}:{isHR:boolean;userId:number;employees:Employee[]}){
 const [items,setItems]=useState<Template[]>([]);
 const [assignments,setAssignments]=useState<Assignment[]>([]);
 const [archived,setArchived]=useState(false);
 const [title,setTitle]=useState('');const [guidance,setGuidance]=useState('');
 const [priority,setPriority]=useState('Normal');const [days,setDays]=useState(3);
 const [editingId,setEditingId]=useState<number|null>(null);
 const [selected,setSelected]=useState('');const [emp,setEmp]=useState('');const [start,setStart]=useState(dateOnly(new Date()));
 const [search,setSearch]=useState('');const [error,setError]=useState('');const [notice,setNotice]=useState('');const [busy,setBusy]=useState(false);
 const load=useCallback(async()=>{setError('');try{
  const [templates,existing]=await Promise.all([call<Template[]>(`/workforce/task-templates${archived?'?include_archived=true':''}`),call<Assignment[]>('/workforce/task-templates/assignments')]);
  setItems(templates);setAssignments(existing);
 }catch(e){setError((e as Error).message)}},[archived]);
 useEffect(()=>{void load()},[load]);
 useRefreshData(load);
 const act=async(fn:()=>Promise<unknown>,success:string)=>{setBusy(true);setError('');setNotice('');try{await fn();setNotice(success);await load()}catch(e){setError((e as Error).message)}finally{setBusy(false)}};
 const resetForm=()=>{setEditingId(null);setTitle('');setGuidance('');setPriority('Normal');setDays(3)};
 const beginEdit=(t:Template)=>{setEditingId(t.id);setTitle(t.title);setGuidance(t.guidance);setPriority(t.priority);setDays(t.due_offset_days);window.scrollTo({top:0,behavior:'smooth'})};
 const removeTemplate=(t:Template)=>{const reason=window.prompt(`Delete archived, unused template "${t.title}"? Enter a reason (at least 5 characters). Previously assigned templates cannot be deleted.`);if(reason===null)return;if(reason.trim().length<5){setError('Deletion reason must be at least 5 characters');return}void act(()=>call(`/workforce/task-templates/${t.id}`,'DELETE',{confirm:'DELETE',reason:reason.trim()}),'Unused template deleted.')};
 const eligibleEmployees=employees.filter(e=>e.account_active!==0&&(isHR||e.id===userId||e.manager_id===userId));
 const filtered=items.filter(x=>[x.title,x.guidance,x.priority].join(' ').toLowerCase().includes(search.toLowerCase()));
 return <section className="wf-page"><header className="wf-header"><div><small>TALENT / REUSABLE WORK</small><h1>HR task templates</h1><p>Standardize repeatable HR assignments. Every assignment creates a real task with a due date, owner and audit record.</p></div><div className="wf-toolbar"></div></header>
 {isHR&&<div className="wf-panel"><h3>{editingId===null?'Create a reusable template':'Edit reusable template'}</h3><div className="wf-form-grid"><label>Task title<input value={title} maxLength={160} onChange={e=>setTitle(e.target.value)} placeholder="Conduct new hire check-in"/></label><label>Priority<select value={priority} onChange={e=>setPriority(e.target.value)}>{['Low','Normal','High'].map(x=><option key={x}>{x}</option>)}</select></label><label>Due after (days)<input type="number" min={0} max={365} value={days} onChange={e=>setDays(Number(e.target.value))}/></label></div><label className="wf-long-field">Instructions (stored as the task's initial comment)<textarea rows={2} maxLength={1000} value={guidance} onChange={e=>setGuidance(e.target.value)}/></label><button className="wf-primary" disabled={busy||title.trim().length<4||days<0||days>365||!Number.isInteger(days)} onClick={()=>void act(async()=>{await call(editingId===null?'/workforce/task-templates':`/workforce/task-templates/${editingId}`,editingId===null?'POST':'PUT',{title,guidance,priority,due_offset_days:days});resetForm()},editingId===null?'Task template created.':'Template updated; existing assigned tasks are unchanged.')}><Plus size={16}/> {editingId===null?'Create template':'Save template changes'}</button>{editingId!==null&&<button type="button" disabled={busy} onClick={resetForm}>Cancel edit</button>}</div>}
 <div className="wf-panel"><div className="wf-panel-title"><div><h3>Template library</h3><p>HR administrators manage template availability. Managers can assign active templates to their teams.</p></div><label>Find template<input type="search" placeholder="Search templates" value={search} onChange={e=>setSearch(e.target.value)}/></label></div>{isHR&&<label className="wf-inline"><input type="checkbox" checked={archived} onChange={e=>setArchived(e.target.checked)}/> Show archived templates</label>}
 <div className="wf-list">{filtered.length?filtered.map(t=><div className="wf-list-row" key={t.id}><div><strong>{t.title}</strong><p>{t.guidance||'No additional instructions'}</p><small>{t.priority} priority · Due {t.due_offset_days} day(s) after assignment start</small></div><div className="wf-toolbar">{!t.active&&<span className="wf-tag">Archived</span>}{isHR&&<><button disabled={busy} onClick={()=>beginEdit(t)}>Edit</button><button disabled={busy} onClick={()=>void act(()=>call(`/workforce/task-templates/${t.id}`,'PATCH',{active:!t.active}),'Template availability updated.')}>{t.active?'Archive':'Restore'}</button>{!t.active&&<button disabled={busy} onClick={()=>removeTemplate(t)}>Delete unused</button>}</>}</div></div>):<p className="wf-muted">No templates match this search.</p>}</div></div>
 <div className="wf-panel"><h3>Assign a template</h3><div className="wf-form-grid"><label>Template<select value={selected} onChange={e=>setSelected(e.target.value)}><option value="">Select active template</option>{items.filter(t=>t.active).map(t=><option key={t.id} value={t.id}>{t.title}</option>)}</select></label><label>Employee<select value={emp} onChange={e=>setEmp(e.target.value)}><option value="">Select employee</option>{eligibleEmployees.map(e=><option key={e.id} value={e.id}>{e.name} · {e.department}</option>)}</select></label><label>Start date<input type="date" min={dateOnly(new Date())} value={start} onChange={e=>setStart(e.target.value)}/></label></div><button className="wf-primary" disabled={busy||!selected||!emp||!start} onClick={()=>void act(()=>call(`/workforce/task-templates/${selected}/assign`,'POST',{employee_id:Number(emp),start_date:start}),'HR task assigned; employee notified.') }><ClipboardList size={16}/> Assign task</button><p className="wf-muted">Managers may only assign tasks within their authorized team. Duplicate assignments for the same template, employee and start date are blocked.</p></div>
 <div className="wf-panel"><h3>Recent template assignments</h3><div className="wf-list">{assignments.length?assignments.map(a=><div className="wf-list-row" key={a.id}><div><strong>{a.title}</strong><small>{a.employee_name} · Due {a.due_date}</small></div><span className="wf-tag">{a.status}</span></div>):<p className="wf-muted">No template assignments yet.</p>}</div></div>
 {error&&<p className="wf-error" role="alert">{error}</p>}{notice&&<p className="wf-notice" role="status">{notice}</p>}
 </section>;
}
