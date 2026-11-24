import {useEffect, useMemo, useState} from 'react';
import {CheckCircle2, ChevronRight, ClipboardCheck, Pencil, Plus, Search, Settings2, ShieldCheck, Trash2, X} from 'lucide-react';
import {hrmFetch} from './apiTransport';
import './hiring-pipeline.css';

type Row=Record<string,any>;
type Stage='Applied'|'Screening'|'Assessment'|'Interview'|'Offer'|'Hired'|'Rejected';
type Review={candidate:Row;stage:Stage;requirements:string[];completed:string[];note:string;fields:{key:string;label:string;type:string;required:boolean}[];details:Record<string,string>;history:{from_stage:string;to_stage:string;reason:string;created_at:string;actor:string}[]};
type RoleReq={required_skills:string;education:string;min_experience_years:number;criteria:string};
type StageSettings={stage:Stage;checklist:string[];instructions:string;sla_days:number;reviewer_role:'admin'|'manager';note_min_chars:number;updated_at:string|null};
type StageSettingsResult={settings:StageSettings;fields:{key:string;label:string;type:string;required:boolean}[];can_edit:boolean;can_review:boolean};
const STAGES:Stage[]=['Applied','Screening','Assessment','Interview','Offer','Hired','Rejected'];
const NEXT:Partial<Record<Stage,Stage>>={Applied:'Screening',Screening:'Assessment',Assessment:'Interview',Interview:'Offer',Offer:'Hired'};
const PURPOSE:Record<Stage,string>={
  Applied:'Application verification and initial qualification',
  Screening:'Skills, education and experience assessment',
  Assessment:'Technical or job-relevant evaluation',
  Interview:'Structured panel review and hiring recommendation',
  Offer:'HR-approved compensation and offer acceptance',
  Hired:'Joining confirmation and onboarding handoff',
  Rejected:'Dispositions, communication and reactivation review'
};
const EMPTY_REQ:RoleReq={required_skills:'',education:'',min_experience_years:0,criteria:''};
const PAGE_SIZE=25;

async function hiringApi<T>(path:string,method='GET',data?:unknown):Promise<T>{
  const token=sessionStorage.getItem('sass_token');
  if(!token)throw new Error('Your sign-in session has expired. Sign in again.');
  let response:Response;
  try{
    response=await hrmFetch(`${(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')}/api${path}`,{
      method,headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},
      ...(data!==undefined?{body:JSON.stringify(data)}:{})
    });
  }catch{throw new Error('Cannot connect to SASS HRM. Check the backend and MySQL connection.');}
  const payload=await response.json().catch(()=>null);
  if(!response.ok)throw new Error(typeof payload?.detail==='string'?payload.detail:`Request failed (HTTP ${response.status}).`);
  return payload as T;
}

