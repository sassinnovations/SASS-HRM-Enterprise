import {useCallback,useEffect,useRef,useState} from 'react';
import type {FormEvent} from 'react';
import {Download, FileSpreadsheet, Filter, Plus, Search, Trash2, Upload, X, Pencil, CheckCircle2, Target} from 'lucide-react';
import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import './job-descriptions.css';

type JD={id:number;title:string;description:string;department:string;location:string;employment_type:string;
  required_skills:string;preferred_skills:string;min_experience:number;education:string;status:string;
  job_opening_id:number|null;import_batch_id:number|null};
type Match={candidate_id:number;name:string;job_title:string;stage:string;location:string;experience_years:number|null;
 score_percent:number;matched_skills:string[];missing_skills:string[];preferred_skills_matched:string[];
 components:{name:string;weight:number;evidence_percent:number}[]};
type Ranked={jd_id:number;job_title:string;total_candidates:number;matches_in_range:number;min_score:number;
 items:Match[];method:string;disclaimer:string};
type SavedRun={id:number;scoring_version:string;candidate_count:number;saved_matches:number;created_at:string};
type SavedMatch={id:number;candidate_id:number|null;name:string|null;job_title:string|null;match_score:number;reviewed_status:string;evidence_summary:string};
type SavedDetails={run:{id:number;created_at:string};items:SavedMatch[];notice:string};
type ShortlistEntry={id:number;candidate_id:number;candidate_name:string;decision:string;rationale:string;decided_at:string};
type Preview={filename:string;sha256:string;total_rows:number;valid_rows:number;invalid_rows:number;duplicates:number;
 issues:{row:number;problem:string}[];preview:{row:number;title:string;department:string;location:string}[]};
type History={id:number;filename:string;rows_received:number;rows_imported:number;rows_skipped:number;remaining:number;imported_at:string};
const initial=()=>({title:'',description:'',department:'',location:'',employment_type:'Full-time',
  required_skills:'',preferred_skills:'',min_experience:0,education:'',status:'Open',job_opening_id:null as number|null});
type FormData=ReturnType<typeof initial>;
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api/job-descriptions';
function errorMessage(body:unknown,fallback:string){
  if(body&&typeof body==='object'&&'detail' in body){
    const detail=(body as {detail:unknown}).detail;
    if(typeof detail==='string')return detail;
    if(detail&&typeof detail==='object'&&'message' in detail)return String((detail as {message:string}).message);
  }
  return fallback;
}
async function request<T>(path='',init:RequestInit={},timeout=30000):Promise<T>{
  const token=sessionStorage.getItem('sass_token');
  const r=await hrmFetch(API+path,{...init,headers:{Authorization:`Bearer ${token||''}`,...init.headers}},timeout);
  if(!r.ok){const data=await r.json().catch(()=>null);throw new Error(errorMessage(data,`JD request failed (HTTP ${r.status})`))}
  return r.json() as Promise<T>;
}
async function download(path:string,filename:string){
  const token=sessionStorage.getItem('sass_token');
  const r=await hrmFetch(API+path,{headers:{Authorization:`Bearer ${token||''}`}},1800000);
  if(!r.ok){const body=await r.json().catch(()=>null);throw new Error(errorMessage(body,`Download failed (${r.status})`))}
  const u=URL.createObjectURL(await r.blob());const link=document.createElement('a');
  link.href=u;link.download=filename;document.body.appendChild(link);link.click();link.remove();
  window.setTimeout(()=>URL.revokeObjectURL(u),1200);
}

