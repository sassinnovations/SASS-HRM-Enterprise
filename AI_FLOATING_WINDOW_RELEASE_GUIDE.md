# SASS HRM Enterprise — Floating AI Bot release

**Release:** 25 November 2026  
**Source:** `SASS_HRM_CANDIDATE_SEARCH_ZERO_JOB_ROLES_2026-11-24.zip` (the latest supplied project)

## What changed

- Replaced the full-height right-hand dock/rail with a **floating robot icon** at the bottom-right of the HRM page.
- Clicking the icon opens or minimizes the **floating SASS AI chat window**. The window is not a modal and adds **no dark backdrop, scroll lock, or layout reservation**.
- On desktop, drag the window by its title bar, or focus the title bar and use arrow keys (Shift+arrow for larger steps). The window can be resized from the corner and expanded/restored with the header control.
- On phones/tablets, the window is anchored within the available screen and is minimized with the bot icon or header button. Move/resize is limited on small screens for reachability.
- The AI component remains mounted while closed, preserving conversation state and unfinished approved-action forms across HRM page navigation.
- Existing dashboard and policy links to AI still open the floating window.
- The sidebar AI entry remains removed.

## Functional scope preserved

No GenAI/RAG server, action approval, feature catalog, authentication, database schema, MySQL migration, candidate search, or import/export behavior was changed by this UI release. The existing role-aware 73-feature navigation and approved AI operations remain subject to the same server-side permissions and confirmation requirements as before.

## Test results

- `python scripts/check-ai-right-dock.py`: **22 static regression checks passed** for floating presentation, chat lifecycle, navigation, non-modal behavior, responsiveness, and existing AI integration.
- TypeScript 5 source transpilation syntax: **44 TS/TSX source files parsed without syntax errors**. This is not a full typecheck.
- Existing `scripts/check-empty-candidate-bundle.py`: passed; no preloaded candidates/job roles were reintroduced.
- ZIP integrity, original-file preservation, and package manifest: verified during packaging.
- **Not completed:** `npm ci --offline` could not find the cached Vite package. Thus full `tsc -b && vite build`, real interactive browser/device testing, live GenAI access, and MySQL connectivity are **not certified** here.

## Deployment steps

1. Back up the current deployed source and MySQL data; do **not** reset or recreate the production database.
2. Extract the ZIP and open the `web` folder. With npm registry access, run `npm ci` then `npm run build`.
3. Run `CHECK_AI_FLOATING_BOT.bat` (or `python scripts/check-ai-right-dock.py`).
4. Test the floating icon/window and existing HRM forms in a staging site at desktop, tablet, and phone widths. Test dragging, window resizing, keyboard focus, mobile navigation, opening from dashboard/policies, minimizing, and retaining chat state when switching features.
5. Deploy the updated frontend after staging verification; unchanged backend and SQL files do not require new migrations for this release.

**Important:** The window itself occupies its own visible rectangle while open, like any floating chat. It can temporarily cover elements behind that rectangle; users can drag, resize, expand, or minimize it. The rest of the page remains usable and is not dimmed or disabled.

**Production status:** No changes have been deployed to `hrms.sassinnovations.com` by this ZIP.
