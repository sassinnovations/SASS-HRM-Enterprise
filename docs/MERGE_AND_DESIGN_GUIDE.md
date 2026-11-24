# SASS HRM Enterprise v1.3 — Demo feature parity & visual design

## Starting point

- Feature source: the user-supplied **SASS_HRM_Enterprise_MySQL_v1.0 (1).zip**.
- Target: **SASS_HRM_Enterprise_Admin_Developer_v1.2.zip**.
- Preserved: SASS real-organization first-admin bootstrap, separate developer diagnostic grant, blank database, one-time activation email, no embedded credentials and payroll publication safeguards.
- Merged: the full non-seeded operational screens and underlying v1.0 routes. Original legacy payslip records are now read-only. Original unsafe document vault has been replaced with a **security-gated encryption and malware scan workflow**.

## User-facing feature map

| Area | Modules | Availability / constraint |
|---|---|---|
| Executive dashboard | Overview, employee calendar, operational summaries | Connected to live authorized API records; no seeded numbers |
| HRIS & organization | Employees, departments, chart, skills, private profile, work arrangement, account invitations | Admin/employee/manager scopes enforced |
| Time & leave | Attendance, correction approval, shifts, timesheets, leave and entitlements | Manager/HR approval restrictions apply |
| Talent | Recruitment ATS, interviews, onboarding, performance, learning, recognition, surveys, exits | Manager/HR access where needed |
| Rewards | Salary workbench, historical payslip archive, tax estimator, benefits and claims | Historic payslips read-only; statutory publishing blocked by default |
| Employee operations | Helpdesk, tasks, approvals, assets, document register and encrypted vault | Secure vault requires external scanner and a separate encryption key |
| Governance | Policies, acknowledgements, audit events, readiness, analytics | Some reporting and legal functions require production validation |
| System | Restricted developer console and employee AI assistant | Developer capability is separately granted; AI is read-only |

## Design changes

- Unified SASS-branded navy/blue/white theme for login, navigation and all module surfaces.
- Navigation grouped into seven functional areas, with existing search retained so users can find modules quickly.
- Responsive layouts, focus-visible outlines, strengthened contrast, tighter cards, consistent buttons and table headings.
- Fixed **OperationsExtra** and **PayrollExtra** to use Vite `/api` proxy by default, matching the main application.

## Secure vault activation (optional, no default credential or bypass)

The vault is **unavailable by default**, but its screen and listing are present. To enable it for a security-approved internal deployment:

1. Provision a long-lived, centrally backed-up, access-controlled symmetric encryption key via a secrets manager. Generate an example local key with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` and store it as `VAULT_FERNET_KEY` in ignored `server/.env`. **Losing the key makes encrypted attachments unrecoverable.** Do not commit or email it.
2. Provision a maintained **ClamAV clamd** server and give the backend private network access. Set `VAULT_AV_HOST` and `VAULT_AV_PORT` (usually 3310) in `server/.env`. Do not expose clamd to the public internet; clamd has no built-in user authentication.
3. Restart the backend. The authenticated `/api/vault/status` endpoint only reports the feature ready when encryption configuration is valid and the scanner responds to `PING`. The UI disables file selection unless the feature is ready.
4. Uploads are limited to 2 MiB, scanned via clamd INSTREAM, encrypted with Fernet, and stored as ciphertext. Downloads require authentication and employee/HR authorization and reject plaintext legacy entries.
5. Before storing actual confidential HR files, implement a comprehensive document governance program: key rotation, lifecycle retention/deletion, encrypted backups, content security, upload quotas, denial-of-service protections, malware handling, and an independent privacy/security review. A clean malware scan is not a guarantee of safety.

### Payroll and tax caveat

India payroll and India/UK/US tax calculations are estimates and reference workflows. Publication remains explicitly gated; they are not certified statutory payroll engines, bank payments, or government filing.

## Automated verification

`server/real_baseline_test.py`, `server/admin_developer_test.py` and `server/merged_release_test.py` and `server/route_audit_test.py` cover blank startup, admin/bootstrap, no demo logins, rights, archive access, and encrypted/scanner-gated vault lifecycle using mocked scanner connectivity (not a real malware engine). Frontend TSX parsing was checked locally, but a real Vite build must be run on a networked Windows machine. Actual MySQL, SMTP and browser regression testing remain outstanding.