export function HiringPipeline({candidates,jobs,isHR,management,refreshCore}:{candidates:Row[];jobs:Row[];isHR:boolean;management:boolean;refreshCore:()=>void|Promise<void>}){
  const [stage,setStage]=useState<Stage|null>(null);
  const [candidateId,setCandidateId]=useState<number|null>(null);
  const [review,setReview]=useState<Review|null>(null);
  const [done,setDone]=useState<string[]>([]);
  const [note,setNote]=useState('');
  const [details,setDetails]=useState<Record<string,string>>({});
  const [reason,setReason]=useState('');
  const [search,setSearch]=useState('');
  const [roleFilter,setRoleFilter]=useState('');
  const [page,setPage]=useState(0);
  const [requirementsJob,setRequirementsJob]=useState<number|null>(null);
  const [roleRequirements,setRoleRequirements]=useState<RoleReq>(EMPTY_REQ);
  const [candidateRoleReq,setCandidateRoleReq]=useState<RoleReq|null>(null);
  const [busy,setBusy]=useState(false);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState('');
  const [success,setSuccess]=useState('');
  const [revision,setRevision]=useState(0);
  const [settingsRevision,setSettingsRevision]=useState(0);
  const [stageSettings,setStageSettings]=useState<StageSettingsResult|null>(null);
  const [settingsDraft,setSettingsDraft]=useState<StageSettings|null>(null);
  const [settingsView,setSettingsView]=useState(false);
  const [settingsLoading,setSettingsLoading]=useState(false);

  const roles=useMemo(()=>Array.from(new Set([...jobs.map(j=>String(j.title||'')),...candidates.map(c=>String(c.job_title||''))].filter(Boolean))).sort((a,b)=>a.localeCompare(b)),[candidates,jobs]);
  const inStage=useMemo(()=>candidates.filter(c=>c.stage===stage && (!roleFilter || c.job_title===roleFilter) && (!search.trim()||[c.name,c.job_title,c.source,c.id].some(x=>String(x??'').toLowerCase().includes(search.trim().toLowerCase())))),[candidates,stage,roleFilter,search]);
  const numberOfPages=Math.max(1,Math.ceil(inStage.length/PAGE_SIZE));
  const listed=inStage.slice(page*PAGE_SIZE,(page+1)*PAGE_SIZE);
  const selected=candidates.find(c=>Number(c.id)===candidateId);
  const canReview=management && (isHR || (stage!=='Offer'&&stage!=='Hired'&&stageSettings?.settings.reviewer_role!=='admin'));
  const canAdvance=!!stage && !!NEXT[stage] && (isHR || NEXT[stage]!=='Offer'&&NEXT[stage]!=='Hired');
  const matchedJob=jobs.find(j=>String(j.title||'').trim().toLowerCase()===String(selected?.job_title||'').trim().toLowerCase());

  const openStage=(s:Stage)=>{setStage(s);setCandidateId(null);setReview(null);setStageSettings(null);setSettingsDraft(null);setSettingsView(false);setError('');setSuccess('');setSearch('');setRoleFilter('');setPage(0);setReason('');};
  const close=()=>{if(!busy){setStage(null);setRequirementsJob(null);setCandidateId(null);setError('');setSuccess('');}};
  useEffect(()=>{
    if(!stage)return;
    let active=true;setSettingsLoading(true);setStageSettings(null);
    hiringApi<StageSettingsResult>(`/talent/hiring/stages/${stage}/settings`).then(data=>{
      if(!active)return;
      setStageSettings(data);setSettingsDraft({...data.settings,checklist:[...data.settings.checklist]});
    }).catch(e=>{if(active)setError(e.message||'Unable to load stage settings')})
      .finally(()=>{if(active)setSettingsLoading(false)});
    return ()=>{active=false};
  },[stage,settingsRevision]);
  useEffect(()=>{
    if(!candidateId||!stage)return;
    let live=true;
    setReview(null);setError('');setLoading(true);
    hiringApi<Review>(`/talent/hiring/candidates/${candidateId}/review`).then(r=>{
      if(!live)return;
      if(r.stage!==stage){setError('Candidate changed stage. Refresh the hiring board.');return;}
      setReview(r);setDone(r.completed);setNote(r.note);setDetails(r.details||{});setReason('');
    }).catch(e=>{if(live)setError(e.message)}).finally(()=>{if(live)setLoading(false)});
    return ()=>{live=false};
  },[candidateId,stage,revision]);
  useEffect(()=>{
    if(!matchedJob){setCandidateRoleReq(null);return;}
    let live=true;setCandidateRoleReq(null);
    hiringApi<{requirements:RoleReq}>(`/talent/hiring/jobs/${matchedJob.id}/requirements`).then(data=>{
      if(live)setCandidateRoleReq({...EMPTY_REQ,...data.requirements});
    }).catch(()=>{if(live)setCandidateRoleReq(null)});
    return ()=>{live=false};
  },[matchedJob?.id]);
  useEffect(()=>{
    if(!requirementsJob)return;
    let live=true;setLoading(true);setError('');
    hiringApi<{requirements:RoleReq}>(`/talent/hiring/jobs/${requirementsJob}/requirements`).then(r=>{
      if(live)setRoleRequirements({...EMPTY_REQ,...r.requirements});
    }).catch(e=>{if(live)setError(e.message)}).finally(()=>{if(live)setLoading(false)});
    return ()=>{live=false};
  },[requirementsJob]);
  useEffect(()=>{if(!stage&&!requirementsJob)return;const listener=(e:KeyboardEvent)=>{if(e.key==='Escape'&&!busy)close();};window.addEventListener('keydown',listener);return ()=>window.removeEventListener('keydown',listener)},[stage,requirementsJob,busy]);

  const perform=async(fn:()=>Promise<unknown>,message:string,after?:()=>void)=>{
    setBusy(true);setError('');setSuccess('');
    try{await fn();setSuccess(message);after?.();await refreshCore();}
    catch(e:any){setError(e.message||'Unable to save change.');}
    finally{setBusy(false)}
  };
  const saveSettings=()=>{
    if(!stage||!isHR||!settingsDraft)return;
    if(settingsDraft.checklist.length<1||settingsDraft.checklist.length>10 ||
      settingsDraft.checklist.some(x=>x.trim().length<4||x.trim().length>160)){
      setError('Add between 1 and 10 checklist items, 4–160 characters each.');return;
    }
    if(['Offer','Hired'].includes(stage)&&settingsDraft.reviewer_role!=='admin'){
      setError('Offer and Hired stages must remain HR administrator-only.');return;
    }
    if(stageSettings?.settings.reviewer_role!==settingsDraft.reviewer_role &&
       !window.confirm('Change the reviewer permission for this hiring stage? This affects who can approve decisions.'))return;
    void perform(()=>hiringApi(`/talent/hiring/stages/${stage}/settings`,'PUT',settingsDraft),
      'Stage settings saved. Existing candidate reviews must satisfy the updated checklist.',()=>{
        setSettingsRevision(v=>v+1);setRevision(v=>v+1);
      });
  };
  const saveReview=()=>{if(!review)return;void perform(()=>hiringApi(`/talent/hiring/candidates/${candidateId}/review`,'PUT',{stage:review.stage,completed:done,note,details}),
    'Stage review saved to MySQL.',()=>setRevision(v=>v+1));};
  const transition=(toStage:Stage)=>{
    if(!review||reason.trim().length<8){setError('Enter a decision reason of at least 8 characters.');return;}
    const from=review.stage;
    if(toStage==='Rejected'&&!window.confirm(`Reject ${selected?.name||'this candidate'}? This decision will be recorded in the audit trail.`))return;
    void perform(()=>hiringApi(`/talent/hiring/candidates/${candidateId}/transition`,'POST',{from_stage:from,to_stage:toStage,reason:reason.trim()}),
      `Candidate moved from ${from} to ${toStage}.`,()=>{setStage(toStage);setReview(null);setSearch('');setRoleFilter('');setRevision(v=>v+1);});
  };

  return <>
    <div className="hiring-grid" aria-label="Open hiring pipeline stages">
      {STAGES.map(s=><button type="button" className={`hiring-stage-tile hiring-stage-${s.toLowerCase()}`} key={s} onClick={()=>openStage(s)} aria-label={`Open ${s} stage, ${candidates.filter(c=>c.stage===s).length} candidates`}>
        <span>{s}<ChevronRight size={15}/></span><strong>{candidates.filter(c=>c.stage===s).length}</strong><small>{PURPOSE[s]}</small>
      </button>)}
    </div>
    {candidates.some(c=>!STAGES.includes(c.stage))&&<p className="hiring-warning">Some imported candidates have nonstandard stage values. Review those values in Candidate Search before moving them through the pipeline.</p>}
    <div className="hiring-role-toolbar"><div><strong>Job-role requirements</strong><p>HR administrators can define required skills, education, experience and criteria for each published vacancy.</p></div>
      <select aria-label="Choose a job role to view requirements" value={requirementsJob??''} onChange={e=>{const id=Number(e.target.value);if(id){setRequirementsJob(id);setStage(null);setError('');setSuccess('')}else setRequirementsJob(null)}}><option value="">Select a job opening</option>{jobs.map(j=><option key={j.id} value={j.id}>{j.title} · {j.department} ({j.status})</option>)}</select>
    </div>

    {stage&&<div className="hiring-overlay" onMouseDown={e=>{if(e.target===e.currentTarget)close()}}>
      <section className="hiring-window" role="dialog" aria-modal="true" aria-label={`${stage} hiring stage`}>
        <div className="hiring-window-heading"><div><span className="hiring-overline">RECRUITMENT / {stage.toUpperCase()}</span><h3>{stage} stage <span className="hiring-count">{candidates.filter(c=>c.stage===stage).length}</span></h3><p>{PURPOSE[stage]} · {isHR?'HR administrator':management?'Recruitment manager':'Read only'}</p></div>
          <div className="hiring-heading-actions">
            <button className={settingsView?'hiring-view-active':''} type="button" onClick={()=>{setSettingsView(v=>!v);setError('');setSuccess('')}} aria-pressed={settingsView} disabled={busy}><Settings2 size={17}/> {settingsView?'Candidate reviews':'Stage requirements & settings'}</button>
            <button type="button" aria-label="Close hiring window" onClick={close} disabled={busy}><X size={20}/></button>
          </div></div>
        <div className="hiring-window-body">
          <div className="hiring-candidate-side">
            <label><Search size={15}/><input value={search} onChange={e=>{setSearch(e.target.value);setPage(0)}} placeholder="Find candidate" aria-label="Find candidate in stage"/></label>
            <select aria-label="Filter stage by job role" value={roleFilter} onChange={e=>{setRoleFilter(e.target.value);setPage(0)}}><option value="">All job roles</option>{roles.map(role=><option key={role} value={role}>{role}</option>)}</select>
            <p className="hiring-side-count">{inStage.length} candidate{inStage.length===1?'':'s'} found</p>
            <div className="hiring-candidate-scroll">{listed.map(c=><button key={c.id} type="button" className={candidateId===Number(c.id)?'selected':''} onClick={()=>{setCandidateId(Number(c.id));setError('');setSuccess('')}}><strong>{c.name}</strong><small>{c.job_title} · {c.source||'Not specified'}</small></button>)}{!inStage.length&&<div className="hiring-empty">No candidates match this stage and filter. Use Candidate Search to import or add applicants.</div>}</div>
            {numberOfPages>1&&<div className="hiring-pages"><button type="button" disabled={!page} onClick={()=>setPage(v=>v-1)}>Previous</button><span>{page+1} / {numberOfPages}</span><button type="button" disabled={page>=numberOfPages-1} onClick={()=>setPage(v=>v+1)}>Next</button></div>}
          </div>
          <div className="hiring-detail-side">
            {settingsView ? <div className="hiring-settings-pane">
              <h4>{stage} — requirements & settings</h4>
              <p className="hiring-muted">Configure this stage without changing candidate data. Settings are stored in MySQL and enforced by the API.</p>
              {settingsLoading&&<p role="status">Loading stage requirements…</p>}
              {settingsDraft&&<>
                <div className="hiring-settings-badges"><span>Stage: {stage}</span><span>Reviewer: {settingsDraft.reviewer_role==='admin'?'HR administrators':'Recruitment managers & HR'}</span><span>Target: {settingsDraft.sla_days} days</span></div>
                <label className="hiring-text-field"><span>Stage instructions</span>
                  <textarea rows={3} value={settingsDraft.instructions} maxLength={1200} disabled={!isHR||busy} onChange={e=>setSettingsDraft(v=>v?({...v,instructions:e.target.value}):v)}/></label>
                <div className="hiring-settings-section"><h4>Required review checklist</h4>
                  <p className="hiring-muted">{stage==='Rejected'||stage==='Hired'?'Use these items for stage documentation. This stage does not automatically advance.':'These items must be checked before a candidate advances. Changing them may require existing reviews to be redone.'}</p>
                  {settingsDraft.checklist.map((item,index)=><div key={index} className="hiring-checklist-editor">
                    <span>{index+1}.</span><input aria-label={`Checklist item ${index+1}`} value={item} maxLength={160} disabled={!isHR||busy} onChange={e=>setSettingsDraft(v=>v?({...v,checklist:v.checklist.map((x,i)=>i===index?e.target.value:x)}):v)}/>
                    {isHR&&<button type="button" aria-label={`Remove checklist item ${index+1}`} disabled={busy||settingsDraft.checklist.length<=1} onClick={()=>setSettingsDraft(v=>v?({...v,checklist:v.checklist.filter((_,i)=>i!==index)}):v)}><Trash2 size={15}/></button>}
                  </div>)}
                  {isHR&&<button type="button" className="hiring-add-check" disabled={busy||settingsDraft.checklist.length>=10} onClick={()=>setSettingsDraft(v=>v?({...v,checklist:[...v.checklist,'']}):v)}><Plus size={15}/> Add checklist item</button>}
                </div>
                <div className="hiring-settings-fields">
                  <label className="hiring-text-field"><span>Review target (days; guidance only)</span><input type="number" min={1} max={90} disabled={!isHR||busy} value={settingsDraft.sla_days} onChange={e=>setSettingsDraft(v=>v?({...v,sla_days:Number(e.target.value)}):v)}/></label>
                  <label className="hiring-text-field"><span>Reviewer role</span><select disabled={!isHR||busy||stage==='Offer'||stage==='Hired'} value={settingsDraft.reviewer_role} onChange={e=>setSettingsDraft(v=>v?({...v,reviewer_role:e.target.value as 'admin'|'manager'}):v)}><option value="manager">Recruitment manager or HR</option><option value="admin">HR administrator only</option></select></label>
                  <label className="hiring-text-field"><span>Required reviewer note (characters)</span><input type="number" min={8} max={100} disabled={!isHR||busy} value={settingsDraft.note_min_chars} onChange={e=>setSettingsDraft(v=>v?({...v,note_min_chars:Number(e.target.value)}):v)}/></label>
                </div>
                <div className="hiring-settings-section"><h4>Mandatory {stage} evidence</h4><p className="hiring-muted">The following server-validated fields are always required where marked. They cannot be bypassed using stage settings.</p>
                  <ul className="hiring-evidence-list">{stageSettings?.fields.map(field=><li key={field.key}><b>{field.label}</b><span>{field.required?'Required':'Optional'}</span></li>)}</ul>
                </div>
                <p className="hiring-muted"><ShieldCheck size={15}/>{isHR?'Only HR administrators may save these stage settings. Offer and Hired approval can never be delegated.':'Settings are read-only for recruitment managers. Ask HR to make changes.'}</p>
                {isHR&&<div className="hiring-actions"><button type="button" className="hiring-primary" disabled={busy||settingsLoading} onClick={saveSettings}><CheckCircle2 size={16}/> Save stage settings</button><button type="button" className="hiring-secondary" disabled={busy} onClick={()=>stageSettings&&setSettingsDraft({...stageSettings.settings,checklist:[...stageSettings.settings.checklist]})}>Discard edits</button></div>}
              </>}
            </div> : <>
            {!selected&&<div className="hiring-empty prominent"><ClipboardCheck size={28}/><strong>Select a candidate</strong><p>Each candidate has a review checklist, history and controlled hiring decisions.</p></div>}
            {selected&&<><div className="hiring-person"><div><strong>{selected.name}</strong><small>{selected.job_title} · Applied {selected.applied_at||'—'}</small></div><span>{selected.stage}</span></div>
              {loading&&<p role="status">Loading candidate review…</p>}
              {review&&<>
                <h4>Required {stage} checks</h4><p className="hiring-muted">Tick each requirement after confirming the evidence. Save your review before advancing. {stageSettings?.settings.reviewer_role==='admin'?'HR administrator review required.':''}</p>
                <div className="hiring-checks">{review.requirements.map(item=><label key={item}><input type="checkbox" checked={done.includes(item)} disabled={!canReview||busy} onChange={e=>setDone(old=>e.target.checked?[...old,item]:old.filter(x=>x!==item))}/><span>{item}</span></label>)}</div>
                <div className="hiring-evidence-fields"><h4>Stage-specific evidence</h4>{review.fields.map(f=><label className="hiring-text-field" key={f.key}><span>{f.label}{f.required?' *':''}</span><input type={f.type==='number'?'number':f.type==='date'?'date':'text'} min={f.type==='number'?0:undefined} max={f.type==='number'?100:undefined} maxLength={f.type==='text'?500:undefined} value={details[f.key]||''} disabled={!canReview||busy} onChange={e=>setDetails(old=>({...old,[f.key]:e.target.value}))}/></label>)}</div>
                <label className="hiring-text-field"><span>Reviewer notes / evidence (minimum {stageSettings?.settings.note_min_chars??8} characters to advance)</span><textarea value={note} disabled={!canReview||busy} onChange={e=>setNote(e.target.value)} rows={3} maxLength={2000} placeholder="Describe the reviewed evidence and outcome"/></label>
                {canReview&&<button type="button" className="hiring-primary" disabled={busy} onClick={saveReview}><CheckCircle2 size={16}/> Save stage review</button>}
                <div className="hiring-role-evidence"><h4>Job-role eligibility requirements</h4>
                  {matchedJob&&candidateRoleReq?<>
                    <p><b>Skills:</b> {candidateRoleReq.required_skills||'Not configured'}</p>
                    <p><b>Education:</b> {candidateRoleReq.education||'Not configured'}</p>
                    <p><b>Experience:</b> {candidateRoleReq.min_experience_years} years minimum</p>
                    <p><b>Additional criteria:</b> {candidateRoleReq.criteria||'Not configured'}</p>
                    <button className="hiring-link" type="button" onClick={()=>{setRequirementsJob(Number(matchedJob.id));setStage(null)}}>View {matchedJob.title} role settings</button>
                  </>:<p className="hiring-muted">{matchedJob?'Loading configured role requirements…':'This candidate’s job title is not linked to a posted vacancy. HR can create a matching vacancy to configure role-specific requirements.'}</p>}
                </div>
                {stage==='Interview'&&<p className="hiring-muted">For interview appointments and interviewer assignments, <a href="/talent/interview-scheduling" className="hiring-link">open Interview Scheduling</a>.</p>}
                {stage==='Hired'&&<p className="hiring-muted">For joining checklists, <a href="/talent/onboarding" className="hiring-link">open Onboarding</a>.</p>}
                <div className="hiring-decision"><h4>Hiring decision</h4><p>Transitions are verified by the server. A rejection requires a reason; final offers and hires require HR approval.</p>
                  <label className="hiring-text-field"><span>Decision reason (minimum 8 characters)</span><textarea rows={2} value={reason} maxLength={1000} onChange={e=>setReason(e.target.value)} placeholder="Explain the hiring decision" disabled={busy}/></label>
                  <div className="hiring-actions">
                    {canAdvance&&NEXT[stage]&&<button type="button" className="hiring-primary" disabled={busy||!canReview||reason.trim().length<8} onClick={()=>transition(NEXT[stage]!)}><ChevronRight size={16}/> Advance to {NEXT[stage]}</button>}
                    {stage!=='Rejected'&&stage!=='Hired'&&(stage!=='Offer'||isHR)&&<button type="button" className="hiring-danger" disabled={busy||!canReview||reason.trim().length<8} onClick={()=>transition('Rejected')}>Reject candidate</button>}
                    {stage==='Rejected'&&isHR&&<button type="button" className="hiring-primary" disabled={busy||reason.trim().length<8} onClick={()=>transition('Applied')}>Reopen application</button>}
                    {(stage==='Hired'||(stage==='Offer'&&!isHR))&&<span className="hiring-muted">{stage==='Hired'?'Hired is a protected final stage.':'Only HR administrators may approve an offer or hire.'}</span>}
                  </div>
                </div>
                <div className="hiring-history"><h4>Stage history</h4>{review.history.length?review.history.map((h,i)=><div key={`${h.created_at}-${i}`}><strong>{h.from_stage} → {h.to_stage}</strong><small>{h.actor||'HR team'} · {h.created_at}</small><p>{h.reason}</p></div>):<p className="hiring-muted">No recorded stage transitions yet.</p>}</div>
              </>}
            </>}
            </>}
          </div>
        </div>
        {error&&<div role="alert" className="hiring-error">{error}</div>}{success&&<div role="status" className="hiring-success">{success}</div>}
      </section>
    </div>}

    {requirementsJob!==null&&<div className="hiring-overlay" onMouseDown={e=>{if(e.target===e.currentTarget)close()}}>
      <section className="hiring-requirements-window" role="dialog" aria-modal="true" aria-label="Job role hiring requirements">
        <div className="hiring-window-heading"><div><span className="hiring-overline">JOB OPENING / REQUIREMENTS</span><h3>{jobs.find(j=>Number(j.id)===requirementsJob)?.title||'Role requirements'}</h3><p>Defined requirements for candidate screening, assessment and interviews.</p></div><button type="button" aria-label="Close job requirements" onClick={close} disabled={busy}><X size={20}/></button></div>
        <div className="hiring-requirements-form">
          <label className="hiring-text-field"><span>Essential skills</span><textarea rows={3} value={roleRequirements.required_skills} disabled={!isHR||busy} onChange={e=>setRoleRequirements(v=>({...v,required_skills:e.target.value}))} maxLength={1200} placeholder="e.g. Java, SQL, REST APIs"/></label>
          <label className="hiring-text-field"><span>Education / certifications</span><textarea rows={2} value={roleRequirements.education} disabled={!isHR||busy} onChange={e=>setRoleRequirements(v=>({...v,education:e.target.value}))} maxLength={500}/></label>
          <label className="hiring-text-field"><span>Minimum years of experience</span><input type="number" min={0} max={60} value={roleRequirements.min_experience_years} disabled={!isHR||busy} onChange={e=>setRoleRequirements(v=>({...v,min_experience_years:Number(e.target.value)}))}/></label>
          <label className="hiring-text-field"><span>Additional hiring criteria / documents</span><textarea rows={3} value={roleRequirements.criteria} disabled={!isHR||busy} onChange={e=>setRoleRequirements(v=>({...v,criteria:e.target.value}))} maxLength={2000}/></label>
          <p className="hiring-muted"><ShieldCheck size={14}/> {isHR?'Only HR administrators can save role requirements.':'You may view requirements, but only HR administrators can edit them.'}</p>
          {isHR&&<button type="button" className="hiring-primary" disabled={busy||loading} onClick={()=>void perform(()=>hiringApi(`/talent/hiring/jobs/${requirementsJob}/requirements`,'PUT',roleRequirements),'Job-role requirements saved.') }><Pencil size={16}/> Save role requirements</button>}
          {error&&<div role="alert" className="hiring-error">{error}</div>}{success&&<div role="status" className="hiring-success">{success}</div>}
        </div>
      </section>
    </div>}
  </>;
}
