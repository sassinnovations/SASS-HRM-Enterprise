# SASS HRM Enterprise — Right-Side AI Bot Release

**Release date:** 24 November 2026  
**Based on:** `SASS_HRM_ENTERPRISE_AI_COPILOT_V3_GENAI_RAG_73_FEATURES_2026-11-24.zip`

## Requested UI change — implemented

1. Removed the **AI Assistant** link under the left sidebar's AI & Preferences section.
2. Removed the **Need HR guidance?** AI promotion card from the bottom of the left sidebar.
3. Kept **Settings** and the other HRM navigation items in the left sidebar.
4. Added a purple **AI bot icon** in a narrow, reserved rail on the **right side** of the authenticated HRM workspace.
5. Clicking it opens a scrollable **SASS AI Copilot** dock at the right. Clicking the close icon collapses it back to an icon.
6. No backdrop, screen dimming, fixed floating panel, or obscured page controls: the dock occupies layout space alongside the existing workspace.
7. On widths at or below **820 px**, opening the bot splits the viewport vertically, with the current HRM page visible in the upper portion and the bot below. Both areas scroll independently.
8. Dashboard and Policy shortcuts to **Ask SASS AI** now expand the dock without leaving the current page.
9. Existing `/ai/assistant` bookmarks open the bot and route users to the Overview page, instead of stranding them on an empty standalone Assistant page.
10. The copilot remains mounted while navigating between HRM modules, retaining chat content and unfinished assisted-action forms during normal page navigation.

## AI capabilities and database

The existing AI Copilot v3 backend and MySQL schema were not modified. The right-side dock reuses **the same GenAI/RAG chat, 73-feature guide, fourteen confirmed AI operations, knowledge scoping, and Knowledge Studio**. User permissions, confirmations, and API validation still apply. This is a **frontend layout update**, not a change granting AI additional database privileges.

## How to use

1. Sign in to SASS HRM.
2. Click the **AI** bot icon at the lower right of the workspace.
3. Select Chat, All features, Assisted actions, or (for administrators) Knowledge Studio.
4. Keep working in your Employee HRIS, ATS, Payroll, Settings, or other authorized feature area while the bot is open beside it.
5. Click **X** on the AI panel header to collapse it and return the full workspace width.

## Deployment

1. Back up the running HRM application and MySQL database before deployment.
2. Replace/deploy frontend sources from the updated ZIP, along with the unchanged bundled backend, environment settings, and migrations, according to your usual process.
3. In `web`, run `npm ci` and `npm run build` on a system that can install frontend dependencies.
4. Launch in staging. Confirm navigation, Settings, Employee HRIS table scrolling, forms, bot open/close behavior, and responsive sizes before production release.
5. Use `CHECK_AI_RIGHT_DOCK.bat` (Windows) or `python scripts/check-ai-right-dock.py` for frontend-source regression assertions.
6. Re-run `CHECK_AI_COPILOT.bat` to verify backend GenAI/RAG and database contracts.

## Verification performed here

- Frontend source parse of **43 TS/TSX files**: passed, no syntax errors.
- Right-side dock source checks: passed.
- Representative CSS layout checked in Chromium at **1440, 1080, 900, 768, and 390 px** viewport widths: bot and main content did not overlap in this **isolated layout harness**; this is not a full live-app visual test.
- Existing `server/ai_copilot_test.py`: passed.
- Existing feature screen and MySQL schema integrity **simulations**: passed.
- Frontend `npm ci --offline` failed because the dependency cache lacks the Vite package. Therefore **full Vite/TypeScript build remains unverified**.
- **Live production UI, hosted MySQL, and external GenAI provider were not connected or modified.**

## Changed project files

- `web/src/App.tsx` — sidebar removal, route compatibility, dock state, persistent mounted copilot.
- `web/src/sass-ai-floating-dock.css` — right-side reserved-space layout and responsive styles.
- `scripts/check-ai-right-dock.py` — regression assertions.
- `CHECK_AI_RIGHT_DOCK.bat` — Windows shortcut.
- `docs/AI_RIGHT_DOCK_RELEASE_2026-11-24.md` — included release document.
