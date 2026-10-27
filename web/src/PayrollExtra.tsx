import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import React,{useCallback,useEffect,useState} from 'react';
import {Calculator,ShieldCheck,Download,FileCheck2,AlertTriangle} from 'lucide-react';
import './payroll-extra.css';

type Item=Record<string,any>;
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
async function api<T=any>(path:string,method='GET',body?:unknown):Promise<T>{
 const token=sessionStorage.getItem('sass_token');
 const res=await hrmFetch(API+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{})});
 const response=await res.json().catch(()=>null);
 if(!res.ok)throw Error(typeof response?.detail==='string'?response.detail:`HTTP ${res.status}: Request failed`);
 return response as T;
}
const money=(amount:number,cur='INR')=>new Intl.NumberFormat('en-IN',{style:'currency',currency:cur,maximumFractionDigits:2}).format(amount||0);
const number=(x:any)=>Number(x||0);
const label=(s:string)=>s.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
function Message({value,error=false}:{value:string;error?:boolean}){return value?<div className={`pay-msg ${error?'pay-error':'pay-good'}`} role="status">{value}</div>:null}
function DataGrid({items,keys}:{items:Item[];keys:string[]}){return <div className="pay-table"><table><thead><tr>{keys.map(k=><th key={k}>{label(k)}</th>)}</tr></thead><tbody>{items.map((r,i)=><tr key={i}>{keys.map(k=><td key={k}>{typeof r[k]==='boolean'?(r[k]?'Yes':'No'):typeof r[k]==='number'&&['basic','hra','allowance','gross','net','employee_pf','employee_esi','income_tax_tds','deductions'].includes(k)?money(r[k],r.currency):String(r[k]??'—')}</td>)}</tr>)}</tbody></table>{!items.length&&<div className="pay-empty">No records yet.</div>}</div>}
export function TaxCalculator(){
 const [country,setCountry]=useState<'IN'|'GB'|'US'>('IN');
 const [regime,setRegime]=useState('new');const [income,setIncome]=useState('');const [deductions,setDeductions]=useState('0');const [resident,setResident]=useState(true);
 const [result,setResult]=useState<Item|null>(null);const [error,setError]=useState('');const [busy,setBusy]=useState(false);
 const opts:Record<string,{code:string;regimes:string[];subtitle:string}>= {
  IN:{code:'INR',regimes:['new','old'],subtitle:'India tax year 2026–27 · salaried ordinary income only'},
  GB:{code:'GBP',regimes:['standard'],subtitle:'UK 2026–27 · England, Wales and Northern Ireland'},
  US:{code:'USD',regimes:['single'],subtitle:'US tax year 2026 · federal single filer only'}
 };
 async function calculate(e:React.FormEvent){e.preventDefault();setBusy(true);setError('');setResult(null);
  try{const r=await api<Item>('/payroll-v2/tax-estimate','POST',{country,annual_gross:Number(income),deductions:Number(deductions),regime,resident});setResult(r)}
  catch(err){setError((err as Error).message)}finally{setBusy(false)}
 }
 return <div className="pay-shell"><div className="pay-heading"><span className="pay-eyebrow">SASS HRM / COMPLIANCE WORKBENCH</span><h1><Calculator size={29}/> Country tax calculator</h1><p>Annual salary income-tax estimates using published 2026 reference rules. Calculations are indicative, not statutory payslips or filing advice.</p></div>
 <div className="pay-warning"><AlertTriangle size={20}/> No tax IDs are collected. This does not calculate full Indian TDS, UK PAYE, US W-4 withholding, or international legal compliance.</div>
 <section className="pay-card"><h2>Estimate annual income tax</h2><p className="pay-hint">{opts[country].subtitle}</p><form className="pay-fields" onSubmit={calculate}>
  <label>Country<select value={country} onChange={e=>{const v=e.target.value as 'IN'|'GB'|'US';setCountry(v);setRegime(v==='IN'?'new':v==='GB'?'standard':'single');setResult(null)}}><option value="IN">India (INR)</option><option value="GB">United Kingdom (GBP)</option><option value="US">United States (USD)</option></select></label>
  <label>Tax regime<select value={regime} onChange={e=>setRegime(e.target.value)}>{opts[country].regimes.map(o=><option key={o} value={o}>{o==='new'?'New':o==='old'?'Old':o==='single'?'Single (federal)': 'Standard rates'}</option>)}</select></label>
  <label>Annual gross salary ({opts[country].code})<input required min="0" max="100000000" type="number" step="0.01" value={income} onChange={e=>setIncome(e.target.value)}/></label>
  <label>Other eligible deductions (where supported)<input required min="0" type="number" step="0.01" value={deductions} onChange={e=>setDeductions(e.target.value)} disabled={country==='IN'&&regime==='new'}/></label>
  {country==='IN'&&<label className="pay-check"><input type="checkbox" checked={resident} onChange={e=>setResident(e.target.checked)}/> Indian tax resident (rebate eligibility)</label>}
  <button className="pay-primary" disabled={busy} type="submit">{busy?'Calculating…':'Calculate tax'}</button>
 </form><Message error value={error}/></section>
 {result&&<section className="pay-card"><h2>Estimated outcome <span className="pay-period">{result.tax_year}</span></h2><div className="pay-metrics"><div><span>Taxable income</span><strong>{money(result.taxable_income,result.currency)}</strong></div><div><span>Estimated annual tax</span><strong>{money(result.estimated_annual_tax,result.currency)}</strong></div><div><span>Illustrative monthly allocation</span><strong>{money(result.estimated_monthly_tax,result.currency)}</strong></div><div><span>Tax rebate</span><strong>{money(result.rebate,result.currency)}</strong></div></div><DataGrid items={[{standard_deduction:money(result.standard_deduction,result.currency),other_deductions:money(result.other_deductions_used,result.currency),income_tax:money(result.base_tax,result.currency),cess:money(result.cess,result.currency)}]} keys={['standard_deduction','other_deductions','income_tax','cess']}/><h3>Important limitations</h3><ul>{result.limitations?.map((s:string)=><li key={s}>{s}</li>)}</ul><p className="pay-hint">Source: {result.sources?.map((s:string)=><a href={s} target="_blank" rel="noreferrer" key={s}>Official tax guidance ↗</a>)}</p></section>}
 </div>;
}