export function JobDescriptions({isHR,context='search',onOpenCandidate}:
  {isHR:boolean;context?:'search'|'ats';onOpenCandidate?:(candidateId:number)=>void}){
  const [list,setList]=useState<JD[]>([]);const [total,setTotal]=useState(0);
  const [page,setPage]=useState(1);const [query,setQuery]=useState('');const [applied,setApplied]=useState('');
  const [filterStatus,setFilterStatus]=useState('');
  const [selected,setSelected]=useState<JD|null>(null);const [editor,setEditor]=useState<FormData|null>(null);
  const [editingId,setEditingId]=useState<number|null>(null);
  const [matching,setMatching]=useState<Ranked|null>(null);const [minScore,setMinScore]=useState(0);
  const [savedRuns,setSavedRuns]=useState<SavedRun[]>([]);
  const [savedDetail,setSavedDetail]=useState<SavedDetails|null>(null);
  const [shortlist,setShortlist]=useState<ShortlistEntry[]>([]);
  const [decisionCandidate,setDecisionCandidate]=useState<Match|null>(null);
  const [decisionReason,setDecisionReason]=useState('');
  const [decisionType,setDecisionType]=useState<'Shortlisted'|'Hold'|'Rejected'>('Shortlisted');
  const [reviewResult,setReviewResult]=useState<number|null>(null);
  const [reviewNote,setReviewNote]=useState('');
  const [reviewAction,setReviewAction]=useState<'Consider'|'NotNow'|'NeedsReview'>('NeedsReview');
  const [uploadFile,setUploadFile]=useState<File|null>(null);const fileRef=useRef<HTMLInputElement>(null);
  const [preview,setPreview]=useState<Preview|null>(null);const [mode,setMode]=useState<'skip'|'reject'>('skip');
  const [invalidMode,setInvalidMode]=useState<'reject'|'skip'>('reject');
  const [history,setHistory]=useState<History[]>([]);
  const [busy,setBusy]=useState(false);const [loading,setLoading]=useState(false);
  const [error,setError]=useState('');const [notice,setNotice]=useState('');
  const [deleteId,setDeleteId]=useState<number|null>(null);const [deleteConfirm,setDeleteConfirm]=useState('');
  const [bulkCount,setBulkCount]=useState<number|null>(null);const [bulkConfirm,setBulkConfirm]=useState('');
  const [bulkReason,setBulkReason]=useState('');const [revision,setRevision]=useState(0);
  const reload=()=>setRevision(n=>n+1);
  useRefreshData(reload);
  const load=useCallback(async()=>{
    setLoading(true);
    try{
      const p=new URLSearchParams({q:applied,status:filterStatus,page:String(page),page_size:'20'});
      const [jds,imports]=await Promise.all([
        request<{items:JD[];total:number}>('?'+p.toString()),request<History[]>('/imports')]);
      setList(jds.items);setTotal(jds.total);setHistory(imports);
      if(selected){
        const replacement=jds.items.find(j=>j.id===selected.id);
        if(replacement)setSelected(replacement);
      }
    }catch(e){setError(e instanceof Error?e.message:'Could not load job descriptions')}
    finally{setLoading(false)}
  // selected is intentionally excluded: selecting one JD must not fetch the entire register again.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  },[applied,filterStatus,page,revision]);
  useEffect(()=>{void load()},[load]);
  const match=async (jd:JD,threshold=minScore)=>{
    setBusy(true);setError('');setMatching(null);
    try{setMatching(await request<Ranked>(`/${jd.id}/matches?limit=100&min_score=${threshold}`,{},90000))}
    catch(e){setError(e instanceof Error?e.message:'Could not score candidates')}
    finally{setBusy(false)}
  };
  const loadSaved=async(jd:JD)=>{
    try{const [runs,decisions]=await Promise.all([
      request<SavedRun[]>(`/${jd.id}/match-runs`),request<ShortlistEntry[]>(`/${jd.id}/shortlist`)]);
      setSavedRuns(runs);setShortlist(decisions)}
    catch(e){setError(e instanceof Error?e.message:'Could not load matching history')}
  };
  const saveMatch=async()=>{
    if(!selected)return;
    setBusy(true);setError('');
    try{const r=await request<{saved_matches:number}>(`/${selected.id}/match-runs`,{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({limit:100,min_score:minScore})},120000);
      setNotice(`Saved ${r.saved_matches} point-in-time ATS match estimates for human review.`);
      await loadSaved(selected)}
    catch(e){setError(e instanceof Error?e.message:'Could not save match run')}
    finally{setBusy(false)}
  };
  const openSaved=async(runId:number)=>{
    setBusy(true);setError('');
    try{setSavedDetail(await request<SavedDetails>(`/match-runs/${runId}`))}
    catch(e){setError(e instanceof Error?e.message:'Could not read saved matches')}
    finally{setBusy(false)}
  };
  const submitReview=async()=>{
    if(reviewResult===null||reviewNote.trim().length<8)return;
    setBusy(true);setError('');
    try{await request(`/match-results/${reviewResult}/reviews`,{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({review_action:reviewAction,review_note:reviewNote.trim()})});
      setNotice('Human review saved. Candidate hiring stage remains unchanged.');
      if(savedDetail)await openSaved(savedDetail.run.id);
      setReviewResult(null);setReviewNote('');}
    catch(e){setError(e instanceof Error?e.message:'Could not save review')}
    finally{setBusy(false)}
  };
  const submitShortlist=async()=>{
    if(!selected||!decisionCandidate||decisionReason.trim().length<8)return;
    setBusy(true);setError('');
    try{await request(`/${selected.id}/shortlist`,{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify({
        candidate_id:decisionCandidate.candidate_id,decision:decisionType,rationale:decisionReason.trim()})});
      setNotice('HR shortlist decision saved. Candidate hiring stage remains unchanged.');
      setDecisionCandidate(null);setDecisionReason('');await loadSaved(selected)}
    catch(e){setError(e instanceof Error?e.message:'Could not save shortlist decision')}
    finally{setBusy(false)}
  };
  const selectJD=(jd:JD)=>{setSelected(jd);setMatching(null);setSavedDetail(null);setSavedRuns([]);
    setDecisionCandidate(null);setError('');void match(jd);void loadSaved(jd)};
  const openForm=(jd?:JD)=>{
    if(jd){setEditingId(jd.id);setEditor({title:jd.title,description:jd.description,department:jd.department,
      location:jd.location,employment_type:jd.employment_type,required_skills:jd.required_skills,
      preferred_skills:jd.preferred_skills,min_experience:jd.min_experience,education:jd.education,
      status:jd.status,job_opening_id:jd.job_opening_id});}
    else{setEditingId(null);setEditor(initial())}
    setError('');
  };
  const save=async(e:FormEvent)=>{
    e.preventDefault();if(!editor)return;
    setBusy(true);setError('');
    try{
      const body=JSON.stringify(editor);
      const result=await request<{id:number}>(editingId?`/${editingId}`:'',
        {method:editingId?'PUT':'POST',headers:{'Content-Type':'application/json'},body});
      setNotice(editingId?'Job description updated. Scores will be recomputed.':'Job description added.');
      setEditor(null);setEditingId(null);setSelected(null);setMatching(null);setPage(1);setApplied('');setQuery('');reload();
      if(result.id) { /* Saved ID supplied for audit traceability; no automatic candidate decision. */ }
    }catch(e){setError(e instanceof Error?e.message:'Unable to save JD')}
    finally{setBusy(false)}
  };
  const remove=async()=>{
    if(deleteId===null||deleteConfirm!=='DELETE')return;
    setBusy(true);setError('');
    try{
      await request(`/${deleteId}?confirm=DELETE`,{method:'DELETE'});
      setNotice('Job description permanently removed. Candidate records were not changed.');
      if(selected?.id===deleteId){setSelected(null);setMatching(null)}
      setDeleteId(null);setDeleteConfirm('');reload();
    }catch(e){setError(e instanceof Error?e.message:'Unable to delete JD')}
    finally{setBusy(false)}
  };
  const clearAll=async()=>{
    if(bulkCount===null||bulkConfirm!=='DELETE ALL JOB DESCRIPTIONS'||bulkReason.trim().length<8)return;
    setBusy(true);setError('');
    try{
      const result=await request<{deleted:number}>('/clear-all',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({confirmation:bulkConfirm,reason:bulkReason,expected_count:bulkCount})});
      setNotice(`${result.deleted} job descriptions and import history entries permanently removed. Candidates and job openings retained.`);
      setSelected(null);setMatching(null);setPreview(null);setBulkCount(null);setBulkReason('');setBulkConfirm('');setPage(1);reload();
    }catch(e){setError(e instanceof Error?e.message:'Could not clear JD records')}
    finally{setBusy(false)}
  };
  const previewUpload=async()=>{
    if(!uploadFile)return;
    setBusy(true);setError('');setPreview(null);
    try{
      const filename=encodeURIComponent(uploadFile.name);
      setPreview(await request<Preview>('/import/preview',{
        method:'POST',headers:{'X-Filename':filename,'Content-Type':'application/octet-stream'},body:uploadFile},1800000));
    }catch(e){setError(e instanceof Error?e.message:'Could not preview JD workbook')}
    finally{setBusy(false)}
  };
  const commitImport=async()=>{
    if(!uploadFile||!preview||(invalidMode==='reject'&&preview.invalid_rows))return;
    setBusy(true);setError('');
    try{
      const result=await request<{imported:number;skipped:number;invalid_skipped:number}>(`/import?duplicate_mode=${mode}&invalid_mode=${invalidMode}`,{
        method:'POST',headers:{'X-Filename':encodeURIComponent(uploadFile.name),'X-Confirm-SHA256':preview.sha256,
          'Content-Type':'application/octet-stream'},body:uploadFile},3600000);
      setNotice(`Imported ${result.imported.toLocaleString()} JD(s); skipped ${result.skipped.toLocaleString()} row(s), including ${result.invalid_skipped.toLocaleString()} invalid row(s). No candidate records were modified.`);
      setUploadFile(null);setPreview(null);if(fileRef.current)fileRef.current.value='';setPage(1);reload();
    }catch(e){setError(e instanceof Error?e.message:'JD import failed')}
    finally{setBusy(false)}
  };
  const triggerExport=async(path:string,name:string)=>{
    setBusy(true);setError('');try{await download(path,name)}
    catch(e){setError(e instanceof Error?e.message:'Export failed')}
    finally{setBusy(false)}
  };
  return <section className="jd-center" aria-label="Job descriptions and ATS candidate matching">
    <header className="jd-center-heading">
      <div><div className="jd-eyebrow">{context==='ats'?'RECRUITMENT ATS':'CANDIDATE SEARCH & DATABASE'} / JOB DESCRIPTIONS</div>
        <h2>Job descriptions & candidate match scores</h2>
        <p>Import or enter a JD, then rank your existing candidates by an explainable, advisory ATS match percentage.</p></div>
      <div className="jd-actions">
        {isHR&&<button className="jd-primary" onClick={()=>openForm()} disabled={busy}><Plus size={15}/> Add JD manually</button>}
        <button onClick={()=>void triggerExport('/export.xlsx','sass-hrm-job-descriptions.xlsx')} disabled={busy}><Download size={15}/> Export Excel</button>
        <button onClick={()=>void triggerExport('/export.csv','sass-hrm-job-descriptions.csv')} disabled={busy}><Download size={15}/> Export CSV</button>
      </div>
    </header>
    {error&&<div className="jd-error" role="alert">{error}<button onClick={()=>setError('')} aria-label="Dismiss error"><X size={15}/></button></div>}
    {notice&&<div className="jd-notice" role="status">{notice}<button onClick={()=>setNotice('')} aria-label="Dismiss notice"><X size={15}/></button></div>}
    <div className="jd-stats"><span><b>{total.toLocaleString()}</b> saved JDs</span><span><b>{history.length}</b> recent import batches</span>
      <span><b>{matching?.total_candidates??'—'}</b> candidates assessed for selected JD</span></div>
    {isHR&&<details className="jd-import-panel"><summary><FileSpreadsheet size={17}/> Excel / CSV JD import, template and settings</summary>
      <p>Required columns: <b>Job Posting Title</b> and <b>Description</b>. Optional columns include skills, experience, qualification, location and linked job-opening ID. Preview before saving.</p>
      <div className="jd-actions"><button onClick={()=>void triggerExport('/template.xlsx','sass-hrm-jd-import-template.xlsx')} disabled={busy}><Download size={14}/> Download Excel template</button>
        <label>Duplicate policy <select value={mode} onChange={e=>setMode(e.target.value as 'skip'|'reject')}>
          <option value="skip">Skip matching JDs</option><option value="reject">Reject entire import</option></select></label>
        <label>Invalid rows <select value={invalidMode} onChange={e=>setInvalidMode(e.target.value as 'reject'|'skip')}>
          <option value="reject">Reject the full import (safer)</option><option value="skip">Skip invalid rows after preview</option>
        </select></label></div>
      <p>Up to <b>1,000,000 rows</b> in the first worksheet, maximum <b>512 MB</b> uploaded file. Large imports can take many minutes and require sufficient server disk space and database capacity.</p>
      <div className="jd-actions"><input ref={fileRef} aria-label="JD Excel or CSV file" type="file" accept=".xlsx,.csv" onChange={e=>{setUploadFile(e.target.files?.[0]||null);setPreview(null)}}/>
        <button className="jd-primary" disabled={!uploadFile||busy} onClick={()=>void previewUpload()}><Upload size={15}/> Preview upload</button></div>
      {preview&&<div className="jd-import-preview"><b>Preview: {preview.filename}</b>
        <p>{preview.total_rows.toLocaleString()} rows · {preview.valid_rows.toLocaleString()} valid · {preview.duplicates.toLocaleString()} duplicates · {preview.invalid_rows.toLocaleString()} invalid ({preview.issues.length} shown)</p>
        {preview.preview.length>0&&<div className="jd-table-wrap"><table><thead><tr><th>Row</th><th>Job title</th><th>Department</th><th>Location</th></tr></thead><tbody>{preview.preview.map(r=><tr key={r.row}><td>{r.row}</td><td>{r.title}</td><td>{r.department||'—'}</td><td>{r.location||'—'}</td></tr>)}</tbody></table></div>}
        {preview.issues.map(issue=><p key={issue.row} className="jd-error">Row {issue.row}: {issue.problem}</p>)}
        <button className="jd-primary" disabled={busy||(invalidMode==='reject'&&preview.invalid_rows>0)||!preview.valid_rows} onClick={()=>void commitImport()}><CheckCircle2 size={16}/> Confirm and import valid JDs</button>
      </div>}
      {!!history.length&&<div className="jd-history"><b>Import history</b>{history.slice(0,10).map(row=><p key={row.id}>{row.filename} · {row.rows_imported} imported · {row.rows_skipped} skipped · {row.remaining} JDs remaining</p>)}</div>}
    </details>}
    <div className="jd-search-row"><form onSubmit={e=>{e.preventDefault();setApplied(query);setPage(1)}}>
      <Search size={17}/><input aria-label="Search job titles and descriptions" placeholder="Search job title, skills or JD text…" value={query} onChange={e=>setQuery(e.target.value)}/>
      <button type="submit"><Search size={14}/> Search</button></form>
      <label><Filter size={15}/> Status <select value={filterStatus} onChange={e=>{setFilterStatus(e.target.value);setPage(1)}}>
        <option value="">All</option><option>Open</option><option>Paused</option><option>Closed</option></select></label></div>
    <div className="jd-table-wrap"><table><thead><tr><th>Job posting title</th><th>Department</th><th>Location</th><th>Required skills</th><th>Status</th><th>Actions</th></tr></thead>
      <tbody>{list.map(jd=><tr key={jd.id} className={selected?.id===jd.id?'jd-active':''}>
        <td><b>{jd.title}</b><small>#{jd.id} · {jd.employment_type}</small></td><td>{jd.department||'—'}</td><td>{jd.location||'—'}</td>
        <td>{jd.required_skills||'Extract from description'}</td><td>{jd.status}</td>
        <td><div className="jd-actions"><button onClick={()=>selectJD(jd)} disabled={busy}><Target size={14}/> Match candidates</button>
          {isHR&&<><button aria-label={`Edit ${jd.title}`} onClick={()=>openForm(jd)} disabled={busy}><Pencil size={14}/></button>
          <button className="jd-danger" aria-label={`Delete ${jd.title}`} onClick={()=>{setDeleteId(jd.id);setDeleteConfirm('')}} disabled={busy}><Trash2 size={14}/></button></>}</div></td></tr>)}
        {!list.length&&<tr><td colSpan={6}>{loading?'Loading…':'No saved job descriptions. Add one manually or import an Excel sheet.'}</td></tr>}</tbody></table></div>
    <div className="jd-pagination"><span>Showing {list.length} of {total} JDs · page {page}</span>
      <div className="jd-actions"><button disabled={page<=1||busy} onClick={()=>setPage(v=>v-1)}>Previous</button>
        <button disabled={page*20>=total||busy} onClick={()=>setPage(v=>v+1)}>Next</button></div></div>
    {selected&&<div className="jd-match-panel"><div className="jd-match-header"><div><h3>Candidate ATS match — {selected.title}</h3>
      <p>{selected.description}</p><small>{selected.required_skills?'Required skills: '+selected.required_skills:'Skills inferred from JD text where recognized'}</small></div>
      <div className="jd-actions"><label>Minimum score <select value={minScore} onChange={e=>setMinScore(Number(e.target.value))}>{[0,25,40,50,60,70,80,90].map(v=><option value={v} key={v}>{v}%</option>)}</select></label>
        <button className="jd-primary" disabled={busy} onClick={()=>void match(selected)}><Target size={15}/> Recalculate ATS %</button>
        <button disabled={busy||!matching} onClick={()=>void saveMatch()}>Save ATS results to MySQL</button>
        <button onClick={()=>{setSelected(null);setMatching(null)}} aria-label="Close results"><X size={15}/></button></div></div>
      {matching&&<><p className="jd-match-disclaimer">{matching.disclaimer} Scored {matching.total_candidates} candidate(s), showing up to {matching.items.length} matches at or above {matching.min_score}%.</p>
        <div className="jd-table-wrap"><table><thead><tr><th>Candidate</th><th>ATS match estimate</th><th>Skill evidence</th><th>Review</th></tr></thead><tbody>
          {matching.items.map((m,index)=><tr key={m.candidate_id}>
            <td><strong>{index+1}. {m.name}</strong><small>{m.job_title} · {m.stage}{m.experience_years!==null?` · ${m.experience_years} years`:''}</small></td>
            <td><span className="jd-score">{m.score_percent}%</span><div className="jd-score-track"><span style={{width:`${m.score_percent}%`}}/></div></td>
            <td><small>Matched: {m.matched_skills.join(', ')||'No stated matches'}</small><small>Not evidenced: {m.missing_skills.join(', ')||'—'}</small></td>
            <td><details><summary>Score factors</summary>{m.components.map(c=><div key={c.name} className="jd-factor">{c.name}: {c.evidence_percent}% evidence · weight {c.weight}</div>)}</details>
              {onOpenCandidate&&<button onClick={()=>onOpenCandidate(m.candidate_id)}>Open candidate profile</button>}
              {isHR&&<button disabled={busy} onClick={()=>{setDecisionCandidate(m);setDecisionReason('')}}>HR shortlist review</button>}</td></tr>)}
          {!matching.items.length&&<tr><td colSpan={4}>No candidates meet this score. Try a lower threshold, import candidates, or check JD skill requirements.</td></tr>}</tbody></table></div>
      </>}
      {busy&&!matching&&<p>Calculating candidate match percentages…</p>}
      {decisionCandidate&&isHR&&<div className="jd-review-box"><strong>Human shortlist review: {decisionCandidate.name}</strong>
        <label>Decision <select value={decisionType} onChange={e=>setDecisionType(e.target.value as typeof decisionType)}>
          <option>Shortlisted</option><option>Hold</option><option>Rejected</option></select></label>
        <label>Rationale (required)<textarea rows={2} minLength={8} maxLength={1200} value={decisionReason} onChange={e=>setDecisionReason(e.target.value)}/></label>
        <div className="jd-actions"><button onClick={()=>setDecisionCandidate(null)}>Cancel</button>
          <button disabled={busy||decisionReason.trim().length<8} onClick={()=>void submitShortlist()}>Save HR decision</button></div></div>}
      <div className="jd-review-box"><h4>Saved ATS matches and review history</h4>
        <p className="jd-match-disclaimer">Saved estimates are historical; recalculating does not automatically change old reviews or hiring stages.</p>
        <div className="jd-actions"><button disabled={busy} onClick={()=>void loadSaved(selected)}>Refresh history</button>
          {savedRuns.map(r=><button key={r.id} onClick={()=>void openSaved(r.id)} disabled={busy}>Run #{r.id} · {r.saved_matches} matches</button>)}</div>
        {savedDetail&&<><small>{savedDetail.notice}</small><div className="jd-table-wrap"><table><thead>
          <tr><th>Candidate</th><th>Saved ATS estimate</th><th>Human review</th></tr></thead><tbody>
          {savedDetail.items.map(r=><tr key={r.id}><td>{r.name||'Candidate removed'}</td>
          <td>{r.match_score}%</td><td>{r.reviewed_status}
          <button onClick={()=>{setReviewResult(r.id);setReviewNote('')}} disabled={busy}>Record review</button></td></tr>)}
          {!savedDetail.items.length&&<tr><td colSpan={3}>No saved candidates in this run.</td></tr>}
          </tbody></table></div></>}
        {reviewResult!==null&&<div className="jd-review-box"><strong>Review saved match #{reviewResult}</strong>
          <label>Review outcome <select value={reviewAction} onChange={e=>setReviewAction(e.target.value as typeof reviewAction)}>
            <option value="NeedsReview">Needs review</option><option value="Consider">Consider</option><option value="NotNow">Not now</option></select></label>
          <label>Review note (required)<textarea rows={2} minLength={8} maxLength={1500} value={reviewNote} onChange={e=>setReviewNote(e.target.value)}/></label>
          <div className="jd-actions"><button onClick={()=>setReviewResult(null)}>Cancel</button>
            <button disabled={busy||reviewNote.trim().length<8} onClick={()=>void submitReview()}>Save review</button></div></div>}
        {!!shortlist.length&&<><h4>HR shortlist decisions</h4><ul>{shortlist.slice(0,10).map(v=><li key={v.id}>
          {v.candidate_name||`Candidate #${v.candidate_id}`} — {v.decision}: {v.rationale}</li>)}</ul></>}
      </div>
    </div>}
    {isHR&&<div className="jd-admin-footer"><button className="jd-danger" onClick={async()=>{try{const p=await request<{job_descriptions:number}>('/clear-all/preview');setBulkCount(p.job_descriptions);setBulkConfirm('');setBulkReason('')}catch(e){setError(e instanceof Error?e.message:'Preview failed')}}} disabled={busy}><Trash2 size={14}/> Remove all job descriptions</button>
      <small>Permanent removal deletes JDs and import history, never candidates or job openings.</small></div>}
    {editor&&<div className="jd-overlay" role="dialog" aria-modal="true" aria-label="Job description editor"><form className="jd-dialog" onSubmit={e=>void save(e)}>
      <div className="jd-dialog-head"><h3>{editingId?'Edit job description':'Add job description manually'}</h3><button type="button" aria-label="Close editor" onClick={()=>setEditor(null)}><X size={18}/></button></div>
      <div className="jd-form-grid">
        {([['title','Job Posting Title *'],['department','Department'],['location','Location'],['required_skills','Required skills (comma-separated)'],['preferred_skills','Preferred skills'],['education','Qualification / education']] as const).map(([key,label])=><label key={key}>{label}<input required={key==='title'} value={editor[key]} onChange={e=>setEditor({...editor,[key]:e.target.value})} maxLength={key.includes('skills')?3500:191}/></label>)}
        <label>Employment type<select value={editor.employment_type} onChange={e=>setEditor({...editor,employment_type:e.target.value})}>{['Full-time','Part-time','Contract','Internship','Temporary'].map(v=><option key={v}>{v}</option>)}</select></label>
        <label>Minimum experience (years)<input type="number" min={0} max={60} step="0.5" value={editor.min_experience} onChange={e=>setEditor({...editor,min_experience:Number(e.target.value)})}/></label>
        <label>Status<select value={editor.status} onChange={e=>setEditor({...editor,status:e.target.value})}>{['Open','Paused','Closed'].map(v=><option key={v}>{v}</option>)}</select></label>
        <label>Existing recruitment opening ID (optional)<input type="number" min={1} value={editor.job_opening_id??''} onChange={e=>setEditor({...editor,job_opening_id:e.target.value?Number(e.target.value):null})}/></label>
        <label className="jd-full">Job Description *<textarea required rows={8} minLength={10} maxLength={30000} placeholder="Responsibilities, required qualifications, tools, and competencies…" value={editor.description} onChange={e=>setEditor({...editor,description:e.target.value})}/></label>
      </div><div className="jd-actions jd-dialog-actions"><button type="button" onClick={()=>setEditor(null)}>Cancel</button><button className="jd-primary" disabled={busy} type="submit"><CheckCircle2 size={14}/> {busy?'Saving…':'Save job description'}</button></div>
    </form></div>}
    {deleteId!==null&&<div className="jd-overlay" role="dialog" aria-modal="true" aria-label="Permanent job description deletion"><div className="jd-dialog jd-dialog-small"><h3>Delete JD #{deleteId} permanently?</h3>
      <p>This permanently removes the JD. Historical matching reviews may retain anonymized references with the JD link cleared. Candidates and job openings remain.</p>
      <label>Type DELETE to confirm<input value={deleteConfirm} onChange={e=>setDeleteConfirm(e.target.value)}/></label>
      <div className="jd-actions"><button onClick={()=>setDeleteId(null)}>Cancel</button><button className="jd-danger" disabled={busy||deleteConfirm!=='DELETE'} onClick={()=>void remove()}><Trash2 size={14}/> Permanently delete</button></div></div></div>}
    {bulkCount!==null&&<div className="jd-overlay" role="dialog" aria-modal="true" aria-label="Clear all job descriptions"><div className="jd-dialog jd-dialog-small">
      <h3>Permanently remove all {bulkCount} JDs?</h3><p>Deletes every job description and its import metadata. Employees, candidates and recruitment vacancies remain unchanged.</p>
      <label>Reason (minimum 8 characters)<textarea rows={3} value={bulkReason} onChange={e=>setBulkReason(e.target.value)}/></label>
      <label>Type DELETE ALL JOB DESCRIPTIONS<input value={bulkConfirm} onChange={e=>setBulkConfirm(e.target.value)}/></label>
      <div className="jd-actions"><button onClick={()=>setBulkCount(null)}>Cancel</button><button className="jd-danger" disabled={busy||bulkConfirm!=='DELETE ALL JOB DESCRIPTIONS'||bulkReason.trim().length<8} onClick={()=>void clearAll()}><Trash2 size={14}/> Confirm permanent removal</button></div>
    </div></div>}
  </section>
}
