import {useEffect, useState, type ReactNode, type FormEvent} from 'react'
import {useRefreshData} from './useRefreshData'
import './service-center.css'

type Kind = 'ticket' | 'request'
type Key = {kind: Kind; id: number}
type Summary = Key & {subject:string; category_name:string; status:string; employee_name:string}
type Page = {items:Summary[];has_more:boolean}
type Message = {id:number;author:string;message:string;created_at:string}
type Detail = Summary & {
  details:string; priority?:string; hr_response?:string;
  assignment?:{assignee_id:number;assignee_name:string;due_date:string};
  can_reply:boolean; can_assign:boolean; allowed_statuses:string[];
  messages:Message[]; has_older_messages:boolean; owners:Owner[];
}
type API = <T>(path:string, method?:string, body?:unknown)=>Promise<T>
type Owner = {id:number;name:string}
const caseLabel = (item:Key) => `${item.kind === 'ticket' ? 'Ticket' : 'Request'} #${item.id}`
const casePath = (item:Key) => `/service-center/cases/${item.kind}/${item.id}`
const pageSize = 30

function useResult<T>(api:API,path:string,revision:number) {
  const [result,setResult] = useState<{key:string;data?:T;error?:string}>({key:''})
  const key = `${path}:${revision}`
  useEffect(()=>{
    let stale=false
    if (path) api<T>(path).then(data=>{if(!stale)setResult({key,data})})
      .catch((error:Error)=>{if(!stale)setResult({key,error:error.message})})
    return ()=>{stale=true}
  },[api,path,key])
  return result.key===key?result:undefined
}

function CaseDetail({selected,api,revision,onChanged,close}:{
  selected:Key;api:API;revision:number;onChanged:()=>void;close:()=>void
}) {
  const [messageOffset,setMessageOffset]=useState(0)
  const [reply,setReply]=useState('')
  const [status,setStatus]=useState('')
  const [note,setNote]=useState('')
  const [owner,setOwner]=useState('')
  const [due,setDue]=useState('')
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const [notice,setNotice]=useState('')
  const result=useResult<Detail>(api,`${casePath(selected)}?message_offset=${messageOffset}`,revision)
  const data=result?.data
  async function save(event:FormEvent,path:string,method:string,payload:unknown,done:()=>void,success:string){
    event.preventDefault()
    if(busy)return
    setBusy(true);setError('');setNotice('')
    try{await api(path,method,payload);done();onChanged();setNotice(success)}
    catch(e){setError((e as Error).message)}
    finally{setBusy(false)}
  }
  const ticket=selected.kind==='ticket'
  const messagePath=ticket?`/helpdesk/tickets/${selected.id}/messages`:`/talent/request-desk/${selected.id}/messages`
  const statusPath=ticket?`/helpdesk/tickets/${selected.id}`:`/request-desk/requests/${selected.id}/decision`
  const needsNote=!ticket&&['Fulfilled','Declined'].includes(status)
  return <section className="service-case-detail" aria-label="Case details">
    <div className="service-panel-title">
      <div><small>{caseLabel(selected)}{data&&` · ${data.status}`}</small><h3>{data?.subject||'Case details'}</h3></div>
      <button type="button" className="btn outline" onClick={close}>Close details</button>
    </div>
    {(error||result?.error)&&<p role="alert">{error||result?.error} {result?.error&&<button type="button" onClick={onChanged}>Retry</button>}</p>}
    {notice&&<p role="status">{notice}</p>}
    {!result&&<p role="status">Loading case…</p>}
    {data&&<>
      <p>{data.category_name} · {data.employee_name}{data.priority&&` · ${data.priority} priority`}</p>
      <p className="service-text">{data.details}</p>
      {data.hr_response&&<p className="service-text"><strong>Latest HR response: </strong>{data.hr_response}</p>}
      {data.assignment&&<p><strong>Assigned to:</strong> {data.assignment.assignee_name} · Due {data.assignment.due_date}</p>}
      <h4>Conversation history</h4>
      {data.messages.length?<ol className="service-thread">{data.messages.map(m=><li key={m.id}><strong>{m.author}</strong> <small>{m.created_at}</small><p className="service-text">{m.message}</p></li>)}</ol>:<p>No messages yet.</p>}
      {messageOffset>0&&<button className="btn outline" type="button" onClick={()=>setMessageOffset(n=>n-50)}>Newer messages</button>}
      {data.has_older_messages&&<button className="btn outline" type="button" onClick={()=>setMessageOffset(n=>n+50)}>Older messages</button>}
      {data.can_reply&&<form onSubmit={e=>void save(e,messagePath,'POST',{message:reply.trim()},()=>{setReply('');setMessageOffset(0)},'Reply sent.')}>
        <label>Reply visible to the employee<textarea rows={3} maxLength={1200} value={reply} onChange={e=>setReply(e.target.value)}/></label>
        <button className="btn primary" disabled={busy||reply.trim().length<2}>Send reply</button>
      </form>}
      {data.allowed_statuses.length>0&&<form onSubmit={e=>void save(e,statusPath,ticket?'PATCH':'POST',
        ticket?{status}:{status,hr_response:note.trim()},()=>{setStatus('');setNote('')},'Status updated.')}>
        <label>Change case status<select value={status} onChange={e=>setStatus(e.target.value)} required>
          <option value="">Select status</option>{data.allowed_statuses.map(s=><option key={s}>{s}</option>)}
        </select></label>
        {!ticket&&<label>Employee-facing resolution note<textarea rows={2} value={note} maxLength={2000} onChange={e=>setNote(e.target.value)} required={needsNote}/></label>}
        <button className="btn outline" disabled={busy||!data.allowed_statuses.includes(status)||(needsNote&&note.trim().length<5)}>Save status</button>
      </form>}
      {data.can_assign&&<form onSubmit={e=>void save(e,`/talent/helpdesk/${selected.id}/triage`,'POST',
        {assignee_id:Number(owner),due_date:due},()=>{setOwner('');setDue('')},'Assignment saved.')}>
        <label>HR owner<select required value={owner} onChange={e=>setOwner(e.target.value)}>
          <option value="">Select HR owner</option>{data.owners.map(o=><option value={o.id} key={o.id}>{o.name}</option>)}
        </select></label>
        <label>Response due date<input value={due} onChange={e=>setDue(e.target.value)} type="date" required/></label>
        <button className="btn outline" disabled={busy||!owner||!due}>Save assignment</button>
      </form>}
    </>}
  </section>
}

