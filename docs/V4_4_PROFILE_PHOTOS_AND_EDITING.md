# SASS HRM v4.4.0 — Profile Photograph, Editing and Safe Deletion

## Included

- My Profile: upload/replace/remove a photograph, editable preferred name, headline, business telephone, about, timezone, language, directory-visibility and avatar-color preferences.
- My Profile: discard unsaved field changes or remove **optional** professional data and photo using a confirmation prompt. This NEVER deletes the employee account, official identity, passwords, payroll or HR records.
- Picture is displayed in My Profile, opt-in Staff Directory, application header, sidebar and My Settings. Protected with bearer tokens, never included in links or browser storage.
- User portrait images are limited to JPEG/PNG/WebP (2 MB upload), decoded and normalized to a static JPEG of at most 512×512, stripped of embedded metadata, and stored as binary inside MySQL. Unsupported, animated, malformed and oversized files are rejected.
- Staff Directory photo access is restricted to authenticated users when the profile owner's account is active and they have opted into directory visibility; private profile images are never exposed through the directory endpoint.
- Photo update/removal and optional-profile deletion events are written to audit records, without logging image content.

## Protected information

Employee ID/code, official name, location, department, designation, role, work email, manager, security credentials and account activation remain under the existing HR Admin/Account Provisioning controls. Work identity changes are not performed by self-service profile editing. For account disable, use existing Account Provisioning. The optional-profile reset is not full account erasure or a GDPR deletion process.

## Database and safe upgrade

New table: `profile_photos(employee_id, mime_type, photo_bytes, updated_at)` (MySQL MEDIUMBLOB, FK to employees). The other 103 tables are unchanged. Full schema: `database/01_application_schema.sql`; additive SQL: `database/UPGRADE_V4_4_PROFILE_PHOTOS_ONLY.sql`; fresh-install schema: `database/02_FRESH_INSTALL_ALL_IN_ONE.sql`.

1. Make and verify a backup of your current HR database and preserve your private `.env` and Docker volume.
2. Extract the upgraded project in a separate folder and carry forward your configured secrets securely; never put them in a shared ZIP.
3. Run `CHECK_PROFILE_IMAGE_V44.bat` for isolated checks. Check the live database with `CHECK_FULL_MYSQL_SCHEMA.bat` and apply reviewed additive SQL if the `profile_photos` table is missing. Do not run the fresh-install script against populated MySQL.
4. Rebuild the Docker API image so its new Pillow dependency installs. Run `START_DOCKER_FULL.bat` and check API health; test with one low-risk employee account.
5. Visit `/workspace/my-profile` and test upload, replace, remove, page refresh, privacy opt-out, reset optional details and login preservation.

## QA status

The isolated FastAPI regression suite, MySQL schema-source validation, TypeScript type checking, static route and single-refresh checks passed. A live MySQL 8.4 database migration, full frontend Vite production build and actual browser tests against the user's Docker installation have NOT been completed here. The frontend build may require a clean `npm ci` on Windows/Docker with the proper platform-native Rollup dependency.
