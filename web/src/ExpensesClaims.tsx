import React, {useCallback, useEffect, useMemo, useState} from 'react';
import {AlertTriangle, CheckCircle2, ClipboardCheck, Download, FileText, HandCoins, Plus, Receipt, Save, Search, Settings2, ShieldCheck} from 'lucide-react';
import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import {pageUrl} from './pageRoutes';
import './expenses-claims.css';

type Row=Record<string,any>;
type ClaimForm={title:string;amount:string;category:string;expense_date:string;merchant:string;business_purpose:string;cost_center:string;receipt_reference:string;reason:string};
type Policy={allowed_categories:string[];max_claim_amount:number;submission_window_days:number;receipt_required:boolean;receipt_threshold:number;business_purpose_required:boolean;allow_employee_edits:boolean;allow_withdrawals:boolean;guidance:string};
const categories=['Travel','Connectivity','Meals','Equipment','Other'];
const defaults:Policy={allowed_categories:[...categories],max_claim_amount:500000,submission_window_days:180,receipt_required:false,receipt_threshold:1000,business_purpose_required:false,allow_employee_edits:true,allow_withdrawals:true,guidance:'Submit only genuine business expenses. HR approval does not initiate reimbursement.'};
const today=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`};
const blank=():ClaimForm=>({title:'',amount:'',category:'Other',expense_date:today(),merchant:'',business_purpose:'',cost_center:'',receipt_reference:'',reason:''});
const formatAmount=(n:number)=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:2}).format(Number(n)||0);
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
async function api<T>(path:string,method='GET',body?:unknown):Promise<T>{
 const token=sessionStorage.getItem('sass_token');
 const response=await hrmFetch(API+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});
 const result=await response.json().catch(()=>({}));
 if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:`Request failed: HTTP ${response.status}`);
 return result as T;
}
const csvValue=(v:unknown)=>{let value=String(v??'');if(/^[=+\-@\t\r]/.test(value))value="'"+value;return '"'+value.replaceAll('"','""')+'"'};
function exportCsv(items:Row[]){
 const fields=['id','employee_name','title','category','amount','currency','expense_date','merchant','business_purpose','cost_center','receipt_reference','status','reimbursement_status','created_at'];
 const contents='\uFEFF'+[fields.join(','),...items.map(row=>fields.map(key=>csvValue(row[key])).join(','))].join('\r\n');
 const url=URL.createObjectURL(new Blob([contents],{type:'text/csv;charset=utf-8'}));
 const anchor=document.createElement('a');anchor.href=url;anchor.download='sass-hrm-expenses-claims.csv';anchor.click();URL.revokeObjectURL(url);
}

export function ExpensesClaims({isHR,userId,expenses,onChanged}:{isHR:boolean;userId:number;expenses:Row[];onChanged:()=>Promise<void>}){
 const [policy,setPolicy]=useState<Policy>(defaults),[policySaved,setPolicySaved]=useState<Policy>(defaults);
 const [source,setSource]=useState('defaults');
 const [activeTab,setActiveTab]=useState<'register'|'claim'|'settings'>('register');
 const [mode,setMode]=useState<'new'|'edit'>('new'),[editingId,setEditingId]=useState<number|null>(null),[form,setForm]=useState<ClaimForm>(blank());
 const [query,setQuery]=useState(''),[statusFilter,setStatusFilter]=useState('All');
 const [selectedId,setSelectedId]=useState<number|null>(null),[activity,setActivity]=useState<Row[]>([]),[reimbursement,setReimbursement]=useState<Row|null>(null);
 const [reviewDecision,setReviewDecision]=useState('Approved'),[reviewReason,setReviewReason]=useState('');
 const [reimburseStatus,setReimburseStatus]=useState('Scheduled'),[paymentReference,setPaymentReference]=useState(''),[paymentNotes,setPaymentNotes]=useState('');
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const selected=expenses.find(item=>Number(item.id)===selectedId)||null;
 const filtered=useMemo(()=>expenses.filter(item=>{
   if(statusFilter!=='All'&&item.status!==statusFilter)return false;
   return [item.id,item.employee_name,item.title,item.category,item.merchant,item.cost_center,item.status,item.receipt_reference].join(' ').toLowerCase().includes(query.trim().toLowerCase());
 }),[expenses,statusFilter,query]);
 const loadPolicy=useCallback(async()=>{
   try{const response=await api<{settings:Policy;source:string}>('/expenses/policy');setPolicy(response.settings);setPolicySaved(response.settings);setSource(response.source);setError('')}
   catch(e){setError((e as Error).message)}
 },[]);
 const loadSelected=useCallback(async(id:number)=>{
  try{const [events,payment]=await Promise.all([api<Row[]>(`/expenses/${id}/activity`),api<Row>(`/expenses/${id}/reimbursement`)]);setActivity(events);setReimbursement(payment)}
  catch(e){setError((e as Error).message)}
 },[]);
 useEffect(()=>{void loadPolicy()},[loadPolicy]);useRefreshData(loadPolicy);
 useEffect(()=>{if(selectedId!==null)void loadSelected(selectedId);else{setActivity([]);setReimbursement(null)}},[selectedId,loadSelected]);
 const setField=(key:keyof ClaimForm,value:string)=>setForm(previous=>({...previous,[key]:value}));
 const beginEdit=(item:Row)=>{
   setMode('edit');setEditingId(Number(item.id));setForm({title:item.title||'',amount:String(item.amount??''),category:item.category||'Other',expense_date:item.expense_date||today(),merchant:item.merchant||'',business_purpose:item.business_purpose||'',cost_center:item.cost_center||'',receipt_reference:item.receipt_reference||'',reason:''});setActiveTab('claim');setError('');setNotice('');
 };
 const resetForm=()=>{setForm(blank());setMode('new');setEditingId(null);setActiveTab('register')};
 const change=async(path:string,method:string,body:unknown,success:string)=>{
  setBusy(true);setError('');setNotice('');
  try{await api(path,method,body);setNotice(success);await onChanged();if(selectedId!==null)await loadSelected(selectedId);return true}
  catch(e){setError((e as Error).message);return false}finally{setBusy(false)}
 };
 async function saveClaim(e:React.FormEvent){e.preventDefault();
  if(!Number.isFinite(Number(form.amount))||Number(form.amount)<=0){setError('Enter a valid amount');return}
  const payload={title:form.title.trim(),amount:Number(form.amount),category:form.category,expense_date:form.expense_date,merchant:form.merchant,business_purpose:form.business_purpose,cost_center:form.cost_center,receipt_reference:form.receipt_reference};
  const path=mode==='edit'?`/expenses/${editingId}/details`:'/expenses';
  const ok=await change(path,mode==='edit'?'PUT':'POST',mode==='edit'?{...payload,reason:form.reason}:payload,mode==='edit'?'Claim updated and audited.':'Claim submitted to HR for review.');
  if(ok)resetForm();
 }
 async function withdraw(id:number){if(!window.confirm('Withdraw this pending claim?'))return;await change(`/expenses/${id}/withdraw`,'POST',{},'Pending claim withdrawn.');}
 async function savePolicy(e:React.FormEvent){e.preventDefault();
  const ok=await change('/expenses/policy','PUT',policy,'Expense policy saved and audited.');if(ok){setPolicySaved({...policy});setSource('organization')}
 }
 async function review(e:React.FormEvent){e.preventDefault();if(!selected)return;
  const ok=await change(`/compensation/expenses/${selected.id}/review`,'POST',{decision:reviewDecision,reason:reviewReason},'HR decision recorded; no payment initiated.');if(ok)setReviewReason('');
 }
 async function saveReimbursement(e:React.FormEvent){e.preventDefault();if(!selected)return;
  const ok=await change(`/expenses/${selected.id}/reimbursement`,'PUT',{status:reimburseStatus,external_payment_reference:paymentReference,notes:paymentNotes},'Reimbursement status recorded. No bank transfer initiated.');if(ok){setPaymentNotes('');setPaymentReference('')}
 }
 const stats=[['Total claims',expenses.length],['Pending approval',expenses.filter(item=>item.status==='Pending').length],['Approved value',formatAmount(expenses.filter(item=>item.status==='Approved').reduce((sum,item)=>sum+Number(item.amount||0),0))],['Recorded paid',expenses.filter(item=>item.reimbursement_status==='Paid').length]];
 return <div className="ex-shell" aria-label="Expenses and claims management">
  <header className="ex-heading"><div className="ex-symbol"><HandCoins size={27}/></div><div><span>FINANCE / EMPLOYEE SELF-SERVICE</span><h1>Expenses & claims</h1><p>Submit claims, review supporting evidence and track approval and reimbursement status.</p></div></header>
  <div className="ex-info"><ShieldCheck size={19}/><p>{policy.guidance} <strong>Reimbursement statuses are manual finance records and do not send money.</strong></p></div>
  {error&&<div className="ex-alert" role="alert"><AlertTriangle size={18}/>{error}</div>}
  {notice&&<div className="ex-success" role="status"><CheckCircle2 size={18}/>{notice}</div>}
  <div className="ex-metrics">{stats.map(([label,value])=><div key={String(label)}><span>{label}</span><strong>{value}</strong></div>)}</div>
  <div className="ex-tabs" role="tablist" aria-label="Expense operations">
    <button type="button" role="tab" aria-selected={activeTab==='register'} className={activeTab==='register'?'active':''} onClick={()=>setActiveTab('register')}><ClipboardCheck size={16}/> Claim register</button>
    <button type="button" role="tab" aria-selected={activeTab==='claim'} className={activeTab==='claim'?'active':''} onClick={()=>{setMode('new');setEditingId(null);setForm(blank());setActiveTab('claim')}}><Plus size={16}/> New claim</button>
    {isHR&&<button type="button" role="tab" aria-selected={activeTab==='settings'} className={activeTab==='settings'?'active':''} onClick={()=>setActiveTab('settings')}><Settings2 size={16}/> Expense policy settings</button>}
  </div>
  {activeTab==='register'&&<>
   <div className="ex-toolbar"><label className="ex-search"><Search size={17}/><input aria-label="Search expense claims" placeholder="Search description, employee, category or reference" value={query} onChange={e=>setQuery(e.target.value)}/></label><label>Status <select value={statusFilter} onChange={e=>setStatusFilter(e.target.value)}>{['All','Pending','Approved','Rejected','Withdrawn'].map(s=><option key={s}>{s}</option>)}</select></label><button type="button" onClick={()=>exportCsv(filtered)} disabled={!filtered.length}><Download size={16}/> Export CSV</button></div>
   <div className="ex-table-scroll"><table><thead><tr><th>Claim / employee</th><th>Category</th><th>Amount</th><th>Approval</th><th>Reimbursement</th><th>Submitted</th><th>Details</th></tr></thead><tbody>{filtered.map(item=><tr key={item.id} className={selectedId===Number(item.id)?'ex-selected':''}><td><strong>#{item.id} · {item.title}</strong><small>{item.employee_name}</small></td><td>{item.category}</td><td>{formatAmount(item.amount)}</td><td><span className="ex-status">{item.status}</span></td><td>{item.reimbursement_status||'Not recorded'}</td><td>{String(item.created_at||'').slice(0,10)}</td><td><button type="button" onClick={()=>setSelectedId(Number(item.id))}>View</button></td></tr>)}</tbody></table>{!filtered.length&&<p className="ex-empty">No expense claims match your filters.</p>}</div>
   {selected&&<section className="ex-panel"><div className="ex-panel-title"><div><h2>Claim #{selected.id}: {selected.title}</h2><p>{selected.employee_name} · {selected.status} · {formatAmount(selected.amount)}</p></div><div className="ex-actions">{selected.status==='Pending'&&(isHR||selected.employee_id===userId)&&(policy.allow_employee_edits||isHR)&&<button type="button" onClick={()=>beginEdit(selected)}>Edit</button>}{selected.status==='Pending'&&(isHR||selected.employee_id===userId)&&(policy.allow_withdrawals||isHR)&&<button type="button" disabled={busy} onClick={()=>void withdraw(selected.id)}>Withdraw</button>}<button type="button" onClick={()=>setSelectedId(null)}>Close</button></div></div>
    <div className="ex-details">{[['Expense date',selected.expense_date||'Legacy claim'],['Merchant',selected.merchant||'—'],['Business purpose',selected.business_purpose||'—'],['Cost center',selected.cost_center||'—'],['Receipt / voucher reference',selected.receipt_reference||'Not recorded'],['Currency',selected.currency||'INR']].map(([name,value])=><div key={name}><span>{name}</span><strong>{value}</strong></div>)}</div>
    <div className="ex-two-cols"><section><h3><FileText size={16}/> Approval & activity history</h3>{activity.length?activity.map((event,i)=><div className="ex-event" key={i}><strong>{event.event_type}</strong><span>{String(event.created_at||'').replace('T',' ').slice(0,19)}</span><p>{event.event_note}</p></div>):<p className="ex-muted">No recorded activity. Legacy claims may have no details.</p>}</section><section><h3><Receipt size={16}/> Reimbursement</h3><div className="ex-payment-status"><strong>{reimbursement?.status||'Not recorded'}</strong><span>{reimbursement?.updated_at?String(reimbursement.updated_at).slice(0,10):'No finance status recorded'}</span></div>{reimbursement?.external_payment_reference&&<p><b>External reference:</b> {reimbursement.external_payment_reference}</p>}{reimbursement?.notes&&<p>{reimbursement.notes}</p>}{isHR&&selected.status==='Pending'&&selected.employee_id!==userId&&<form onSubmit={review} className="ex-miniform"><h4>HR approval decision</h4><label>Decision<select value={reviewDecision} onChange={e=>setReviewDecision(e.target.value)}><option>Approved</option><option>Rejected</option></select></label><label>Review reason *<textarea required minLength={5} maxLength={500} rows={2} value={reviewReason} onChange={e=>setReviewReason(e.target.value)}/></label><button type="submit" disabled={busy}>Save review decision</button></form>}
      {isHR&&selected.status==='Approved'&&reimbursement?.status!=='Paid'&&<form className="ex-miniform" onSubmit={saveReimbursement}><h4>Record finance follow-up</h4><label>Manual status<select value={reimburseStatus} onChange={e=>setReimburseStatus(e.target.value)}><option>Scheduled</option><option>Paid</option><option>Cancelled</option></select></label><label>External payment reference {reimburseStatus==='Paid'?'*':''}<input maxLength={120} required={reimburseStatus==='Paid'} value={paymentReference} onChange={e=>setPaymentReference(e.target.value)}/></label><label>Finance notes *<textarea minLength={8} maxLength={500} required rows={2} value={paymentNotes} onChange={e=>setPaymentNotes(e.target.value)}/></label><button type="submit" disabled={busy}>Record reimbursement status</button><p className="ex-muted">This does not send funds, confirm bank settlement, or generate payroll entries.</p></form>}
     </section></div>
   </section>}
  </>}
  {activeTab==='claim'&&<section className="ex-panel"><div className="ex-panel-title"><div><h2>{mode==='edit'?`Edit pending claim #${editingId}`:'Submit a new expense claim'}</h2><p>Required fields are marked *. Company rules are validated on the server.</p></div><button type="button" onClick={resetForm}>Cancel</button></div>
   <form onSubmit={saveClaim}><div className="ex-fields"><label>Expense description *<input required minLength={3} maxLength={150} value={form.title} onChange={e=>setField('title',e.target.value)} placeholder="e.g. Client meeting travel"/></label><label>Amount (INR) *<input type="number" required min={0.01} max={policy.max_claim_amount} step="0.01" value={form.amount} onChange={e=>setField('amount',e.target.value)}/></label><label>Category *<select value={form.category} onChange={e=>setField('category',e.target.value)}>{Array.from(new Set([form.category,...policy.allowed_categories])).map(v=><option disabled={!policy.allowed_categories.includes(v)} key={v}>{v}</option>)}</select></label><label>Expense date *<input required type="date" max={today()} value={form.expense_date} onChange={e=>setField('expense_date',e.target.value)}/></label><label>Merchant / supplier<input maxLength={150} value={form.merchant} onChange={e=>setField('merchant',e.target.value)} placeholder="Vendor name"/></label><label>Cost center / project<input maxLength={80} value={form.cost_center} onChange={e=>setField('cost_center',e.target.value)} placeholder="Optional department or project code"/></label><label className="ex-wide">Business purpose {policy.business_purpose_required?'*':''}<textarea rows={3} required={policy.business_purpose_required} minLength={policy.business_purpose_required?8:undefined} maxLength={1000} value={form.business_purpose} onChange={e=>setField('business_purpose',e.target.value)} placeholder="Describe how this cost supports company work"/></label><label className="ex-wide">Receipt or invoice reference {policy.receipt_required?'(required above configured threshold)':''}<input maxLength={240} value={form.receipt_reference} onChange={e=>setField('receipt_reference',e.target.value)} placeholder="e.g. vendor invoice / receipt number"/><small>Reference metadata only — this field does not upload a receipt file. Use the <a href={pageUrl('vault')}>Secure document vault</a> separately if your organization has configured encrypted uploads.</small></label>{mode==='edit'&&<label className="ex-wide">Reason for editing *<textarea rows={2} required minLength={8} maxLength={300} value={form.reason} onChange={e=>setField('reason',e.target.value)}/></label>}</div><p className="ex-muted">Allowed categories: {policy.allowed_categories.join(', ')}. Maximum per claim: {formatAmount(policy.max_claim_amount)}. Submission window: {policy.submission_window_days} days.</p><div className="ex-actions"><button type="submit" className="ex-primary" disabled={busy}><Plus size={16}/>{busy?'Saving…':mode==='edit'?'Save claim changes':'Submit claim'}</button></div></form></section>}
  {activeTab==='settings'&&isHR&&<section className="ex-panel"><div className="ex-panel-title"><div><h2>Organization expense policy</h2><p>Saved configuration: {source==='organization'?'Custom company settings':'Default settings'} · HR administrator only</p></div><Settings2 size={21}/></div><form onSubmit={savePolicy}><div className="ex-fields"><label>Maximum claim amount (INR) *<input type="number" required min={1} max={500000} value={policy.max_claim_amount} onChange={e=>setPolicy(p=>({...p,max_claim_amount:Number(e.target.value)}))}/></label><label>Submission window (days) *<input type="number" required min={1} max={1095} value={policy.submission_window_days} onChange={e=>setPolicy(p=>({...p,submission_window_days:Number(e.target.value)}))}/></label><label>Receipt reference threshold (INR)<input type="number" min={0} max={500000} value={policy.receipt_threshold} onChange={e=>setPolicy(p=>({...p,receipt_threshold:Number(e.target.value)}))}/></label><div className="ex-checkboxes"><label><input type="checkbox" checked={policy.receipt_required} onChange={e=>setPolicy(p=>({...p,receipt_required:e.target.checked}))}/> Enforce receipt references at threshold</label><label><input type="checkbox" checked={policy.business_purpose_required} onChange={e=>setPolicy(p=>({...p,business_purpose_required:e.target.checked}))}/> Require business purpose</label><label><input type="checkbox" checked={policy.allow_employee_edits} onChange={e=>setPolicy(p=>({...p,allow_employee_edits:e.target.checked}))}/> Allow pending claim edits</label><label><input type="checkbox" checked={policy.allow_withdrawals} onChange={e=>setPolicy(p=>({...p,allow_withdrawals:e.target.checked}))}/> Allow pending claim withdrawals</label></div><fieldset className="ex-wide"><legend>Allowed expense categories</legend><div className="ex-categories">{categories.map(cat=><label key={cat}><input type="checkbox" checked={policy.allowed_categories.includes(cat)} onChange={e=>setPolicy(p=>({...p,allowed_categories:e.target.checked?[...p.allowed_categories,cat]:p.allowed_categories.filter(v=>v!==cat)}))}/>{cat}</label>)}</div><small>Keep at least one category enabled. Existing claims retain their original category.</small></fieldset><label className="ex-wide">Employee-facing guidance<textarea rows={3} maxLength={500} value={policy.guidance} onChange={e=>setPolicy(p=>({...p,guidance:e.target.value}))}/></label></div><div className="ex-actions"><button type="button" disabled={busy||JSON.stringify(policy)===JSON.stringify(policySaved)} onClick={()=>setPolicy({...policySaved})}>Discard edits</button><button type="submit" className="ex-primary" disabled={busy||JSON.stringify(policy)===JSON.stringify(policySaved)}><Save size={16}/> Save & audit settings</button></div></form><p className="ex-muted">This policy does not calculate tax deductions, authorize reimbursements automatically or change employee salary records.</p></section>}
  <p className="ex-footer"><ShieldCheck size={16}/> All claims and review decisions are permission-scoped and audited. Receipt references are not file uploads. Bank transfers and reconciliation must be completed in the authorized finance system.</p>
 </div>;
}
