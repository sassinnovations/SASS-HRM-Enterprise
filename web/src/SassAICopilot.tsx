import {pageFromPath} from './pageRoutes';
import React,{useEffect,useMemo,useRef,useState} from 'react';
import {ArrowRight,BookOpen,CheckCircle2,ChevronRight,ClipboardCheck,Copy,Database,FolderOpen,LockKeyhole,MessageCircle,Send,Settings2,ShieldCheck,Sparkles,X} from 'lucide-react';
import {hrmFetch} from './apiTransport';
import './sass-ai-copilot.css';

type KnowledgeImportRow={title:string;category:string;content:string;feature_key:string;audience:'All'|'Manager'|'Admin'};
type KnowledgeBatchPreview={count:number;status:'Draft';preview_token:string;requires_confirmation:boolean;items:{title:string;feature_key:string;audience:string}[]};

/** Parse CSV on the device, including quoted commas and quoted newlines. */
function parseKnowledgeCSV(text:string):KnowledgeImportRow[]{
 const source=text.replace(/^\uFEFF/,'');
 const parsed:string[][]=[];let cells:string[]=[];let field='';let quoted=false;
 const pushRow=()=>{cells.push(field);if(cells.some(c=>c.trim()))parsed.push(cells);cells=[];field=''};
 for(let i=0;i<source.length;i++){
  const ch=source[i];
  if(quoted){if(ch==='"'&&source[i+1]==='"'){field+='"';i++}else if(ch==='"')quoted=false;else field+=ch;continue}
  if(ch==='"'){if(field.trim())throw new Error('Invalid CSV quote placement');quoted=true}
  else if(ch===','){cells.push(field);field=''}
  else if(ch==='\n')pushRow();
  else if(ch==='\r'&&source[i+1]==='\n'){} // CRLF
  else if(ch==='\r')pushRow();
  else field+=ch;
 }
 if(quoted)throw new Error('CSV has an unclosed quoted field');
 if(cells.length||field)pushRow();
 if(parsed.length<2)throw new Error('Include a header and at least one knowledge row');
 const header=parsed[0].map(x=>x.trim().toLowerCase());
 const required=['title','category','content','feature_key','audience'];
 if(new Set(header).size!==header.length||required.some(h=>!header.includes(h)))throw new Error('Required CSV columns: '+required.join(', '));
 if(parsed.length>51)throw new Error('Import at most 50 articles at a time');
 return parsed.slice(1).map((row,i)=>{
  if(row.length!==header.length)throw new Error(`CSV row ${i+2} has the wrong number of columns`);
  const cell=(name:string)=>row[header.indexOf(name)].trim();
  const audience=(cell('audience')||'All') as KnowledgeImportRow['audience'];
  if(!['All','Manager','Admin'].includes(audience))throw new Error(`CSV row ${i+2} has invalid audience`);
  return {title:cell('title'),category:cell('category'),content:cell('content'),feature_key:cell('feature_key'),audience};
 });
}

type Tab='chat'|'features'|'workflows'|'actions'|'knowledge';
type WorkflowStep={feature_key:string;feature:string;url:string;guidance:string;actions:{operation:string;label:string}[]};
type WorkflowRecipe={key:string;title:string;description:string;steps:WorkflowStep[];guide_only:boolean};
type FeatureCommandPlan={feature_key:string;feature:string;intent:string;target_key:string;target_url:string;guidance:string;declared_api_methods:string[];approved_actions:{operation:string;label:string;effect:string}[];executed:boolean;requires_confirmation:boolean};
type CommandPreview={status:'matched'|'ambiguous'|'not_found'|'unrecognized';intent:string;plans:FeatureCommandPlan[];message:string;executed:boolean};
type AssistantAgent={key:string;label:string;description:string;feature_count:number};
type FeatureIntegration={feature_key:string;feature:string;api_registered:boolean;tables_mapped:number;tables_accessible:number;status:'ready'|'needs-attention';verification:string};
type IntegrationReport={feature_count:number;ready:number;items:FeatureIntegration[];note:string};
type Feature={key:string;label:string;url:string;group:string;settings_key:string;copilot_actions:string[];control_level:string;declared_api_methods:string[]};
type ActionItem={operation:string;label:string;feature:string;effect:string;description:string};
type AdminOffice={id:number;code:string;name:string;city:string;country:string;address:string;timezone:string;is_active:boolean};
type AdminCategory={id:number;name:string;description:string;active:boolean};
type AdminTemplate={id:number;title:string;guidance:string;priority:string;due_offset_days:number;active:boolean};
type ActionHistory={operation:string;state:string;created_at:string};
type MyOptions={unread_notifications:{id:number;title:string}[];personal_events:{id:number;title:string;day:string;start_time:string;notes:string}[];pending_work_mode:{id:number;requested_mode:string}[];pending_corrections:{id:number;work_day:string}[];my_tasks:{id:number;title:string;status:string}[];assignable_staff:{id:number;name:string;code:string}[];offices:AdminOffice[];service_categories:AdminCategory[];task_templates:AdminTemplate[]};
type ControlPlan={feature_key:string;feature:string;intent:string;target_key:string;guidance:string;approved_actions:{operation:string;label:string;effect:string}[];executed:boolean};
const blankOptions:MyOptions={unread_notifications:[],personal_events:[],pending_work_mode:[],pending_corrections:[],my_tasks:[],assignable_staff:[],offices:[],service_categories:[],task_templates:[]};
type FeatureGuide={key:string;title:string;domain:string;url:string;settings_key:string;actions:ActionItem[];guidance:string;knowledge:{id:number;title:string;category:string}[];declared_api_methods:string[];contract_note:string};
type Source={kind:string;title:string;url:string;id?:string;excerpt?:string};
type FeaturedLink={key:string;label:string;url:string};
type Answer={conversation_context?:string;followups?:string[];answer:string;mode:string;sources:Source[];features:FeaturedLink[];actions?:{operation:string;label:string}[]};
type Message={conversationContext?:string;followups?:string[];type:'user'|'bot';text:string;mode?:string;sources?:Source[];features?:FeaturedLink[];actions?:{operation:string;label:string}[]};
type Article={id:number;title:string;category:string;status:'Draft'|'Published';created_at:string;feature_key:string;audience:'All'|'Manager'|'Admin'};
type Proposal={proposal_id:string;preview:string;expires_at:string;operation:string};
type Capabilities={generation_enabled:boolean;mode:string;private_records_sent_to_llm:boolean;external_provider_note:string;provider_status?:'ready'|'missing-key'|'disabled';recent_general_context?:boolean};
type AIHealth={inventoried_features:number;confirmed_action_types:number;published_articles:number;draft_articles:number;policy_documents:number;generation_enabled:boolean;retrieval_mode:string;provider_configured:boolean;vector_search_enabled:boolean};
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
function asList<T>(value:unknown):T[]{return Array.isArray(value)?value.filter((item):item is T=>item!=null):[]}
async function api<T>(path:string,method='GET',body?:unknown):Promise<T>{
 const token=sessionStorage.getItem('sass_token');
 const res=await hrmFetch(API+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{})});
 const json=await res.json().catch(()=>({}));
 if(!res.ok){
  if(res.status===503)throw new Error('SASS AI service is temporarily unavailable (503). Please retry; an administrator should check API and MySQL health.');
  if(res.status>=500)throw new Error(`SASS AI server error (HTTP ${res.status}). Please retry; an administrator can check the backend logs and /api/health.`);
  throw new Error(typeof json.detail==='string'?json.detail:(typeof json.detail==='object'?JSON.stringify(json.detail):`HTTP ${res.status}`));
 }
 return json as T;
}

