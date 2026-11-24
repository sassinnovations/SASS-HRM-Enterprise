# File upload, settings, and QA – reviewed patch

## Features involved

- **My profile & settings**: JPEG/PNG/WebP photo uploads up to 2 MiB; normalized JPEG, metadata removed, private and directory permission checks.
- **Company setup & HRIS import**: CSV-only employee import (up to 250 employee rows / 250 KB). Preview first, then confirm. Requires a live MySQL backend and authorized HR role in the web UI.
- **Private employee file vault**: PDF, PNG, JPEG, and UTF-8 TXT, up to 2 MiB, max 30 files per employee. Every upload is scanned by ClamAV and stored Fernet-encrypted in MySQL, with owner/admin access controls. Downloads require the scanner and key; authorized deletion works even when the scanner is unavailable.
- **Employee documents**: metadata register only, intentionally not binary upload.

## New local installation

1. Run `SETUP_SASS_HRM.bat` **once**. It now generates a random, persistent `VAULT_FERNET_KEY` in `server/.env` and sets a local scanner address. The key is not printed or committed.
2. Start Docker Desktop with at least **4 GiB RAM available for ClamAV** in addition to the application/database. A first ClamAV start/update may be slow and needs network access. ClamAV uses a persistent named signature-volume; wait until it reports healthy.
3. `START_HERE.bat` runs the local stack, or `START_DOCKER_FULL.bat` starts the containerized stack with MySQL and ClamAV. The scanner's unauthenticated TCP port is bound to **127.0.0.1 only**, not a public interface.
4. Sign in, navigate to **Private employee file vault** and check the banner. When it reports scanning and encryption are available, upload a small safe TXT/PDF and verify download and delete. Check **My profile & settings** separately for photo uploads, and **Company setup & import** for CSV.
5. For an **existing** `server/.env`, do not rerun initial setup; instead generate the key securely using `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`, store `VAULT_FERNET_KEY` once and keep it in safe backups, set `VAULT_AV_HOST=127.0.0.1` and `VAULT_AV_PORT=3310`. Do not replace a key after storing files; old encrypted files would be unreadable.

Run `CHECK_FILE_UPLOAD_SETTINGS.bat` on Windows for the isolated scanner/profile/CSV/settings regression suite. Run `VERIFY_EVERYTHING.bat` for the fuller regression suite and frontend build. Both require Python dependencies; the full build also requires npm and network access.

## Verification performed for this package

- SQLite-backed role-scoped backend feature suites and route registry/static checks.
- New real-socket ClamAV protocol simulation plus API tests for clean upload, blocked malware, encrypted data, permissions, size/type validation, download/delete, scanner/key failures. Simulator is **not** a genuine antivirus scan.
- Existing profile photo, HRIS import, and API smoke tests.

## Remaining environment-dependent verification

- MySQL 8.4 SQL migrations and actual database persistence, Docker image pulls and scanner signatures, live SMTP, frontend npm build/React browser interactions, end-to-end testing across real role accounts **must be run on the deployment machine**. This package cannot be certified production-ready based on the simulated tests alone.
- ClamAV is not a complete DLP or document-security program. An independent security and privacy review, HTTPS, access governance, retention and recovery controls are required before sensitive personnel files are used.
