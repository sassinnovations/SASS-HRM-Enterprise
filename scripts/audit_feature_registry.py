"""Offline feature and API registry audit; no DB reads and no writes to HR data.

Run: python scripts/audit_feature_registry.py
Produces CSV inventories and a Markdown summary beside this script's parent directory.
"""
from __future__ import annotations

import ast
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs'
OUT.mkdir(parents=True, exist_ok=True)


def api_inventory():
    output = []
    for source in sorted((ROOT / 'server').glob('*.py')):
        if source.name.endswith('_test.py'):
            continue
        try:
            tree = ast.parse(source.read_text(encoding='utf-8'))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in node.decorator_list:
                if (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                        and isinstance(dec.func.value, ast.Name) and dec.func.value.id == 'app'
                        and dec.func.attr in {'get', 'post', 'put', 'patch', 'delete'}
                        and dec.args and isinstance(dec.args[0], ast.Constant)
                        and isinstance(dec.args[0].value, str)):
                    output.append(dict(method=dec.func.attr.upper(), route=dec.args[0].value,
                                       backend_module=source.name, handler=node.name,
                                       source_line=node.lineno))
    return output


def page_inventory():
    routes = re.findall(r"^\s*(\w+):\s*['\"](/[^'\"]+)",
                        (ROOT / 'web/src/pageRoutes.ts').read_text(encoding='utf-8'), re.M)
    app = (ROOT / 'web/src/App.tsx').read_text(encoding='utf-8')
    menu_data = {key: {'label': label, 'permission': role or 'authenticated'}
                 for key, label, role in re.findall(
                     r"\{key:'(\w+)',label:'([^']+)',icon:[^},]+(?:,only:'([^']+)')?\}", app)}
    # Covers single-line key/label/icon entries in the existing menu registry.
    module = (ROOT / 'web/src/featureCatalog.ts').read_text(encoding='utf-8')
    sections = re.findall(r"\{title:'([^']+)',description:'[^']+'(?:,settingsKey:'([^']+)',settingsLabel:'[^']+')?,pages:\[(.*?)\]\}",
                          module, re.S)
    groups = {}
    for title, settings, entries in sections:
        for key in re.findall(r"\{key:'(\w+)',label:", entries):
            if key in groups:
                raise RuntimeError(f'Duplicate page in group: {key}')
            groups[key] = (title, settings)
    if set(groups) != {x[0] for x in routes}:
        raise RuntimeError('Catalog and page routes differ: ' + str(set(groups) ^ {x[0] for x in routes}))
    return [dict(feature_key=key, url=url, title=menu_data.get(key, {}).get('label', key),
                 domain=groups[key][0], settings_page=groups[key][1],
                 menu_permission=menu_data.get(key, {}).get('permission', 'review'))
            for key, url in routes]


