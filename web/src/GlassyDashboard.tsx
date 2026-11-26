import {useCallback,useEffect,useId,useState} from 'react';
import type {ReactNode} from 'react';
import {Activity,ArrowRight,ArrowUpRight,BarChart3,Building2,CalendarDays,CalendarCheck2,ChartNoAxesCombined,Clock3,Download,FolderKanban,GraduationCap,Headphones,LayoutDashboard,Megaphone,Package,ShieldCheck,Sparkles,UsersRound} from 'lucide-react';
import {useRefreshData} from './useRefreshData';
import './glassy-dashboard.css';

type Row=Record<string,any>;
type Tab='overview'|'companies'|'reports'|'support'|'products'|'projects';
type Series={label:string;value:number}[];
type Case={id:number;kind:'ticket'|'request';subject:string;category_name?:string;status:string};
type CaseResult={items:Case[];has_more:boolean;summary:{total:number;completed:number;tickets:number}};
type Props={
 name:string; organization:string; role:string; loading:boolean;
 data:Record<string,Row[]>; failures:string[]; report:Row|null; today:string;
 navigate:(key:string)=>void; api:<T>(path:string)=>Promise<T>;
 applyLeave:()=>void; createTicket:()=>void; exportDepartments:()=>void;
 formatDate:(s:string)=>string;
};
const tabs=[{key:'overview',label:'Overview',Icon:LayoutDashboard},{key:'companies',label:'Companies',Icon:Building2},{key:'reports',label:'Reports',Icon:ChartNoAxesCombined},{key:'support',label:'Support',Icon:Headphones},{key:'products',label:'Products',Icon:Package},{key:'projects',label:'Projects',Icon:FolderKanban}] as const;
const count=(v:number|null|undefined)=>v==null?'—':v.toLocaleString('en-IN');
const month=(s:string)=>new Date(s+'-01T12:00:00').toLocaleDateString('en-IN',{month:'short'});
function Panel({title,desc,action,children}:{title:string;desc:string;action?:ReactNode;children:ReactNode}){
 return <section className="gd-panel"><div className="gd-panel-head"><div><h2>{title}</h2><p>{desc}</p></div>{action}</div>{children}</section>
}
function Action({children,onClick,primary=false}:{children:ReactNode;onClick:()=>void;primary?:boolean}){
 return <button type="button" className={primary?'gd-action gd-primary':'gd-action'} onClick={onClick}>{children}</button>
}
function Metric({label,value,note,tone,children,onClick}:{label:string;value:number|null|string|undefined;note:string;tone:string;children:ReactNode;onClick:()=>void}){
 return <button type="button" className={`gd-metric gd-${tone}`} onClick={onClick}><span className="gd-metric-top"><span>{label}</span><i aria-hidden="true">{children}</i></span><strong>{typeof value==='string'?value:count(value)}</strong><small>{note} <ArrowUpRight size={13} aria-hidden="true"/></small></button>
}
function Empty({children}:{children:ReactNode}){return <p className="gd-empty">{children}</p>}
function Bars({series,ready,empty}:{series:Series;ready:boolean;empty:string}){
 if(!ready||!series.length)return <Empty>{empty}</Empty>;
 const max=Math.max(1,...series.map(s=>s.value));
 return <div className="gd-bars">{series.map(s=><div key={s.label}><span>{s.label}</span><div className="gd-rail" aria-hidden="true"><i style={{width:`${s.value/max*100}%`}}/></div><b>{count(s.value)}</b></div>)}</div>
}
function Trend({series,ready}:{series:Series;ready:boolean}){
 const id=useId();
 if(!ready||!series.length)return <Empty>Trend data is not available yet.</Empty>;
 const max=Math.max(1,...series.map(s=>s.value));
 const xy=series.map(({value},i)=>[22+i*356/Math.max(1,series.length-1),116-value/max*98]);
 const points=xy.map(([x,y])=>`${x},${y}`).join(' ');
 return <figure className="gd-trend"><svg viewBox="0 0 400 132" aria-hidden="true"><defs><linearGradient id={id} x1="0" y1="0" x2="0" y2="1" gradientUnits="objectBoundingBox"><stop stopColor="#8c7dff" stopOpacity=".55"/><stop offset="1" stopColor="#8c7dff" stopOpacity=".03"/></linearGradient></defs>
 {[18,50,83,116].map(y=><line key={y} x1="22" x2="378" y1={y} y2={y} stroke="#d7dcfc" strokeOpacity=".16" strokeDasharray="4 5"/>)}
 <polygon points={`22,116 ${points} 378,116`} fill={`url(#${id})`}/><polyline points={points} fill="none" stroke="#a79aff" strokeWidth="3" strokeLinejoin="round"/>
 {xy.map(([x,y],i)=><circle key={i} cx={x} cy={y} r="4" fill="#ddd8ff" stroke="#7a68ee" strokeWidth="2"/>)}</svg>
 <figcaption>{series.map(s=><span key={s.label}><b>{s.value}</b>{s.label}</span>)}</figcaption></figure>
}
const caseStates=['all','active','completed'] as const;
export default function GlassyDashboard(p:Props){
 const [tab,setTab]=useState<Tab>('overview');
 const [period,setPeriod]=useState(6);
 const [seriesKey,setSeriesKey]=useState<'headcount'|'approved_leave'|'approved_claims'>('headcount');
 const [caseState,setCaseState]=useState<typeof caseStates[number]>('all');
 const [cases,setCases]=useState<CaseResult|null>(null);
 const [caseStatus,setCaseStatus]=useState<'loading'|'ready'|'error'>('loading');
 const [retry,setRetry]=useState(0);
 const [assetFilter,setAssetFilter]=useState('all');
 const refreshCases=useCallback(()=>setRetry(x=>x+1),[]);
 useRefreshData(refreshCases);
 useEffect(()=>{
  if(tab!=='support')return;
  let active=true;
  setCaseStatus('loading');setCases(null);
  p.api<CaseResult>(`/service-center/cases?limit=5&include_summary=true&state=${caseState}`)
  .then(data=>{if(active){setCases(data);setCaseStatus('ready')}})
  .catch(()=>{if(active)setCaseStatus('error')});
  return ()=>{active=false}
 },[p.api,caseState,tab,retry]);
 function selectTab(key:Tab){setTab(key);if(key==='support'){setCases(null);setCaseStatus('loading')}}
 const admin=p.role==='admin',manager=p.role!=='employee';
 const go=(key:string)=>()=>p.navigate(key);
 const configured=(key:string)=>Object.hasOwn(p.data,key)&&!p.failures.includes(key);
 const rows=(key:string)=>{const value=p.data?.[key];return Array.isArray(value)?value.filter((row):row is Row=>!!row&&typeof row==='object'):[]};
 const total=(key:string,test?:(row:Row)=>boolean)=>configured(key)?(test?rows(key).filter(test).length:rows(key).length):null;
 const reportReady=!!p.report&&!p.failures.includes('reports');
 const trend=rows('trends').slice(-period).map(r=>({label:month(r.month),value:Number(r[seriesKey])}));
 const scope=admin?'Organization view':manager?'Manager view':'Employee view';
 const departments=(p.report?.departments||[]).map((r:Row)=>({label:String(r.name||'Unassigned'),value:Number(r.value)})) as Series;
 const assets=rows('assets').filter(r=>assetFilter==='all'||r.status===assetFilter);
 const dayPart=new Date().getHours()<12?'morning':new Date().getHours()<17?'afternoon':'evening';
 const summaries:Record<Tab,{title:string;subtitle:string}>={
  overview:{title:`Good ${dayPart}${p.name?', '+p.name.split(' ')[0]:''}`,subtitle:'Your people, work and services in one place.'},
  companies:{title:'Companies',subtitle:'Your organization, departments and reporting structure.'},
  reports:{title:'Reports',subtitle:'Workforce trends and department headcount in your reporting scope.'},
  support:{title:'Support',subtitle:'Helpdesk tickets and service requests in one queue.'},
  products:{title:admin?'Products & equipment':'Work equipment',subtitle:admin?'Open the product catalog or review the separate equipment register.':'Work equipment assigned to you and its current status.'},
  projects:{title:'Projects',subtitle:'Project records, ownership and time tracking.'},
 };
 return <div className="gd" aria-label="SASS HRM dashboard">
  <div className="gd-mast"><div className="gd-brand"><i><Activity size={18}/></i><div><b>SASS HRM</b><small>{p.organization}</small></div></div><span className="gd-scope"><ShieldCheck size={15}/>{scope}</span></div>
  <nav className="gd-tabs" aria-label="Dashboard sections">{tabs.filter(x=>x.key!=='reports'||manager).map(({key,label,Icon})=><button type="button" key={key} aria-pressed={tab===key} onClick={()=>{if(tab!==key)selectTab(key)}}><Icon size={17}/>{label}</button>)}</nav>
  <div className="gd-hero">
   <div><span className="gd-kicker"><i/> PEOPLE OPERATIONS / {tab.toUpperCase()}</span><h1>{summaries[tab].title}</h1><p>{summaries[tab].subtitle}</p></div>
   <div className="gd-actions">
    {tab==='overview'&&<><Action primary onClick={()=>p.navigate('assistant')}><Sparkles size={16}/> Ask SASS AI</Action><Action onClick={p.applyLeave}><CalendarDays size={16}/> Apply for leave</Action></>}
    {tab==='companies'&&<><Action primary onClick={go('organization')}><Building2 size={16}/> Open organization</Action>{admin&&<Action onClick={go('orgsettings')}>Organization settings <ArrowRight size={16}/></Action>}</>}
    {tab==='reports'&&<Action primary onClick={p.exportDepartments}><Download size={16}/> Export department CSV</Action>}
    {tab==='support'&&<><Action primary onClick={p.createTicket}>New ticket <ArrowUpRight size={16}/></Action><Action onClick={()=>p.navigate('requestdesk')}>Open HR Service Center <ArrowRight size={16}/></Action></>}
    {tab==='products'&&<>{admin&&<Action primary onClick={go('products')}><Package size={16}/> Open product catalog</Action>}<Action primary={!admin} onClick={go('assets')}><Package size={16}/> Open asset register</Action></>}
    {tab==='projects'&&<>{admin&&<Action primary onClick={go('projects')}><FolderKanban size={16}/> Open project register</Action>}<Action primary={!admin} onClick={go('timesheets')}><Clock3 size={16}/> Open project timesheets</Action></>}
   </div>
  </div>
  {tab==='overview'&&<>
   <div className="gd-metrics">
    <Metric label={manager?'Workforce':'My profile'} value={manager?(reportReady?p.report?.stats?.employees:null):'Active'} note={manager?'People in reporting scope':'Your workspace account'} tone="violet" onClick={go(manager?'employees':'profile')}><UsersRound size={18}/></Metric>
    <Metric label="Present today" value={total('attendance',r=>r.day===p.today&&r.status==='Present')} note="From attendance records" tone="mint" onClick={go('attendance')}><Clock3 size={18}/></Metric>
    <Metric label="Pending leave" value={total('leave',r=>r.status==='Pending')} note="Requests awaiting a decision" tone="amber" onClick={go('leave')}><CalendarDays size={18}/></Metric>
    <Metric label={manager?'Open jobs':'My learning'} value={manager?total('jobs',r=>r.status==='Open'):total('enrollments',r=>r.status!=='Completed')} note={manager?'Open recruiting roles':'Active enrollments'} tone="blue" onClick={go(manager?'recruitment':'training')}>{manager?<BarChart3 size={18}/>:<GraduationCap size={18}/>}</Metric>
   </div>
   <div className="gd-grid"><Panel title="Announcements" desc="News from your people team" action={<Action onClick={go('organization')}><Megaphone size={14}/> Announcements</Action>}><div className="gd-list">{configured('announcements')&&rows('announcements').length?rows('announcements').slice(0,3).map(r=><div key={r.id}><div><b>{r.title}</b><small>{r.body}</small></div><span>{p.formatDate(r.created_at)}</span></div>):<Empty>{configured('announcements')?'No announcements published yet.':'Announcements are not available yet.'}</Empty>}</div></Panel>
   <Panel title="Quick actions" desc="Jump straight into a workflow"><div className="gd-links">{[
    {name:'Employee HRIS',key:'employees',Icon:UsersRound},{name:'Time & attendance',key:'attendance',Icon:Clock3},{name:'Learning & training',key:'training',Icon:GraduationCap},{name:'Career development',key:'career',Icon:ChartNoAxesCombined},
   ].map(({name,key,Icon})=><button type="button" key={key} onClick={()=>p.navigate(key)}><Icon size={16}/>{name}<ArrowUpRight size={15}/></button>)}</div></Panel></div>
   <div className="gd-grid"><Panel title="Upcoming holidays" desc="Published dates" action={<Action onClick={()=>p.navigate('calendar')}>My calendar <ArrowRight size={14}/></Action>}><div className="gd-list">{configured('holidays')&&rows('holidays').some(r=>r.day>=p.today)?[...rows('holidays')].filter(r=>r.day>=p.today).sort((a,b)=>String(a.day||'').localeCompare(String(b.day||''))).slice(0,3).map(r=><div key={r.id}><b>{r.name}</b><span>{p.formatDate(r.day)}</span></div>):<Empty>{configured('holidays')?'No upcoming holidays are published.':'Holiday data is not available yet.'}</Empty>}</div></Panel>
   <Panel title="Recent activity" desc="Leave requests and helpdesk tickets" action={<Action onClick={()=>selectTab('support')}>Support <ArrowRight size={14}/></Action>}><div className="gd-list">{[...(configured('leave')?rows('leave').slice(0,2).map(r=>({key:'l'+r.id,title:r.leave_type,status:r.status,route:'leave'})):[]),...(configured('tickets')?rows('tickets').slice(0,2).map(r=>({key:'t'+r.id,title:r.subject,status:r.status,route:'helpdesk'})):[])].map(r=><button type="button" className="gd-row-link" key={r.key} onClick={go(r.route)}><b>{r.title}</b><span className="gd-chip">{r.status}</span></button>)}{!(configured('leave')&&rows('leave').length)&&!(configured('tickets')&&rows('tickets').length)&&<Empty>{configured('leave')&&configured('tickets')?'No recent activity.':'Some activity sources are not available yet.'}</Empty>}</div></Panel></div>
  </>}
  {tab==='companies'&&<>
   <div className="gd-metrics">
    <Metric onClick={go('organization')} label="Organization" value="1" note={p.organization} tone="violet"><Building2 size={18}/></Metric>
    <Metric onClick={go('organization')} label="Departments" value={total('departments')} note="Published department records" tone="mint"><BarChart3 size={18}/></Metric>
    <Metric onClick={go('orgchart')} label="Directory entries" value={total('orgChart')} note="People in the organization chart" tone="amber"><UsersRound size={18}/></Metric>
    <Metric onClick={go('organization')} label="Department locations" value={configured('departments')?new Set(rows('departments').map(r=>r.location).filter(Boolean)).size:null} note="Unique published locations" tone="blue"><Building2 size={18}/></Metric>
   </div>
   <div className="gd-grid"><Panel title="Department directory" desc="Department and office information" action={<Action onClick={()=>p.navigate('orgchart')}>Org chart <ArrowRight size={14}/></Action>}><div className="gd-list">{configured('departments')&&rows('departments').length?rows('departments').slice(0,6).map(r=><div key={r.id}><b>{r.name}</b><span>{r.location||'Location not recorded'}</span></div>):<Empty>{configured('departments')?'No departments are configured.':'Department data is not available yet.'}</Empty>}</div></Panel>
   <Panel title={manager?'Headcount by department':'Organization links'} desc={manager?'Counts from your reporting scope':'Explore your workplace'}>
    {manager?<Bars series={departments.slice(0,8)} ready={reportReady} empty={reportReady?'No headcount data in this scope.':'Department headcount is not available yet.'}/>:<div className="gd-links"><button type="button" onClick={()=>p.navigate('employees')}><UsersRound size={16}/> Employee directory <ArrowUpRight size={15}/></button><button type="button" onClick={()=>p.navigate('policies')}><ShieldCheck size={16}/> Policies & handbook <ArrowUpRight size={15}/></button></div>}
   </Panel></div>
  </>}
  {tab==='reports'&&manager&&<>
   <div className="gd-metrics">{[{key:'employees',route:'employees',label:'Headcount',Icon:UsersRound,tone:'violet'},{key:'pending_leave',route:'leave',label:'Pending leave',Icon:CalendarDays,tone:'amber'},{key:'active_jobs',route:'recruitment',label:'Open jobs',Icon:BarChart3,tone:'mint'},{key:'learning_enrollments',route:'training',label:'Learning enrollments',Icon:GraduationCap,tone:'blue'}].map(({key,label,Icon,tone,route})=>
    <Metric onClick={go(route)} key={key} label={label} value={reportReady?p.report?.stats?.[key]:null} note="From the reports service" tone={tone}><Icon size={18}/></Metric>)}</div>
   <div className="gd-grid"><Panel title="Workforce trends" desc="Monthly figures from your reporting scope" action={<Action onClick={go(seriesKey==='approved_leave'?'leave':seriesKey==='approved_claims'?'expenses':'employees')}>Open source module <ArrowRight size={14}/></Action>}><div className="gd-filters">
    <label>Metric<select value={seriesKey} onChange={e=>setSeriesKey(e.target.value as typeof seriesKey)}><option value="headcount">Active headcount</option><option value="approved_leave">Approved leave</option><option value="approved_claims">Approved claims</option></select></label>
    <label>Period<select value={period} onChange={e=>setPeriod(Number(e.target.value))}><option value={3}>3 months</option><option value={6}>6 months</option></select></label></div><Trend series={trend} ready={configured('trends')}/></Panel>
   <Panel title="Headcount by department" desc="Top departments in your reporting scope" action={<Action onClick={()=>p.navigate('reports')}>Full reports <ArrowRight size={14}/></Action>}><Bars series={departments.slice(0,8)} ready={reportReady} empty={reportReady?'No headcount data in this scope.':'Department headcount is not available yet.'}/></Panel></div>
  </>}
  {tab==='support'&&<>
   <div className="gd-metrics">
    <Metric onClick={go('requestdesk')} label="All cases" value={cases?.summary?.total} note="Tickets and service requests" tone="violet"><Headphones size={18}/></Metric>
    <Metric onClick={go('requestdesk')} label="Active cases" value={cases?.summary?cases.summary.total-cases.summary.completed:null} note="Awaiting completion" tone="amber"><Clock3 size={18}/></Metric>
    <Metric onClick={go('requestdesk')} label="Completed cases" value={cases?.summary?.completed} note="Resolved or finalized" tone="mint"><CalendarCheck2 size={18}/></Metric>
    <Metric onClick={go('helpdesk')} label="Helpdesk tickets" value={cases?.summary?.tickets} note="Tickets in your scope" tone="blue"><Activity size={18}/></Metric>
   </div>
   <div className="gd-grid"><Panel title="Recent service cases" desc={admin?'Organization tickets and requests':'Your own tickets and requests'} action={<Action onClick={go('requestdesk')}><Headphones size={14}/> Service Center</Action>}>
   <div className="gd-filters"><label>Status<select aria-label="Status" value={caseState} onChange={e=>{setCases(null);setCaseStatus('loading');setCaseState(e.target.value as typeof caseState)}}><option value="all">All cases</option><option value="active">Active</option><option value="completed">Completed</option></select></label></div>
   <div className="gd-list" aria-live="polite">{caseStatus==='loading'?<Empty>Loading support cases…</Empty>:caseStatus==='error'?<Empty>Support cases could not load. <Action onClick={refreshCases}>Retry</Action></Empty>:cases?.items?.length?cases.items.filter(Boolean).map(c=><button className="gd-row-link" type="button" key={c.kind+c.id} onClick={go(c.kind==='ticket'?'helpdesk':'requestdesk')}><span><b>{c.subject}</b><small>{c.kind==='ticket'?'Helpdesk ticket':'Service request'} #{c.id}{c.category_name?` · ${c.category_name}`:''}</small></span><span className="gd-chip">{c.status}</span></button>):<Empty>No cases match that status.</Empty>}</div>
   {caseStatus==='ready'&&cases?.has_more&&<Action onClick={()=>p.navigate('requestdesk')}>View all in the Service Center <ArrowRight size={15}/></Action>}
  </Panel><Panel title="Get HR help" desc="Pick the workflow that matches what you need"><div className="gd-links"><button type="button" onClick={p.createTicket}><Headphones size={16}/> Create a helpdesk ticket <ArrowUpRight size={15}/></button><button type="button" onClick={()=>p.navigate('requestdesk')}><CalendarCheck2 size={16}/> Open service requests and messages <ArrowUpRight size={15}/></button><button type="button" onClick={()=>p.navigate('policies')}><ShieldCheck size={16}/> Read HR policies <ArrowUpRight size={15}/></button></div></Panel></div></>}
  {tab==='products'&&<>
   {admin&&<>
    <div className="gd-metrics">
     <Metric label="Total products" value={total('products')} note="In the product catalog" tone="violet" onClick={go('products')}><Package size={18}/></Metric>
     <Metric label="Active products" value={total('products',r=>r.status==='Active')} note="From the product catalog" tone="mint" onClick={go('products')}><CalendarCheck2 size={18}/></Metric>
    </div>
    <Panel title="Product catalog preview" desc="Products and equipment are tracked separately." action={<Action onClick={go('products')}>Manage products <ArrowRight size={14}/></Action>}>
    <div className="gd-list">{configured('products')&&rows('products').length?rows('products').slice(0,5).map(r=><button type="button" className="gd-row-link" key={r.id} onClick={go('products')}><span><b>{r.name}</b><small>{r.code}</small></span><span className="gd-chip">{r.status}</span></button>):<Empty>{configured('products')?'No products are registered yet.':'Product data is not available yet.'}</Empty>}</div>
    </Panel>
   </>}
   <div className="gd-metrics">{[{label:'Total assets',Icon:Package,tone:'violet'},{label:'Assigned',Icon:UsersRound,tone:'mint'},{label:'Maintenance',Icon:Activity,tone:'amber'},{label:'Returned',Icon:Package,tone:'blue'}].map(({label,tone,Icon},i)=><Metric onClick={go('assets')} key={label} label={label} value={total('assets',i?r=>r.status===label:undefined)} note={admin?'Organization equipment':'Your equipment records'} tone={tone}><Icon size={18}/></Metric>)}</div>
   <div className="gd-grid"><Panel title="Equipment register preview" desc={admin?'Recently registered equipment':'Equipment linked to your account'}><div className="gd-filters"><label>Status<select aria-label="Status" value={assetFilter} onChange={e=>setAssetFilter(e.target.value)}><option value="all">All statuses</option><option>Assigned</option><option>Maintenance</option><option>Returned</option></select></label></div>
   <div className="gd-list" aria-live="polite">{configured('assets')&&assets.length?assets.slice(0,6).map(r=><button type="button" className="gd-row-link" key={r.id} onClick={go('assets')}><b>{r.asset_name}</b><span className="gd-chip">{r.status}</span></button>):<Empty>{configured('assets')?'No assets match that status.':'Asset data is not available yet.'}</Empty>}</div></Panel>
   <Panel title="Equipment by status" desc="From your visible equipment records"><Bars series={['Assigned','Maintenance','Returned'].map(label=>({label,value:total('assets',r=>r.status===label)??0}))} ready={configured('assets')} empty="Equipment data is not available yet."/></Panel></div>
  </>}
  {tab==='projects'&&<>
   <div className="gd-metrics">
    {admin&&<>
     <Metric label="Total projects" value={total('projects')} note="Project register" tone="violet" onClick={go('projects')}><FolderKanban size={18}/></Metric>
     <Metric label="Active projects" value={total('projects',r=>r.status==='Active')} note="From the project register" tone="blue" onClick={go('projects')}><Activity size={18}/></Metric>
     <Metric label="Completed projects" value={total('projects',r=>r.status==='Completed')} note="From the project register" tone="amber" onClick={go('projects')}><CalendarCheck2 size={18}/></Metric>
    </>}
    <Metric label="Time entries" value={total('timesheets')} note="From your permitted work log" tone="mint" onClick={go('timesheets')}><Clock3 size={18}/></Metric>
   </div>
   <div className="gd-grid">
    {admin&&<Panel title="Project register preview" desc="Recently listed projects." action={<Action onClick={go('projects')}>Manage projects <ArrowRight size={14}/></Action>}>
     <div className="gd-list">{configured('projects')&&rows('projects').length?rows('projects').slice(0,5).map(r=><button type="button" className="gd-row-link" key={r.id} onClick={go('projects')}><span><b>{r.name}</b><small>{r.code}</small></span><span className="gd-chip">{r.status}</span></button>):<Empty>{configured('projects')?'No projects are registered yet.':'Project data is not available yet.'}</Empty>}</div>
    </Panel>}
    <Panel title="Project timesheets" desc="Record work hours and track approval in the project work log." action={<Action onClick={go('timesheets')}>Open work log <ArrowRight size={14}/></Action>}>
     <Bars series={['Draft','Submitted','Approved','Rejected'].map(label=>({label,value:total('timesheets',r=>r.status===label)??0}))} ready={configured('timesheets')} empty="Timesheet data is not available yet."/>
    </Panel>
   </div>
  </>}
  <div className="gd-foot"><ShieldCheck size={15}/> Counts use what your account can access.<span role="status">{p.loading?'Refreshing workspace data…':'SASS Innovations Enterprise'}</span></div>
 </div>
}
