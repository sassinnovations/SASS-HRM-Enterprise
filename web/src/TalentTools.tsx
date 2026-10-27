import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import {useEffect, useMemo, useState} from 'react'
import {
  BriefcaseBusiness, Headset, MessagesSquare, Route, Send, Settings2, Sparkles, UserCheck, ShieldCheck, ListChecks, CalendarClock,
  AlertTriangle, CheckCircle2, DoorOpen, ClipboardList, Workflow, Search, Pencil, Plus, X
} from 'lucide-react'
import './talent-tools.css'

type Row=Record<string,any>

type Props={
  page:string
  isHR:boolean
  management:boolean
  userId:number
  candidates:Row[]
  employees:Row[]
  tickets:Row[]
  offboarding:Row[]
  tasks:Row[]
  jobs:Row[]
  onboarding:Row[]
  interviews:Row[]
  refreshCore:()=>void|Promise<void>
}

const eligible=new Set(['recruitment','onboarding','requestdesk','helpdesk','offboarding','interviews','tasks'])
const today=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`}
const fmt=(v?:string)=>v?new Date(v).toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'}):'—'
const fmtDateTime=(v?:string)=>v?new Date(v).toLocaleString('en-IN',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'}):'—'
const count=(items:Row[], predicate:(r:Row)=>boolean)=>items.filter(predicate).length
const overdue=(d?:string)=>!!d && d.slice(0,10)<today()
const initials=(name='')=>name.split(' ').filter(Boolean).slice(0,2).map(s=>s[0]).join('').toUpperCase()||'—'

export function TalentTools({page,isHR,management,userId,candidates,employees,tickets,offboarding,tasks,jobs,onboarding,interviews,refreshCore}:Props){
  const [rows,setRows]=useState<Row[]>([])
  const [queue,setQueue]=useState<Row[]>([])
  const [requests,setRequests]=useState<Row[]>([])
  const [interviewRows,setInterviewRows]=useState<Row[]>([])
  const [target,setTarget]=useState('')
  const [message,setMessage]=useState('')
  const [employeeId,setEmployeeId]=useState('')
  const [startDate,setStartDate]=useState(today())
  const [assigneeId,setAssigneeId]=useState('')
  const [dueDate,setDueDate]=useState(today())
  const [orgGuidance,setOrgGuidance]=useState<{onboarding_default_offset_days:number;service_request_review_days:number;recruiter_guidance:string;helpdesk_guidance:string;onboarding_guidance:string;offboarding_guidance:string}|null>(null)
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const [note,setNote]=useState('')
  const [searchText,setSearchText]=useState('')
  const [statusFilter,setStatusFilter]=useState('All')
  const [modal,setModal]=useState<null|{kind:'candidate'|'template'|'task',id?:number}>(null)
  const [form,setForm]=useState<Row>({})

  // Match the main app's authenticated /api proxy; never log or embed JWTs.
  const api=async(path:string,method='GET',body?:any)=>{
    const token=sessionStorage.getItem('sass_token')
    if(!token)throw new Error('Your login session has expired. Please sign in again.')
    let res:Response
    try{
      res=await hrmFetch(`${(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')}/api${path}`,{
        method,
        headers:{'Content-Type':'application/json',Authorization:`Bearer ${token}`},
        ...(body!==undefined?{body:JSON.stringify(body)}:{})
      })
    }catch{throw new Error('Cannot reach SASS HRM API. Check Docker and the backend connection.')}
    const txt=await res.text()
    let json:any=null
    try{json=txt?JSON.parse(txt):null}catch{json=null}
    if(!res.ok){
      if(res.status===401)throw new Error('Your session is no longer valid. Sign in again.')
      throw new Error(typeof json?.detail==='string'?json.detail:`Unable to save or load data (HTTP ${res.status})`)
    }
    return json
  }

  const filter=(items:Row[],keys:string[],statusKey='status')=>items.filter(item=>{
    const q=searchText.trim().toLowerCase()
    return (!q||keys.some(k=>String(item[k]??'').toLowerCase().includes(q)))&&
      (statusFilter==='All'||String(item[statusKey]??'')===statusFilter)
  })
  const optionsForFilter=(()=>{
    const source:Row[]=page==='recruitment'?candidates:page==='onboarding'?onboarding:
      page==='requestdesk'?requests:page==='helpdesk'?(queue.length?queue:tickets):
      page==='offboarding'?offboarding:page==='interviews'?(interviewRows.length?interviewRows:interviews):tasks
    const key=page==='recruitment'?'stage':'status'
    return ['All',...Array.from(new Set(source.map(x=>String(x[key]??'')).filter(Boolean))).sort()]
  })()

  const openModal=(kind:'candidate'|'template'|'task',item?:Row)=>{
    setError('');setNote('')
    setForm(kind==='template'?{title:item?.title||'',offset_days:item?.offset_days??orgGuidance?.onboarding_default_offset_days??0,active:item?.active??1}:
      kind==='candidate'?{name:item?.name||'',job_title:item?.job_title||'',source:item?.source||''}:
      {title:item?.title||'',due_date:item?.due_date||today(),priority:item?.priority||'Normal'})
    setModal({kind,id:item?.id})
  }

  const saveModal=async()=>{
    if(!modal)return
    const fields=modal.kind==='candidate'?{name:String(form.name||'').trim(),job_title:String(form.job_title||'').trim(),source:String(form.source||'').trim()}:
      modal.kind==='template'?{title:String(form.title||'').trim(),offset_days:Number(form.offset_days),active:!!Number(form.active)}:
      {title:String(form.title||'').trim(),due_date:String(form.due_date||''),priority:String(form.priority||'Normal')}
    if(modal.kind==='candidate' && (!modal.id||!management))return setError('Only authorized recruiting managers can edit candidates.')
    if(modal.kind==='template' && !isHR)return setError('Only HR administrators can change templates.')
    if(modal.kind==='task' && (!modal.id||!management))return setError('Only authorized managers can edit task details.')
    const kind=modal.kind,id=modal.id
    const path=kind==='candidate'?`/talent/candidates/${id}/details`:
      kind==='template'?(id?`/talent/onboarding/templates/${id}`:'/talent/onboarding/templates'):
      `/talent/tasks/${id}/details`
    await act(()=>api(path,kind==='template'&&!id?'POST':'PATCH',fields),()=>setModal(null))
  }


  const rosterOptions=useMemo(()=>employees.filter(e=>e.account_active!==0).map(e=>({id:String(e.id),label:`${e.name} · ${e.designation||e.role}`})),[employees])
  const hrOptions=useMemo(()=>employees.filter(e=>e.role==='admin'&&e.account_active===1).map(e=>({id:String(e.id),label:`${e.name} · ${e.designation||'HR Administrator'}`})),[employees])
  const currentCandidate=useMemo(()=>candidates.find(c=>String(c.id)===target),[candidates,target])
  const currentRequest=useMemo(()=>requests.find(r=>String(r.id)===target),[requests,target])
  const currentTicket=useMemo(()=>queue.find(r=>String(r.id)===target) || tickets.find(r=>String(r.id)===target),[queue,tickets,target])
  const currentExit=useMemo(()=>offboarding.find(r=>String(r.id)===target),[offboarding,target])
  const currentTask=useMemo(()=>tasks.find(r=>String(r.id)===target),[tasks,target])
  const currentInterview=useMemo(()=>interviewRows.find(r=>String(r.id)===target) || interviews.find(r=>String(r.id)===target),[interviewRows,interviews,target])

  const load=async(selected=target)=>{
    setError('')
    try{
      if(page==='recruitment'){
        setRows(selected?await api(`/talent/candidates/${selected}/activity`):[])
        return
      }
      if(page==='onboarding'){
        setRows(await api(isHR?'/talent/onboarding/templates?include_archived=true':'/talent/onboarding/templates'))
        return
      }
      if(page==='requestdesk'){
        const reqs=await api('/request-desk/requests')
        setRequests(reqs)
        setRows(selected?await api(`/talent/request-desk/${selected}/messages`):[])
        return
      }
      if(page==='helpdesk'){
        if(isHR){
          const q=await api('/talent/helpdesk/queue')
          setQueue(q)
        }
        setRows(selected?await api(`/helpdesk/tickets/${selected}/messages`):[])
        return
      }
      if(page==='offboarding'){
        setRows(selected?await api(`/talent/offboarding/${selected}/clearance`):[])
        return
      }
      if(page==='interviews'){
        const list=await api('/recruitment/interviews')
        setInterviewRows(list)
        return
      }
      if(page==='tasks'){
        setRows(selected?await api(`/talent/tasks/${selected}/comments`):[])
      }
    }catch(e:any){setError(e.message||'Unable to load module data')}
  }

  useEffect(()=>{
    if(!eligible.has(page)) return
    setRows([]); setQueue([]); setRequests([]); setInterviewRows([]); setTarget(''); setMessage(''); setEmployeeId(''); setAssigneeId(''); setDueDate(today()); setError(''); setNote(''); setSearchText(''); setStatusFilter('All'); setModal(null)
    void load('')
  },[page])

  useEffect(()=>{ if(eligible.has(page)) void load(target) },[target])
  useRefreshData(()=>{if(eligible.has(page))void load(target)});
  useEffect(()=>{
    if(!isHR||!eligible.has(page))return
    // Used only for suggested defaults and staff guidance; final approval rules remain server-side.
    void api('/admin/settings/talent').then((result:{settings:any})=>{
      const config=result.settings
      setOrgGuidance(config)
      if(page==='helpdesk' && typeof config.service_request_review_days==='number'){
        const d=new Date(); d.setDate(d.getDate()+config.service_request_review_days)
        setDueDate(`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`)
      }
    }).catch(()=>setOrgGuidance(null))
  },[page,isHR])


  useEffect(()=>{
    if(!modal)return
    const onKey=(e:KeyboardEvent)=>{
      if(e.key==='Escape'&&!busy)setModal(null)
    }
    window.addEventListener('keydown',onKey)
    return ()=>window.removeEventListener('keydown',onKey)
  },[modal,busy])

  if(!eligible.has(page)) return null

  const act=async(fn:()=>Promise<any>, after?:()=>void)=>{
    setBusy(true); setError(''); setNote('')
    try{
      await fn()
      await refreshCore()
      await load(target)
      after?.()
      setNote('Saved successfully.')
    }catch(e:any){setError(e.message||'Action failed')}
    finally{setBusy(false)}
  }

  const metrics=(()=>{
    switch(page){
      case 'recruitment': return [
        ['Candidates', String(candidates.length)],
        ['Open positions', String(count(jobs,x=>x.status==='Open'))],
        ['Interview stage', String(count(candidates,x=>x.stage==='Interview'))],
        ['Hired', String(count(candidates,x=>x.stage==='Hired'))],
      ]
      case 'onboarding': return [
        ['Active templates', String(count(rows,x=>Number(x.active)===1))],
        ['Pending tasks', String(count(onboarding,x=>x.status==='Pending'))],
        ['Completed', String(count(onboarding,x=>x.status==='Completed'))],
        ['Overdue', String(count(onboarding,x=>x.status!=='Completed'&&overdue(String(x.due_date||''))))],
      ]
      case 'requestdesk': return [
        ['Requests', String(requests.length)],
        ['Open', String(count(requests,x=>x.status==='Open'))],
        ['In progress', String(count(requests,x=>x.status==='In Progress'))],
        ['Closed', String(count(requests,x=>['Fulfilled','Declined'].includes(x.status)))],
      ]
      case 'helpdesk': return [
        ['Open tickets', String(count(queue.length?queue:tickets,x=>x.status==='Open'))],
        ['In progress', String(count(queue.length?queue:tickets,x=>x.status==='In Progress'))],
        ['High priority', String(count(queue.length?queue:tickets,x=>x.priority==='High'))],
        ['Unassigned', String(count(queue,x=>!x.assignee_id))],
      ]
      case 'offboarding': return [
        ['Requested', String(count(offboarding,x=>x.status==='Requested'))],
        ['Under review', String(count(offboarding,x=>x.status==='Under Review'))],
        ['Approved', String(count(offboarding,x=>x.status==='Approved'))],
        ['Closed', String(count(offboarding,x=>x.status==='Closed'))],
      ]
      case 'interviews': {
        const base=interviewRows.length?interviewRows:interviews
        return [
          ['Scheduled', String(count(base,x=>x.status==='Scheduled'))],
          ['Today', String(count(base,x=>String(x.scheduled_at||'').slice(0,10)===today()))],
          ['Completed', String(count(base,x=>x.status==='Completed'))],
          ['Cancelled', String(count(base,x=>x.status==='Cancelled'))],
        ]
      }
      case 'tasks': return [
        ['Open', String(count(tasks,x=>x.status==='Open'))],
        ['In progress', String(count(tasks,x=>x.status==='In Progress'))],
        ['Completed', String(count(tasks,x=>x.status==='Completed'))],
        ['Overdue', String(count(tasks,x=>x.status!=='Completed'&&overdue(String(x.due_date||''))))],
      ]
      default: return []
    }
  })()

  const intro=(()=>{
    switch(page){
      case 'recruitment': return {icon:<BriefcaseBusiness size={20}/>,title:'Recruitment operations hub',desc:'Capture candidate notes, review the pipeline and keep hiring actions in one organized workspace.'}
      case 'onboarding': return {icon:<UserCheck size={20}/>,title:'Onboarding designer',desc:'Create reusable onboarding templates, assign them quickly and monitor checklist completion.'}
      case 'requestdesk': return {icon:<MessagesSquare size={20}/>,title:'Request Desk collaboration',desc:'Keep employee requests organized with threaded communication and controlled status transitions.'}
      case 'helpdesk': return {icon:<Headset size={20}/>,title:'HR helpdesk triage',desc:'Assign owners, set response dates and keep the support queue clean and trackable.'}
      case 'offboarding': return {icon:<DoorOpen size={20}/>,title:'Exit clearance manager',desc:'Track each offboarding request using checklist-based clearance steps and handover progress.'}
      case 'interviews': return {icon:<CalendarClock size={20}/>,title:'Interview coordination console',desc:'Review upcoming interviews, appointment health and operating reminders for interviewers and HR.'}
      case 'tasks': return {icon:<ListChecks size={20}/>,title:'HR task manager',desc:'Track task ownership, comments, due dates and operational follow-ups in one place.'}
      default: return {icon:<Sparkles size={20}/>,title:'Talent toolkit',desc:''}
    }
  })()

  const settingPoints=(()=>{
    switch(page){
      case 'recruitment': return ['Define recruiter note discipline for every interview-stage candidate.','Keep job openings and candidate stages aligned so analytics remain accurate.','Use structured notes for screening, panel feedback and offer readiness.']
      case 'onboarding': return ['Use templates with clear due offsets for each day-one activity.','Assign onboarding tasks only after the employee record is created.','Monitor overdue tasks to prevent missed first-week readiness actions.']
      case 'requestdesk': return ['Use status transitions from Open to In Progress to Fulfilled or Declined.','Record HR responses before closing any employee service request.','Use request threads for audit-friendly employee communication.']
      case 'helpdesk': return ['Assign every active ticket to an HR owner with a target date.','Prioritize high-severity issues first and keep employee updates in the message thread.','Close tickets only after the issue and response are documented.']
      case 'offboarding': return ['Maintain a standard clearance checklist for handover, assets and payroll items.','Track clearance completion before closing an exit request.','Use approval status and clearance status together for full visibility.']
      case 'interviews': return ['Schedule only relevant interviewers and confirm appointment status promptly.','Use interview notes and candidate-stage updates together.','Treat cancelled interviews separately from completed evaluations for better reporting.']
      case 'tasks': return ['Give each task a clear owner, due date and priority.','Use comments for traceable updates instead of informal follow-ups.','Monitor overdue work items weekly from the HR operations view.']
      default: return []
    }
  })()

  const renderRecruitment=()=>{
    const stageCounts=['Applied','Screening','Assessment','Interview','Offer','Hired','Rejected'].map(stage=>({stage,total:count(candidates,x=>x.stage===stage)}))
    return <>
      <div className="talent-split">
        <section className="talent-panel">
          <div className="talent-panel-head"><h4>Candidate activity log</h4><p>Select a candidate to view or add recruiter notes.</p></div>
          <label className="talent-field"><span>Candidate</span><select value={target} onChange={e=>setTarget(e.target.value)}><option value="">Select candidate</option>{filter(candidates,['name','job_title','source'],'stage').map(c=><option key={c.id} value={c.id}>{c.name} · {c.job_title}</option>)}</select></label>
          {currentCandidate&&management&&<div className="talent-actions"><button className="talent-secondary" type="button" onClick={()=>openModal('candidate',currentCandidate)}><Pencil size={14}/> Edit candidate details</button></div>}
          {currentCandidate&&<div className="talent-person-card"><div className="talent-avatar">{initials(currentCandidate.name)}</div><div><strong>{currentCandidate.name}</strong><small>{currentCandidate.job_title} · {currentCandidate.source}</small><div className="talent-chip-row"><span className="talent-chip">Stage: {currentCandidate.stage}</span><span className="talent-chip">Applied: {fmt(currentCandidate.applied_at)}</span></div></div></div>}
          <label className="talent-field"><span>Recruiter note</span><textarea rows={4} value={message} onChange={e=>setMessage(e.target.value)} placeholder="Add screening summary, panel feedback or follow-up notes"/></label>
          <div className="talent-actions"><button disabled={!target||message.trim().length<3||busy} onClick={()=>act(()=>api(`/talent/candidates/${target}/activity`,'POST',{note:message}),()=>setMessage(''))}><Send size={15}/> Save note</button></div>
          <div className="talent-list">{rows.length?rows.map(r=><article className="talent-list-item" key={r.id}><div><strong>{r.author}</strong><small>{fmtDateTime(r.created_at)}</small></div><p>{r.note}</p></article>):<div className="talent-empty">Select a candidate to display recruiter activity.</div>}</div>
        </section>
        <section className="talent-panel">
          <div className="talent-panel-head"><h4>Hiring layout</h4><p>Quick stage overview and open role snapshot.</p></div>
          <div className="talent-stage-grid">{stageCounts.map(s=><div className="talent-stat-tile" key={s.stage}><span>{s.stage}</span><strong>{s.total}</strong></div>)}</div>
          <div className="talent-subgrid two">
            <div className="talent-mini-panel"><h5>Open roles</h5>{jobs.filter(j=>j.status==='Open').length?filter(jobs,['title','department','location']).filter(j=>j.status==='Open').slice(0,6).map(j=><div className="talent-mini-row" key={j.id}><div><strong>{j.title}</strong><small>{j.department} · {j.location}</small></div><span>{j.openings} open</span></div>):<div className="talent-empty">No active job openings.</div>}</div>
            <div className="talent-mini-panel"><h5>Interview readiness</h5><ul className="talent-point-list"><li>{count(candidates,x=>x.stage==='Interview')} candidates currently need interview follow-up.</li><li>{count(candidates,x=>x.stage==='Offer')} candidates are in the offer stage.</li><li>{count(candidates,x=>x.stage==='Screening'||x.stage==='Assessment')} candidates are still mid-pipeline.</li></ul></div>
          </div>
        </section>
      </div>
    </>
  }

  const renderOnboarding=()=>{
    const sortedTasks=[...onboarding].sort((a,b)=>String(a.due_date||'').localeCompare(String(b.due_date||'')))
    return <>
      <div className="talent-split">
        <section className="talent-panel">
          <div className="talent-panel-head"><h4>Template settings</h4><p>Create reusable onboarding tasks and assign them with date offsets.</p></div>
          {isHR&&<div className="talent-actions"><button type="button" onClick={()=>openModal('template')}><Plus size={15}/> Create checklist template</button></div>}
          <div className="talent-list">{rows.length?rows.filter(t=>!searchText||String(t.title).toLowerCase().includes(searchText.toLowerCase())).map(t=><article className="talent-list-item" key={t.id}><div><strong>{t.title}</strong><small>{Number(t.active)?'Active':'Archived'} · Due {Number(t.offset_days||0)} day(s) after start date</small></div>{isHR&&<div className="talent-inline-form"><button type="button" className="talent-secondary" onClick={()=>openModal('template',t)}><Pencil size={14}/> Edit template</button><label className="talent-field compact"><span>Employee</span><select value={employeeId} onChange={e=>setEmployeeId(e.target.value)}><option value="">Select employee</option>{rosterOptions.map(o=><option key={o.id} value={o.id}>{o.label}</option>)}</select></label><label className="talent-field compact"><span>Start date</span><input type="date" value={startDate} onChange={e=>setStartDate(e.target.value)}/></label><button disabled={!employeeId||!Number(t.active)||busy} onClick={()=>act(()=>api(`/talent/onboarding/templates/${t.id}/assign`,'POST',{employee_id:Number(employeeId),start_date:startDate}))}><Send size={14}/> Assign</button></div>}</article>):<div className="talent-empty">No onboarding templates created yet.</div>}</div>
        </section>
        <section className="talent-panel">
          <div className="talent-panel-head"><h4>Checklist execution</h4><p>Recent onboarding tasks arranged by due date.</p></div>
          <div className="talent-list">{sortedTasks.length?filter(sortedTasks,['employee_name','title']).slice(0,12).map(t=><article className="talent-list-item" key={`${t.id}-${t.employee_name}`}><div><strong>{t.title}</strong><small>{t.employee_name} · due {fmt(t.due_date)}</small></div><div className="talent-chip-row"><span className={`talent-chip ${t.status==='Completed'?'ok':''}`}>{t.status}</span>{overdue(String(t.due_date||''))&&t.status!=='Completed'&&<span className="talent-chip warn">Overdue</span>}</div></article>):<div className="talent-empty">No onboarding tasks have been assigned yet.</div>}</div>
        </section>
      </div>
    </>
  }

  const renderRequestDesk=()=>{
    const closed=currentRequest&&['Fulfilled','Declined'].includes(String(currentRequest.status||''))
    return <>
      <div className="talent-split">
        <section className="talent-panel">
          <div className="talent-panel-head"><h4>Service request threads</h4><p>Select a request to view updates and continue the conversation.</p></div>
          <label className="talent-field"><span>Request</span><select value={target} onChange={e=>setTarget(e.target.value)}><option value="">Select request</option>{filter(requests,['subject','category_name','employee_name']).map(r=><option key={r.id} value={r.id}>#{r.id} · {r.subject} · {r.status}</option>)}</select></label>
          {currentRequest&&<div className="talent-details-card"><div className="talent-details-top"><strong>{currentRequest.subject}</strong><span className="talent-chip">{currentRequest.status}</span></div><p>{currentRequest.details}</p><small>{currentRequest.category_name} · updated {fmtDateTime(currentRequest.updated_at||currentRequest.created_at)}</small>{currentRequest.hr_response&&<div className="talent-note-box"><strong>Latest HR response</strong><p>{currentRequest.hr_response}</p></div>}</div>}
          <label className="talent-field"><span>Message / response</span><textarea rows={4} value={message} onChange={e=>setMessage(e.target.value)} placeholder={isHR?'Add an internal HR reply or employee-facing update':'Reply or add a follow-up question'}/></label>
          <div className="talent-actions multi">
            <button disabled={!target||message.trim().length<2||closed||busy} onClick={()=>act(()=>api(`/talent/request-desk/${target}/messages`,'POST',{message}),()=>setMessage(''))}><Send size={15}/> Send message</button>
            {isHR&&currentRequest?.employee_id!==userId&&currentRequest?.status==='Open'&&<button className="talent-secondary" disabled={busy} onClick={()=>act(()=>api(`/request-desk/requests/${target}/decision`,'POST',{status:'In Progress',hr_response:message||'Request is under review'}))}><Route size={14}/> Mark in progress</button>}
            {isHR&&currentRequest?.employee_id!==userId&&currentRequest?.status==='In Progress'&&<button className="talent-secondary" disabled={busy||message.trim().length<5} onClick={()=>act(()=>api(`/request-desk/requests/${target}/decision`,'POST',{status:'Fulfilled',hr_response:message}),()=>setMessage(''))}><CheckCircle2 size={14}/> Fulfill</button>}
            {isHR&&currentRequest?.employee_id!==userId&&['Open','In Progress'].includes(String(currentRequest?.status||''))&&<button className="talent-secondary danger" disabled={busy||message.trim().length<5} onClick={()=>act(()=>api(`/request-desk/requests/${target}/decision`,'POST',{status:'Declined',hr_response:message}),()=>setMessage(''))}><AlertTriangle size={14}/> Decline</button>}
          </div>
        </section>
        <section className="talent-panel">
          <div className="talent-panel-head"><h4>Conversation history</h4><p>Chronological request communication for accurate service tracking.</p></div>
          <div className="talent-list">{rows.length?rows.map(r=><article className="talent-list-item" key={r.id}><div><strong>{r.author}</strong><small>{fmtDateTime(r.created_at)}</small></div><p>{r.message}</p></article>):<div className="talent-empty">Select a request to view its message thread.</div>}</div>
        </section>
      </div>
    </>
  }

  const renderHelpdesk=()=>{
    const items=queue.length?queue:tickets
    return <>
      <div className="talent-split">
        <section className="talent-panel">
          <div className="talent-panel-head"><h4>Triage & ownership</h4><p>Assign an HR owner and response target for each active support case.</p></div>
          <label className="talent-field"><span>Ticket</span><select value={target} onChange={e=>setTarget(e.target.value)}><option value="">Select ticket</option>{filter(items,['subject','category','employee_name']).map((r:any)=><option key={r.id} value={r.id}>#{r.id} · {r.subject} · {r.status}</option>)}</select></label>
          {currentTicket&&<div className="talent-details-card"><div className="talent-details-top"><strong>{currentTicket.subject}</strong><span className="talent-chip">{currentTicket.status}</span></div><p>{currentTicket.category} · Priority {currentTicket.priority}</p><small>{currentTicket.employee_name||'Employee'} · opened {fmtDateTime(currentTicket.created_at)}</small></div>}
          {isHR&&<div className="talent-form-grid three">
            <label className="talent-field"><span>Assign owner</span><select value={assigneeId} onChange={e=>setAssigneeId(e.target.value)}><option value="">Select HR owner</option>{hrOptions.map(o=><option key={o.id} value={o.id}>{o.label}</option>)}</select></label>
            <label className="talent-field"><span>Target date</span><input type="date" value={dueDate} min={today()} onChange={e=>setDueDate(e.target.value)}/></label>
            <div className="talent-actions fill"><button disabled={!target||!assigneeId||busy} onClick={()=>act(()=>api(`/talent/helpdesk/${target}/triage`,'POST',{assignee_id:Number(assigneeId),due_date:dueDate}))}><ShieldCheck size={15}/> Save triage</button></div>
          </div>}
          <div className="talent-list compact">{queue.length?filter(queue,['subject','employee_name','assignee_name','priority']).slice(0,10).map(r=><article className="talent-list-item" key={r.id}><div><strong>{r.subject}</strong><small>{r.employee_name} · {r.priority} · {r.status}</small></div><div className="talent-chip-row">{r.assignee_name?<span className="talent-chip ok">{r.assignee_name}</span>:<span className="talent-chip warn">Unassigned</span>}{r.due_date&&<span className={`talent-chip ${overdue(String(r.due_date))?'warn':''}`}>Due {fmt(r.due_date)}</span>}</div></article>):<div className="talent-empty">No triage records are available.</div>}</div>
        </section>
        <section className="talent-panel">
          <div className="talent-panel-head"><h4>Ticket conversation</h4><p>Support history is visible to the owner and HR only.</p></div>
          <div className="talent-list">{rows.length?rows.map(r=><article className="talent-list-item" key={r.id}><div><strong>{r.author_name||r.author}</strong><small>{fmtDateTime(r.created_at)}</small></div><p>{r.message}</p></article>):<div className="talent-empty">Open a ticket to review its conversation history.</div>}</div>
        </section>
      </div>
    </>
  }

  const renderOffboarding=()=>{
    const done=count(rows,x=>x.status==='Completed')
    return <>
      <div className="talent-split">
        <section className="talent-panel">
          <div className="talent-panel-head"><h4>Clearance checklist</h4><p>Maintain the checklist that must be completed before the exit can be closed.</p></div>
          <label className="talent-field"><span>Exit request</span><select value={target} onChange={e=>setTarget(e.target.value)}><option value="">Select request</option>{filter(offboarding,['employee_name','reason']).map(r=><option key={r.id} value={r.id}>{r.employee_name} · {fmt(r.last_working_day)} · {r.status}</option>)}</select></label>
          {currentExit&&<div className="talent-details-card"><div className="talent-details-top"><strong>{currentExit.employee_name}</strong><span className="talent-chip">{currentExit.status}</span></div><p>{currentExit.reason||'No exit reason recorded.'}</p><small>Last working day: {fmt(currentExit.last_working_day)}</small></div>}
          {isHR&&<div className="talent-inline-form stack"><label className="talent-field"><span>New clearance step</span><input value={message} onChange={e=>setMessage(e.target.value)} placeholder="Laptop return / Knowledge transfer / Final payroll check"/></label><button disabled={!target||message.trim().length<3||busy} onClick={()=>act(()=>api(`/talent/offboarding/${target}/clearance`,'POST',{title:message}),()=>setMessage(''))}><ClipboardList size={15}/> Add step</button></div>}
          {rows.length>0&&<div className="talent-progress-box"><span>Completion progress</span><div className="talent-progress"><i style={{width:`${Math.round(done*100/rows.length)}%`}}/></div><strong>{done}/{rows.length} completed</strong></div>}
        </section>
        <section className="talent-panel">
          <div className="talent-panel-head"><h4>Clearance actions</h4><p>Mark steps complete as handover tasks finish.</p></div>
          <div className="talent-list">{rows.length?rows.map(r=><article className="talent-list-item" key={r.id}><div><strong>{r.title}</strong><small>{r.completed_at?`Completed ${fmtDateTime(r.completed_at)}`:'Pending completion'}</small></div>{isHR?<button className={r.status==='Completed'?'talent-secondary':'talent-toggle'} disabled={busy} onClick={()=>act(()=>api(`/talent/offboarding/clearance/${r.id}`,'PATCH',{status:r.status==='Completed'?'Pending':'Completed'}))}>{r.status==='Completed'?'Reopen':'Mark complete'}</button>:<span className={`talent-chip ${r.status==='Completed'?'ok':''}`}>{r.status}</span>}</article>):<div className="talent-empty">Choose an exit request to load clearance items.</div>}</div>
        </section>
      </div>
    </>
  }

  const renderInterviews=()=>{
    const base=interviewRows.length?interviewRows:interviews
    const upcoming=[...base].sort((a,b)=>String(a.scheduled_at||'').localeCompare(String(b.scheduled_at||'')))
    return <>
      <div className="talent-split">
        <section className="talent-panel">
          <div className="talent-panel-head"><h4>Upcoming interview board</h4><p>Review candidate appointments and keep interview status current.</p></div>
          <label className="talent-field"><span>Appointment</span><select value={target} onChange={e=>setTarget(e.target.value)}><option value="">Select interview</option>{filter(upcoming,['candidate_name','interviewer_name','job_title','mode']).map(r=><option key={r.id} value={r.id}>{r.candidate_name} · {fmtDateTime(r.scheduled_at)} · {r.status}</option>)}</select></label>
          {currentInterview&&<div className="talent-details-card"><div className="talent-details-top"><strong>{currentInterview.candidate_name}</strong><span className="talent-chip">{currentInterview.status}</span></div><p>{currentInterview.job_title} · {currentInterview.mode}</p><small>Interviewer: {currentInterview.interviewer_name} · {fmtDateTime(currentInterview.scheduled_at)}</small>{currentInterview.notes&&<div className="talent-note-box"><strong>Preparation notes</strong><p>{currentInterview.notes}</p></div>}</div>}
          {currentInterview?.status==='Scheduled'&&management&&(isHR||Number(currentInterview.interviewer_id)===userId)&&<div className="talent-actions multi"><button disabled={busy} onClick={()=>act(()=>api(`/recruitment/interviews/${target}`,'PATCH',{status:'Completed'}))}><CheckCircle2 size={15}/> Mark completed</button><button className="talent-secondary danger" disabled={busy} onClick={()=>act(()=>api(`/recruitment/interviews/${target}`,'PATCH',{status:'Cancelled'}))}><AlertTriangle size={14}/> Cancel interview</button></div>}
        </section>
        <section className="talent-panel">
          <div className="talent-panel-head"><h4>Scheduling guidance</h4><p>Suggested operating rules for a cleaner recruitment flow.</p></div>
          <div className="talent-stage-grid">{['Video','On-site','Phone'].map(mode=><div className="talent-stat-tile" key={mode}><span>{mode}</span><strong>{count(base,x=>x.mode===mode)}</strong></div>)}</div>
          <ul className="talent-point-list roomy"><li>Use the top Schedule interview action to create a new appointment with the correct interviewer.</li><li>Update the candidate stage to Interview or Offer in the Recruitment ATS after each completed interview.</li><li>Cancelled interviews remain in history for auditability and reporting continuity.</li></ul>
          <div className="talent-mini-panel"><h5>Upcoming schedule</h5>{upcoming.length?filter(upcoming,['candidate_name','interviewer_name','job_title','mode']).slice(0,8).map(r=><div className="talent-mini-row" key={r.id}><div><strong>{r.candidate_name}</strong><small>{r.interviewer_name} · {r.mode}</small></div><span>{fmtDateTime(r.scheduled_at)}</span></div>):<div className="talent-empty">No interviews are currently scheduled.</div>}</div>
        </section>
      </div>
    </>
  }

  const renderTasks=()=>{
    const ordered=[...tasks].sort((a,b)=>String(a.due_date||'').localeCompare(String(b.due_date||'')))
    return <>
      <div className="talent-split">
        <section className="talent-panel">
          <div className="talent-panel-head"><h4>Task detail & follow-up</h4><p>Select a task to review ownership, due date and progress notes.</p></div>
          <label className="talent-field"><span>Task</span><select value={target} onChange={e=>setTarget(e.target.value)}><option value="">Select task</option>{filter(ordered,['title','assignee_name','priority']).map(t=><option key={t.id} value={t.id}>{t.title} · {t.assignee_name} · {t.status}</option>)}</select></label>
          {currentTask&&management&&(isHR||Number(currentTask.created_by)===userId)&&currentTask.status!=='Completed'&&<div className="talent-actions"><button type="button" className="talent-secondary" onClick={()=>openModal('task',currentTask)}><Pencil size={14}/> Edit task details</button></div>}
          {currentTask&&<div className="talent-details-card"><div className="talent-details-top"><strong>{currentTask.title}</strong><span className="talent-chip">{currentTask.status}</span></div><p>Owner: {currentTask.assignee_name} · Priority {currentTask.priority}</p><small>Due {fmt(currentTask.due_date)} {overdue(String(currentTask.due_date||''))&&currentTask.status!=='Completed'?'· Overdue':''}</small></div>}
          <label className="talent-field"><span>Comment</span><textarea rows={4} value={message} onChange={e=>setMessage(e.target.value)} placeholder="Add progress update, blocker or completion note"/></label>
          <div className="talent-actions"><button disabled={!target||message.trim().length<2||busy} onClick={()=>act(()=>api(`/talent/tasks/${target}/comments`,'POST',{message}),()=>setMessage(''))}><Send size={15}/> Add comment</button></div>
          <div className="talent-mini-panel"><h5>Task radar</h5>{ordered.length?filter(ordered,['title','assignee_name','priority']).slice(0,8).map(t=><div className="talent-mini-row" key={t.id}><div><strong>{t.title}</strong><small>{t.assignee_name} · {t.priority}</small></div><span>{fmt(t.due_date)}</span></div>):<div className="talent-empty">No HR tasks available.</div>}</div>
        </section>
        <section className="talent-panel">
          <div className="talent-panel-head"><h4>Comment stream</h4><p>Use comments for structured follow-ups and audit-friendly collaboration.</p></div>
          <div className="talent-list">{rows.length?rows.map(r=><article className="talent-list-item" key={r.id}><div><strong>{r.author}</strong><small>{fmtDateTime(r.created_at)}</small></div><p>{r.message}</p></article>):<div className="talent-empty">Select a task to display its comment history.</div>}</div>
        </section>
      </div>
    </>
  }

  return <div className="talent-addon">
    <div className="talent-head">
      <span className="talent-head-icon">{intro.icon}</span>
      <div>
        <h3>{intro.title}</h3>
        <p>{intro.desc}</p>
      </div>
      
    </div>

    <div className="talent-filter-bar" role="search" aria-label="Search and filter talent records">
      <label className="talent-filter-search"><Search size={16}/><input value={searchText} onChange={e=>setSearchText(e.target.value)} placeholder="Search by employee, title, role or subject" aria-label="Search talent records"/></label>
      <label className="talent-filter-status"><span>Status / stage</span><select value={statusFilter} onChange={e=>setStatusFilter(e.target.value)}>{optionsForFilter.map(s=><option key={s} value={s}>{s}</option>)}</select></label>
      <button type="button" className="talent-secondary" onClick={()=>{setSearchText('');setStatusFilter('All')}} disabled={!searchText&&statusFilter==='All'}>Clear filters</button>
    </div>

    <div className="talent-metric-grid">{metrics.map(([label,value])=><article className="talent-metric-card" key={label}><span>{label}</span><strong>{value}</strong></article>)}</div>

    <div className="talent-subgrid two top-gap">
      <section className="talent-panel soft">
        <div className="talent-panel-head"><h4>Recommended settings</h4><p>Important configuration and operational checks for this module.</p></div>
        <ul className="talent-point-list">{settingPoints.map(point=><li key={point}>{point}</li>)}</ul>
      </section>
      <section className="talent-panel soft">
        <div className="talent-panel-head"><h4>Arrangement focus</h4><p>How this redesign improves day-to-day usability.</p></div>
        <div className="talent-arrangement-grid">
          <div><Workflow size={17}/><span>Cleaner workflow grouping</span></div>
          <div><Settings2 size={17}/><span>Module-specific settings</span></div>
          <div><MessagesSquare size={17}/><span>Tracked communication</span></div>
          <div><Sparkles size={17}/><span>Consistent visual layout</span></div>
        </div>
      </section>
    </div>

    <div className="top-gap">
      {page==='recruitment'&&renderRecruitment()}
      {page==='onboarding'&&renderOnboarding()}
      {page==='requestdesk'&&renderRequestDesk()}
      {page==='helpdesk'&&renderHelpdesk()}
      {page==='offboarding'&&renderOffboarding()}
      {page==='interviews'&&renderInterviews()}
      {page==='tasks'&&renderTasks()}
    </div>


    {modal&&<div className="talent-dialog-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget&&!busy)setModal(null)}}>
      <section className="talent-dialog" role="dialog" aria-modal="true" aria-label={`${modal.id?'Edit':'Create'} ${modal.kind}`}>
        <div className="talent-dialog-header"><div><h3>{modal.id?'Edit':'Create'} {modal.kind==='candidate'?'candidate details':modal.kind==='template'?'onboarding template':'HR task'}</h3><p>Saved to the HRM database with role permissions and an audit record.</p></div><button type="button" aria-label="Close dialog" disabled={busy} onClick={()=>setModal(null)}><X size={19}/></button></div>
        <form className="talent-dialog-fields" onSubmit={e=>{e.preventDefault();void saveModal()}}>
          <label className="talent-field"><span>{modal.kind==='candidate'?'Candidate name':modal.kind==='template'?'Template title':'Task title'}</span><input autoFocus required minLength={modal.kind==='candidate'?2:modal.kind==='task'?4:3} maxLength={modal.kind==='candidate'?140:modal.kind==='task'?180:160} value={form[modal.kind==='candidate'?'name':'title']||''} onChange={e=>setForm({...form,[modal.kind==='candidate'?'name':'title']:e.target.value})}/></label>
          {modal.kind==='candidate'&&<><label className="talent-field"><span>Position</span><input required minLength={2} maxLength={140} value={form.job_title||''} onChange={e=>setForm({...form,job_title:e.target.value})}/></label><label className="talent-field"><span>Candidate source</span><input required minLength={2} maxLength={100} value={form.source||''} onChange={e=>setForm({...form,source:e.target.value})}/></label></>}
          {modal.kind==='template'&&<><label className="talent-field"><span>Days after start</span><input type="number" required min={0} max={365} value={form.offset_days??0} onChange={e=>setForm({...form,offset_days:Number(e.target.value)})}/></label>{!!modal.id&&<label className="talent-field"><span>Template state</span><select value={String(form.active)} onChange={e=>setForm({...form,active:Number(e.target.value)})}><option value="1">Active</option><option value="0">Archived</option></select></label>}</>}
          {modal.kind==='task'&&<><label className="talent-field"><span>Due date</span><input type="date" required min={today()} value={form.due_date||''} onChange={e=>setForm({...form,due_date:e.target.value})}/></label><label className="talent-field"><span>Priority</span><select value={form.priority||'Normal'} onChange={e=>setForm({...form,priority:e.target.value})}><option>Low</option><option>Normal</option><option>High</option></select></label></>}
          <div className="talent-actions"><button type="submit" disabled={busy}>{busy?'Saving…':'Save changes'}</button><button className="talent-secondary" type="button" disabled={busy} onClick={()=>setModal(null)}>Cancel</button></div>
        </form>
      </section>
    </div>}

    {error&&<div className="talent-error">{error}</div>}
    {note&&<div className="talent-success">{note}</div>}
  </div>
}