const fresh={employee_id:'',basic:'',hra:'',allowance:'',pf_enabled:false,esi_enabled:false,pf_cap:'15000',professional_tax:'0',other_deductions:'0',tax_regime:'new',tds_mode:'estimate',monthly_tds:'0'};
const currentPeriod=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`}
const periodDays=(v:string)=>{const [y,m]=v.split('-').map(Number);return new Date(y,m,0).getDate()}
export function PayrollWorkbench({isHR}:{isHR:boolean}){
 const [packages,setPackages]=useState<Item[]>([]);const [people,setPeople]=useState<Item[]>([]);const [runs,setRuns]=useState<Item[]>([]);const [adjustments,setAdjustments]=useState<Item[]>([]);
 const [adjust,setAdjust]=useState<Item>({employee_id:'',bonus:0,reimbursements:0,extra_deductions:0,days_worked:30,payable_days:30,tds_override:'',notes:''});
 const [statements,setStatements]=useState<Item[]>([]);const [selected,setSelected]=useState<Item|null>(null);const [selection,setSelection]=useState('');
 void selection;
 const [form,setForm]=useState<Item>(fresh);const [period,setPeriod]=useState(currentPeriod);const [busy,setBusy]=useState(false);const [message,setMessage]=useState('');const [error,setError]=useState('');
 const refresh=useCallback(async()=>{
  try{setError('');if(isHR){const [p,e,r,a]=await Promise.all([api<Item[]>('/payroll-v2/salary-packages'),api<Item[]>('/employees'),api<Item[]>('/payroll-v2/runs'),api<Item[]>('/payroll-v2/adjustments')]);setPackages(p);setPeople(e);setRuns(r);setAdjustments(a)}
  else setStatements(await api<Item[]>('/payroll-v2/my-statements'));
  }catch(e){setError((e as Error).message)}
 },[isHR]);
 useEffect(()=>{refresh()},[refresh]);
 useRefreshData(refresh);
 const go=async(fn:()=>Promise<any>,success:string)=>{setBusy(true);setError('');setMessage('');try{await fn();setMessage(success);await refresh()}catch(e){setError((e as Error).message)}finally{setBusy(false)}};
 const loadPackage=(id:number)=>{const p=packages.find(x=>x.employee_id===id);setForm(p?Object.fromEntries(Object.keys(fresh).map(k=>[k,k==='employee_id'?id:['pf_enabled','esi_enabled'].includes(k)?!!p[k]:p[k]??(fresh as Item)[k]])):{...fresh,employee_id:id})};
 async function saveSalary(e:React.FormEvent){e.preventDefault();const id=Number(form.employee_id);if(!id)return setError('Select an employee');
  await go(()=>api(`/payroll-v2/salary-packages/${id}`,'PUT',{employee_id:id,...Object.fromEntries(['basic','hra','allowance','pf_cap','professional_tax','other_deductions','monthly_tds'].map(k=>[k,number(form[k])])),pf_enabled:!!form.pf_enabled,esi_enabled:!!form.esi_enabled,tax_regime:form.tax_regime,tds_mode:form.tds_mode}),'Salary structure saved. Previously generated pay runs remain unchanged.');
 }
 async function saveAdjustment(e:React.FormEvent){e.preventDefault();const id=Number(adjust.employee_id);
  if(!id)return setError('Select employee for the adjustment');
  const payload={employee_id:id,month:period,...Object.fromEntries(['bonus','reimbursements','extra_deductions','days_worked','payable_days'].map(k=>[k,number(adjust[k])])),tds_override:adjust.tds_override===''?null:number(adjust.tds_override),notes:adjust.notes||''};
  await go(()=>api(`/payroll-v2/adjustments/${id}/${period}`,'PUT',payload),'One-off adjustment recorded. Generate a new payroll draft for the period to include it.');
 }
  async function runDetail(id:number){setSelection(String(id));setError('');try{setSelected(await api<Item>(`/payroll-v2/runs/${id}`))}catch(e){setError((e as Error).message)}}
 async function transition(action:'review'|'publish'){if(!selected)return;
  if(!window.confirm(action==='publish'?'Publish all payslips for this period to the employees? This cannot be undone. No payments will be sent.':'Confirm you have manually checked the payroll preview and want to mark it Reviewed?'))return;
  await go(()=>api(`/payroll-v2/runs/${selected.run.id}/transition`,'POST',{action,reviewed:true}),`Pay run ${action==='review'?'reviewed':'published'} successfully.`);await runDetail(selected.run.id);
 }
 async function csv(){if(!selected)return;try{setError('');const token=sessionStorage.getItem('sass_token');const r=await hrmFetch(API+`/payroll-v2/runs/${selected.run.id}/export.csv`,{headers:{Authorization:`Bearer ${token}`}});if(!r.ok)throw Error('Export failed');const b=await r.blob();const u=URL.createObjectURL(b);const a=document.createElement('a');a.href=u;a.download=`sass-payroll-${selected.run.month}.csv`;a.click();URL.revokeObjectURL(u)}catch(e){setError((e as Error).message)}}
 return <div className="pay-shell"><div className="pay-heading"><span className="pay-eyebrow">SASS HRM / FINANCE OPERATIONS</span><h1><ShieldCheck size={29}/> Payroll processing workbench</h1><p>India salary structures, estimated PF/ESI/TDS, immutable monthly snapshots, draft review and employee payslip publication.</p></div>
 <div className="pay-warning"><AlertTriangle size={20}/> Development payroll simulation only. Local eligibility, exemptions, state professional tax, tax declarations, PF/EPS splits and compliance filings require qualified payroll review. No payment integration exists.</div>
 <Message value={message}/><Message error value={error}/>
 {!isHR?<section className="pay-card"><h2>My published salary statements</h2><p className="pay-hint">Only your own published payroll workbench payslips are visible here.</p><DataGrid items={statements} keys={['month','currency','gross','employee_pf','employee_esi','income_tax_tds','deductions','net']}/>{statements.map(s=><details className="pay-details" key={s.month}><summary>{s.month} · Detailed pay statement (simulated)</summary><div className="pay-statement"><div className="pay-statement-head"><strong>SASS INNOVATIONS · PAY STATEMENT</strong><span>{s.month} / {s.currency}</span></div><p><strong>{s.employee_name}</strong> · {s.code}</p><div className="pay-slip-rows">{[
 ['Basic salary (configured)',s.salary_components?.basic],['HRA (configured)',s.salary_components?.hra],['Allowance (configured)',s.salary_components?.allowance],
 ['Gross earned pay',s.gross],['Reimbursements',s.reimbursements],['Provident fund (employee)',s.employee_pf],
 ['ESI (employee)',s.employee_esi],['Professional tax',s.professional_tax],['Estimated TDS',s.income_tax_tds],
 ['Other deductions',s.other_deductions],['Total deductions',s.deductions],['Net simulated pay',s.net]
 ].map(([label,value])=><div key={label as string}><span>{label}</span><strong>{money(Number(value),s.currency)}</strong></div>)}</div><p className="pay-hint">This statement is a simulated estimate and does not prove payment, tax withholding or statutory compliance. Contact HR for an official payslip.</p></div></details>)}</section>:<>
 <section className="pay-card"><h2>1 · Salary structures <span className="pay-period">HR restricted</span></h2><p className="pay-hint">Enter monthly pay. PF and ESI apply only after eligibility verification; professional tax is a manually approved state-specific amount.</p><form onSubmit={saveSalary} className="pay-fields">
  <label>Employee<select required value={form.employee_id} onChange={e=>loadPackage(Number(e.target.value))}><option value="">Select employee</option>{people.map(p=><option key={p.id} value={p.id}>{p.name} · {p.code}</option>)}</select></label>
  {(['basic','hra','allowance','professional_tax','other_deductions','pf_cap'] as const).map(k=><label key={k}>{label(k)} (INR)<input type="number" required min="0" step="0.01" value={form[k]} onChange={e=>setForm(x=>({...x,[k]:e.target.value}))}/></label>)}
  <label>Income tax regime<select value={form.tax_regime} onChange={e=>setForm(x=>({...x,tax_regime:e.target.value}))}><option value="new">New tax regime</option><option value="old">Old tax regime</option></select></label>
  <label>TDS method<select value={form.tds_mode} onChange={e=>setForm(x=>({...x,tds_mode:e.target.value}))}><option value="estimate">Estimated from annual fixed salary</option><option value="manual">Manually reviewed monthly TDS</option></select></label>
  {form.tds_mode==='manual'&&<label>Manual monthly TDS (INR)<input type="number" min="0" required step="0.01" value={form.monthly_tds} onChange={e=>setForm(x=>({...x,monthly_tds:e.target.value}))}/></label>}
  <label className="pay-check"><input type="checkbox" checked={!!form.pf_enabled} onChange={e=>setForm(x=>({...x,pf_enabled:e.target.checked}))}/> PF eligible / apply example 12% employee rate</label>
  <label className="pay-check"><input type="checkbox" checked={!!form.esi_enabled} onChange={e=>setForm(x=>({...x,esi_enabled:e.target.checked}))}/> ESI eligible / apply example 0.75% employee rate</label>
  <button type="submit" className="pay-primary" disabled={busy||!form.employee_id}>Save salary package</button></form>
  <h3>Configured salary packages</h3><DataGrid items={packages} keys={['employee_name','basic','hra','allowance','tax_regime','tds_mode','pf_enabled','esi_enabled']}/></section>
 <section className="pay-card"><h2>2 · Monthly adjustments &amp; attendance corrections</h2><p className="pay-hint">Bonuses, expense reimbursements, pay-day proration and manual withholding overrides for an employee in the selected month. Save before creating the monthly payroll draft.</p>
  <form className="pay-fields" onSubmit={saveAdjustment}><label>Employee<select required value={adjust.employee_id} onChange={e=>setAdjust(x=>({...x,employee_id:e.target.value}))}><option value="">Select employee</option>{packages.map(p=><option key={p.employee_id} value={p.employee_id}>{p.employee_name}</option>)}</select></label>
  {(['bonus','reimbursements','extra_deductions','days_worked','payable_days'] as const).map(k=><label key={k}>{label(k)}<input type="number" required min="0" max={k==='days_worked'||k==='payable_days'?31:10000000} step={k.includes('days')?1:'0.01'} value={adjust[k]} onChange={e=>setAdjust(x=>({...x,[k]:e.target.value}))}/></label>)}
  <label>Manual TDS override (blank = use package)<input type="number" min="0" step="0.01" value={adjust.tds_override} onChange={e=>setAdjust(x=>({...x,tds_override:e.target.value}))}/></label><label>Adjustment reason<input maxLength={300} value={adjust.notes} onChange={e=>setAdjust(x=>({...x,notes:e.target.value}))}/></label>
  <button type="submit" className="pay-primary" disabled={busy||!adjust.employee_id}>Save period adjustment</button></form>
  <DataGrid items={adjustments.filter(a=>a.month===period)} keys={['employee_name','month','bonus','reimbursements','extra_deductions','days_worked','payable_days','tds_override']}/></section>
  <section className="pay-card"><h2>3 · Create monthly payroll snapshot</h2><p className="pay-hint">Tax year supported: April 2026 through March 2027. Each period can be created once. No silent salary changes to historical runs.</p><div className="pay-inline"><label>Payroll month<input type="month" min="2026-04" max="2027-03" value={period} onChange={e=>{const next=e.target.value;setPeriod(next);setAdjust(a=>({...a,days_worked:periodDays(next),payable_days:periodDays(next)}))}}/></label><button className="pay-primary" disabled={busy} onClick={()=>go(()=>api('/payroll-v2/runs','POST',{month:period}),'Draft payroll created. Review the breakdown before publishing.')}>Create draft</button></div>
  <div className="pay-table"><table><thead><tr><th>Month</th><th>Status</th><th>Employees</th><th>Actions</th></tr></thead><tbody>{runs.map(r=><tr key={r.id}><td>{r.month}</td><td>{r.status}</td><td>{r.employee_count}</td><td><button className="pay-secondary" onClick={()=>runDetail(r.id)}>Inspect run</button></td></tr>)}</tbody></table>{!runs.length&&<div className="pay-empty">No runs created yet.</div>}</div></section>
 {selected&&<section className="pay-card"><h2>4 · Review payslips <span className="pay-period">{selected.run.month} · {selected.run.status}</span></h2><div className="pay-metrics"><div><span>Gross pay</span><strong>{money(selected.totals?.gross)}</strong></div><div><span>Deductions</span><strong>{money(selected.totals?.deductions)}</strong></div><div><span>Net pay</span><strong>{money(selected.totals?.net)}</strong></div><div><span>Employer cost estimate</span><strong>{money(selected.totals?.employer_total_estimate)}</strong></div></div>
  <DataGrid items={selected.items||[]} keys={['code','employee_name','gross','employee_pf','employee_esi','professional_tax','income_tax_tds','deductions','net']}/>
  <div className="pay-actions"><button className="pay-secondary" onClick={csv}><Download size={15}/> Export CSV</button>{selected.run.status==='Draft'&&<button disabled={busy} className="pay-primary" onClick={()=>transition('review')}><FileCheck2 size={16}/> Mark reviewed</button>}{selected.run.status==='Reviewed'&&<button disabled={busy} className="pay-primary" onClick={()=>transition('publish')}>Publish employee statements</button>}</div>
  <p className="pay-hint">{selected.run.status==='Published'?'Published statements are visible to each employee.':'Draft and reviewed statements are only visible to HR.'} Publishing does not transfer money or file government returns.</p></section>}
 </>}
 </div>;
}
