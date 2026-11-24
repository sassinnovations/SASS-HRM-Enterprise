# Branding change log — SASS HRM — SASS INNOVATIONS ENTERPRISE

Date: 18 November 2026

## What changed

- Desktop sign-in, mobile sign-in and application sidebar now display `SASS HRM` with `SASS INNOVATIONS ENTERPRISE` below it.
- Browser tabs and page titles use `SASS HRM — SASS INNOVATIONS ENTERPRISE`.
- Login information panel, footer, frontend boot/error labels, public API display title and service-health labels use the new branding.
- Employee activation and password reset email subjects/bodies use the new branding.
- Simulated payroll statement heading shows `SASS INNOVATIONS ENTERPRISE`.
- This package uses a brand-specific project folder and ZIP name, with the README and change log updated.

## What stayed unchanged

- 243-table MySQL schema, including Job Description records and JD import history.
- Candidate Search & Database, Recruitment ATS JD/Excel/CSV matching workflows and all other application APIs and modules.
- MySQL database name, usernames, table names, application environment-variable keys, API paths, JWT issuer and client storage identifiers. Changing those would be a breaking migration and is not required for a visual rebrand.
- User-configured organization identity (an existing customer-defined company name takes precedence).
- Railway and Vercel deployment configuration.
- No existing employee, candidate, JD, payroll or asset records were edited.

## Upgrade

Back up existing deployment and database, then redeploy this release's frontend and backend. The branding itself requires **no SQL migration**. If the installed database is older than the 243-table release, follow the existing staged migration guide before activating newer functional modules. Never run the fresh-install script against a populated database.

## Verification boundary

Brand text, code syntax, unchanged SQL hashes and selected backend regression tests can be checked offline. A live MySQL migration, production Vite build and browser confirmation require a configured environment.