/** All changes remain opt-in and require explicit confirmation. The client never runs raw tool/SQL calls. */
export function SassAICopilot({user,navigate,activeFeatureKey}:{user:{name:string;role:string};navigate:(key:string)=>void;activeFeatureKey:string}){
 const [tab,setTab]=useState<Tab>('chat');
 const [agents,setAgents]=useState<AssistantAgent[]>([]);
 const [agent,setAgent]=useState('general');
 const threadRef=useRef<HTMLDivElement>(null);
 const [workflows,setWorkflows]=useState<WorkflowRecipe[]>([]);
 const [selectedWorkflow,setSelectedWorkflow]=useState('');
 const [completedWorkflowSteps,setCompletedWorkflowSteps]=useState<string[]>([]);
 const [featureCommand,setFeatureCommand]=useState('');
 const [commandPreview,setCommandPreview]=useState<CommandPreview|null>(null);
 const [commandBusy,setCommandBusy]=useState(false);
 const [suggestedQuestions,setSuggestedQuestions]=useState<string[]>([]);
 const [messages,setMessages]=useState<Message[]>([{type:'bot',text:`Hello ${user.name?.split(' ')[0]||'there'}! I can explain approved policies, find any HRM feature, and help with reviewed actions such as leave, attendance, work arrangements and your personal calendar. What would you like to do?`}]);
 const [draft,setDraft]=useState('');const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [success,setSuccess]=useState('');
 const [features,setFeatures]=useState<Feature[]>([]);const [caps,setCaps]=useState<Capabilities|null>(null);const [search,setSearch]=useState('');
 const [operation,setOperation]=useState<string>('submit_leave');
 const [actionCatalog,setActionCatalog]=useState<ActionItem[]>([]);
 const [aiHealth,setAiHealth]=useState<AIHealth|null>(null);
 const [myOptions,setMyOptions]=useState<MyOptions>(blankOptions);
 const [recentActions,setRecentActions]=useState<ActionHistory[]>([]);
 const [historyOpen,setHistoryOpen]=useState(false);
 const [guide,setGuide]=useState<FeatureGuide|null>(null);
 const [contextGuide,setContextGuide]=useState<FeatureGuide|null>(null);
 const [integrations,setIntegrations]=useState<IntegrationReport|null>(null);const [checkingIntegrations,setCheckingIntegrations]=useState(false);
 const [plan,setPlan]=useState<ControlPlan|null>(null);const [controlIntent,setControlIntent]=useState<'view'|'create'|'edit'|'delete'|'settings'|'help'>('view');
 const [categories,setCategories]=useState<{id:number;name:string}[]>([]);
 const [form,setForm]=useState({start_date:'',end_date:'',leave_type:'Annual Leave',reason:'',category_id:'',subject:'',details:'',day:'',start_time:'',title:'',notes:'',event_id:'',requested_mode:'Remote',effective_date:'',request_id:'',amount:'',category:'Other',expense_date:'',merchant:'',business_purpose:'',cost_center:'',receipt_reference:'',work_day:'',proposed_in:'',proposed_out:'',correction_id:'',task_id:'',status:'In Progress',assignee_id:'',notification_id:'',date_format:'DD MMM YYYY',density:'Comfortable',reduce_motion:false,due_date:'',priority:'Normal',office_id:'',office_code:'',office_name:'',city:'',country:'India',address:'',timezone:'Asia/Kolkata',is_active:true,service_category_id:'',category_name:'',description:'',template_id:'',template_title:'',guidance:'',due_offset_days:'7',admin_reason:''});
 const [proposal,setProposal]=useState<Proposal|null>(null);
 const [articles,setArticles]=useState<Article[]>([]);const [selectedArticle,setSelectedArticle]=useState<number|null>(null);
 const [bulkRows,setBulkRows]=useState<KnowledgeImportRow[]>([]);
 const [bulkPreview,setBulkPreview]=useState<KnowledgeBatchPreview|null>(null);
 const [bulkBusy,setBulkBusy]=useState(false);
 const [article,setArticle]=useState({title:'',category:'HR guidance',content:'',status:'Draft' as 'Draft'|'Published',feature_key:'',audience:'All' as 'All'|'Manager'|'Admin'});
 const admin=user.role==='admin';
 useEffect(()=>{void api<Feature[]>('/ai/copilot/features').then(rows=>setFeatures(asList(rows))).catch(e=>setError(e.message));void api<Capabilities>('/ai/copilot/capabilities').then(value=>{if(value&&typeof value==='object')setCaps(value)}).catch(e=>setError(e.message));void api<AssistantAgent[]>('/ai/copilot/agents').then(rows=>setAgents(asList(rows))).catch(e=>setError(e.message))},[]);
 useEffect(()=>{void api<ActionItem[]>('/ai/copilot/actions/catalog').then(rows=>setActionCatalog(asList(rows))).catch(e=>setError(e.message))},[]);
 useEffect(()=>{if(tab==='actions'){void api<{id:number;name:string}[]>('/request-desk/categories').then(setCategories).catch(e=>setError(e.message));void refreshMyOptions()}if(tab==='knowledge'&&admin){void loadArticles();void api<AIHealth>('/ai/copilot/health').then(setAiHealth).catch(e=>setError(e.message))}},[tab,admin]);
 useEffect(()=>{if(tab==='workflows'&&!(Array.isArray(workflows)&&workflows.length)){void api<{workflows:WorkflowRecipe[]}>('/ai/copilot/workflows').then(r=>setWorkflows(asList(r?.workflows))).catch(e=>setError(e.message))}},[tab,Array.isArray(workflows)?workflows.length:0]);
 useEffect(()=>{
  let live=true;
  if(!activeFeatureKey || activeFeatureKey==='__unavailable__'){setContextGuide(null);return()=>{live=false};}
  void api<FeatureGuide>('/ai/copilot/features/'+encodeURIComponent(activeFeatureKey)+'/guide')
   .then(value=>{if(live)setContextGuide(value)})
   .catch(()=>{if(live)setContextGuide(null)});
  return()=>{live=false};
 },[activeFeatureKey]);
 useEffect(()=>{
  let active=true;
  void api<{questions:string[]}>('/ai/copilot/suggestions'+(activeFeatureKey?'?feature_key='+encodeURIComponent(activeFeatureKey):''))
   .then(value=>{if(active)setSuggestedQuestions(asList(value?.questions))})
   .catch(()=>{if(active)setSuggestedQuestions([])});
  return()=>{active=false};
 },[activeFeatureKey]);
 useEffect(()=>{if(tab==='chat')threadRef.current?.scrollTo({top:threadRef.current.scrollHeight,behavior:'smooth'})},[messages.length,busy,tab]);
 async function previewCommand(event?:React.FormEvent){
  event?.preventDefault();if(!featureCommand.trim()||commandBusy)return;
  setCommandBusy(true);setError('');setCommandPreview(null);
  try{setCommandPreview(await api<CommandPreview>('/ai/copilot/commands/preview','POST',
     {command:featureCommand.trim(),feature_key:activeFeatureKey||''}));}
  catch(e){setError((e as Error).message)}finally{setCommandBusy(false)}
 }
 function selectWorkflow(key:string){setSelectedWorkflow(key);setCompletedWorkflowSteps([])}
 function toggleWorkflowStep(key:string){setCompletedWorkflowSteps(old=>old.includes(key)?old.filter(x=>x!==key):[...old,key])}
 async function checkFeatureConnections(){setCheckingIntegrations(true);setError('');try{setIntegrations(await api<IntegrationReport>('/ai/copilot/integrations'))}catch(e){setError((e as Error).message)}finally{setCheckingIntegrations(false)}}
 const refreshMyOptions=()=>api<MyOptions>('/ai/copilot/actions/my-options').then(value=>setMyOptions(value&&typeof value==='object'?{...blankOptions,...value,unread_notifications:asList(value.unread_notifications),personal_events:asList(value.personal_events),pending_work_mode:asList(value.pending_work_mode),pending_corrections:asList(value.pending_corrections),my_tasks:asList(value.my_tasks),assignable_staff:asList(value.assignable_staff),offices:asList(value.offices),service_categories:asList(value.service_categories),task_templates:asList(value.task_templates)}:blankOptions)).catch(e=>setError(e.message));
 async function showActionHistory(){setError('');try{const data=await api<{items:ActionHistory[]}>('/ai/copilot/actions/history');setRecentActions(data.items);setHistoryOpen(true)}catch(e){setError((e as Error).message)}}
 async function planFeature(key:string,intent:'view'|'create'|'edit'|'delete'|'settings'|'help'){
  setError('');setPlan(null);
  try{setPlan(await api<ControlPlan>('/ai/copilot/control/plan','POST',{feature_key:key,intent}))}
  catch(e){setError((e as Error).message)}
 }
 async function showGuide(key:string){setError('');try{setGuide(await api<FeatureGuide>('/ai/copilot/features/'+encodeURIComponent(key)+'/guide'))}catch(e){setError((e as Error).message)}}
 const featureList=asList<Feature>(features);
 const agentList=asList<AssistantAgent>(agents);
 const questionList=asList<string>(suggestedQuestions);
 const workflowList=asList<WorkflowRecipe>(workflows);
 const actionList=asList<ActionItem>(actionCatalog);
 const filtered=useMemo(()=>featureList.filter(f=>((f?.label||'')+' '+(f?.group||'')+' '+(f?.key||'')).toLowerCase().includes(search.toLowerCase())),[featureList,search]);
 const loadArticles=()=>api<Article[]>('/ai/copilot/knowledge').then(setArticles).catch(e=>setError(e.message));
 // Only previously generated *general* Q&A is offered as follow-up context.
 // Personal record lookups, RAG answers and restricted knowledge never enter chat history for the LLM.
 function generalHistory():{role:'user'|'assistant';content:string}[]{
  if(messages.at(-1)?.mode!=='generated-general')return [];
  const pairs:{role:'user'|'assistant';content:string}[]=[];
  for(let i=messages.length-1;i>0&&pairs.length<6;i-=2){
   if(messages[i].mode!=='generated-general'||messages[i].type!=='bot'||messages[i-1].type!=='user')break;
   pairs.unshift({role:'user',content:messages[i-1].text.slice(0,700)},
                 {role:'assistant',content:messages[i].text.slice(0,700)});
  }
  return pairs.slice(-6);
 }
 async function send(message?:string){const q=(message??draft).trim();if(!q||busy)return;setError('');setSuccess('');setDraft('');
  const history=generalHistory();setMessages(m=>[...m,{type:'user',text:q}]);setBusy(true);try{
  const reply=await api<Answer>('/ai/copilot/ask','POST',{message:q,feature_key:contextGuide?.key,agent,recent_turns:history,conversation_context:messages.at(-1)?.conversationContext});setMessages(m=>[...m,{type:'bot',text:reply.answer,mode:reply.mode,sources:reply.sources,features:reply.features,actions:reply.actions,conversationContext:reply.conversation_context,followups:reply.followups}]);
 }catch(e){setMessages(m=>m.slice(0,-1));setDraft(q);setError((e as Error).message+' Your question has been restored so you can retry.')}finally{setBusy(false)}}
 function exportConversation(){
  if(!messages.length){setError('The chat is empty.');return}
  // Export remains local to the browser; the transcript is not uploaded to HRM.
  if(!window.confirm('Export this conversation to a local text file? It may contain personal HR information. Keep the file private.'))return;
  const transcript=messages.map(m=>`${m.type==='user'?'You':'SASS AI'}: ${m.text}${m.sources?.length?'\nSources: '+m.sources.map(s=>s.title).join('; '):''}`).join('\n\n');
  const url=URL.createObjectURL(new Blob([transcript+'\n'],{type:'text/plain;charset=utf-8'}));
  const link=document.createElement('a');link.href=url;link.download='SASS-AI-conversation.txt';
  document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(url);
  setSuccess('Conversation exported locally. Handle the file as confidential if it contains HR information.');
 }
 function downloadKnowledgeTemplate(){
  const headers='title,category,content,feature_key,audience\n';
  const url=URL.createObjectURL(new Blob([headers],{type:'text/csv;charset=utf-8'}));
  const link=document.createElement('a');link.href=url;link.download='SASS-AI-knowledge-import-template.csv';
  document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(url);
 }
 async function previewKnowledgeFile(file?:File){
  setBulkPreview(null);setBulkRows([]);setError('');setSuccess('');
  if(!file)return;
  if(file.size>250000){setError('CSV is larger than 250 KB. Split into batches of up to 50 articles.');return}
  setBulkBusy(true);
  try{
   const rows=parseKnowledgeCSV(await file.text());
   const preview=await api<KnowledgeBatchPreview>('/ai/copilot/knowledge/bulk/preview','POST',{rows});
   setBulkRows(rows);setBulkPreview(preview);
  }catch(e){setError((e as Error).message)}finally{setBulkBusy(false)}
 }
 async function importKnowledgeDrafts(){
  if(!bulkPreview||!bulkRows.length||bulkBusy)return;
  if(!window.confirm(`Import ${bulkPreview.count} knowledge article(s) as unpublished drafts? Review and publish each article separately.`))return;
  setBulkBusy(true);setError('');
  try{
   const result=await api<{created:number;status:string}>('/ai/copilot/knowledge/bulk/import','POST',
    {rows:bulkRows,preview_token:bulkPreview.preview_token,confirm:'IMPORT_DRAFTS'});
   setSuccess(`${result.created} knowledge drafts imported. Review each before publishing.`);
   setBulkRows([]);setBulkPreview(null);await loadArticles();
  }catch(e){setError((e as Error).message);setBulkPreview(null)}finally{setBulkBusy(false)}
 }
 async function copyAnswer(answer:string){
  try{await navigator.clipboard.writeText(answer);setSuccess('Answer copied to clipboard.')}
  catch{setError('Clipboard access is unavailable. Select the answer text to copy it.')}
 }
 async function prepare(event:React.FormEvent){event.preventDefault();setBusy(true);setError('');setSuccess('');setProposal(null);try{
  let parameters:Record<string,string|number|boolean>={};
  switch(operation){
   case 'submit_leave':parameters={start_date:form.start_date,end_date:form.end_date,leave_type:form.leave_type,reason:form.reason};break;
   case 'submit_service_request':parameters={category_id:Number(form.category_id),subject:form.subject,details:form.details};break;
   case 'create_personal_event':parameters={day:form.day,start_time:form.start_time,title:form.title,notes:form.notes};break;
   case 'edit_personal_event':parameters={event_id:Number(form.event_id),day:form.day,start_time:form.start_time,title:form.title,notes:form.notes};break;
   case 'delete_personal_event':parameters={event_id:Number(form.event_id)};break;
   case 'request_work_mode':parameters={requested_mode:form.requested_mode,reason:form.reason,effective_date:form.effective_date};break;
   case 'cancel_work_mode':parameters={request_id:Number(form.request_id)};break;
   case 'submit_expense':parameters={title:form.title,amount:Number(form.amount),category:form.category,expense_date:form.expense_date||'',merchant:form.merchant,business_purpose:form.business_purpose,cost_center:form.cost_center,receipt_reference:form.receipt_reference};if(!form.expense_date)delete parameters.expense_date;break;
   case 'request_attendance_correction':parameters={work_day:form.work_day,proposed_in:form.proposed_in,proposed_out:form.proposed_out,reason:form.reason};break;
   case 'cancel_attendance_correction':parameters={correction_id:Number(form.correction_id)};break;
   case 'update_task_status':parameters={task_id:Number(form.task_id),status:form.status};break;
   case 'create_hr_task':parameters={assignee_id:Number(form.assignee_id),title:form.title,due_date:form.due_date,priority:form.priority};break;
   case 'mark_notification_read':parameters={notification_id:Number(form.notification_id)};break;
   case 'update_my_preferences':parameters={date_format:form.date_format,density:form.density,reduce_motion:form.reduce_motion};break;
   case 'admin_office_create':case 'admin_office_edit':parameters={code:form.office_code,name:form.office_name,city:form.city,country:form.country,address:form.address,timezone:form.timezone,is_active:form.is_active};if(operation==='admin_office_edit')parameters.office_id=Number(form.office_id);break;
   case 'admin_office_activate':case 'admin_office_deactivate':case 'admin_office_delete':parameters={office_id:Number(form.office_id)};if(operation==='admin_office_delete')parameters.reason=form.admin_reason;break;
   case 'admin_category_create':case 'admin_category_edit':parameters={name:form.category_name,description:form.description};if(operation==='admin_category_edit')parameters.category_id=Number(form.service_category_id);break;
   case 'admin_category_archive':case 'admin_category_restore':case 'admin_category_delete':parameters={category_id:Number(form.service_category_id)};if(operation==='admin_category_delete')parameters.reason=form.admin_reason;break;
   case 'admin_template_create':case 'admin_template_edit':parameters={title:form.template_title,guidance:form.guidance,priority:form.priority,due_offset_days:Number(form.due_offset_days)};if(operation==='admin_template_edit')parameters.template_id=Number(form.template_id);break;
   case 'admin_template_archive':case 'admin_template_restore':case 'admin_template_delete':parameters={template_id:Number(form.template_id)};if(operation==='admin_template_delete')parameters.reason=form.admin_reason;break;
   default:parameters={};
  }
  const result=await api<Proposal>('/ai/copilot/actions/prepare','POST',{operation,parameters});setProposal(result);
 }catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 async function confirm(){if(!proposal||busy)return;setBusy(true);setError('');try{const result=await api<{state:string;result:{id?:number;message?:string;status?:string}}>('/ai/copilot/actions/'+encodeURIComponent(proposal.proposal_id)+'/confirm','POST',{confirm:'CONFIRM'});setSuccess(`Action completed. ${result.result.message||result.result.status||'Saved to HRM'}${result.result.id?' · Record #'+result.result.id:''}.`);setProposal(null);void refreshMyOptions();window.dispatchEvent(new Event('sass-hrm:refresh-data'))}catch(e){setError((e as Error).message);setProposal(null)}finally{setBusy(false)}}
 async function cancel(){if(!proposal)return;const proposalId=proposal.proposal_id;setProposal(null);try{await api('/ai/copilot/actions/'+encodeURIComponent(proposalId)+'/cancel','POST')}catch(e){setError((e as Error).message)}}
 async function editArticle(id:number){setError('');try{const data=await api<typeof article>('/ai/copilot/knowledge/'+id);setArticle(data);setSelectedArticle(id)}catch(e){setError((e as Error).message)}}
 async function saveArticle(event:React.FormEvent){event.preventDefault();setBusy(true);setError('');setSuccess('');try{
  await api('/ai/copilot/knowledge'+(selectedArticle?'/'+selectedArticle:''),selectedArticle?'PUT':'POST',article);
  setSuccess('Knowledge article saved. Published articles are searchable by the copilot.');setSelectedArticle(null);setArticle({title:'',category:'HR guidance',content:'',status:'Draft',feature_key:'',audience:'All'});await loadArticles();
 }catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 async function toggleArticle(item:Article){setBusy(true);setError('');try{await api(`/ai/copilot/knowledge/${item.id}/state`,'PATCH',{status:item.status==='Published'?'Draft':'Published'});await loadArticles()}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 const suggestions=['How do I change an employee code?','Explain what an ATS does','Show my leave balance','Open Employee HRIS','What is RAG in AI?'];
 return <div className="sass-ai-v2">
  <div className="sass-ai-hero"><div className="sass-ai-logo"><Sparkles size={26}/></div><div><span className="sass-ai-eyebrow">SASS INNOVATIONS · ENTERPRISE INTELLIGENCE</span><h2>SASS AI Assistant</h2></div><span className="sass-ai-indicator"><ShieldCheck size={15}/> Role-scoped</span></div>
  <div className="sass-ai-tabs" role="tablist" aria-label="AI Copilot sections">
   {([['chat','Chat',MessageCircle],['features','All features',FolderOpen],['workflows','Workflow center',BookOpen],['actions','Assisted actions',ClipboardCheck],...(admin?([['knowledge','Knowledge studio',Database]] as const):[])] as const).map(([key,label,Icon])=><button key={key} role="tab" aria-selected={tab===key} className={tab===key?'selected':''} onClick={()=>{setTab(key);setError('');setSuccess('')}}><Icon size={16}/>{label}</button>)}
  </div>
   {contextGuide&&<section className="sass-ai-active-feature" aria-label="Current HRM feature">
    <div><small>CONNECTED TO THE SCREEN YOU ARE USING</small><strong>{contextGuide.title}</strong><span>{contextGuide.domain}</span></div>
    <div className="sass-ai-context-actions"><button onClick={()=>{setTab('chat');void send(`How do I use this page: ${contextGuide.title}?`)}}>Ask about page</button><button onClick={()=>{setTab('features');void showGuide(contextGuide.key)}}>Controls</button>{contextGuide.settings_key&&featureList.some(f=>f.key===contextGuide.settings_key)&&<button onClick={()=>navigate(contextGuide.settings_key)}>Settings</button>}</div>
   </section>}
  {error&&<div className="sass-ai-alert error" role="alert"><span>{error}</span>{draft.trim()&&tab==='chat'&&<button type="button" disabled={busy} onClick={()=>void send()}>Retry question</button>}<button type="button" onClick={()=>setError('')} aria-label="Dismiss"><X size={14}/></button></div>}
  {success&&<div className="sass-ai-alert success" role="status"><CheckCircle2 size={17}/>{success}</div>}
  {tab==='chat'&&<div className="sass-ai-chat-layout"><section className="sass-ai-panel"><div className="sass-ai-chat-head"><div><strong>Ask SASS AI</strong><small>{caps?.generation_enabled?'GenAI connected · general chat and HR help':caps?.provider_status==='missing-key'?'GenAI needs an API key · HRM guidance is available':'HR help and follow-ups · general AI is off'}</small></div><div className="sass-ai-chat-tools"><button type="button" onClick={exportConversation}>Export chat</button><button type="button" onClick={()=>{if(window.confirm('Clear this AI conversation from the window?')){setMessages([]);setDraft('');setError('')}}} disabled={busy}>New chat</button></div></div>
    <div className="sass-ai-agent-switch"><label htmlFor="sass-ai-agent">Ask a specialist</label><select id="sass-ai-agent" aria-label="Choose AI assistant" value={agent} onChange={e=>setAgent(e.target.value)}>{agentList.map(item=><option key={item.key} value={item.key}>{item.label}</option>)}</select><small>{agentList.find(item=>item.key===agent)?.description||'Ask about your authorized HRM features or general topics'}</small></div>
    <div className="sass-ai-thread" ref={threadRef} aria-live="polite">{messages.map((m,i)=><div className={`sass-ai-msg ${m.type}`} key={i}><span className="sass-ai-msg-icon">{m.type==='bot'?<Sparkles size={16}/>:user.name?.charAt(0).toUpperCase()}</span><div className="sass-ai-msg-body"><p>{m.text}</p>{m.mode&&<small>{m.mode==='action-guidance'?'Action available · nothing changed yet':m.mode==='generated-rag'?'AI answer using approved sources':m.mode==='generated-general'?'General AI answer · not company policy':m.mode==='assistant-fallback'?'Built-in assistant help':m.mode==='data-backed'?'Your authorized HR records':m.mode==='register-summary'?'Authorized register totals':m.mode==='retrieved-rag'?'Retrieved source evidence':m.mode==='guardrail'?'Access restricted':'Available feature knowledge'}</small>}{m.type==='bot'&&<button type="button" className="sass-ai-copy" title="Copy answer" aria-label="Copy AI answer" onClick={()=>void copyAnswer(m.text)}><Copy size={12}/> Copy</button>}{m.sources&&m.sources.length>0&&<div className="sass-ai-citations"><strong>Sources</strong>{m.sources.slice(0,5).map((s,index)=><div key={index}><span>[{index+1}] {s.kind==='feature'?'Module':s.kind==='policy'?'Policy':s.kind==='own_record'?'My record':s.kind==='organization_record'?'Register':'Knowledge'}: {s.title}</span>{s.url&&(()=>{const key=featureList.find(f=>f.url===s.url)?.key??(s.kind==='policy'?'policies':pageFromPath(s.url));return key&&<button type="button" onClick={()=>navigate(key)}>Open <ArrowRight size={12}/></button>})()}</div>)}</div>}{m.features&&m.features.length>0&&<div className="sass-ai-related">{m.features.map(f=><button key={f.key} onClick={()=>navigate(f.key)}><FolderOpen size={13}/> {f.label} <ChevronRight size={13}/></button>)}</div>}{m.actions&&m.actions.length>0&&<div className="sass-ai-related">{m.actions.map(a=><button key={a.operation} onClick={()=>{setOperation(a.operation);setTab('actions');setProposal(null)}}><ClipboardCheck size={13}/> Review: {a.label}</button>)}</div>}</div></div>)}{busy&&<p className="sass-ai-working">Preparing your answer…</p>}</div>
    {!busy&&messages.at(-1)?.followups?.length? <div className="sass-ai-followups" role="group" aria-label="Follow-up questions">{messages.at(-1)?.followups?.map(prompt=><button type="button" key={prompt} onClick={()=>void send(prompt)}>{prompt} <ArrowRight size={12}/></button>)}</div>:null}
    <form className="sass-ai-compose" onSubmit={e=>{e.preventDefault();void send()}}><input value={draft} onChange={e=>setDraft(e.target.value)} placeholder="Ask anything, or request help with an HRM feature…" maxLength={1000} aria-label="Ask SASS AI"/><button type="submit" disabled={busy||!draft.trim()} aria-label="Send question"><Send size={19}/></button></form>
   </section><aside className="sass-ai-panel sass-ai-info"><strong>{contextGuide?'On this feature':'Suggested questions'}</strong><div className="sass-ai-suggestions"><button type="button" className="sass-ai-pending-shortcut" disabled={busy} onClick={()=>void send('Show my pending HR requests and tasks')}>My pending work <ArrowRight size={13}/></button>{(questionList.length?questionList:suggestions).map(q=><button key={q} onClick={()=>void send(q)}>{q}<ArrowRight size={13}/></button>)}</div><div className="sass-ai-tip"><BookOpen size={17}/><div><strong>Source-grounded answers</strong><p>The assistant retrieves authorized company knowledge for HRM questions. With a configured GenAI model, it can also answer general questions; company rules must be verified against approved sources.</p></div></div><div className="sass-ai-tip"><LockKeyhole size={17}/><div><strong>No unrestricted automation</strong><p>Payroll, hiring decisions, deletion and approvals stay in their existing permission-checked screens. Other assisted changes require your confirmation.</p></div></div></aside></div>}
   {tab==='workflows'&&<section className="sass-ai-panel sass-ai-workflow-center">
    <h3>AI Feature & Workflow Center</h3>
    <p>Plan an operation for any of your authorized HRM features. Commands identify the correct existing screen and show reviewed actions when available; they never change records automatically.</p>
    <form onSubmit={e=>void previewCommand(e)} className="sass-ai-command-form">
     <label htmlFor="sass-ai-command-input">What would you like to do?</label>
     <div><input id="sass-ai-command-input" value={featureCommand} onChange={e=>setFeatureCommand(e.target.value)} placeholder="Edit Employee HRIS, Delete a candidate, Settings for Payroll…" maxLength={400} required aria-label="Plan an HRM feature command"/><button disabled={commandBusy||!featureCommand.trim()} type="submit">{commandBusy?'Checking…':'Plan command'}</button></div>
    </form>
    <div className="sass-ai-command-examples">{['Edit Employee HRIS','Settings for Payroll workbench','Create HR tasks','View Recruitment ATS'].map(example=><button key={example} type="button" onClick={()=>{setFeatureCommand(example);setCommandPreview(null)}}>{example}</button>)}</div>
    {commandPreview&&<div className="sass-ai-command-result" role="status"><strong>{commandPreview.status==='matched'?'Matched authorized feature':commandPreview.status==='ambiguous'?'Choose a feature':'Unable to find a permitted feature'}</strong><p>{commandPreview.message}</p>{commandPreview.plans.map(plan=><div className="sass-ai-command-plan" key={plan.feature_key}>
     <strong>{plan.feature} · {plan.intent}</strong><p>{plan.guidance}</p><small>Declared API methods: {plan.declared_api_methods.join(', ')||'None inventoried'} · No operation executed</small>
     <div className="sass-ai-workflow-buttons"><button type="button" onClick={()=>navigate(plan.target_key)}>Open permitted screen <ArrowRight size={13}/></button>{plan.approved_actions.map(action=><button type="button" key={action.operation} onClick={()=>{setOperation(action.operation);setTab('actions');setProposal(null)}}>Review: {action.label}</button>)}</div>
    </div>)}</div>}
    <h3>Guided cross-module workflows</h3><p>These guides connect existing HRM modules. Select a workflow, open its steps and tick them off in this window; the checklist is local and does not mark backend records complete.</p>
    <div className="sass-ai-workflow-grid">{workflowList.map(flow=><button type="button" className={selectedWorkflow===flow.key?'selected':''} key={flow.key} onClick={()=>selectWorkflow(flow.key)}><strong>{flow.title}</strong><small>{asList(flow.steps).length} accessible screens · {flow.description}</small></button>)}</div>
    {selectedWorkflow&&workflowList.filter(flow=>flow.key===selectedWorkflow).map(flow=><div className="sass-ai-workflow-steps" key={flow.key}><h4>{flow.title}</h4><ol>{asList<WorkflowStep>(flow.steps).map(step=><li key={step.feature_key}>
     <label><input type="checkbox" checked={completedWorkflowSteps.includes(step.feature_key)} onChange={()=>toggleWorkflowStep(step.feature_key)}/><span><strong>{step.feature}</strong><small>{step.guidance}</small></span></label>
     <div className="sass-ai-workflow-buttons"><button type="button" onClick={()=>navigate(step.feature_key)}>Open feature <ArrowRight size={13}/></button>{asList<{operation:string;label:string}>(step.actions).map(action=><button type="button" key={action.operation} onClick={()=>{setOperation(action.operation);setTab('actions');setProposal(null)}}>Review: {action.label}</button>)}</div>
    </li>)}</ol><p role="status">{completedWorkflowSteps.length} of {asList(flow.steps).length} steps marked in this window. Backend approvals and record status are unchanged.</p></div>)}
   </section>}

  {tab==='features'&&<section className="sass-ai-panel sass-ai-directory"><div className="sass-ai-directory-head"><div><h3>HRM feature navigator</h3><p>{featureList.length} modules available to your account. Every shortcut opens the existing authorized screen.</p></div><input type="search" placeholder="Search feature or department…" value={search} onChange={e=>setSearch(e.target.value)} aria-label="Search HRM features"/></div><div className="sass-ai-integration-toolbar"><span>Each module operates in the main HRM workspace, while the bot guides on the right without covering records.</span><button type="button" disabled={checkingIntegrations} onClick={()=>void checkFeatureConnections()}><Database size={14}/>{checkingIntegrations?'Checking…':'Check feature connections'}</button></div>
    {integrations&&<p className="sass-ai-integration-summary" role="status"><strong>{integrations.ready} / {integrations.feature_count}</strong> feature API/table contracts accessible to your account. Checks do not verify saving/editing/deleting. Failures need administrator review.</p>}
    <div className="sass-ai-feature-grid">{filtered.map(f=><div className="sass-ai-feature" key={f.key}><div><small>{f.group}</small><strong>{f.label}</strong><small>{f.copilot_actions?.length?`${f.copilot_actions.length} confirmed AI actions`:'Guided feature control'}</small>{integrations&&<small className={asList<FeatureIntegration>(integrations.items).find(x=>x.feature_key===f.key)?.status==='ready'?'sass-ai-ready':'sass-ai-needs-attention'}>{asList<FeatureIntegration>(integrations.items).find(x=>x.feature_key===f.key)?.status==='ready'?'API and tables reachable':'Connection check needs attention'}</small>}</div><div><button onClick={()=>navigate(f.key)}>Open <ArrowRight size={13}/></button><button onClick={()=>void showGuide(f.key)}>Guide</button>{f.settings_key&&featureList.some(x=>x.key===f.settings_key)&&<button className="sass-ai-settings-link" onClick={()=>navigate(f.settings_key)} title="Open related settings"><Settings2 size={15}/></button>}</div></div>)}</div>{filtered.length===0&&<p>No matching features available for your account.</p>}{guide&&<div className="sass-ai-guide"><div className="sass-ai-guide-head"><div><small>{guide.domain}</small><h4>{guide.title}</h4></div><button onClick={()=>setGuide(null)} aria-label="Close feature guide"><X size={16}/></button></div><p>{guide.guidance}</p><p className="sass-ai-small">Source-declared API methods: {guide.declared_api_methods.length?guide.declared_api_methods.join(' · '):'None mapped'}. These are not proof of permitted CRUD or live operation.</p><div className="sass-ai-guide-actions"><button onClick={()=>navigate(guide.key)}>Open feature</button>{guide.settings_key&&features.some(f=>f.key===guide.settings_key)&&<button onClick={()=>navigate(guide.settings_key)}>Open settings</button>}{guide.actions.map(a=><button key={a.operation} onClick={()=>{setOperation(a.operation);setTab('actions');setProposal(null)}}>{a.label}</button>)}</div><div className="sass-ai-plan-bar"><label>Help with<select value={controlIntent} onChange={e=>setControlIntent(e.target.value as typeof controlIntent)}><option value="view">View records</option><option value="create">Add / create</option><option value="edit">Edit / update</option><option value="delete">Delete / remove</option><option value="settings">Settings</option><option value="help">How to use</option></select></label><button onClick={()=>void planFeature(guide.key,controlIntent)}>Prepare workflow guide</button></div>
     {plan&&plan.feature_key===guide.key&&<div className="sass-ai-plan-result" role="status"><strong>{plan.feature} · {plan.intent}</strong><p>{plan.guidance}</p><div className="sass-ai-guide-actions"><button onClick={()=>navigate(plan.target_key)}>Open authorized screen</button>{plan.approved_actions.map(a=><button key={a.operation} onClick={()=>{setOperation(a.operation);setTab('actions');setProposal(null)}}>{a.label}</button>)}</div><small>This plan has not changed records.</small></div>}
     {asList<{title:string}>(guide?.knowledge).length>0&&<p className="sass-ai-guide-sources">Published guidance: {asList<{title:string}>(guide?.knowledge).map(k=>k.title).join(' · ')}</p>}</div>}</section>}
  {tab==='actions'&&<section className="sass-ai-panel sass-ai-form-panel"><h3>Confirmed feature actions</h3><p>Select an allowlisted operation, review the server-generated preview, then explicitly confirm. Every action uses its existing HRM handler and your logged-in employee identity. Changes outside this catalog remain in their own HRM screens.</p><div className="sass-ai-action-history"><button type="button" onClick={()=>void showActionHistory()}>My recent AI actions</button>{historyOpen&&<div role="status"><strong>My action history</strong><button type="button" onClick={()=>setHistoryOpen(false)}>Close</button>{recentActions.length===0?<p>No actions prepared yet.</p>:<ul>{recentActions.map((h,i)=><li key={i}>{h.operation.replaceAll('_',' ')} · {h.state} · {new Date(h.created_at).toLocaleString()}</li>)}</ul>}</div>}</div>
   <div className="sass-ai-action-picker"><label>Choose an HRM operation<select value={operation} onChange={e=>{setOperation(e.target.value);setProposal(null);setError('')}}>{actionList.map(a=><option key={a.operation} value={a.operation}>{a.label}</option>)}</select></label><p>{actionList.find(a=>a.operation===operation)?.description}</p></div>
   <form className="sass-ai-action-form" key={operation} onSubmit={prepare}>
    {operation.startsWith('admin_office_')&&<>
     {operation!=='admin_office_create'&&<label className="wide">Office location<select required value={form.office_id} onChange={e=>{const id=e.target.value;const r=myOptions.offices.find(x=>x.id===Number(id));setForm(f=>({...f,office_id:id,...(r?{office_code:r.code,office_name:r.name,city:r.city,country:r.country,address:r.address,timezone:r.timezone,is_active:!!r.is_active}:{})}))}}><option value="">Select office</option>{myOptions.offices.map(o=><option key={o.id} value={o.id}>#{o.id} · {o.name} ({o.is_active?'Active':'Inactive'})</option>)}</select></label>}
     {['admin_office_create','admin_office_edit'].includes(operation)&&<><label>Office code<input required minLength={2} maxLength={24} value={form.office_code} onChange={e=>setForm(f=>({...f,office_code:e.target.value}))}/></label><label>Office name<input required minLength={2} maxLength={120} value={form.office_name} onChange={e=>setForm(f=>({...f,office_name:e.target.value}))}/></label><label>City<input required value={form.city} onChange={e=>setForm(f=>({...f,city:e.target.value}))}/></label><label>Country<input required value={form.country} onChange={e=>setForm(f=>({...f,country:e.target.value}))}/></label><label>Timezone (IANA)<input required value={form.timezone} onChange={e=>setForm(f=>({...f,timezone:e.target.value}))}/></label><label className="wide">Address<input maxLength={500} value={form.address} onChange={e=>setForm(f=>({...f,address:e.target.value}))}/></label><label className="wide"><input type="checkbox" checked={form.is_active} onChange={e=>setForm(f=>({...f,is_active:e.target.checked}))}/> Office active</label></>}
    </>}
    {operation.startsWith('admin_category_')&&<>
     {operation!=='admin_category_create'&&<label className="wide">Request Desk category<select required value={form.service_category_id} onChange={e=>{const id=e.target.value;const r=myOptions.service_categories.find(x=>x.id===Number(id));setForm(f=>({...f,service_category_id:id,...(r?{category_name:r.name,description:r.description}:{})}))}}><option value="">Select category</option>{myOptions.service_categories.map(c=><option key={c.id} value={c.id}>#{c.id} · {c.name} ({c.active?'Active':'Archived'})</option>)}</select></label>}
     {['admin_category_create','admin_category_edit'].includes(operation)&&<><label className="wide">Category name<input required minLength={3} maxLength={100} value={form.category_name} onChange={e=>setForm(f=>({...f,category_name:e.target.value}))}/></label><label className="wide">Description<textarea rows={3} maxLength={700} value={form.description} onChange={e=>setForm(f=>({...f,description:e.target.value}))}/></label></>}
    </>}
    {operation.startsWith('admin_template_')&&<>
     {operation!=='admin_template_create'&&<label className="wide">HR task template<select required value={form.template_id} onChange={e=>{const id=e.target.value;const r=myOptions.task_templates.find(x=>x.id===Number(id));setForm(f=>({...f,template_id:id,...(r?{template_title:r.title,guidance:r.guidance,priority:r.priority,due_offset_days:String(r.due_offset_days)}:{})}))}}><option value="">Select template</option>{myOptions.task_templates.map(t=><option key={t.id} value={t.id}>#{t.id} · {t.title} ({t.active?'Active':'Archived'})</option>)}</select></label>}
     {['admin_template_create','admin_template_edit'].includes(operation)&&<><label className="wide">Template title<input required minLength={4} maxLength={160} value={form.template_title} onChange={e=>setForm(f=>({...f,template_title:e.target.value}))}/></label><label className="wide">Guidance<textarea maxLength={1000} rows={3} value={form.guidance} onChange={e=>setForm(f=>({...f,guidance:e.target.value}))}/></label><label>Priority<select value={form.priority} onChange={e=>setForm(f=>({...f,priority:e.target.value}))}><option>Low</option><option>Normal</option><option>High</option></select></label><label>Due after days<input type="number" min="0" max="365" required value={form.due_offset_days} onChange={e=>setForm(f=>({...f,due_offset_days:e.target.value}))}/></label></>}
    </>}
    {['admin_office_delete','admin_category_delete','admin_template_delete'].includes(operation)&&<label className="wide">Deletion reason (recorded in audit log)<textarea required minLength={5} maxLength={500} rows={3} value={form.admin_reason} onChange={e=>setForm(f=>({...f,admin_reason:e.target.value}))}/></label>}
    {operation==='submit_leave'&&<><label>Start date<input type="date" required value={form.start_date} onChange={e=>setForm(f=>({...f,start_date:e.target.value}))}/></label><label>End date<input type="date" required value={form.end_date} onChange={e=>setForm(f=>({...f,end_date:e.target.value}))}/></label><label>Leave type<input required maxLength={100} value={form.leave_type} onChange={e=>setForm(f=>({...f,leave_type:e.target.value}))}/></label><label className="wide">Reason<textarea required minLength={3} maxLength={500} rows={3} value={form.reason} onChange={e=>setForm(f=>({...f,reason:e.target.value}))}/></label></>}
    {operation==='submit_service_request'&&<><label className="wide">Service category<select required value={form.category_id} onChange={e=>setForm(f=>({...f,category_id:e.target.value}))}><option value="">Select an active HR service</option>{categories.map(c=><option value={c.id} key={c.id}>{c.name}</option>)}</select></label><label className="wide">Subject<input required minLength={4} maxLength={180} value={form.subject} onChange={e=>setForm(f=>({...f,subject:e.target.value}))}/></label><label className="wide">Request details<textarea required minLength={10} maxLength={2000} rows={4} value={form.details} onChange={e=>setForm(f=>({...f,details:e.target.value}))}/></label></>}
    {['create_personal_event','edit_personal_event','delete_personal_event'].includes(operation)&&<>
     {operation!=='create_personal_event'&&<label className="wide">My personal event<select required value={form.event_id} onChange={e=>{const id=e.target.value;const match=myOptions.personal_events.find(x=>x.id===Number(id));setForm(f=>({...f,event_id:id,...(match?{day:match.day,title:match.title,start_time:match.start_time,notes:match.notes}:{})}))}}><option value="">Select an event you own</option>{myOptions.personal_events.map(e=><option key={e.id} value={e.id}>#{e.id} · {e.day} · {e.title}</option>)}</select></label>}
     {operation!=='delete_personal_event'&&<><label>Day<input type="date" required value={form.day} onChange={e=>setForm(f=>({...f,day:e.target.value}))}/></label><label>Start time (optional)<input type="time" value={form.start_time} onChange={e=>setForm(f=>({...f,start_time:e.target.value}))}/></label><label className="wide">Event title<input required minLength={2} maxLength={120} value={form.title} onChange={e=>setForm(f=>({...f,title:e.target.value}))}/></label><label className="wide">Notes (optional)<textarea rows={3} maxLength={1000} value={form.notes} onChange={e=>setForm(f=>({...f,notes:e.target.value}))}/></label></>}
    </>}
    {operation==='request_work_mode'&&<><label>Requested mode<select value={form.requested_mode} onChange={e=>setForm(f=>({...f,requested_mode:e.target.value}))}><option>Remote</option><option>Hybrid</option><option>On-site</option></select></label><label>Effective date<input type="date" required value={form.effective_date} onChange={e=>setForm(f=>({...f,effective_date:e.target.value}))}/></label><label className="wide">Reason<textarea required minLength={5} maxLength={700} rows={3} value={form.reason} onChange={e=>setForm(f=>({...f,reason:e.target.value}))}/></label></>}
    {operation==='submit_expense'&&<><label className="wide">Expense title<input required minLength={3} maxLength={150} value={form.title} onChange={e=>setForm(f=>({...f,title:e.target.value}))}/></label><label>Amount<input required type="number" min="0.01" max="500000" step="0.01" value={form.amount} onChange={e=>setForm(f=>({...f,amount:e.target.value}))}/></label><label>Category<select value={form.category} onChange={e=>setForm(f=>({...f,category:e.target.value}))}>{['Travel','Connectivity','Meals','Equipment','Other'].map(c=><option key={c}>{c}</option>)}</select></label><label>Date of expense<input type="date" value={form.expense_date} onChange={e=>setForm(f=>({...f,expense_date:e.target.value}))}/></label><label>Merchant<input maxLength={150} value={form.merchant} onChange={e=>setForm(f=>({...f,merchant:e.target.value}))}/></label><label className="wide">Business purpose<textarea rows={3} maxLength={1000} value={form.business_purpose} onChange={e=>setForm(f=>({...f,business_purpose:e.target.value}))}/></label><label>Cost center<input maxLength={80} value={form.cost_center} onChange={e=>setForm(f=>({...f,cost_center:e.target.value}))}/></label><label>Receipt reference<input maxLength={240} value={form.receipt_reference} onChange={e=>setForm(f=>({...f,receipt_reference:e.target.value}))}/></label></>}
    {operation==='request_attendance_correction'&&<><label>Work date<input type="date" required value={form.work_day} onChange={e=>setForm(f=>({...f,work_day:e.target.value}))}/></label><label>Corrected check-in<input required type="time" value={form.proposed_in} onChange={e=>setForm(f=>({...f,proposed_in:e.target.value}))}/></label><label>Corrected check-out<input required type="time" value={form.proposed_out} onChange={e=>setForm(f=>({...f,proposed_out:e.target.value}))}/></label><label className="wide">Reason<textarea required minLength={8} maxLength={500} value={form.reason} onChange={e=>setForm(f=>({...f,reason:e.target.value}))}/></label></>}
    {operation==='cancel_attendance_correction'&&<label className="wide">My pending correction<select required value={form.correction_id} onChange={e=>setForm(f=>({...f,correction_id:e.target.value}))}><option value="">Select correction</option>{myOptions.pending_corrections.map(r=><option key={r.id} value={r.id}>#{r.id} · {r.work_day}</option>)}</select></label>}
    {operation==='update_task_status'&&<><label className="wide">My HR task<select required value={form.task_id} onChange={e=>setForm(f=>({...f,task_id:e.target.value}))}><option value="">Select task</option>{myOptions.my_tasks.map(t=><option value={t.id} key={t.id}>#{t.id} · {t.title} ({t.status})</option>)}</select></label><label>New task status<select value={form.status} onChange={e=>setForm(f=>({...f,status:e.target.value}))}>{['Open','In Progress','Completed'].map(x=><option key={x}>{x}</option>)}</select></label></>}
    {operation==='create_hr_task'&&<><label className="wide">Assign to<select required value={form.assignee_id} onChange={e=>setForm(f=>({...f,assignee_id:e.target.value}))}><option value="">Select authorized employee</option>{myOptions.assignable_staff.map(x=><option value={x.id} key={x.id}>{x.name} ({x.code})</option>)}</select></label><label className="wide">Task title<input required minLength={4} maxLength={180} value={form.title} onChange={e=>setForm(f=>({...f,title:e.target.value}))}/></label><label>Due date<input required type="date" value={form.due_date} onChange={e=>setForm(f=>({...f,due_date:e.target.value}))}/></label><label>Priority<select value={form.priority} onChange={e=>setForm(f=>({...f,priority:e.target.value}))}>{['Low','Normal','High'].map(x=><option key={x}>{x}</option>)}</select></label></>}
    {operation==='mark_notification_read'&&<label className="wide">My unread notification<select required value={form.notification_id} onChange={e=>setForm(f=>({...f,notification_id:e.target.value}))}><option value="">Choose notification</option>{myOptions.unread_notifications.map(n=><option value={n.id} key={n.id}>#{n.id} · {n.title}</option>)}</select></label>}
    {operation==='update_my_preferences'&&<><label>Date format<select value={form.date_format} onChange={e=>setForm(f=>({...f,date_format:e.target.value}))}>{['DD MMM YYYY','YYYY-MM-DD','MM/DD/YYYY'].map(x=><option key={x}>{x}</option>)}</select></label><label>Display density<select value={form.density} onChange={e=>setForm(f=>({...f,density:e.target.value}))}><option>Comfortable</option><option>Compact</option></select></label><label className="wide"><input type="checkbox" checked={form.reduce_motion} onChange={e=>setForm(f=>({...f,reduce_motion:e.target.checked}))}/> Reduce motion</label></>}
    {operation==='cancel_work_mode'&&<label className="wide">My pending work arrangement<select required value={form.request_id} onChange={e=>setForm(f=>({...f,request_id:e.target.value}))}><option value="">Select an open request</option>{myOptions.pending_work_mode.map(r=><option value={r.id} key={r.id}>#{r.id} · {r.requested_mode}</option>)}</select></label>}
    {['check_in','check_out'].includes(operation)&&<p className="wide sass-ai-confirm-note">This records your own attendance at the current time in your HRM company timezone. No employee identifier can be supplied.</p>}
    <button type="submit" disabled={busy||!!proposal} className="sass-ai-primary">Review action <ArrowRight size={16}/></button>
   </form>
   {proposal&&<div className="sass-ai-review"><strong>Review before saving</strong><p>{proposal.preview}</p><small>Expires at {new Date(proposal.expires_at).toLocaleString()}. Changes are made only if you press Confirm. Calendar deletions cannot be undone.</small><div><button disabled={busy} onClick={()=>void cancel()}>Cancel</button><button disabled={busy} className="sass-ai-primary" onClick={()=>void confirm()}><CheckCircle2 size={16}/> Confirm action</button></div></div>}
  </section>}
  {tab==='knowledge'&&admin&&<div className="sass-ai-chat-layout"><section className="sass-ai-panel sass-ai-form-panel"><h3>Admin knowledge studio</h3><p>Create approved HR guidance for RAG search. Drafts are private to HR admins; published articles are searchable only by the selected audience and within the selected feature scope. Never publish confidential employee data.</p><form className="sass-ai-action-form" onSubmit={saveArticle}><label className="wide">Article title<input required minLength={4} maxLength={190} value={article.title} onChange={e=>setArticle(a=>({...a,title:e.target.value}))}/></label><label>Category<input required minLength={2} maxLength={100} value={article.category} onChange={e=>setArticle(a=>({...a,category:e.target.value}))}/></label><label>Publication status<select value={article.status} onChange={e=>setArticle(a=>({...a,status:e.target.value as 'Draft'|'Published'}))}><option>Draft</option><option>Published</option></select></label><label>Linked HRM feature<select value={article.feature_key} onChange={e=>setArticle(a=>({...a,feature_key:e.target.value}))}><option value="">General HR policy</option>{features.map(f=><option key={f.key} value={f.key}>{f.label}</option>)}</select></label><label>Visible to<select value={article.audience} onChange={e=>setArticle(a=>({...a,audience:e.target.value as 'All'|'Manager'|'Admin'}))}><option value="All">All staff</option><option value="Manager">Managers and HR admin</option><option value="Admin">HR admin only</option></select></label><label className="wide">Approved knowledge content<textarea required minLength={20} maxLength={24000} rows={10} value={article.content} onChange={e=>setArticle(a=>({...a,content:e.target.value}))}/></label><button className="sass-ai-primary" disabled={busy}>{selectedArticle?'Update article':'Add knowledge article'}</button>{selectedArticle&&<button type="button" onClick={()=>{setSelectedArticle(null);setArticle({title:'',category:'HR guidance',content:'',status:'Draft',feature_key:'',audience:'All'})}}>Cancel editing</button>}</form><div className="sass-ai-bulk-import"><strong>Bulk RAG knowledge import (CSV)</strong><p>Import up to 50 HR guidance articles at once. The server checks scope, duplicates and permissions. Imported articles always remain unpublished Drafts until an HR Administrator reviews and publishes them.</p><button type="button" onClick={downloadKnowledgeTemplate}>Download CSV template</button><label>Choose knowledge CSV (max 250 KB)<input type="file" accept=".csv,text/csv" disabled={bulkBusy} onChange={e=>{void previewKnowledgeFile(e.target.files?.[0]);e.target.value=''}}/></label>{bulkBusy&&<p role="status">Checking knowledge import…</p>}{bulkPreview&&<div className="sass-ai-bulk-preview" role="status"><strong>{bulkPreview.count} articles ready as Draft</strong><ul>{bulkPreview.items.slice(0,6).map((a,i)=><li key={i}>{a.title} · {a.feature_key||'General'} · {a.audience}</li>)}</ul>{bulkPreview.count>6&&<small>Plus {bulkPreview.count-6} more articles</small>}<div><button type="button" onClick={()=>{setBulkPreview(null);setBulkRows([])}} disabled={bulkBusy}>Cancel</button><button type="button" className="sass-ai-primary" disabled={bulkBusy} onClick={()=>void importKnowledgeDrafts()}>Confirm import drafts</button></div></div>}</div></section><aside className="sass-ai-panel sass-ai-info"><strong>AI & RAG status</strong>{aiHealth&&<div className="sass-ai-health"><p>Feature guides: <strong>{aiHealth.inventoried_features}</strong></p><p>Confirmed action types: <strong>{aiHealth.confirmed_action_types}</strong></p><p>Published articles: <strong>{aiHealth.published_articles}</strong></p><p>Published policies: <strong>{aiHealth.policy_documents}</strong></p><p>Generation: <strong>{aiHealth.generation_enabled?'Enabled':'Disabled'}</strong></p><p>Search: <strong>{aiHealth.retrieval_mode}</strong></p></div>}<strong>Knowledge library</strong><p>{articles.length} article(s)</p><div className="sass-ai-articles">{articles.map(a=><div key={a.id}><div><strong>{a.title}</strong><small>{a.category} · {a.status} · {a.feature_key||'General'} · {a.audience}</small></div><button onClick={()=>void editArticle(a.id)}>Edit</button><button disabled={busy} onClick={()=>void toggleArticle(a)}>{a.status==='Published'?'Unpublish':'Publish'}</button></div>)}</div><p className="sass-ai-small">Unpublishing removes an article from future retrieval while retaining its audit history.</p></aside></div>}
  <footer className="sass-ai-footer"><ShieldCheck size={16}/> Permission checks are enforced by the backend. No AI-issued approvals, hiring decisions, salary edits, or employee deletion. Only your own personal-calendar events can be deleted through the assistant. {caps?.generation_enabled?'Approved excerpts may be sent to your configured LLM provider.':'No external generative model is enabled.'}</footer>
 </div>;
}
