import {ArrowRight, Bell, CalendarDays, CalendarRange, Inbox, ShieldCheck} from 'lucide-react';
import {pageUrl} from './pageRoutes';
import './workspace-settings-directory.css';

const sections = [
 {key:'coverage', title:'Team leave & coverage planner', description:'Planner views, coverage warnings, and backup assignments.', icon:CalendarDays},
 {key:'selfservice', title:'My requests & shortcuts', description:'Draft defaults, request history, and pinned shortcuts.', icon:Inbox},
 {key:'inbox', title:'Notification inbox', description:'Notification display, reminder views, and inbox actions.', icon:Bell},
 {key:'calendar', title:'My calendar', description:'Calendar layout, private categories, and export preferences.', icon:CalendarRange},
 {key:'mysecurity', title:'My Account Security', description:'Sign-in history, password and sessions, and checklist preferences.', icon:ShieldCheck},
] as const;

export function WorkspaceSettingsDirectory({navigate,canOpen}:{navigate:(page:string)=>void;canOpen:(page:string)=>boolean}){
 const available=sections.filter(item=>canOpen(item.key));
 return <section className="section-card ws-settings-directory" aria-labelledby="ws-settings-directory-title">
  <header>
   <span className="eyebrow">WORKSPACE TOOLS</span>
   <h2 id="ws-settings-directory-title">Workspace settings by page</h2>
   <p>Choose a page to manage its settings. Your role determines which organization-wide controls you can change.</p>
  </header>
  <ul className="ws-settings-directory-grid">
   {available.map(({key,title,description,icon:Icon})=><li key={key}>
    <a className="ws-settings-directory-link" href={pageUrl(key)} onClick={e=>{
      if(e.button!==0||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;
      e.preventDefault();navigate(key);
    }} aria-label={title}>
     <span className="ws-settings-directory-icon"><Icon size={19} aria-hidden="true"/></span>
     <span className="ws-settings-directory-copy"><strong>{title}</strong><span>{description}</span></span>
     <ArrowRight size={16} aria-hidden="true" className="ws-settings-directory-arrow"/>
    </a>
   </li>)}
  </ul>
 </section>;
}
