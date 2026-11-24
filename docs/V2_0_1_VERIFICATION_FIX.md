# v2.0.1 verification hotfix (app code remains v2.0.0)

## Fixed
- `scripts/verify-design-parity.py` no longer rejects frontend releases purely because their version is outside the old 1.4–1.6 allowlist. It validates the frontend package name, semver, build script, and **all previous theme, menu, route, and security-related static assertions**.
- Added `scripts/test-design-parity.py` covering v2.0, a later 2.1 version, invalid semver, and a deliberate broken theme token. It runs automatically before backend tests in `VERIFY_EVERYTHING.bat`.
- Refreshed the batch runner label and GitHub CI coverage for the new validator and v2.0 backend workflows.

## How to check on Windows
1. Extract this release into a separate directory and **preserve your existing database and `.env` files**; do not copy secret files into the archive.
2. Run `VERIFY_EVERYTHING.bat` from the extracted project root. The order is design parity → validator regression tests → 10 backend test scripts → npm installation (if necessary) → React/Vite production build.
3. If npm installation fails with `EAI_AGAIN`, that indicates a registry DNS/network issue, not a successful frontend build. Verify network/DNS and retry.
4. For production readiness, independently validate a full MySQL-backed login and authorized CRUD workflows, email delivery, the encrypted vault/scanner integration, and real desktop/mobile browser interaction tests.

## Verification in the build workspace
- Design parity and validator regression tests: PASSED.
- 10 backend suites: PASSED on isolated SQLite test databases (not a live MySQL server).
- React production build: NOT VERIFIED because npm registry dependencies were unavailable (`EAI_AGAIN` / not cached).
- The Windows `.bat` runner itself was not executable in the Linux build workspace; its underlying Python checks were executed directly.

This patch does **not** add demo credentials, change payroll behavior, or alter database migrations.
