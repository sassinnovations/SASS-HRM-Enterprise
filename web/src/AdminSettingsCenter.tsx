import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import {useCallback,useEffect,useMemo,useState} from 'react';
import {AlertCircle,ArrowRight,Building2,CalendarDays,CheckCircle2,ClipboardCheck,FileText,RotateCcw,Save,Settings2,ShieldCheck,SlidersHorizontal,UsersRound,WalletCards} from 'lucide-react';
import './admin-settings-center.css';

type Settings = {
  candidate_followup_days:number; interview_confirmation_hours:number; vacancy_review_days:number; recruiter_guidance:string;
  onboarding_default_offset_days:number; onboarding_review_days:number; onboarding_guidance:string;
  service_request_review_days:number; helpdesk_triage_hours:number; helpdesk_escalation_review_days:number; helpdesk_guidance:string;
  task_default_due_days:number; task_overdue_review_days:number; offboarding_clearance_review_days:number; offboarding_guidance:string;
  document_review_days:number; asset_inventory_review_days:number; profile_review_days:number; employee_services_guidance:string;
  policy_review_months:number; announcement_review_days:number; policy_guidance:string;
};
type Entry = {settings:Settings;source:'defaults'|'organization';updated_at:string|null;updated_by:number|null};
type Overview = {sections:Record<string,boolean>;configured:number;total:number;note:string};
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
const defaults:Settings={
  candidate_followup_days:5, interview_confirmation_hours:24, vacancy_review_days:30,
  recruiter_guidance:'Record job-relevant interview feedback without sensitive personal details.',
  onboarding_default_offset_days:3, onboarding_review_days:7,
  onboarding_guidance:'Confirm identity, access, policies and assigned equipment through authorized workflows.',
  service_request_review_days:3, helpdesk_triage_hours:8, helpdesk_escalation_review_days:2,
  helpdesk_guidance:'Keep request updates in the case conversation and review urgent items promptly.',
  task_default_due_days:7,task_overdue_review_days:1, offboarding_clearance_review_days:5,
  offboarding_guidance:'Review handover, access and company assets before closing an approved exit.',
  document_review_days:5,asset_inventory_review_days:90,profile_review_days:30,
  employee_services_guidance:'Review employee documents only through approved, role-restricted processes.',
  policy_review_months:12,announcement_review_days:30,
  policy_guidance:'Publish only HR-approved policies and obtain legal review when required.',
};
type NumericKey = {[K in keyof Settings]:Settings[K] extends number?K:never}[keyof Settings];
type TextKey = {[K in keyof Settings]:Settings[K] extends string?K:never}[keyof Settings];
type NumberField={key:NumericKey;label:string;unit:string;min:number;max:number};
type TextField={key:TextKey;label:string};
type Group={title:string;detail:string;numbers:NumberField[];texts:TextField[]};
const groups:Group[]=[
 {title:'Recruitment ATS & interviews', detail:'Targets for hiring reviews and candidate communication; not automatic screening decisions.',numbers:[
  {key:'candidate_followup_days',label:'Candidate follow-up target',unit:'days',min:1,max:90},
  {key:'interview_confirmation_hours',label:'Interview confirmation lead time',unit:'hours',min:1,max:168},
  {key:'vacancy_review_days',label:'Open vacancy review cycle',unit:'days',min:1,max:180},
 ],texts:[{key:'recruiter_guidance',label:'Recruiter guidance'}]},
 {title:'Onboarding & joining checklists',detail:'Suggested scheduling defaults and HR review guidance.',numbers:[
  {key:'onboarding_default_offset_days',label:'Suggested template due offset',unit:'days',min:0,max:90},
  {key:'onboarding_review_days',label:'First onboarding review target',unit:'days',min:1,max:60},
 ],texts:[{key:'onboarding_guidance',label:'Onboarding guidance'}]},
 {title:'HR Helpdesk & Request Desk',detail:'Review and escalation guidance; no background SLA timers are created.',numbers:[
  {key:'service_request_review_days',label:'Service request review target',unit:'days',min:1,max:60},
  {key:'helpdesk_triage_hours',label:'Helpdesk triage target',unit:'hours',min:1,max:168},
  {key:'helpdesk_escalation_review_days',label:'Helpdesk escalation review',unit:'days',min:1,max:30},
 ],texts:[{key:'helpdesk_guidance',label:'Case handling guidance'}]},
 {title:'HR Tasks & Offboarding',detail:'Targets for assignees and clearance reviews; all approvals remain manual.',numbers:[
  {key:'task_default_due_days',label:'Suggested task due window',unit:'days',min:1,max:90},
  {key:'task_overdue_review_days',label:'Overdue task review window',unit:'days',min:0,max:30},
  {key:'offboarding_clearance_review_days',label:'Exit clearance review',unit:'days',min:1,max:90},
 ],texts:[{key:'offboarding_guidance',label:'Exit clearance guidance'}]},
 {title:'Employee Documents, Assets & Profiles',detail:'Review timeframes for staff-service administrators; access controls remain unchanged.',numbers:[
  {key:'document_review_days',label:'Document review target',unit:'days',min:1,max:90},
  {key:'asset_inventory_review_days',label:'Asset inventory review interval',unit:'days',min:7,max:365},
  {key:'profile_review_days',label:'Professional profile review',unit:'days',min:1,max:180},
 ],texts:[{key:'employee_services_guidance',label:'Employee services guidance'}]},
 {title:'Policy & Announcements',detail:'Internal HR content-review schedules. Publishing still requires authorized personnel.',numbers:[
  {key:'policy_review_months',label:'Policy review frequency',unit:'months',min:1,max:36},
  {key:'announcement_review_days',label:'Announcement freshness review',unit:'days',min:1,max:365},
 ],texts:[{key:'policy_guidance',label:'Policy publishing guidance'}]},
];
async function api<T>(path:string,method='GET',body?:unknown):Promise<T>{
  const token=sessionStorage.getItem('sass_token');
  const response=await hrmFetch(API+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});
  const content=await response.json().catch(()=>({}));
  if(!response.ok)throw Error(typeof content.detail==='string'?content.detail:`Request failed (HTTP ${response.status})`);
  return content as T;
}
const pages:{key:string;name:string;description:string;icon:typeof Settings2;checks:string[]}[]=[
 {key:'orgsettings',name:'Organization settings',description:'Workspace identity, offices, timezone and reporting preferences.',icon:Building2,checks:['organization_preferences','office_directory']},
 {key:'companysetup',name:'Company setup & import',description:'Company profile, departments, leave entitlements and HR policies.',icon:ClipboardCheck,checks:['company_identity','department_structure','leave_entitlements','published_policies']},
 {key:'workflowsettings',name:'Workflow settings',description:'HR helpdesk response and task/onboarding warning guidance.',icon:SlidersHorizontal,checks:['workflow_guidance']},
 {key:'coverage',name:'Team leave & coverage planner',description:'View approved team leave, office holidays, and set advisory coverage warning thresholds.',icon:CalendarDays,checks:[]},
 {key:'dataquality',name:'HR data quality center',description:'Review directory completeness and delayed workflows with owner assignment, safe CSV export and audit records.',icon:ClipboardCheck,checks:[]},
 {key:'tasktemplates',name:'Reusable HR task templates',description:'Create standard tasks, assign them securely to employees and track completion.',icon:ClipboardCheck,checks:[]},
 {key:'compensationsettings',name:'Compensation settings',description:'Attendance, payroll cutoff, timesheet and expense review targets.',icon:WalletCards,checks:['compensation_guidance']},
 {key:'talentsettings',name:'Talent & Employee Services settings',description:'Recruitment, onboarding, service cases, asset and document review targets.',icon:UsersRound,checks:['talent_service_guidance']},
 {key:'accounts',name:'Account provisioning',description:'Create and suspend accounts, manage roles and JWT session revocation.',icon:ShieldCheck,checks:['account_bootstrap']},
 {key:'profilemgmt',name:'Profile management',description:'Oversee employee professional profile completion and correction requests.',icon:UsersRound,checks:[]},
 {key:'audit',name:'Audit trail',description:'Review account, settings and workflow change records.',icon:FileText,checks:[]},
];

