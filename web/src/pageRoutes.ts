/**
 * SASS HRM public client route registry. Every existing sidebar feature has a
 * stable, refreshable URL. Permissions are enforced separately in App and API.
 * Nginx and Vite must serve index.html for these frontend routes.
 */
export const PAGE_ROUTES: Record<string, string> = {
  dashboard: '/workspace/overview',
  workcenter: '/workspace/action-center',
  globalsearch: '/workspace/global-search',
  dataquality: '/people/data-quality-center',
  reminders: '/workspace/workflow-reminders',
  coverage: '/workspace/team-leave-planner',
  selfservice: '/workspace/my-requests',
  inbox: '/workspace/notifications',
  calendar: '/workspace/calendar',
  profile: '/workspace/my-profile',

  employees: '/people/employee-hris',
  orgchart: '/people/organization-chart',
  privateprofile: '/people/private-contact-profile',
  skills: '/people/skills-competencies',
  profilemgmt: '/people/profile-management',
  accounts: '/people/account-administration',
  companysetup: '/people/company-setup-import',
  orgsettings: '/people/organization-settings',
  settingscenter: '/people/admin-settings-center',
  talentsettings: '/people/talent-service-settings',
  workflowsettings: '/people/workflow-settings',
  organization: '/people/organization',
  policies: '/people/policies-handbook',
  compliance: '/people/policy-acknowledgements',
  reports: '/people/reports-analytics',
  audit: '/people/audit-trail',
  readiness: '/people/hr-operations-center',
  developer: '/people/developer-console',

  recruitment: '/talent/recruitment-ats',
  interviews: '/talent/interview-scheduling',
  onboarding: '/talent/onboarding',
  requestdesk: '/talent/request-desk',
  helpdesk: '/talent/hr-helpdesk',
  tasks: '/talent/hr-tasks',
  tasktemplates: '/talent/hr-task-templates',
  offboarding: '/talent/offboarding',

  leave: '/compensation/leave-management',
  attendance: '/compensation/time-attendance',
  corrections: '/compensation/attendance-corrections',
  shifts: '/compensation/shifts-schedules',
  timesheets: '/compensation/project-timesheets',
  payrollengine: '/compensation/payroll-workbench',
  compensationsettings: '/compensation/organization-settings',
  payroll: '/compensation/payslip-archive',
  taxcalculator: '/compensation/tax-calculator',
  benefits: '/compensation/benefits-programs',
  expenses: '/compensation/expenses-claims',

  performance: '/culture/performance-goals',
  performancecycles: '/culture/review-cycles',
  appraisals: '/culture/employee-appraisals',
  checkins: '/culture/one-on-one-checkins',
  growthplans: '/culture/development-plans',
  feedbackrequests: '/culture/manager-feedback',
  followups: '/culture/performance-followups',
  reviewprogress: '/culture/review-progress',
  evidence: '/culture/performance-evidence',
  goaljournal: '/culture/goal-checkin-journal',
  career: '/culture/career-development',
  training: '/culture/learning-training',
  surveys: '/culture/employee-pulse',
  voice: '/culture/employee-voice',
  discipline: '/culture/discipline-conduct',
  recognition: '/culture/recognition-wall',
  workmode: '/culture/work-arrangements',

  approvals: '/services/approval-inbox',
  assets: '/services/asset-management',
  documents: '/services/employee-documents',
  vault: '/services/secure-document-vault',

  assistant: '/ai/assistant',
  settings: '/settings/my-workspace',
  mysecurity: '/settings/account-security',
  securityaudit: '/people/account-security-review',
};

const reverseRoutes: Record<string, string> = Object.fromEntries(
  Object.entries(PAGE_ROUTES).map(([key, path]) => [path, key]),
);

export function pageUrl(key: string): string {
  return PAGE_ROUTES[key] || PAGE_ROUTES.dashboard;
}

export function pageFromPath(pathname: string): string | null {
  // Accept / and /index.html for older bookmarks and first-time visits.
  const clean = pathname.replace(/\/+$/, '') || '/';
  if (clean === '/' || clean === '/index.html') return 'dashboard';
  return reverseRoutes[clean] || null;
}

export function isSignInPath(pathname: string): boolean {
  return pathname.replace(/\/+$/, '') === '/sign-in';
}
