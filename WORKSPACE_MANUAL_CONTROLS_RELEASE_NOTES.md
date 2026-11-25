# SASS HRM Enterprise: workspace controls upgrade

This is the full White and Blue project, based on the attached AI Assistant release. It keeps the borderless login, Overview, Products, Projects, and floating assistant.

| Page | What you can manage |
| --- | --- |
| Team leave & coverage planner | HR admins and managers can add, edit, and delete advisory backup plans. Managers are limited to themselves and their direct reports. HR admins can set the absence warning threshold and restrict warnings to weekdays. Employees see plans naming them, without internal handover notes. |
| My requests & shortcuts | Add, edit, or delete private drafts; open the relevant module to submit separately. Add, replace, reorder, and remove shortcuts. Save history category, status, and page size defaults. Submitted history and approvals remain unchanged. |
| Notification inbox | Search, sort, mark read or unread, archive, and restore HR notifications. Set unread-only and compact display preferences. Add, edit, complete, reopen, or delete separate private reminders. Their due dates are for prioritization, not scheduled messages. |
| My calendar | Add, edit, duplicate, or delete private events. Jump to a date and filter personal or official events. Save week start, event visibility, and a default time. Calendar exports exclude private events and their notes unless explicitly enabled. Official HR entries are read-only. |
| My Account Security | Change your password, sign out all sessions, select the sign-in history display limit and time zone, and manage your own security checklist. The checklist does not enforce security policy. Official login and audit histories cannot be edited or deleted. |

## Update an existing installation

1. Stop the running frontend and backend. Back up your project folder and the existing MySQL database. Keep Docker/MySQL and its data volume intact.
2. Extract the ZIP to a separate folder. Merge its contents into the existing White and Blue project folder, keeping your existing root, server and frontend `.env` files. Do not rerun `SETUP_SASS_HRM.bat`, reset MySQL volumes, or use the fresh-install SQL on a populated database.
3. The supported backend schema installer adds eight tables and does not remove existing tables or records. If schema changes are managed separately, have your database administrator apply `database/27_WORKSPACE_MANUAL_CONTROLS_ADD_ONLY.sql` to a verified staging copy first. The file has no database-selection statement; select the intended database before running it. If upgrading from a version that did not include Products and Projects, refer to that release's additive migration too.
4. Restart using the usual launcher for that folder. For the split Windows setup, start MySQL and run `START_LOCAL_DEV.bat`. Check `http://localhost:8000/api/ready`, then open `http://localhost:5173` and verify the five pages with an authorized test account.
5. Built-in HR assistant functions still work without a model API key. OpenAI drafting/chat still requires the documented server-side configuration. No API key, production credentials, or live HR records are bundled.

## Checks

Build the frontend with `npm ci` and `npm run build` in `web`. The isolated API suites in `server` are `workforce_planning_v36_test.py`, `self_service_v31_test.py`, `workspace_v30_test.py`, `calendar_v27_test.py`, and `security_center_v45_test.py`. `ai_copilot_test.py` verifies that confirmed calendar actions still work. Use `python schema_audit.py --file-only` for static schema coverage. These tests do not certify a live MySQL or Windows installation.