export function AdminSettingsCenter({mode,navigate}:{mode:'center'|'talent';navigate:(page:string)=>void}){
  const [overview,setOverview]=useState<Overview|null>(null);
  const [saved,setSaved]=useState<Entry|null>(null);
  const [editing,setEditing]=useState<Settings>(defaults);
  const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');
  const load=useCallback(async()=>{
    setBusy(true);setError('');
    try{
      if(mode==='center')setOverview(await api<Overview>('/admin/settings/overview'));
      else{const result=await api<Entry>('/admin/settings/talent');setSaved(result);setEditing(result.settings)}
    }catch(e){setError((e as Error).message)}finally{setBusy(false)}
  },[mode]);
  useEffect(()=>{void load()},[load]);
  useRefreshData(load);
  const dirty=useMemo(()=>saved?JSON.stringify(editing)!==JSON.stringify(saved.settings):false,[saved,editing]);
  const invalid=groups.some(g=>g.numbers.some(f=>!Number.isInteger(editing[f.key])||editing[f.key]<f.min||editing[f.key]>f.max));
  const save=async()=>{
    setBusy(true);setError('');setNotice('');
    try{const result=await api<Entry>('/admin/settings/talent','PUT',editing);setSaved(result);setEditing(result.settings);setNotice('Settings saved to MySQL and recorded in the audit trail.');}
    catch(e){setError((e as Error).message)}finally{setBusy(false)}
  };
  return <section className="asc-page">
    <header className="asc-heading"><div><span className="asc-eyebrow">SASS HRM / SECURE ADMINISTRATION</span><h1>{mode==='center'?'Administration settings center':'Talent & employee services settings'}</h1><p>{mode==='center'?'Find every organization-wide settings page, check setup progress and open the correct administration workflow.':'Configure validated operational guidance for the employee lifecycle. These values do not automate decisions or override approved policies.'}</p></div><div className="asc-buttons">{mode==='talent'&&<button type="button" onClick={()=>navigate('settingscenter')}><ArrowRight size={15}/> Settings center</button>}</div></header>
    {error&&<div className="asc-alert error" role="alert"><AlertCircle size={18}/>{error}</div>}
    {notice&&<div className="asc-alert success" role="status"><CheckCircle2 size={18}/>{notice}</div>}
    {mode==='center'?<>
      <div className="asc-summary"><div className="asc-summary-icon"><Settings2 size={23}/></div><div><h2>Workspace configuration</h2><p>{overview?`${overview.configured} of ${overview.total} setup indicators contain saved records.`:'Checking saved organization settings...'}</p><small>These indicators measure setup records, not legal compliance, security approval or production readiness.</small></div></div>
      <div className="asc-grid">{pages.map(item=>{const Icon=item.icon;const hasStatus=Boolean(item.checks.length&&overview);const configured=item.checks.length?item.checks.every(k=>overview?.sections[k]):false;return <button key={item.key} type="button" className="asc-navigation" onClick={()=>navigate(item.key)}><span className="asc-icon"><Icon size={21}/></span><span className="asc-nav-body"><strong>{item.name}</strong><small>{item.description}</small>{hasStatus&&<em className={configured?'ok':'pending'}>{configured?'Settings present':'Setup remaining'}</em>}</span><ArrowRight size={17}/></button>})}</div>
      <div className="asc-info"><ShieldCheck size={20}/><span>Administrator-only access is checked by the API. Only changed setting names are recorded in the audit log; passwords, JWT signing keys and employee records are not displayed here.</span></div>
    </>:<>
      <div className="asc-info"><ShieldCheck size={20}/><span><strong>Operational guidance only.</strong> Saving these settings changes the values shown to HR for planning; it does not send mail, activate escalations, delete records, grant permissions or execute payroll. Use the existing HRM workflows for those actions.</span></div>
      <div className="asc-meta"><div><strong>Configuration source</strong><span>{saved?.source==='organization'?'Saved organization settings':'Default guidance values'}</span></div><div><strong>Last updated</strong><span>{saved?.updated_at?new Date(saved.updated_at).toLocaleString():'No saved changes yet'}</span></div><div><strong>Unsaved changes</strong><span>{dirty?'Yes — review and save':'None'}</span></div></div>
      <div className="asc-group-grid">{groups.map(group=><section className="asc-section" key={group.title}><div className="asc-section-head"><h2>{group.title}</h2><p>{group.detail}</p></div><div className="asc-fields">{group.numbers.map(f=><label className="asc-field" key={f.key}><span>{f.label}</span><div className="asc-unit"><input type="number" min={f.min} max={f.max} step="1" value={editing[f.key]} onChange={e=>setEditing(prev=>({...prev,[f.key]:e.target.value===''?NaN:Number(e.target.value)}))}/><small>{f.unit}</small></div><small>Allowed: {f.min}–{f.max} {f.unit}</small></label>)}{group.texts.map(f=><label className="asc-field asc-full" key={f.key}><span>{f.label}</span><textarea rows={3} maxLength={350} value={editing[f.key]} onChange={e=>setEditing(prev=>({...prev,[f.key]:e.target.value}))}/><small>{editing[f.key].length}/350 characters</small></label>)}</div></section>)}</div>
      <div className="asc-savebar"><div><strong>Save talent and service guidance</strong><p>Review your changes before saving them to the HRM database.</p></div><div className="asc-buttons"><button type="button" disabled={busy||!dirty} onClick={()=>{setEditing(saved?.settings??defaults);setNotice('');setError('')}}><RotateCcw size={15}/> Discard changes</button><button type="button" disabled={busy||!dirty||invalid} className="asc-primary" onClick={()=>void save()}><Save size={15}/>{busy?'Saving...':'Save settings'}</button></div></div>
    </>}
  </section>
}
