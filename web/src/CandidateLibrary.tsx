import {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import type {FormEvent} from 'react';
import {ArrowDown, ArrowUp, ChevronLeft, ChevronRight, Download, Eye, FileSpreadsheet, Filter, LocateFixed, Pencil, Plus, Search, Trash2, UploadCloud, X} from 'lucide-react';
import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import './candidate-library.css';

type Candidate=Record<string,any>;
type Results={total:number;page:number;page_size:number;pages:number;items:Candidate[]};
type ImportBatch={id:number;filename:string;rows_imported:number;created_at:string;archive_available:boolean;candidates_remaining:number};
type Options={roles:string[];role_counts:Record<string,number>;educations:string[];stages:string[];sources:string[];total:number;can_delete_imports:boolean;imports:ImportBatch[]};
type ClearPreview={counts:{candidates:number;candidate_profiles:number;import_batches:number;import_chunks:number;interviews:number;recruitment_activity:number;hiring_reviews:number;hiring_events:number};blocked:boolean;message:string};
type Filters={q:string;skills:string;education:string;role:string;location:string;company:string;stage:string;source:string;notice:string;preferred_location:string;designation:string;min_salary:string;max_salary:string;applied_from:string;applied_to:string;min_experience:string;max_experience:string;skill_mode:string;sort:string;direction:string;page_size:string};
const defaultFilters:Filters={q:'',skills:'',education:'',role:'',location:'',company:'',stage:'',source:'',notice:'',preferred_location:'',designation:'',min_salary:'',max_salary:'',applied_from:'',applied_to:'',min_experience:'',max_experience:'',skill_mode:'all',sort:'original',direction:'asc',page_size:'30'};
const initialForm=()=>({name:'',job_title:'',stage:'Applied',source:'Manual',applied_at:new Date().toLocaleDateString('sv-SE'),skills_manual:'',raw_fields:{} as Record<string,string>});
const commonFields=['Email ID','Phone Number','Current Location','Preferred Locations','Total Experience','Curr. Company name','Curr. Company Designation','Annual Salary','Notice period/ Availability to join','Resume Headline','Under Graduation degree','UG Specialization','UG University/institute Name','Post graduation degree','PG specialization','PG university/institute name','Doctorate degree','Doctorate specialization','Doctorate university/institute name','Candidate Profile URL','Screening answers'];
const sortOptions=[['original','Original Excel row order'],['name','Candidate name'],['role','Job role'],['date','Application date'],['experience','Experience'],['salary','Salary (LPA)'],['education','Education'],['location','Location'],['company','Current company'],['stage','Pipeline stage'],['id','Record ID']];
const createParams=(selected:Filters,targetPage:number,includeRaw:boolean)=>{
  const params=new URLSearchParams();
  for(const [key,value] of Object.entries(selected)){
    if(value!=='' && (['page_size','sort','direction','skill_mode'].includes(key) || String(value).trim()))params.set(key,String(value));
  }
  params.set('page',String(targetPage));
  if(includeRaw)params.set('include_raw','true');
  return params;
};
const corePath=`${(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')}/api/candidate-library`;

async function candidateApi<T>(path:string,opts:RequestInit={}):Promise<T>{
  const token=sessionStorage.getItem('sass_token');
  if(!token)throw new Error('Please sign in again to manage candidates.');
  const res=await hrmFetch(corePath+path,{...opts,headers:{Authorization:`Bearer ${token}`,...(opts.headers||{})}});
  if(!res.ok){let detail='';try{const j=await res.json();detail=typeof j?.detail==='string'?j.detail:''}catch{}throw new Error(detail||`Request failed (HTTP ${res.status})`)}
  return res.json() as Promise<T>;
}

const dateDisplay=(v:any)=>String(v||'').slice(0,10)||'—';
const display=(v:any)=>v===null||v===undefined||v===''?'—':String(v);

export function CandidateLibrary(){
  const [filters,setFilters]=useState<Filters>(defaultFilters);
  const [appliedFilters,setAppliedFilters]=useState<Filters>(defaultFilters);
  const [showAllFields,setShowAllFields]=useState(false);
  const [viewer,setViewer]=useState<Candidate|null>(null);
  const [page,setPage]=useState(1);
  const [refreshKey,setRefreshKey]=useState(0);
  const [results,setResults]=useState<Results>({total:0,page:1,page_size:30,pages:1,items:[]});
  const [options,setOptions]=useState<Options>({roles:[],role_counts:{},educations:[],stages:[],sources:[],total:0,can_delete_imports:false,imports:[]});
  const [loading,setLoading]=useState(false);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const [editor,setEditor]=useState<null|{id?:number;form:ReturnType<typeof initialForm>}>(null);
  const [showExtra,setShowExtra]=useState(false);
  const [uploadFile,setUploadFile]=useState<File|null>(null);
  const [confirmDelete,setConfirmDelete]=useState<number|null>(null);
  const [clearPreview,setClearPreview]=useState<ClearPreview|null>(null);
  const [clearTyped,setClearTyped]=useState('');
  const [clearReason,setClearReason]=useState('');
  const [confirmImportDelete,setConfirmImportDelete]=useState<ImportBatch|null>(null);
  const [importDeleteMode,setImportDeleteMode]=useState<'archive'|'all'>('archive');
  const [importDeleteTyped,setImportDeleteTyped]=useState('');
  const fileRef=useRef<HTMLInputElement>(null);
  const requestId=useRef(0);

  const params=useMemo(()=>createParams(appliedFilters,page,showAllFields),[appliedFilters,page,showAllFields]);
  const pendingFilters=JSON.stringify(filters)!==JSON.stringify(appliedFilters);
  const allExcelColumns=useMemo(()=>Array.from(new Set(results.items.flatMap(item=>Object.keys(item.raw_fields||{})))),[results.items]);
  const query=params.toString();
  const load=useCallback(async()=>{
    const current=++requestId.current;
    setLoading(true);
    try{
      const data=await candidateApi<Results>('?'+query);
      if(current===requestId.current){setResults(data);setError('')}
    }catch(err){if(current===requestId.current)setError(err instanceof Error?err.message:'Unable to load candidate list')}
    finally{if(current===requestId.current)setLoading(false)}
  },[query]);
  useEffect(()=>{const handle=window.setTimeout(()=>void load(),250);return()=>window.clearTimeout(handle)},[load,refreshKey]);
  const loadOptions=useCallback(async()=>{try{setOptions(await candidateApi<Options>('/options'))}catch(err){setError(err instanceof Error?err.message:'Could not load filter choices')}},[]);
  useEffect(()=>{void loadOptions()},[loadOptions,refreshKey]);

  const change=(key:keyof Filters,value:string)=>{
    setFilters(prev=>({...prev,[key]:value}));
    // Sort direction and page size take effect immediately. Text filters require Search/Find.
    if(['sort','direction','page_size'].includes(key))setAppliedFilters(prev=>({...prev,[key]:value}));
    setPage(1);
  };
  const reset=()=>{setFilters({...defaultFilters});setAppliedFilters({...defaultFilters});setPage(1);setRefreshKey(i=>i+1)};
  const reload=()=>setRefreshKey(i=>i+1);
  // Use the shared toolbar refresh instead of showing a duplicate page-level control.
  useRefreshData(reload);
  const runSearch=()=>{setAppliedFilters({...filters});setPage(1);reload();setNotice('')};
  const openViewer=async(id:number)=>{
    setBusy(true);setError('');
    try{setViewer(await candidateApi<Candidate>('/'+id))}
    catch(err){setError(err instanceof Error?err.message:'Unable to view candidate details')}
    finally{setBusy(false)}
  };
  const findCandidate=async()=>{
    setBusy(true);setError('');setNotice('');
    try{
      const q=createParams(filters,1,false);q.set('page_size','1');
      const found=await candidateApi<Results>('?'+q.toString());
      setAppliedFilters({...filters});setPage(1);
      if(!found.total){setNotice('No candidate matches those filters. Try another name, skill, education or job role.');return}
      const first=found.items[0];
      setViewer(await candidateApi<Candidate>('/'+first.id));
      setNotice(`Found ${found.total.toLocaleString()} matching candidate(s). Showing the first match in the selected sort order.`);
    }catch(err){setError(err instanceof Error?err.message:'Unable to find candidate')}
    finally{setBusy(false)}
  };
  const openEditor=async(id?:number)=>{
    setError('');setShowExtra(false);setViewer(null);
    if(!id){setEditor({form:initialForm()});return}
    setBusy(true);
    try{
      const data=await candidateApi<Candidate>('/'+id);
      setEditor({id,form:{name:data.name||'',job_title:data.job_title||'',stage:data.stage||'Applied',
        source:data.source||'Manual',applied_at:String(data.applied_at||'').slice(0,10),
        skills_manual:data.skills_manual||'',raw_fields:data.raw_fields||{}}});
    }catch(err){setError(err instanceof Error?err.message:'Unable to open candidate')}
    finally{setBusy(false)}
  };
  const updateForm=(key:string,value:string)=>setEditor(current=>current?({...current,form:{...current.form,[key]:value}}):null);
  const updateRaw=(key:string,value:string)=>setEditor(current=>current?({...current,form:{...current.form,
      raw_fields:{...current.form.raw_fields,[key]:value}}}):null);
  const save=async(e:FormEvent)=>{
    e.preventDefault();if(!editor)return;setBusy(true);setError('');
    try{
      const path=editor.id?'/'+editor.id:'';
      await candidateApi<{id:number}>(path,{method:editor.id?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(editor.form)});
      setNotice(editor.id?'Candidate updated in MySQL.':'Candidate added to MySQL.');setEditor(null);reload();
    }catch(err){setError(err instanceof Error?err.message:'Unable to save candidate')}
    finally{setBusy(false)}
  };
  const deleteCandidate=async(id:number)=>{
    setBusy(true);setError('');
    try{await candidateApi('/'+id,{method:'DELETE'});setConfirmDelete(null);setNotice('Candidate deleted from MySQL.');reload()}
    catch(err){setError(err instanceof Error?err.message:'Unable to delete candidate')}
    finally{setBusy(false)}
  };
  const askRemoveImport=(batch:ImportBatch)=>{
    setConfirmImportDelete(batch);
    setImportDeleteMode(batch.archive_available?'archive':'all');
    setImportDeleteTyped('');setError('');
  };
  const removeImport=async()=>{
    if(!confirmImportDelete)return;
    if(importDeleteMode==='all'&&importDeleteTyped!=='DELETE')return;
    setBusy(true);setError('');setNotice('');
    try{
      const response=await candidateApi<{candidates_deleted:number;candidates_retained:number}>(
        `/imports/${confirmImportDelete.id}?mode=${importDeleteMode}${importDeleteMode==='all'?'&confirm=DELETE':''}`,{method:'DELETE'});
      setNotice(importDeleteMode==='archive'
        ?`Excel file removed. ${response.candidates_retained.toLocaleString()} imported candidates are still available in MySQL.`
        :`Excel file and ${response.candidates_deleted.toLocaleString()} imported candidates deleted from MySQL.`);
      setConfirmImportDelete(null);setImportDeleteTyped('');setPage(1);reload();
    }catch(err){setError(err instanceof Error?err.message:'Unable to remove imported Excel file')}
    finally{setBusy(false)}
  };
  const openClearAll=async()=>{
    setBusy(true);setError('');setClearTyped('');setClearReason('');
    try{setClearPreview(await candidateApi<ClearPreview>('/clear-all/preview'))}
    catch(err){setError(err instanceof Error?err.message:'Unable to preview candidate deletion')}
    finally{setBusy(false)}
  };
  const clearAll=async()=>{
    if(!clearPreview||clearPreview.blocked||clearTyped!=='CLEAR ALL CANDIDATES'||clearReason.trim().length<10)return;
    setBusy(true);setError('');setNotice('');
    try{
      const response=await candidateApi<{deleted_candidates:number;deleted_import_batches:number;total_candidates:number}>('/clear-all',{
        method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
          confirmation:clearTyped,reason:clearReason.trim(),
          expected_candidates:clearPreview.counts.candidates,expected_import_batches:clearPreview.counts.import_batches
        })
      });
      setClearPreview(null);setClearTyped('');setClearReason('');setViewer(null);
      setNotice(`Candidate database cleared: ${response.deleted_candidates.toLocaleString()} candidate(s) and ${response.deleted_import_batches.toLocaleString()} import batch(es) removed. Total candidates: 0.`);
      setFilters({...defaultFilters});setAppliedFilters({...defaultFilters});setPage(1);reload();
    }catch(err){setError(err instanceof Error?err.message:'Candidate database could not be cleared');
      try{setClearPreview(await candidateApi<ClearPreview>('/clear-all/preview'))}catch{}}
    finally{setBusy(false)}
  };
  const upload=async()=>{
    if(!uploadFile)return;
    if(!uploadFile.name.toLowerCase().endsWith('.xlsx')||uploadFile.size>25*1024*1024){setError('Choose an .xlsx workbook no larger than 25 MB.');return}
    setBusy(true);setError('');setNotice('');
    try{
      // Upload raw XLSX bytes; backend validates ZIP structure and writes one MySQL transaction.
      const token=sessionStorage.getItem('sass_token');
      if(!token)throw new Error('Sign in again before uploading.');
      const r=await hrmFetch(corePath+'/import',{method:'POST',headers:{Authorization:`Bearer ${token}`,
        'Content-Type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'X-Filename':encodeURIComponent(uploadFile.name)},body:uploadFile},170_000);
      const answer=await r.json().catch(()=>({}));
      if(!r.ok)throw new Error(typeof answer.detail==='string'?answer.detail:`Upload failed (HTTP ${r.status})`);
      setNotice(answer.restored_archive
        ?`Original Excel archive restored for ${answer.total.toLocaleString()} existing candidates. No duplicate candidates were inserted.`
        :answer.already_imported?`This file was already imported (${answer.total} existing records). No duplicates were inserted.`:
        `Imported all ${answer.imported} rows to MySQL in original Excel order. The full workbook was archived.`);
      setUploadFile(null);if(fileRef.current)fileRef.current.value='';setPage(1);setAppliedFilters({...filters});reload();
    }catch(err){setError(err instanceof Error?err.message:'Excel import failed')}
    finally{setBusy(false)}
  };
  const exportCsv=async()=>{
    setError('');setBusy(true);
    try{
      const token=sessionStorage.getItem('sass_token');
      const res=await hrmFetch(corePath+'/export.csv?'+query,{headers:{Authorization:`Bearer ${token}`}});
      if(!res.ok)throw new Error(`Export failed (HTTP ${res.status})`);
      const url=URL.createObjectURL(await res.blob());
      const a=document.createElement('a');a.href=url;a.download='candidate-search-results.csv';
      document.body.appendChild(a);a.click();a.remove();window.setTimeout(()=>URL.revokeObjectURL(url),1000);
    }catch(err){setError(err instanceof Error?err.message:'Could not export candidates')}
    finally{setBusy(false)}
  };
  const getOriginal=async(batchId:number,filename:string)=>{
    setError('');
    try{
      const token=sessionStorage.getItem('sass_token');
      const response=await hrmFetch(corePath+`/imports/${batchId}/original`,{headers:{Authorization:`Bearer ${token}`}});
      if(!response.ok)throw new Error(`Could not download original Excel file (HTTP ${response.status})`);
      const url=URL.createObjectURL(await response.blob());const link=document.createElement('a');
      link.href=url;link.download=filename;document.body.appendChild(link);link.click();link.remove();window.setTimeout(()=>URL.revokeObjectURL(url),1000);
    }catch(err){setError(err instanceof Error?err.message:'Download failed')}
  };
  const filteredCount=results.total;
  return <main className="candidate-library">
    <header className="candidate-library-header">
      <div><div className="candidate-eyebrow">TALENT MANAGEMENT / MYSQL CANDIDATE LIBRARY</div>
        <h1>Candidate Search & Database</h1>
        <p>Search every imported candidate, combine job-relevant filters, edit records and preserve original Excel order.</p></div>
      <div className="candidate-header-actions">
        {options.can_delete_imports&&(options.total>0||options.imports.length>0)&&<button type="button" className="candidate-btn danger" onClick={()=>void openClearAll()} disabled={busy}><Trash2 size={16}/> Clear all candidates</button>}
        <button type="button" className="candidate-btn primary" onClick={()=>void openEditor()} disabled={busy}><Plus size={16}/> Add candidate</button>
      </div>
    </header>
    <div className="candidate-stats"><div><span>Matching candidates</span><strong>{filteredCount.toLocaleString()}</strong></div>
      <div><span>Total candidates</span><strong>{options.total.toLocaleString()}</strong></div>
      <div><span>Excel import batches</span><strong>{options.imports.length.toLocaleString()}</strong></div></div>
    {error&&<div className="candidate-error" role="alert">{error}<button aria-label="Dismiss error" onClick={()=>setError('')}><X size={16}/></button></div>}
    {notice&&<div className="candidate-success" role="status">{notice}<button aria-label="Dismiss message" onClick={()=>setNotice('')}><X size={16}/></button></div>}
    {options.total===0&&options.imports.length===0&&<p className="candidate-success" role="status">Candidate database is empty (0 records). Add a candidate or upload your own Excel workbook to begin.</p>}
    <section className="candidate-panel" aria-label="Excel import">
      <div className="candidate-panel-title"><FileSpreadsheet size={20}/><div><h2>Excel → MySQL Import</h2>
        <p>Import every row from the “All Candidates” sheet without removing duplicates. Every original worksheet and hyperlink is saved in a downloadable archive.</p></div></div>
      <div className="candidate-upload-row"><input ref={fileRef} aria-label="Choose candidate Excel workbook" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={e=>setUploadFile(e.target.files?.[0]||null)}/>
        <button className="candidate-btn primary" disabled={!uploadFile||busy} onClick={()=>void upload()}><UploadCloud size={17}/>{busy?'Processing…':'Upload and save to MySQL'}</button></div>
      {!!options.imports.length&&<div className="candidate-imports"><strong>Import history · Excel sheets</strong>
        {options.imports.map(batch=><div className="candidate-import-entry" key={batch.id}>
          <span><b>{batch.filename}</b> · {batch.candidates_remaining.toLocaleString()} candidates remaining of {batch.rows_imported.toLocaleString()} imported · {dateDisplay(batch.created_at)}</span>
          <div className="candidate-import-actions">
            {batch.archive_available?<button type="button" disabled={busy} onClick={()=>void getOriginal(batch.id,batch.filename)}><Download size={14}/> Original XLSX</button>
              :<span className="candidate-archive-removed">Excel file removed · candidates retained</span>}
            {options.can_delete_imports&&<button type="button" className="candidate-remove-excel" disabled={busy} onClick={()=>askRemoveImport(batch)}><Trash2 size={14}/> {batch.archive_available?'Remove Excel':'Delete import'}</button>}
          </div></div>)}</div>}
    </section>
    <section className="candidate-panel" aria-label="Search and filter candidates">
      <div className="candidate-panel-title"><Filter size={20}/><div><h2>Advanced Candidate Filters</h2><p>Filters combine using AND. Comma-separated skills must all appear in candidate text or manually entered skills.</p></div></div>
      <form onSubmit={event=>{event.preventDefault();runSearch()}}>
      <div className="candidate-filter-grid">
        <label className="wide">Search name, email, phone, headline or keywords<input placeholder="Search all candidate details…" value={filters.q} onChange={e=>change('q',e.target.value)}/></label>
        <label className="wide">Required skills (comma-separated)<input placeholder="Java, Spring Boot, SQL" value={filters.skills} onChange={e=>change('skills',e.target.value)}/></label>
        <label>Job role (all {options.roles.length} available)<select value={filters.role} onChange={e=>change('role',e.target.value)}><option value="">All job roles ({options.roles.length})</option>{options.roles.map(r=><option key={r} value={r}>{r} ({options.role_counts?.[r]||0})</option>)}</select></label>
        <label>Education / degree / university<input list="candidate-education-options" value={filters.education} onChange={e=>change('education',e.target.value)} placeholder="Choose or enter B.Tech, MCA, MBA…"/><datalist id="candidate-education-options">{options.educations.map(value=><option key={value} value={value}/>)}</datalist></label>
        <label>Skill matching<select value={filters.skill_mode} onChange={e=>change('skill_mode',e.target.value)}><option value="all">Match ALL required skills</option><option value="any">Match ANY required skill</option></select></label>
        <label>Current location<input placeholder="Hyderabad" value={filters.location} onChange={e=>change('location',e.target.value)}/></label>
        <label>Current company<input placeholder="Current employer" value={filters.company} onChange={e=>change('company',e.target.value)}/></label>
        <label>Preferred work location<input placeholder="Pune, Bengaluru, Remote…" value={filters.preferred_location} onChange={e=>change('preferred_location',e.target.value)}/></label>
        <label>Current designation<input placeholder="Software Engineer" value={filters.designation} onChange={e=>change('designation',e.target.value)}/></label>
        <label>Pipeline stage<select value={filters.stage} onChange={e=>change('stage',e.target.value)}><option value="">All stages</option>{options.stages.map(s=><option key={s}>{s}</option>)}</select></label>
        <label>Candidate source<select value={filters.source} onChange={e=>change('source',e.target.value)}><option value="">All sources</option>{options.sources.map(s=><option key={s}>{s}</option>)}</select></label>
        <label>Minimum experience (years)<input type="number" min="0" max="80" step="0.5" value={filters.min_experience} onChange={e=>change('min_experience',e.target.value)}/></label>
        <label>Maximum experience (years)<input type="number" min="0" max="80" step="0.5" value={filters.max_experience} onChange={e=>change('max_experience',e.target.value)}/></label>
        <label>Availability / notice period<input placeholder="Immediate, 15 Days…" value={filters.notice} onChange={e=>change('notice',e.target.value)}/></label>
        <label>Minimum current salary (LPA)<input type="number" min="0" step="0.5" value={filters.min_salary} onChange={e=>change('min_salary',e.target.value)}/></label>
        <label>Maximum current salary (LPA)<input type="number" min="0" step="0.5" value={filters.max_salary} onChange={e=>change('max_salary',e.target.value)}/></label>
        <label>Applied on or after<input type="date" value={filters.applied_from} onChange={e=>change('applied_from',e.target.value)}/></label>
        <label>Applied on or before<input type="date" value={filters.applied_to} onChange={e=>change('applied_to',e.target.value)}/></label>
      </div>
      <div className="candidate-sort-bar"><label>Sort by <select value={filters.sort} onChange={e=>change('sort',e.target.value)}>{sortOptions.map(([v,t])=><option value={v} key={v}>{t}</option>)}</select></label>
        <button type="button" className="candidate-btn secondary" onClick={()=>change('direction',filters.direction==='asc'?'desc':'asc')}>
          {filters.direction==='asc'?<ArrowUp size={15}/>:<ArrowDown size={15}/>} {filters.direction==='asc'?'Ascending':'Descending'}</button>
        <label>Rows per page <select value={filters.page_size} onChange={e=>change('page_size',e.target.value)}>{['20','30','50','100'].map(s=><option key={s}>{s}</option>)}</select></label>
        <button type="button" className="candidate-btn secondary" onClick={reset}><X size={15}/> Clear filters</button>
        <button type="submit" className="candidate-btn primary" disabled={busy||loading}><Search size={16}/> Search Candidates</button>
        <button type="button" className="candidate-btn secondary" disabled={busy||loading} onClick={()=>void findCandidate()}><LocateFixed size={16}/> Find Candidate</button>
        {pendingFilters&&<span className="candidate-pending" role="status">Filters changed · click Search or Find to apply</span>}</div>
      </form>
    </section>
    <section className="candidate-panel candidate-results" aria-label="Filtered candidate results">
      <div className="candidate-panel-title"><Search size={20}/><div><h2>Candidate List</h2><p>{loading?'Loading records…':`${results.total.toLocaleString()} results · Page ${results.page} of ${results.pages}`}</p></div>
        <div className="candidate-result-controls"><label className="candidate-column-toggle"><input type="checkbox" checked={showAllFields} onChange={event=>setShowAllFields(event.target.checked)}/> Show every original Excel column</label>
        <button type="button" className="candidate-btn secondary" disabled={busy||!results.total} onClick={()=>void exportCsv()}><Download size={16}/> Export filtered CSV (Excel)</button></div></div>
      <div className="candidate-table-scroll"><table className={showAllFields?'candidate-full-table':''}>
        <thead>{showAllFields?<tr><th>Excel order</th><th>Record ID</th>{allExcelColumns.map(column=><th key={column}>{column}</th>)}<th>Current role</th><th>Confirmed skills</th><th>Stage</th><th>Actions</th></tr>:
          <tr><th>Excel order</th><th>Candidate</th><th>Job role</th><th>Skills / headline</th><th>Education</th><th>Experience</th><th>Location</th><th>Company</th><th>Applied</th><th>Stage</th><th>Actions</th></tr>}</thead>
        <tbody>{results.items.map(item=>showAllFields?<tr key={item.id}>
            <td>{display(item.source_order)}</td><td>{item.id}</td>
            {allExcelColumns.map(column=><td key={column} title={String(item.raw_fields?.[column]||'')}>{display(item.raw_fields?.[column])}</td>)}
            <td>{display(item.job_title)}</td><td>{display(item.skills_manual)}</td><td>{display(item.stage)}</td>
            <td><div className="candidate-row-actions">
              <button type="button" title="View every candidate field" aria-label={`View ${item.name}`} onClick={()=>void openViewer(item.id)} disabled={busy}><Eye size={16}/></button>
              <button type="button" title="Edit candidate and original fields" aria-label={`Edit ${item.name}`} onClick={()=>void openEditor(item.id)} disabled={busy}><Pencil size={16}/></button>
              <button type="button" title="Delete candidate" aria-label={`Delete ${item.name}`} onClick={()=>setConfirmDelete(item.id)} disabled={busy}><Trash2 size={16}/></button></div></td>
          </tr>:<tr key={item.id}><td>{display(item.source_order)}</td>
          <td><strong>{display(item.name)}</strong><small>{display(item.email)} · {display(item.phone)}</small></td>
          <td>{display(item.job_title)}</td><td className="candidate-clamp" title={item.resume_headline||''}>{display(item.skills_manual||item.resume_headline)}</td>
          <td>{display(item.education||item.degree)}</td><td>{item.experience_years===null||item.experience_years===undefined?display(item.experience_raw):Number(item.experience_years).toFixed(1)+' yrs'}</td>
          <td>{display(item.location)}</td><td>{display(item.company)}</td><td>{dateDisplay(item.applied_at)}</td><td>{display(item.stage)}</td>
          <td><div className="candidate-row-actions"><button type="button" title="View every candidate field" aria-label={`View ${item.name}`} onClick={()=>void openViewer(item.id)} disabled={busy}><Eye size={16}/></button>
            <button type="button" title="Edit candidate and original fields" aria-label={`Edit ${item.name}`} onClick={()=>void openEditor(item.id)} disabled={busy}><Pencil size={16}/></button>
            <button type="button" title="Delete candidate" aria-label={`Delete ${item.name}`} onClick={()=>setConfirmDelete(item.id)} disabled={busy}><Trash2 size={16}/></button></div></td></tr>)}
          {!results.items.length&&<tr><td colSpan={showAllFields?allExcelColumns.length+6:11} className="candidate-empty">{loading?'Loading…':'No candidates match these filters.'}</td></tr>}</tbody></table></div>
      <div className="candidate-pagination"><span>Records {results.total?((page-1)*results.page_size+1).toLocaleString():'0'}–{Math.min(page*results.page_size,results.total).toLocaleString()} of {results.total.toLocaleString()}</span>
        <div><button className="candidate-btn secondary" disabled={page===1||loading} onClick={()=>setPage(p=>Math.max(1,p-1))}><ChevronLeft size={16}/> Previous</button>
        <span>Page {page} / {results.pages}</span><button className="candidate-btn secondary" disabled={page>=results.pages||loading} onClick={()=>setPage(p=>p+1)}>Next <ChevronRight size={16}/></button></div></div>
    </section>
    {viewer&&<div className="candidate-overlay"><div className="candidate-dialog candidate-editor" role="dialog" aria-modal="true" aria-label="Candidate full details">
      <div className="candidate-editor-head"><div><h2>{display(viewer.name)} — Full Candidate Profile</h2><p>Read-only view of every saved Excel field and current candidate data.</p></div>
        <button type="button" className="candidate-icon-btn" onClick={()=>setViewer(null)} aria-label="Close candidate details"><X size={20}/></button></div>
      <div className="candidate-detail-meta"><div><b>Current job role</b><span>{display(viewer.job_title)}</span></div><div><b>Current stage</b><span>{display(viewer.stage)}</span></div>
        <div><b>Confirmed skills</b><span>{display(viewer.skills_manual)}</span></div><div><b>Excel order</b><span>{display(viewer.source_order)}</span></div>
        <div><b>Imported worksheet</b><span>{display(viewer.source_sheet)}</span></div><div><b>Original row</b><span>{display(viewer.source_row)}</span></div></div>
      <div className="candidate-details-list">{Object.entries(viewer.raw_fields||{}).map(([label,value])=><div key={label}><strong>{label}</strong><span>{display(value)}</span></div>)}</div>
      <div className="candidate-dialog-actions"><button type="button" className="candidate-btn secondary" onClick={()=>setViewer(null)}>Close</button>
        <button type="button" className="candidate-btn primary" onClick={()=>void openEditor(viewer.id)}><Pencil size={16}/> Edit this candidate</button></div>
    </div></div>}
    {clearPreview&&<div className="candidate-overlay"><div className="candidate-dialog" role="dialog" aria-modal="true" aria-label="Clear entire candidate database">
      <h2>Clear all candidates from MySQL?</h2>
      <p>This permanent operation removes <strong>{clearPreview.counts.candidates.toLocaleString()} candidates</strong>, <strong>{clearPreview.counts.import_batches.toLocaleString()} Excel import batches</strong>, their archived files and associated hiring-stage review history. It preserves employees, published payroll, job openings and the HR audit trail.</p>
      <p><strong>Back up your MySQL database before proceeding.</strong> This action cannot be undone from SASS HRM.</p>
      {clearPreview.blocked?<div className="candidate-error" role="alert">Deletion blocked: {clearPreview.counts.interviews} linked interview(s) and {clearPreview.counts.recruitment_activity} recruitment activity record(s) must be resolved first. No records have been deleted.</div>:
        <div className="candidate-clear-controls">
          <label>Reason for clearing all candidates (minimum 10 characters)<textarea rows={3} maxLength={500} value={clearReason} onChange={e=>setClearReason(e.target.value)} placeholder="Explain why the database must be emptied"/></label>
          <label>Type CLEAR ALL CANDIDATES to confirm<input autoComplete="off" value={clearTyped} onChange={e=>setClearTyped(e.target.value)} placeholder="CLEAR ALL CANDIDATES"/></label>
        </div>}
      {error&&<div className="candidate-error" role="alert">{error}</div>}
      <div className="candidate-dialog-actions"><button type="button" className="candidate-btn secondary" disabled={busy} onClick={()=>{setClearPreview(null);setError('')}}>Cancel</button>
        {!clearPreview.blocked&&<button type="button" className="candidate-btn danger" disabled={busy||clearTyped!=='CLEAR ALL CANDIDATES'||clearReason.trim().length<10} onClick={()=>void clearAll()}><Trash2 size={16}/> Permanently clear candidate database</button>}
      </div>
    </div></div>}
    {confirmImportDelete&&<div className="candidate-overlay"><div className="candidate-dialog" role="dialog" aria-modal="true" aria-label="Remove imported Excel sheet">
      <h2>Remove imported Excel sheet?</h2>
      <p><strong>{confirmImportDelete.filename}</strong> has {confirmImportDelete.candidates_remaining.toLocaleString()} candidate records currently linked to this import.</p>
      <div className="candidate-delete-choices">
        <label className="candidate-delete-choice"><input type="radio" name="candidate-import-removal" value="archive" checked={importDeleteMode==='archive'} disabled={!confirmImportDelete.archive_available||busy} onChange={()=>{setImportDeleteMode('archive');setImportDeleteTyped('')}}/>
          <span><b>Remove Excel file only (recommended)</b><small>Delete the stored XLSX archive, but keep every imported candidate, skill, filter, edit and Excel row order in MySQL.</small></span></label>
        <label className="candidate-delete-choice"><input type="radio" name="candidate-import-removal" value="all" checked={importDeleteMode==='all'} disabled={busy} onChange={()=>{setImportDeleteMode('all');setImportDeleteTyped('')}}/>
          <span><b>Delete Excel file AND imported candidates</b><small>Permanently delete this import and its {confirmImportDelete.candidates_remaining.toLocaleString()} remaining candidate records. Candidates from other imports and manually added candidates are untouched. Linked hiring records block deletion.</small></span></label>
      </div>
      {importDeleteMode==='all'&&<label className="candidate-delete-typed">Type DELETE to confirm permanent candidate removal
        <input autoFocus value={importDeleteTyped} onChange={event=>setImportDeleteTyped(event.target.value)} placeholder="DELETE" autoComplete="off"/></label>}
      {error&&<div className="candidate-error" role="alert">{error}</div>}
      <div className="candidate-dialog-actions"><button type="button" className="candidate-btn secondary" disabled={busy} onClick={()=>setConfirmImportDelete(null)}>Cancel</button>
        <button type="button" className="candidate-btn danger" disabled={busy||(importDeleteMode==='all'&&importDeleteTyped!=='DELETE')}
          onClick={()=>void removeImport()}><Trash2 size={16}/>{busy?'Removing…':importDeleteMode==='archive'?'Remove Excel file':'Delete file and candidates'}</button></div>
    </div></div>}
    {confirmDelete!==null&&<div className="candidate-overlay"><div className="candidate-dialog" role="dialog" aria-modal="true" aria-label="Confirm candidate deletion"><h2>Delete candidate?</h2><p>This removes the candidate from MySQL. Existing interview records prevent unsafe deletion. The original uploaded Excel archive is retained if it has not been removed separately.</p>
      <div className="candidate-dialog-actions"><button className="candidate-btn secondary" onClick={()=>setConfirmDelete(null)}>Cancel</button><button className="candidate-btn danger" disabled={busy} onClick={()=>void deleteCandidate(confirmDelete)}><Trash2 size={16}/> Delete permanently</button></div></div></div>}
    {editor&&<div className="candidate-overlay"><div className="candidate-dialog candidate-editor" role="dialog" aria-modal="true" aria-label={editor.id?'Edit candidate':'Add candidate'}>
      <div className="candidate-editor-head"><div><h2>{editor.id?'Edit Candidate & Excel Fields':'Add Candidate'}</h2><p>All changes save to MySQL; original upload archive stays unchanged.</p></div><button className="candidate-icon-btn" aria-label="Close editor" onClick={()=>setEditor(null)}><X size={20}/></button></div>
      <form onSubmit={e=>void save(e)}><div className="candidate-editor-grid">
        <label>Full name *<input required maxLength={191} value={editor.form.name} onChange={e=>updateForm('name',e.target.value)}/></label>
        <label>Job role *<input required list="candidate-all-job-roles" maxLength={191} value={editor.form.job_title} onChange={e=>updateForm('job_title',e.target.value)}/><datalist id="candidate-all-job-roles">{options.roles.map(role=><option key={role} value={role}/>)}</datalist></label>
        <label>Pipeline stage<select value={editor.form.stage} onChange={e=>updateForm('stage',e.target.value)}>{['Applied','Screening','Assessment','Interview','Offer','Hired','Rejected',...options.stages.filter(s=>!['Applied','Screening','Assessment','Interview','Offer','Hired','Rejected'].includes(s))].map(s=><option key={s}>{s}</option>)}</select></label>
        <label>Source<input maxLength={191} value={editor.form.source} onChange={e=>updateForm('source',e.target.value)}/></label>
        <label>Application date<input type="date" value={editor.form.applied_at} onChange={e=>updateForm('applied_at',e.target.value)}/></label>
        <label>Confirmed skills (comma-separated)<input value={editor.form.skills_manual} onChange={e=>updateForm('skills_manual',e.target.value)} placeholder="Java, React, AWS"/></label>
      </div>
      <button type="button" className="candidate-toggle" aria-expanded={showExtra} onClick={()=>setShowExtra(v=>!v)}>{showExtra?'Hide':'Show / Edit'} all original Excel columns ({Object.keys(editor.form.raw_fields).length})</button>
      {showExtra&&<div className="candidate-editor-grid candidate-fields">{Array.from(new Set([...commonFields,...Object.keys(editor.form.raw_fields)])).filter(key=>!['Name','Job Title','Latest Pipeline Stage'].includes(key)).map(key=><label key={key}>{key}
        {String(editor.form.raw_fields[key]||'').length>110?<textarea rows={3} value={editor.form.raw_fields[key]||''} onChange={e=>updateRaw(key,e.target.value)}/>:<input value={editor.form.raw_fields[key]||''} onChange={e=>updateRaw(key,e.target.value)}/>}</label>)}</div>}
      <div className="candidate-dialog-actions"><button type="button" className="candidate-btn secondary" onClick={()=>setEditor(null)}>Cancel</button><button type="submit" className="candidate-btn primary" disabled={busy}>{busy?'Saving…':editor.id?'Save changes':'Create candidate'}</button></div></form>
    </div></div>}
  </main>
}
