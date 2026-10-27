# SASS HRM Enterprise — Login design refresh

This is a visual and usability update to the v2.5.0 account system. It **does not** change API routes, JWT authentication, MySQL schemas, access rules, or existing HRM modules.

## Corrections

- Centered the sign-in experience within a consistent rounded panel with more balanced whitespace.
- Kept the original SASS dark-to-violet branding gradient and platform copy.
- Adjusted the headline and margins for common laptop/desktop widths and short screens.
- Improved mobile sign-in layout, including a complete SASS HRM brand header.
- Added a keyboard-accessible show/hide password control.
- Made password reset available next to the Password label; activation stays in a collapsible panel.
- Added form labels, autocomplete hints, and an announcement region for login errors.
- Preserved the account activation and password-reset APIs, including backend access controls.

## Installation/update

1. Back up any configuration files (`.env`, `server/.env`) and database data before replacing project files. Keep credentials private.
2. Replace the **application source files** with this update, keeping your existing runtime configuration and MySQL Docker volume. **Do not run fresh-install setup or erase database volumes** on an existing installation.
3. Start Docker Desktop. From the project folder, run `START_DOCKER_FULL.bat`, which rebuilds the Docker images and starts the containers.
4. Visit `http://localhost:5173` and press **Ctrl+Shift+R** to load the latest frontend. If an older page continues to appear, check which project folder was used to build the `web` container.
5. Sign in with an **existing, valid administrator account**. A redesign does not create accounts or correct an incorrect password.

## Verification

- TypeScript `tsc -b` passed with dependencies available for type checking.
- Static design/theme parity checks passed.
- Account administration/JWT and basic authentication regression checks passed.
- Chromium viewport checks with a **representative HTML/CSS preview fixture** passed at 320, 390, 768, 900, 1024, 1280, 1440 and 1800px widths (nine size combinations), without horizontal scrolling.
- Live Docker/MySQL login, email delivery, and the complete Vite production build were **not performed** in this audit environment. The Windows-specific installed dependencies in an earlier upload lacked the Linux Rollup package; the distributed ZIP does not include these dependencies. The target installation must run `npm ci` / Docker build to install dependencies for its platform.

To repeat the static login checks, run `python scripts/verify-login-design.py` from the project folder. These checks are not a substitute for testing a live deployment.
