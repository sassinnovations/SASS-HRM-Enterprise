# SASS HRM | Enterprise White

The white dashboard design now extends across the full application. Existing page layouts and modules are retained, with a shared white workspace, indigo actions, darker text, a consistent header treatment, and subtle borders and shadows. Colored status badges, warning messages, and chart marks remain meaningful. Sign-in, account request, password recovery, dialogs, loading and error pages, and the floating AI assistant use the same light surfaces.

## Update an existing installation

If you already use the Glassy White dashboard release, back up your project and copy these three files into it, then rebuild and restart the frontend using your existing startup procedure:

- `web/index.html`
- `web/src/main.tsx`
- `web/src/enterprise-white.css`

If you use an older release, use the full package as a base. Preserve your existing environment configuration. Do not rerun setup, reset, or seed scripts just to install this design. No backend changes or MySQL migrations are included in this update.

## Verification

The production frontend build and route smoke tests use a disposable SQLite database. See `tests/enterprise_white_browser_smoke.cjs` for the route and surface checks and `GLASSY_DASHBOARD_RELEASE_NOTES.md` for the dashboard workflow details. The live database is not contacted.

## Porcelain Botanical edition

Subtle white flower and leaf artwork appears in the white workspace and around the sign-in form. Desktop sign-in keeps the original indigo gradient on the branding panel and the original indigo sign-in action. The decorative artwork is bundled locally. Mobile sign-in stays on a white background with the white-on-white floral detail.

To add this edition to the previous Enterprise White release, copy `web/src/main.tsx`, `web/src/botanical-white.css`, and `web/src/art/porcelain-botanical.svg`, then rebuild the frontend. No backend files or database settings changed.

## Sign-in Blue edition

The primary buttons and selected tabs use the same blue as sign-in across the workspace. The white leaf-and-flower backgrounds and sign-in gradient remain. Status and alert colors are unchanged.

If you already use the Porcelain Botanical edition, copy `web/src/main.tsx` and `web/src/sign-in-blue.css`, then rebuild the frontend. No backend or database changes are needed.