def write_csv(dest, rows):
    if not rows:
        return
    with dest.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    apis, pages = api_inventory(), page_inventory()
    write_csv(OUT / 'FEATURE_API_ROUTES_INVENTORY.csv', apis)
    write_csv(OUT / 'FEATURE_PAGES_INVENTORY.csv', pages)
    method_routes = defaultdict(list)
    for item in apis:
        method_routes[(item['method'], item['route'])].append(item['backend_module'])
    duplicate_endpoints = [(method, path, files) for (method, path), files in method_routes.items() if len(files) > 1]
    defined_tables = len(set(re.findall(r'CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?([A-Za-z_][A-Za-z0-9_]*)', (ROOT / 'server/mysql_schema.sql').read_text(), re.I)))
    groups = Counter(page['domain'] for page in pages)
    lines = [
        '# SASS HRM Feature Audit & Consolidation Report',
        '',
        '> Offline source-level audit, not live workflow or production database verification.',
        '',
        '## Observed source inventory',
        '',
        f'- **Frontend feature URLs:** {len(pages)} unique paths.',
        f'- **API method + route declarations:** {len(apis)} in {len({api["backend_module"] for api in apis})} backend modules.',
        f'- **MySQL CREATE TABLE declarations:** {defined_tables} in `server/mysql_schema.sql` (not live database verification).',
        f'- **Duplicate method + path definitions found:** {len(duplicate_endpoints)}.',
        '',
        '## Consolidated feature groups',
        '',
        '| Group | Frontend pages |',
        '|---|---:|',
    ]
    for group, count in groups.items():
        lines.append(f'| {group} | {count} |')
    lines += ['', '## Updated in this release', '',
        '1. **Unified organization preference editor.** The `Organization` workspace now links directly to `Organization settings`, rather than maintaining a second form for the same five preference fields. Both previously wrote `/api/admin/organization/settings`. No data was migrated or overwritten.',
        '2. **Single module index.** The Administration settings center now groups all feature URLs into eight workstreams and links to the authoritative settings and record-management screens.',
        '3. **Office location delete.** Added administrator-only, reason-confirmed `DELETE /api/admin/organization/offices/{office_id}`, audit history, and safe blocking when employee, department, shift, holiday or job records use the office name. Existing create/edit retained.',
        '4. **Shift template edit/delete.** Added administrator-only `PUT` and reason-confirmed `DELETE /api/shifts/{shift_id}`. Assigned templates cannot be changed or deleted because they would change historical rosters.',
        '5. **Scheduled shift edit/delete.** Added manager/HR-scoped `PUT` and reason-confirmed `DELETE /api/schedule/{assignment_id}`. Edits recheck active employee, shift existence, approved leave and duplicate-day assignments. Past records cannot be edited/deleted.',
        '',
        '## Similar concepts that must not be destructively merged', '',
        '| Related screens | Decision | Why |', '|---|---|---|',
        '| Organization / Organization settings / Company setup | **Unify preference editor and navigation; retain separate record types** | Departments/holidays/announcements, company profile/offices, and import workflows have different life cycles. |',
        '| HR helpdesk / Request desk | **Link in shared talent group; retain case types** | Tickets and service requests use different tables and workflow decisions. |',
        '| Recruitment ATS / Candidate Search / Interviews | **Unified navigation; keep specialized workflows** | Vacancies, candidate profile scoring and interview evidence are not identical records. |',
        '| HR tasks / Task templates | **Retain templates distinct from created tasks** | Deleting a template must not delete assigned work. |',
        '| Payroll workbench / Payslip archive | **Retain separate** | Processing and immutable historical financial records serve different purposes. |',
        '| Employee documents / Secure document vault | **Retain separate** | Document lifecycle metadata and protected file custody have different access safeguards. |',
        '| Review cycles / Appraisals / Check-ins / Evidence | **Group under Performance; retain source records** | Distinct review, evidence and assessment permissions. |',
        '',
        '## Incomplete or intentionally non-CRUD workflows', '',
        '- **Employee HRIS:** `GET /api/employees`, `POST /api/employees`, `PATCH /api/employees/{employee_id}`; a hard-delete employee endpoint was **not** added. Employee identifiers are referenced by payroll, audit, attendance and other history; use account suspension and documented retention/offboarding procedures rather than cascading deletion.',
        '- **Candidate Search:** The search and scoring interface uses recruitment/candidate APIs. Candidate profile updates and stage transitions exist, but blanket bulk deletion was **not** added; candidate retention and rights need separate design and tests.',
        '- **Payroll and approval history:** Not appropriate for universal hard-delete. Reversal and audit/retention workflows must be reviewed separately.',
        '- **Other modules:** Presence of a frontend route or a database table does not prove its add/edit/delete/settings flows work. The inventories below are implementation indexes, not certification.',
        '',
        '## Validation and deployment limitations', '',
        '- New isolated backend integration test: `server/feature_consolidation_crud_test.py`.',
        '- Existing organization and employee-code regression tests should also be run before deployment.',
        '- Frontend TS/TSX was checked for parse errors; complete build requires dependency installation.',
        '- MySQL 268 table definitions are source artifacts only. Verify against your live MySQL host with a backup and the provided database connectivity checks.',
        '- Production deployment was **not** performed; the local release does not update live HR data.',
        '',
        '## Full feature pages', '',
        '| Feature | Module | Existing URL | Canonical settings link |',
        '|---|---|---|---|',
    ]
    for item in pages:
        lines.append(f'| {item["title"]} | {item["domain"]} | `{item["url"]}` | `{item["settings_page"] or "—"}` |')
    lines += ['', '## Exports', '',
              '- `docs/FEATURE_PAGES_INVENTORY.csv` — each of the feature pages, URL, domain and settings association.',
              '- `docs/FEATURE_API_ROUTES_INVENTORY.csv` — each declared API method, path, Python file and handler.',
              '', '**Interpretation:** A route inventory and successful isolated tests are useful engineering evidence but are not substitutes for complete production workflow, role and data migration testing.']
    (ROOT / 'FEATURE_AUDIT_AND_CONSOLIDATION_REPORT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(f'PASS: {len(pages)} page routes, {len(apis)} API entries, {defined_tables} declared MySQL tables, {len(duplicate_endpoints)} duplicate method/path definitions; generated inventory files')
    if duplicate_endpoints:
        for method, route, files in duplicate_endpoints:
            print('DUPLICATE', method, route, files)


if __name__ == '__main__':
    main()
