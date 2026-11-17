import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import React,{useCallback,useEffect,useState} from 'react';
import {Calculator,ShieldCheck,Download,FileCheck2,AlertTriangle,Trash2,RotateCcw,ClipboardCheck,Search,History} from 'lucide-react';
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
type TaxCountry='IN'|'GB'|'US'|'AU'|'AE';
const taxCountries:Record<TaxCountry,{name:string;code:string;regimes:{value:string;label:string}[];subtitle:string;year:string}>={
 IN:{name:'India',code:'INR',year:'2026–27',regimes:[{value:'new',label:'New tax regime'},{value:'old',label:'Old tax regime (under 60)'}],subtitle:'Salary income · regular income tax (FY 2026–27)'},
 GB:{name:'United Kingdom',code:'GBP',year:'2026–27',regimes:[{value:'standard',label:'England, Wales & Northern Ireland'},{value:'scotland',label:'Scotland (employment income)'}],subtitle:'Personal Allowance and regional UK employment tax rates'},
 US:{name:'United States',code:'USD',year:'2026',regimes:[{value:'single',label:'Single federal filer'},{value:'married_joint',label:'Married filing jointly'},{value:'head_household',label:'Head of household'},{value:'married_separate',label:'Married filing separately'}],subtitle:'Federal ordinary income tax only · no state tax or payroll withholding'},
 AU:{name:'Australia',code:'AUD',year:'2026–27',regimes:[{value:'resident',label:'Full-year Australian resident'}],subtitle:'Full-year resident with tax-free threshold · Medicare levy excluded'},
 AE:{name:'United Arab Emirates',code:'AED',year:'2026',regimes:[{value:'salary',label:'Personal employment salary'}],subtitle:'UAE personal employment income tax only · foreign tax obligations excluded'}
};
export function TaxCalculator(){
 const [country,setCountry]=useState<TaxCountry>('IN');
 const [regime,setRegime]=useState('new');
 const [payPeriod,setPayPeriod]=useState<'annual'|'monthly'>('annual');
 const [income,setIncome]=useState('');
 const [deductions,setDeductions]=useState('0');
 const [resident,setResident]=useState(true);
 const [result,setResult]=useState<Item|null>(null);
 const [error,setError]=useState('');
 const [busy,setBusy]=useState(false);
 const option=taxCountries[country];
 const deductionsAllowed=(country==='IN'&&regime==='old') || country==='AU' || country==='GB';
 const clearResult=()=>{setResult(null);setError('')};
 const switchCountry=(next:TaxCountry)=>{
  setCountry(next);setRegime(taxCountries[next].regimes[0].value);setDeductions('0');clearResult();
 };
 async function calculate(e:React.FormEvent){
  e.preventDefault();clearResult();
  const salary=Number(income);
  const annual=payPeriod==='monthly'?salary*12:salary;
  const other=deductionsAllowed?Number(deductions):0;
  if(!income.trim() || !Number.isFinite(annual) || annual<0 || annual>100000000 ||
     !Number.isFinite(other) || other<0 || other>annual){
   setError('Enter valid salary and deduction amounts. Deductions cannot exceed annual salary.');return;
  }
  setBusy(true);
  try{
   const r=await api<Item>('/payroll-v2/tax-estimate','POST',{
    country,annual_gross:annual,deductions:other,regime,resident
   });
   setResult(r);
  }catch(err){setError((err as Error).message)}finally{setBusy(false)}
 }
 function downloadEstimate(){
  if(!result)return;
  const fields:[string,string|number][]=[
   ['Country',taxCountries[result.country as TaxCountry]?.name||String(result.country)],
   ['Tax year',result.tax_year],['Regime',result.regime],['Currency',result.currency],
   ['Annual gross',result.annual_gross],['Taxable income',result.taxable_income],
   ['Standard allowance',result.standard_deduction],['Other deductions',result.other_deductions_used],
   ['Rebate',result.rebate],['Base income tax',result.base_tax],['Cess',result.cess],
   ['Estimated annual tax',result.estimated_annual_tax],['Estimated monthly tax',result.estimated_monthly_tax],
   ['Estimated annual salary less income tax',result.estimated_annual_net],
   ['Effective income tax rate (%)',result.effective_tax_rate_percent],
   ['Calculation type','Illustrative only — not payroll withholding or a tax return']
  ];
  const esc=(v:string|number)=>`"${String(v??'').replace(/"/g,'""')}"`;
  const csv='Field,Value\r\n'+fields.map(([key,val])=>`${esc(key)},${esc(val)}`).join('\r\n')+'\r\n';
  const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
  const anchor=document.createElement('a');anchor.href=url;anchor.download=`sass-hrm-tax-estimate-${result.country}-${result.tax_year}.csv`;anchor.click();
  window.setTimeout(()=>URL.revokeObjectURL(url),1000);
 }
 return <div className="pay-shell">
  <div className="pay-heading"><span className="pay-eyebrow">SASS HRM / COMPLIANCE WORKBENCH</span><h1><Calculator size={29}/> Country tax calculator</h1>
   <p>Compare illustrative 2026 salary income tax in five jurisdictions using country-specific tax bands. These estimates do not update payroll records or submit tax returns.</p>
  </div>
  <div className="pay-warning"><AlertTriangle size={20}/><span>Reference calculations only: exclude some credits, social contributions, exemptions and withholding rules. Consult local payroll specialists before paying employees or filing statutory returns.</span></div>
  <section className="pay-card pay-tax-card"><h2>Estimate income tax <span className="pay-period">{option.year}</span></h2>
   <p className="pay-hint">{option.subtitle}</p>
   <form className="pay-tax-form" onSubmit={calculate}>
    <div className="pay-tax-input-grid">
     <label className="pay-tax-control">Country or jurisdiction
      <select value={country} onChange={e=>switchCountry(e.target.value as TaxCountry)}>
       {(Object.keys(taxCountries) as TaxCountry[]).map(c=><option value={c} key={c}>{taxCountries[c].name} ({taxCountries[c].code})</option>)}
      </select>
     </label>
     <label className="pay-tax-control">{country==='GB'?'Region':country==='US'?'Federal filing status':'Tax status / regime'}
      <select value={regime} onChange={e=>{setRegime(e.target.value);if(country==='IN'&&e.target.value==='new')setDeductions('0');clearResult()}}>
       {option.regimes.map(r=><option value={r.value} key={r.value}>{r.label}</option>)}
      </select>
     </label>
     <label className="pay-tax-control">Salary input period
      <select value={payPeriod} onChange={e=>{setPayPeriod(e.target.value as 'monthly'|'annual');clearResult()}}>
       <option value="annual">Annual</option><option value="monthly">Monthly (×12)</option>
      </select>
     </label>
     <label className="pay-tax-control">{payPeriod==='annual'?'Annual':'Monthly'} salary ({option.code})
      <input type="number" min="0" step="0.01" max={payPeriod==='annual'?100000000:8333333.33} required value={income} onChange={e=>{setIncome(e.target.value);clearResult()}} placeholder="Enter salary"/>
     </label>
     <label className="pay-tax-control">Other eligible annual deductions ({option.code})
      <input type="number" min="0" max="100000000" step="0.01" required value={deductionsAllowed?deductions:'0'} disabled={!deductionsAllowed}
       onChange={e=>{setDeductions(e.target.value);clearResult()}}/>
      <small className="pay-tax-field-help">{deductionsAllowed?'Illustrative only; eligibility depends on local tax rules.':'Not used for this tax status.'}</small>
     </label>
    </div>
    <div className="pay-tax-form-footer">
     <div className="pay-tax-options">
      {country==='IN'&&<label className="pay-tax-resident"><input type="checkbox" checked={resident} onChange={e=>{setResident(e.target.checked);clearResult()}}/><span>Indian tax resident <small>Rebate eligibility, where applicable</small></span></label>}
     </div>
     <div className="pay-tax-buttons">
      <button className="pay-primary" disabled={busy} type="submit">{busy?'Calculating…':'Calculate income tax'}</button>
      <button type="button" className="pay-secondary" onClick={()=>{setIncome('');setDeductions('0');clearResult()}} disabled={busy}>Clear values</button>
     </div>
    </div>
   </form><Message error value={error}/>
  </section>
  {result&&<section className="pay-card" aria-live="polite">
   <div className="pay-tax-result-heading"><div><h2>Estimated income tax <span className="pay-period">{result.tax_year}</span></h2><p className="pay-hint">{option.name} · {option.regimes.find(x=>x.value===result.regime)?.label||result.regime}</p></div>
    <button className="pay-secondary" type="button" onClick={downloadEstimate}><Download size={16}/> Export estimate CSV</button>
   </div>
   <div className="pay-metrics">
    <div><span>Annual gross salary</span><strong>{money(result.annual_gross,result.currency)}</strong></div>
    <div><span>Taxable salary income</span><strong>{money(result.taxable_income,result.currency)}</strong></div>
    <div><span>Estimated annual income tax</span><strong>{money(result.estimated_annual_tax,result.currency)}</strong></div>
    <div><span>Illustrative monthly income tax</span><strong>{money(result.estimated_monthly_tax,result.currency)}</strong></div>
    <div><span>Annual salary less estimated income tax</span><strong>{money(result.estimated_annual_net,result.currency)}</strong></div>
    <div><span>Effective income tax rate</span><strong>{Number(result.effective_tax_rate_percent).toFixed(2)}%</strong></div>
   </div>
   <h3>Calculation components</h3>
   <DataGrid items={[{
    standard_allowance:money(result.standard_deduction,result.currency),
    eligible_deductions:money(result.other_deductions_used,result.currency),
    rebate:money(result.rebate,result.currency),
    income_tax_after_rebate:money(result.base_tax,result.currency),
    cess:money(result.cess,result.currency)
   }]} keys={['standard_allowance','eligible_deductions','rebate','income_tax_after_rebate','cess']}/>
   {result.bracket_breakdown?.length>0&&<><h3>Progressive tax-band breakdown</h3>
    <div className="pay-table"><table><thead><tr><th>Band starts</th><th>Band ends</th><th>Rate</th><th>Income in band</th><th>Tax before rebates</th></tr></thead>
     <tbody>{result.bracket_breakdown.map((b:Item,i:number)=><tr key={`${b.from}-${i}`}><td>{money(b.from,result.currency)}</td>
      <td>{money(b.to,result.currency)}</td><td>{b.rate_percent}%</td><td>{money(b.taxable_in_band,result.currency)}</td><td>{money(b.tax_in_band,result.currency)}</td></tr>)}</tbody>
    </table></div>
   </>}
   {country==='AE'&&<p className="pay-hint">The UAE does not levy federal personal income tax on employment salary. Taxes in another country may still apply.</p>}
   <h3>Limitations and verification</h3><ul>{result.limitations?.map((s:string)=><li key={s}>{s}</li>)}</ul>
   <p className="pay-hint">Official reference: {result.sources?.map((s:string)=><a href={s} target="_blank" rel="noopener noreferrer" key={s}>Tax authority guidance ↗</a>)}. Rule set: {result.ruleset_version}.</p>
  </section>}
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
 const [preflight,setPreflight]=useState<Item|null>(null);const [runHistory,setRunHistory]=useState<Item[]>([]);
 const [runQuery,setRunQuery]=useState('');const [reviewNote,setReviewNote]=useState('');
 const [reviewChecks,setReviewChecks]=useState({roster:false,adjustments:false,statutory:false});
 const previewIssues=preflight?.issues||[];
 const readyToReview=Object.values(reviewChecks).every(Boolean)&&reviewNote.trim().length>=8;
 const esiReviewRequired=number(form.basic)+number(form.hra)+number(form.allowance)>21000;
 const markEsiPendingReview=()=>{
  setForm(x=>({...x,esi_enabled:false}));
  setError('');
  setMessage('ESI is now unchecked in this form, not yet saved. Verify coverage with your payroll specialist, then click Save salary package if suspension is appropriate.');
 };
 const refresh=useCallback(async()=>{
  try{setError('');if(isHR){const [p,e,r,a]=await Promise.all([api<Item[]>('/payroll-v2/salary-packages'),api<Item[]>('/employees'),api<Item[]>('/payroll-v2/runs'),api<Item[]>('/payroll-v2/adjustments')]);setPackages(p);setPeople(e);setRuns(r);setAdjustments(a)}
  else setStatements(await api<Item[]>('/payroll-v2/my-statements'));
  }catch(e){setError((e as Error).message)}
 },[isHR]);
 useEffect(()=>{refresh()},[refresh]);
 useRefreshData(refresh);
 const refreshPreflight=useCallback(async()=>{
  if(!isHR)return;
  try{setPreflight(await api<Item>(`/payroll-v2/preflight?month=${encodeURIComponent(period)}`))}
  catch{setPreflight(null)}
 },[isHR,period]);
 useEffect(()=>{void refreshPreflight()},[refreshPreflight]);
 const go=async(fn:()=>Promise<any>,success:string):Promise<boolean>=>{setBusy(true);setError('');setMessage('');try{await fn();setMessage(success);await refresh();await refreshPreflight();return true}catch(e){setError((e as Error).message);return false}finally{setBusy(false)}};
 const loadPackage=(id:number)=>{const p=packages.find(x=>x.employee_id===id);setForm(p?Object.fromEntries(Object.keys(fresh).map(k=>[k,k==='employee_id'?id:['pf_enabled','esi_enabled'].includes(k)?!!p[k]:p[k]??(fresh as Item)[k]])):{...fresh,employee_id:id})};
 async function saveSalary(e:React.FormEvent){e.preventDefault();const id=Number(form.employee_id);if(!id)return setError('Select an employee');
  await go(()=>api(`/payroll-v2/salary-packages/${id}`,'PUT',{employee_id:id,...Object.fromEntries(['basic','hra','allowance','pf_cap','professional_tax','other_deductions','monthly_tds'].map(k=>[k,number(form[k])])),pf_enabled:!!form.pf_enabled,esi_enabled:!!form.esi_enabled,tax_regime:form.tax_regime,tds_mode:form.tds_mode}),'Salary structure saved. Previously generated pay runs remain unchanged.');
 }
 async function saveAdjustment(e:React.FormEvent){e.preventDefault();const id=Number(adjust.employee_id);
  if(!id)return setError('Select employee for the adjustment');
  const payload={employee_id:id,month:period,...Object.fromEntries(['bonus','reimbursements','extra_deductions','days_worked','payable_days'].map(k=>[k,number(adjust[k])])),tds_override:adjust.tds_override===''?null:number(adjust.tds_override),notes:adjust.notes||''};
  await go(()=>api(`/payroll-v2/adjustments/${id}/${period}`,'PUT',payload),'One-off adjustment recorded. Generate a new payroll draft for the period to include it.');
 }
 function editAdjustment(record:Item){
  setPeriod(record.month);
  setAdjust({employee_id:String(record.employee_id),bonus:record.bonus,reimbursements:record.reimbursements,
   extra_deductions:record.extra_deductions,days_worked:record.days_worked,payable_days:record.payable_days,
   tds_override:record.tds_override??'',notes:record.notes||''});
  setMessage(`Editing adjustment for ${record.employee_name} / ${record.month}. Save before generating a draft.`);setError('');
 }
  async function deletePayrollItem(kind:'package'|'adjustment'|'run',record:Item){
  const name=kind==='package'?`${record.employee_name} (${record.code})`:kind==='adjustment'?`${record.employee_name} / ${record.month}`:`${record.month} (${record.status})`;
  if(kind==='run'&&record.status==='Published')return setError('Published payroll statements are protected and cannot be deleted.');
  const what=kind==='package'?'salary package':kind==='adjustment'?'monthly adjustment':'unpublished payroll run';
  const consequences=kind==='package'?'Existing payroll snapshots and employee profiles will stay intact. Remove any monthly adjustments for this employee first.':kind==='adjustment'?'A payroll run for this month must be removed first. Other records will stay intact.':'All snapshot items in this unpublished payroll run will be removed. Salary packages and monthly adjustments will stay intact.';
  const reason=window.prompt(`DELETE ${what} for ${name}?\n${consequences}\n\nEnter a reason (at least 8 characters):`);
  if(reason===null)return;
  if(reason.trim().length<8)return setError('Deletion cancelled: enter a reason with at least 8 characters.');
  const confirm=window.prompt(`Final confirmation: type DELETE to permanently remove ${what} for ${name}.`);
  if(confirm!=='DELETE')return setError('Deletion cancelled: confirmation did not match DELETE.');
  const path=kind==='package'?`/payroll-v2/salary-packages/${record.employee_id}`:kind==='adjustment'?`/payroll-v2/adjustments/${record.employee_id}/${record.month}`:`/payroll-v2/runs/${record.id}`;
  const deleted=await go(()=>api(path,'DELETE',{confirm:'DELETE',reason:reason.trim()}),`${what} deleted successfully; payroll audit event recorded.`);
  if(!deleted)return;
  if(kind==='run'&&selected?.run?.id===record.id)setSelected(null);
  if(kind==='package'&&Number(form.employee_id)===record.employee_id)setForm(fresh);
  if(kind==='adjustment'&&Number(adjust.employee_id)===record.employee_id&&period===record.month)setAdjust(x=>({...x,employee_id:''}));
 }
  async function runDetail(id:number){setSelection(String(id));setError('');try{
  const [detail,history]=await Promise.all([api<Item>(`/payroll-v2/runs/${id}`),api<Item[]>(`/payroll-v2/runs/${id}/history`)]);
  setSelected(detail);setRunHistory(history);setRunQuery('');
 }catch(e){setError((e as Error).message)}}
 async function transition(action:'review'|'publish'){if(!selected)return;
  if(action==='review'&&!readyToReview)return setError('Complete all three review checks and enter a reason (8+ characters).');
  if(!window.confirm(action==='publish'?'Publish all payslips for this period to the employees? This cannot be undone. No payments will be sent.':'Confirm you have manually checked the payroll preview and want to mark it Reviewed?'))return;
  await go(()=>api(`/payroll-v2/runs/${selected.run.id}/transition`,'POST',{action,reviewed:true,note:action==='review'?reviewNote.trim():'Approved for release after prior review',checklist:action==='review'?reviewChecks:{}}),`Pay run ${action==='review'?'reviewed':'published'} successfully.`);await runDetail(selected.run.id);
 }
 async function correctRun(action:'recalculate'|'reopen'){
  if(!selected)return;
  const id=selected.run.id;
  const word=action==='recalculate'?'RECALCULATE':'REOPEN';
  const reason=window.prompt(action==='recalculate'?'This will REPLACE the current Draft snapshot with values from salary packages and monthly adjustments. It will not publish or pay anyone. Enter the correction reason (at least 8 characters):':'This will return the Reviewed run to Draft and remove its review status. Enter the reason (at least 8 characters):');
  if(reason===null)return;
  if(reason.trim().length<8)return setError('A correction reason with at least 8 characters is required.');
  if(window.prompt(`Type ${word} to confirm this payroll action.`)!==word)return setError('Confirmation did not match; no changes made.');
  const result=await go(()=>api(`/payroll-v2/runs/${id}/${action}`,'POST',{confirm:word,reason:reason.trim()}),
   action==='reopen'?'Reviewed payroll reopened as Draft.':'Draft recalculated. Inspect the new employee pay figures before review.');
  if(result){setReviewNote('');setReviewChecks({roster:false,adjustments:false,statutory:false});await runDetail(id)}
 }
 async function downloadOwn(month:string){
  try{const token=sessionStorage.getItem('sass_token');const response=await hrmFetch(API+`/payroll-v2/my-statements/${month}/export.csv`,{headers:{Authorization:`Bearer ${token}`}});
   if(!response.ok)throw Error('Only a published personal statement can be downloaded');
   const url=URL.createObjectURL(await response.blob());const a=document.createElement('a');a.href=url;a.download=`sass-own-pay-statement-${month}.csv`;a.click();window.setTimeout(()=>URL.revokeObjectURL(url),1000);
  }catch(e){setError((e as Error).message)}
 }
 async function csv(){if(!selected)return;try{setError('');const token=sessionStorage.getItem('sass_token');const r=await hrmFetch(API+`/payroll-v2/runs/${selected.run.id}/export.csv`,{headers:{Authorization:`Bearer ${token}`}});if(!r.ok)throw Error('Export failed');const b=await r.blob();const u=URL.createObjectURL(b);const a=document.createElement('a');a.href=u;a.download=`sass-payroll-${selected.run.month}.csv`;a.click();URL.revokeObjectURL(u)}catch(e){setError((e as Error).message)}}
 return <div className="pay-shell"><div className="pay-heading"><span className="pay-eyebrow">SASS HRM / FINANCE OPERATIONS</span><h1><ShieldCheck size={29}/> Payroll processing workbench</h1><p>India salary structures, estimated PF/ESI/TDS, immutable monthly snapshots, draft review and employee payslip publication.</p></div>
 <div className="pay-warning"><AlertTriangle size={20}/> Development payroll simulation only. Local eligibility, exemptions, state professional tax, tax declarations, PF/EPS splits and compliance filings require qualified payroll review. No payment integration exists.</div>
 <Message value={message}/><Message error value={error}/>
 {!isHR?<section className="pay-card"><h2>My published salary statements</h2><p className="pay-hint">Only your own published payroll workbench payslips are visible here.</p><DataGrid items={statements} keys={['month','currency','gross','employee_pf','employee_esi','income_tax_tds','deductions','net']}/>{statements.map(s=><details className="pay-details" key={s.month}><summary>{s.month} · Detailed pay statement (simulated)</summary><button className="pay-secondary pay-download-own" type="button" onClick={()=>downloadOwn(s.month)}><Download size={15}/> Download my statement CSV</button><div className="pay-statement"><div className="pay-statement-head"><strong>SASS INNOVATIONS · PAY STATEMENT</strong><span>{s.month} / {s.currency}</span></div><p><strong>{s.employee_name}</strong> · {s.code}</p><div className="pay-slip-rows">{[
 ['Basic salary (configured)',s.salary_components?.basic],['HRA (configured)',s.salary_components?.hra],['Allowance (configured)',s.salary_components?.allowance],
 ['Gross earned pay',s.gross],['Reimbursements',s.reimbursements],['Provident fund (employee)',s.employee_pf],
 ['ESI (employee)',s.employee_esi],['Professional tax',s.professional_tax],['Estimated TDS',s.income_tax_tds],
 ['Other deductions',s.other_deductions],['Total deductions',s.deductions],['Net simulated pay',s.net]
 ].map(([label,value])=><div key={label as string}><span>{label}</span><strong>{money(Number(value),s.currency)}</strong></div>)}</div><p className="pay-hint">This statement is a simulated estimate and does not prove payment, tax withholding or statutory compliance. Contact HR for an official payslip.</p></div></details>)}</section>:<>
 <section className="pay-card" aria-label="Payroll readiness and exceptions"><div className="pay-section-header"><div><h2><ClipboardCheck size={20}/> Payroll readiness <span className="pay-period">{period}</span></h2><p className="pay-hint">Check exclusions, adjustments and sample calculation before creating a draft. These are reference estimates, not a statutory sign-off.</p></div><button type="button" className="pay-secondary" onClick={()=>void refreshPreflight()}>Recheck readiness</button></div>
 {preflight?<><div className="pay-metrics"><div><span>Active employees</span><strong>{preflight.active_employee_count}</strong></div><div><span>Configured salary packages</span><strong>{preflight.configured_employee_count}</strong></div><div><span>Missing packages</span><strong>{preflight.missing_salary_package_count}</strong></div><div><span>Monthly adjustments</span><strong>{preflight.adjustment_count}</strong></div><div><span>Preview net total (not final)</span><strong>{money(preflight.totals?.net)}</strong></div></div>
 <p className="pay-hint">Draft readiness: <strong>{preflight.can_create_draft?'Ready to create':'Not ready or period already has a run'}</strong> · Payslip publishing {preflight.publication_enabled?'configured':'disabled until finance verification'}.</p>
 {previewIssues.length>0?<ul className="pay-preflight-list">{previewIssues.slice(0,25).map((issue:Item,i:number)=><li key={`${issue.code}-${i}`} className={`pay-preflight-${issue.level}`}><strong>{String(issue.level).toUpperCase()}</strong> {issue.message}{issue.employee_codes?.length?' · '+issue.employee_codes.join(', '):''}</li>)}{previewIssues.length>25&&<li>Additional issues not displayed. Check salary packages before proceeding.</li>}</ul>:<p className="pay-hint">No readiness issues found in this reference calculation.</p>}</>:<p className="pay-hint">The readiness preview is unavailable. Check the backend connection and period before generating payroll.</p>}
 </section>
 <section className="pay-card"><h2>1 · Salary structures <span className="pay-period">HR restricted</span></h2><p className="pay-hint">Enter monthly pay. PF and ESI apply only after eligibility verification; professional tax is a manually approved state-specific amount.</p><form onSubmit={saveSalary} className="pay-fields">
  <label>Employee<select required value={form.employee_id} onChange={e=>loadPackage(Number(e.target.value))}><option value="">Select employee</option>{people.map(p=><option key={p.id} value={p.id}>{p.name} · {p.code}</option>)}</select></label>
  {(['basic','hra','allowance','professional_tax','other_deductions','pf_cap'] as const).map(k=><label key={k}>{label(k)} (INR)<input type="number" required min="0" step="0.01" value={form[k]} onChange={e=>setForm(x=>({...x,[k]:e.target.value}))}/></label>)}
  <label>Income tax regime<select value={form.tax_regime} onChange={e=>setForm(x=>({...x,tax_regime:e.target.value}))}><option value="new">New tax regime</option><option value="old">Old tax regime</option></select></label>
  <label>TDS method<select value={form.tds_mode} onChange={e=>setForm(x=>({...x,tds_mode:e.target.value}))}><option value="estimate">Estimated from annual fixed salary</option><option value="manual">Manually reviewed monthly TDS</option></select></label>
  {form.tds_mode==='manual'&&<label>Manual monthly TDS (INR)<input type="number" min="0" required step="0.01" value={form.monthly_tds} onChange={e=>setForm(x=>({...x,monthly_tds:e.target.value}))}/></label>}
  <label className="pay-check"><input type="checkbox" checked={!!form.pf_enabled} onChange={e=>setForm(x=>({...x,pf_enabled:e.target.checked}))}/> PF eligible / apply example 12% employee rate</label>
  <label className="pay-check"><input type="checkbox" checked={!!form.esi_enabled} onChange={e=>setForm(x=>({...x,esi_enabled:e.target.checked}))}/> ESI eligible / apply example 0.75% employee rate</label>
  {esiReviewRequired&&<div className="pay-esi-review" role="status">
   <strong>ESI eligibility review required · wages above ₹21,000</strong>
   <span>Do not assume ESI coverage has ended: existing insured employees may remain covered through the contribution period, and a ₹25,000 threshold can apply to persons with disabilities. Consult a qualified payroll specialist before changing deductions.</span>
   {form.esi_enabled?<button type="button" className="pay-secondary" disabled={busy} onClick={markEsiPendingReview}>Turn ESI off pending assessment (form only)</button>:<span>ESI is unchecked in this form. Save the salary package only after confirming the correct treatment for this employee.</span>}
  </div>}
  <button type="submit" className="pay-primary" disabled={busy||!form.employee_id}>Save salary package</button></form>
  <h3>Configured salary packages</h3><p className="pay-hint">Delete removes only the active package, never historical payroll snapshots. Remove this employee's adjustments first.</p>
  <div className="pay-table"><table><thead><tr>{['employee_name','basic','hra','allowance','tax_regime','tds_mode','pf_enabled','esi_enabled'].map(k=><th key={k}>{label(k)}</th>)}<th>Actions</th></tr></thead><tbody>{packages.map(p=><tr key={p.employee_id}>{['employee_name','basic','hra','allowance','tax_regime','tds_mode','pf_enabled','esi_enabled'].map(k=><td key={k}>{['basic','hra','allowance'].includes(k)?money(p[k]):String(p[k]??'—')}</td>)}<td><button type="button" className="pay-danger" disabled={busy} onClick={()=>deletePayrollItem('package',p)} aria-label={`Delete salary package for ${p.employee_name}`}><Trash2 size={15}/> Delete</button></td></tr>)}</tbody></table>{!packages.length&&<div className="pay-empty">No salary packages yet.</div>}</div></section>
 <section className="pay-card"><h2>2 · Monthly adjustments &amp; attendance corrections</h2><p className="pay-hint">Bonuses, expense reimbursements, pay-day proration and manual withholding overrides for an employee in the selected month. If a Draft exists, save changes and then click Recalculate draft before review.</p>
  <form className="pay-fields" onSubmit={saveAdjustment}><label>Employee<select required value={adjust.employee_id} onChange={e=>setAdjust(x=>({...x,employee_id:e.target.value}))}><option value="">Select employee</option>{packages.map(p=><option key={p.employee_id} value={p.employee_id}>{p.employee_name}</option>)}</select></label>
  {(['bonus','reimbursements','extra_deductions','days_worked','payable_days'] as const).map(k=><label key={k}>{label(k)}<input type="number" required min="0" max={k==='days_worked'||k==='payable_days'?31:10000000} step={k.includes('days')?1:'0.01'} value={adjust[k]} onChange={e=>setAdjust(x=>({...x,[k]:e.target.value}))}/></label>)}
  <label>Manual TDS override (blank = use package)<input type="number" min="0" step="0.01" value={adjust.tds_override} onChange={e=>setAdjust(x=>({...x,tds_override:e.target.value}))}/></label><label>Adjustment reason<input maxLength={300} value={adjust.notes} onChange={e=>setAdjust(x=>({...x,notes:e.target.value}))}/></label>
  <button type="submit" className="pay-primary" disabled={busy||!adjust.employee_id}>Save period adjustment</button></form>
  <div className="pay-table"><table><thead><tr>{['employee_name','month','bonus','reimbursements','extra_deductions','days_worked','payable_days','tds_override'].map(k=><th key={k}>{label(k)}</th>)}<th>Actions</th></tr></thead><tbody>{adjustments.filter(a=>a.month===period).map(a=><tr key={a.id}>{['employee_name','month','bonus','reimbursements','extra_deductions','days_worked','payable_days','tds_override'].map(k=><td key={k}>{String(a[k]??'—')}</td>)}<td><div className="pay-row-actions"><button type="button" className="pay-secondary" disabled={busy||runs.some(r=>r.month===a.month&&r.status!=='Draft')} onClick={()=>editAdjustment(a)}>Edit</button><button type="button" className="pay-danger" disabled={busy||runs.some(r=>r.month===a.month&&r.status!=='Draft')} title={runs.some(r=>r.month===a.month&&r.status!=='Draft')?'Reopen the reviewed pay run before changing adjustments; published runs are immutable.':'Remove adjustment'} onClick={()=>deletePayrollItem('adjustment',a)}><Trash2 size={15}/> Delete</button></div></td></tr>)}</tbody></table>{!adjustments.some(a=>a.month===period)&&<div className="pay-empty">No adjustments for the selected month.</div>}</div></section>
  <section className="pay-card"><h2>3 · Create monthly payroll snapshot</h2><p className="pay-hint">Tax year supported: April 2026 through March 2027. Each period can be created once. No silent salary changes to historical runs.</p><div className="pay-inline"><label>Payroll month<input type="month" min="2026-04" max="2027-03" value={period} onChange={e=>{const next=e.target.value;setPeriod(next);setAdjust(a=>({...a,days_worked:periodDays(next),payable_days:periodDays(next)}))}}/></label><button className="pay-primary" disabled={busy} onClick={()=>go(()=>api('/payroll-v2/runs','POST',{month:period}),'Draft payroll created. Review the breakdown before publishing.')}>Create draft</button></div>
  <div className="pay-table"><table><thead><tr><th>Month</th><th>Status</th><th>Employees</th><th>Actions</th></tr></thead><tbody>{runs.map(r=><tr key={r.id}><td>{r.month}</td><td>{r.status}</td><td>{r.employee_count}</td><td><div className="pay-row-actions"><button type="button" className="pay-secondary" onClick={()=>runDetail(r.id)}>Inspect run</button>{r.status!=='Published'&&<button type="button" className="pay-danger" disabled={busy} onClick={()=>deletePayrollItem('run',r)} aria-label={`Delete ${r.status} payroll run for ${r.month}`}><Trash2 size={15}/> Delete</button>}</div></td></tr>)}</tbody></table>{!runs.length&&<div className="pay-empty">No runs created yet.</div>}</div></section>
 {selected&&<section className="pay-card"><h2>4 · Review payslips <span className="pay-period">{selected.run.month} · {selected.run.status}</span></h2><div className="pay-metrics"><div><span>Gross pay</span><strong>{money(selected.totals?.gross)}</strong></div><div><span>Deductions</span><strong>{money(selected.totals?.deductions)}</strong></div><div><span>Net pay</span><strong>{money(selected.totals?.net)}</strong></div><div><span>Employer cost estimate</span><strong>{money(selected.totals?.employer_total_estimate)}</strong></div></div>
  {selected.draft_out_of_date&&<div className="pay-warning" role="alert"><AlertTriangle size={18}/> Payroll inputs have changed since this snapshot. Reopen if reviewed, then recalculate before review or publication.</div>}
  <div className="pay-toolbar"><label className="pay-filter"><Search size={17}/><input type="search" placeholder="Find employee code or name in this run" value={runQuery} onChange={e=>setRunQuery(e.target.value)}/></label><span className="pay-hint">{(selected.items||[]).length} employees in snapshot</span></div>
  <DataGrid items={(selected.items||[]).filter((i:Item)=>`${i.code} ${i.employee_name}`.toLowerCase().includes(runQuery.toLowerCase().trim()))} keys={['code','employee_name','gross','employee_pf','employee_esi','professional_tax','income_tax_tds','deductions','net']}/>
  {selected.comparison_period&&<details className="pay-details" open={selected.flagged_variance_count>0}><summary>Net pay variance against published {selected.comparison_period} · {selected.flagged_variance_count} flagged</summary><p className="pay-hint">Flagged when change exceeds both 20% and ₹1,000; newly included employees are flagged. Investigate before review.</p><DataGrid items={selected.variance||[]} keys={['code','employee_name','prior_net','current_net','difference','change_percent','reason']}/></details>}
  {selected.run.status==='Draft'&&<section className="pay-review-panel"><h3>HR review checklist</h3><p className="pay-hint">Complete every check and record a reason before marking the payroll run Reviewed.</p>
   {([['roster','Employee roster and excluded employees checked'],['adjustments','Attendance, leave and monthly adjustments checked'],['statutory','PF, ESI, professional tax and TDS reviewed by qualified payroll staff']] as const).map(([k,v])=><label className="pay-review-check" key={k}><input type="checkbox" checked={reviewChecks[k]} onChange={e=>setReviewChecks(old=>({...old,[k]:e.target.checked}))}/>{v}</label>)}
   <label className="pay-review-note">Review note / evidence<input maxLength={500} value={reviewNote} onChange={e=>setReviewNote(e.target.value)} placeholder="Reason and key checks (minimum 8 characters)"/></label>
  </section>}

  <div className="pay-actions"><button className="pay-secondary" onClick={csv}><Download size={15}/> Export CSV</button>{selected.run.status==='Draft'&&<button className="pay-secondary" disabled={busy} onClick={()=>correctRun('recalculate')}><RotateCcw size={15}/> Recalculate draft</button>}{selected.run.status==='Reviewed'&&<button className="pay-secondary" disabled={busy} onClick={()=>correctRun('reopen')}><RotateCcw size={15}/> Reopen for corrections</button>}{selected.run.status==='Draft'&&<button disabled={busy||!readyToReview||!!selected.draft_out_of_date} className="pay-primary" onClick={()=>transition('review')}><FileCheck2 size={16}/> Mark reviewed</button>}{selected.run.status==='Reviewed'&&<button disabled={busy} className="pay-primary" onClick={()=>transition('publish')}>Publish employee statements</button>}</div>
  <p className="pay-hint">{selected.run.status==='Published'?'Published statements are visible to each employee.':'Draft and reviewed statements are only visible to HR.'} Publishing does not transfer money or file government returns.</p>
  <details className="pay-details"><summary><History size={16}/> Payroll run review and correction history</summary><div className="pay-table"><table><thead><tr><th>Time (UTC)</th><th>Action</th><th>HR actor</th><th>Recorded note</th></tr></thead><tbody>{runHistory.map(row=><tr key={row.id}><td>{row.created_at}</td><td>{row.action}</td><td>{row.actor_name||row.actor_id}</td><td className="pay-note-cell">{row.note||'—'}</td></tr>)}</tbody></table>{!runHistory.length&&<div className="pay-empty">No history entries are available for this run.</div>}</div></details></section>}
 </>}
 </div>;
}