export default function ServiceCenter({page,api,isHR,onNewTicket,children}:{
  page:string;api:API;isHR:boolean;onNewTicket:()=>void;children:ReactNode
}){
  const [kind,setKind]=useState('all')
  const [state,setState]=useState('all')
  const [draft,setDraft]=useState('')
  const [query,setQuery]=useState('')
  const [offset,setOffset]=useState(0)
  const [selected,setSelected]=useState<Key|null>(null)
  const [revision,setRevision]=useState(0)
  const refresh=()=>setRevision(v=>v+1)
  useRefreshData(refresh)
  const path='/service-center/cases?'+new URLSearchParams({kind,state,q:query,offset:String(offset),limit:String(pageSize)})
  const result=useResult<Page>(api,path,revision)
  const data=result?.data
  return <section className="service-center panel" aria-label="HR Service Center">
    <h1>HR Service Center</h1>
    <p>Open, reply to, and manage service requests and support tickets from one inbox.</p>
    <div className="button-pair"><button type="button" className="btn primary" onClick={onNewTicket}>New support ticket</button>{children}</div>
    {page==='helpdesk'&&<p className="service-legacy">You opened an existing Helpdesk link. Support tickets and service requests now share this inbox.</p>}
    <form className="service-filters" onSubmit={event=>{event.preventDefault();setOffset(0);setQuery(draft.trim())}}>
      <label>Case type<select value={kind} onChange={e=>{setKind(e.target.value);setOffset(0)}}>
        <option value="all">All cases</option><option value="ticket">Support tickets</option><option value="request">Service requests</option>
      </select></label>
      <label>Case status<select value={state} onChange={e=>{setState(e.target.value);setOffset(0)}}>
        <option value="all">All statuses</option><option value="active">Active</option><option value="completed">Completed</option>
      </select></label>
      <label>Search cases<input value={draft} onChange={e=>setDraft(e.target.value)} maxLength={150} placeholder={isHR?'Subject, category or employee':'Subject or category'}/></label>
      <button className="btn outline">Search</button>
      <button className="btn outline" type="button" onClick={()=>{setKind('all');setState('all');setQuery('');setDraft('');setOffset(0)}}>Clear filters</button>
    </form>
    <div className="service-case-scroll" aria-label="Combined case queue">
    {result?.error?<p role="alert">{result.error} <button type="button" onClick={refresh}>Retry</button></p>
      :!data?<p role="status">Loading cases…</p>
      :data.items.length?<table>
        <thead><tr><th scope="col">Case</th><th scope="col">Subject</th><th scope="col">Category</th><th scope="col">Status</th>{isHR&&<th scope="col">Employee</th>}</tr></thead>
        <tbody>{data.items.map(item=><tr key={casePath(item)}><td>{caseLabel(item)}</td>
          <td><button className="service-open" type="button" aria-label={`Open ${caseLabel(item)}: ${item.subject}`}
            onClick={()=>setSelected({kind:item.kind,id:item.id})}>{item.subject}</button></td>
          <td>{item.category_name}</td><td>{item.status}</td>{isHR&&<td>{item.employee_name}</td>}</tr>)}</tbody>
      </table>:<p>No cases found.</p>}
    </div>
    {(offset>0||data?.has_more)&&<div className="button-pair">
      <button className="btn outline" type="button" disabled={offset===0} onClick={()=>setOffset(v=>v-pageSize)}>Previous</button>
      <button className="btn outline" type="button" disabled={!data?.has_more} onClick={()=>setOffset(v=>v+pageSize)}>Next</button>
    </div>}
    {selected&&<CaseDetail key={casePath(selected)} selected={selected} api={api} revision={revision} onChanged={refresh} close={()=>setSelected(null)}/>}
  </section>
}
