# Production rollout checklist

This project removes demo defaults but **is not approved for live employee PII/payroll**.

- Complete full browser E2E tests, authentication review, and external penetration testing.
- Integrate enterprise SSO/MFA, account recovery, enterprise rate limits, and central secrets management.
- Add audit retention, backups, disaster recovery, disaster drills and monitoring/alerting.
- Replace SQLite-compat SQL bridge with real migrations, tested data isolation and schema version upgrades.
- Replace disabled document vault with dedicated encrypted object storage, malware scanning and retention policies.
- Review survey privacy, labor rules, data subject access/deletion requirements, and manager scopes.
- Verify India state-wise payroll/PF/ESI/PT/TDS and country-specific statutory filing rules; test against approved payroll examples.
- Provide SMTP email provider credentials and outbound email monitoring; audit invite delivery and expiry.
- Obtain security, HR, finance, and privacy approvals before connecting live data.
