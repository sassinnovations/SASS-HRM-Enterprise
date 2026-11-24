# SASS HRM v3.6.0 — Single Refresh Data Control (frontend patch)

## User interface

- The authenticated application has one global **Refresh data** button in the top bar.
- Removed the extra **Reload page** button and individual **Refresh**, **Refresh settings**, **Refresh checks**, **Refresh data**, **Reload history**, and similar duplicated feature controls.
- Navigation still uses 59 separate feature URLs. Browser F5 / Ctrl+R still works and restores the URL as before; it just isn't shown as a second refresh action in the product.
- The only exception is the React application-crash recovery screen (outside the normal authenticated HRM UI); its **Reload app** action remains available if the application cannot render a top bar.

## What Refresh data updates

1. The main HRM workspace fetches its authorized shared datasets again (`App.refresh`). A failed fetch is flagged, not silently dropped.
2. After that completes, the application sends `sass-hrm:refresh-data` to **mounted** module listeners, which re-fetch their current account-authorized API records while keeping filters/selections/forms mounted.
3. Special cases also update local state: notification inbox and workflow settings, candidate activity, payroll runs, profiles, My Requests, calendar, attendance corrections, document vault, employee service approval queues and history, employee voice conversations, case timelines, HR task templates, leave coverage, and an expanded helpdesk conversation.
4. Subscription listeners are removed on component unmount, so visiting other routes does not accumulate refresh handlers.

**Refresh data is not a Save button.** Unsaved changes are not written to MySQL. On a settings page whose previous refresh action already discarded unsaved edits by reloading saved settings, the new top-bar action keeps that existing behavior. Save intentionally before refreshing on such pages.

## Verification

- `CHECK_REFRESH_DATA_ONLY.bat` checks duplicate controls, mounted module event listeners, route preservation, visual-theme checks, and shared UI source checks.
- `cd web && npm ci && npm run build` is the recommended full frontend build on Windows with an internet connection.
- Production browser/real MySQL verification remains required. The Linux QA environment used archived Windows dependencies, which lack the native Linux Rollup package and cannot execute Vite build.

## Upgrade without data loss

This patch modifies only frontend and frontend static test files. It does not change MySQL tables, backend API behavior, authentication, or employee records. Back up your DB and preserve private `.env` files as standard practice. Do not delete Docker volumes and do not run fresh-install schema scripts.
