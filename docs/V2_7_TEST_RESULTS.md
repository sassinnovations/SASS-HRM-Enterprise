# v2.7 validation report (October 2026)

## Passed

- 15 isolated backend test scripts, including CRUD, authentication, password resets, account administration, leave/talent/payroll/culture/HR operations, organization setup, personal calendar, export privacy and role restrictions.
- Static GET permission audit: **170 role-scoped API calls across 85 endpoints**, with no unexpected errors.
- Frontend `tsc --noEmit` passed against the archived toolchain, using it for type-checking only. These platform-specific dependencies are NOT packaged.
- Static design, navigation, login and Docker configuration checks passed.
- `scripts/verify-v24-package.py` confirms no `.env` secrets, local node_modules, build output, or missing repair launcher.

## Not verified

- A clean Vite build was not completed in this Linux environment: the archived dependencies are Windows-native and a fresh dependency install could not finish. A clean Windows `npm ci` or Docker build is still required.
- No live Docker Desktop/MySQL instance, actual browser walkthrough, SMTP delivery, production SSO/MFA, payroll-compliance signoff or mobile-device runtime testing was performed in this environment.

## Upgrade notes

Normal startup creates the additive MySQL table when missing; the schema installer logs migration 8. Never remove Docker volumes to solve a frontend issue. Back up the existing MySQL data and private environment variables before switching app versions.
