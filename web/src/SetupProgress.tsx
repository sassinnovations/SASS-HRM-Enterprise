import {hrmFetch} from './apiTransport';
import {useRefreshData} from './useRefreshData';
import {useEffect,useState} from 'react';
import {ArrowRight,CheckCircle2,ClipboardCheck} from 'lucide-react';
import './setup-progress.css';
const BASE=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')+'/api';
type Check={key:string;label:string;ready:boolean;hint:string};
type Readiness={completed:number;total:number;checks:Check[]};
const targets:Record<string,string>={profile:'companysetup',departments:'organization',workforce:'employees',employees:'employees',mysql:'companysetup',leave:'leave',policies:'policies',smtp:'companysetup',database:'developer',offices:'orgsettings',preferences:'orgsettings'};
function target(check:Check){const key=check.key.toLowerCase();return targets[key]||(/department/.test(key)?'organization':/leave/.test(key)?'leave':/staff|workforce/.test(key)?'employees':/polic/.test(key)?'policies':/smtp|company|profile/.test(key)?'companysetup':'orgsettings')}
export function SetupProgress({navigate}:{navigate:(key:string)=>void}){
 const[data,setData]=useState<Readiness|null>(null);const[error,setError]=useState('');const[busy,setBusy]=useState(false);
 async function reload(){setBusy(true);setError('');try{
  const token=sessionStorage.getItem('sass_token');const response=await hrmFetch(BASE+'/admin/setup/overview',{headers:{Authorization:`Bearer ${token||''}`}});if(!response.ok)throw Error(`Setup check unavailable (${response.status})`);setData(await response.json());
 }catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 useEffect(()=>{void reload()},[]);
 useRefreshData(reload);
 return <section aria-busy={busy} className="v27-setup-banner" aria-label="Organization setup progress"><div className="v27-setup-icon"><ClipboardCheck size={22}/></div><div className="v27-setup-content"><div className="v27-setup-header"><div><strong>Set up the SASS organization</strong><p>Complete your real HRM configuration before onboarding employees. This checklist reflects your current database records.</p></div><div className="v27-setup-score">{data?`${data.completed}/${data.total}`:'Checking…'}</div></div>
 {data&&<><div className="v27-setup-bar" role="progressbar" aria-valuenow={data.completed} aria-valuemin={0} aria-valuemax={data.total} aria-label="Organization setup checks completed"><span style={{width:`${data.total?data.completed/data.total*100:0}%`}}/></div><div className="v27-setup-tasks">{data.checks.filter(c=>!c.ready).slice(0,4).map(check=><button type="button" key={check.key} onClick={()=>navigate(target(check))} title={check.hint}><span>{check.label}</span><ArrowRight size={13}/></button>)}{data.checks.every(c=>c.ready)&&<span className="v27-setup-done"><CheckCircle2 size={16}/> All checklist items configured. Verify payroll, email delivery and production security separately.</span>}</div></>}
 {error&&<p role="alert" className="v27-setup-error">{error}</p>}
 <div className="v27-setup-actions"><button type="button" onClick={()=>navigate('orgsettings')}>Organization settings <ArrowRight size={14}/></button><button type="button" onClick={()=>navigate('companysetup')}>Company setup & import <ArrowRight size={14}/></button></div></div></section>
}
