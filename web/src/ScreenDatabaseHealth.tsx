import {useMemo,useState} from 'react';
import {AlertTriangle,CheckCircle2,Database,ExternalLink,RefreshCcw,Search,Settings2,ShieldCheck} from 'lucide-react';
import {hrmFetch} from './apiTransport';
import './screen-database-health.css';

type ScreenCheck={feature_key:string;feature_name:string;feature_url:string;domain:string;settings_page:string;
 representative_route:string;api_registered:boolean;key_tables:string[];missing_tables:string[];
 table_access_failures:string[];state:string;end_to_end_verified:false};
type Report={engine:string;live_mysql_inspected:boolean;table_access_probed:boolean;schema_complete:boolean|null;
 screen_count:number;api_routes_registered:number;structural_matches:number;missing_api_count:number;
 missing_table_screen_count:number;end_to_end_verified_count:number;note:string;screens:ScreenCheck[]};
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
const statusText:Record<string,string>={
 structural_match:'API and key tables accessible',
 tables_present_not_probed:'API and key tables present · access not tested',
 missing_api:'Representative API not registered',
 missing_tables:'Required key table missing',
 table_access_failed:'Key table access blocked',
 not_live_verified:'Live MySQL not checked',
 no_table_mapping:'API exists · no persisted table mapped',
};
const issue=(state:string)=>['missing_api','missing_tables','table_access_failed'].includes(state);

export function ScreenDatabaseHealth({navigate}:{navigate:(page:string)=>void}){
 const [report,setReport]=useState<Report|null>(null);
 const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 const [query,setQuery]=useState('');const [domain,setDomain]=useState('all');
 const [onlyIssues,setOnlyIssues]=useState(false);
 const domains=useMemo(()=>Array.from(new Set(report?.screens.map(s=>s.domain)||[])).sort(),[report]);
 const visible=useMemo(()=>report?.screens.filter(s=>
    (domain==='all'||s.domain===domain)&&(!onlyIssues||issue(s.state))&&
    [s.feature_name,s.domain,s.representative_route,...s.key_tables].join(' ').toLowerCase().includes(query.toLowerCase()))||[],
    [report,domain,onlyIssues,query]);
 const verify=async(probe:boolean)=>{
   setBusy(true);setError('');
   try{const token=sessionStorage.getItem('sass_token');
     const response=await hrmFetch(`${API}/admin/database/screen-integrations?probe_tables=${probe}`,{
       headers:token?{Authorization:`Bearer ${token}`}:{}});
     const value=await response.json().catch(()=>({}));
     if(!response.ok)throw Error(typeof value.detail==='string'?value.detail:`Database check failed (HTTP ${response.status})`);
     setReport(value as Report);
   }catch(e){setError((e as Error).message)}finally{setBusy(false)}
 };
 return <section className="sdh-wrapper" aria-labelledby="sdh-title">
   <header className="sdh-header"><div><h2 id="sdh-title"><Database size={20}/> Feature-to-database health</h2><p>Check 73 screens against their registered API and key MySQL tables. This is a read-only structural inspection, not an end-to-end save/edit/delete test.</p></div><div className="sdh-actions"><button disabled={busy} onClick={()=>void verify(false)}><RefreshCcw size={15}/>{busy?'Checking…':'Check schema'}</button><button disabled={busy} className="sdh-primary" onClick={()=>void verify(true)}><ShieldCheck size={15}/> Check table access</button></div></header>
   {error&&<p className="sdh-error" role="alert"><AlertTriangle size={16}/>{error}</p>}
   {report&&<><div className="sdh-stats"><div><strong>{report.screen_count}</strong><span>Screens mapped</span></div><div><strong>{report.api_routes_registered}</strong><span>Representative APIs registered</span></div><div><strong>{report.live_mysql_inspected?(report.table_access_probed?report.structural_matches:'—'):'—'}</strong><span>Key tables accessible</span></div><div><strong>{report.end_to_end_verified_count}</strong><span>Full workflows verified</span></div></div>
    <div className="sdh-caution"><AlertTriangle size={17}/><span><strong>{report.live_mysql_inspected?'MySQL structure inspected':'Not a live MySQL verification'}.</strong> Engine: {report.engine}. {report.table_access_probed?'Zero-row table access checks were run.':'Table access checks not run.'} All workflow write/persistence checks remain outstanding.</span></div>
    <div className="sdh-filters"><label><Search size={15}/> <input aria-label="Search feature or database table" type="search" placeholder="Search feature, endpoint or table" value={query} onChange={e=>setQuery(e.target.value)}/></label><select aria-label="Filter feature domain" value={domain} onChange={e=>setDomain(e.target.value)}><option value="all">All workstreams</option>{domains.map(d=><option key={d} value={d}>{d}</option>)}</select><label className="sdh-only"><input type="checkbox" checked={onlyIssues} onChange={e=>setOnlyIssues(e.target.checked)}/> Show structural issues only</label></div>
    <div className="sdh-scroller"><table className="sdh-table"><thead><tr><th>Feature</th><th>Representative API</th><th>Key tables</th><th>Structure status</th><th>Manage</th></tr></thead><tbody>{visible.map(s=><tr key={s.feature_key}><td><strong>{s.feature_name}</strong><small>{s.domain}</small></td><td><code>{s.representative_route}</code></td><td><small>{s.key_tables.join(', ')||'Not mapped (no storage contract)'}</small>{s.missing_tables.length>0&&<small className="sdh-problem">Missing: {s.missing_tables.join(', ')}</small>}{s.table_access_failures.length>0&&<small className="sdh-problem">Access denied: {s.table_access_failures.join(', ')}</small>}</td><td><span className={`sdh-status ${issue(s.state)?'sdh-bad':s.state==='structural_match'?'sdh-ok':'sdh-neutral'}`}>{issue(s.state)?<AlertTriangle size={13}/>:s.state==='structural_match'?<CheckCircle2 size={13}/>:null}{statusText[s.state]||s.state}</span></td><td><div className="sdh-links"><button onClick={()=>navigate(s.feature_key)}>Open <ExternalLink size={13}/></button>{s.settings_page&&s.settings_page!==s.feature_key&&<button onClick={()=>navigate(s.settings_page)}><Settings2 size={13}/> Settings</button>}</div></td></tr>)}</tbody></table>{!visible.length&&<p className="sdh-empty">No feature checks match the filters.</p>}</div>
    <p className="sdh-footnote">{report.note}</p>
   </>}
   {!report&&!error&&<p className="sdh-footnote">Use “Check schema” to see actual server results, or “Check table access” to additionally test SELECT permission for schema tables. Neither command changes employee data.</p>}
  </section>
}
