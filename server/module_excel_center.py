"""Secure, curated Excel data exchange for SASS HRM.

This is NOT a raw MySQL dump, unrestricted spreadsheet editor, or bypass around
module-specific workflows. Selected datasets have explicit export allowlists;
only three non-sensitive master catalogs allow create-only, preview-confirmed
bulk import. All other editing/deletion stays in the owning HRM module.
"""
from __future__ import annotations

import base64
import binascii
import csv
import hashlib
import hmac
import io
import math
import re
import secrets
import sqlite3
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from fastapi import Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, ValidationError
from main import JWT_SECRET, app, audit, db, require_hr

MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_ROWS = 500
MAX_EXPORT_ROWS = 5000
ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Dataset:
    key: str
    label: str
    table: str
    columns: tuple[str, ...]
    feature: str
    importable: bool = False
    note: str = ''


# Allowlisted column names are constant (never taken from the user's request).
# Never export secrets, authentication data, private notes, identity documents or audit details.
DATASETS = (
    Dataset('employee_directory', 'Employee HRIS', 'employees', ('id', 'code', 'name', 'work_email', 'role', 'designation', 'department', 'location', 'work_mode', 'join_date', 'account_active'), 'employees', note='Identity/role changes use Account Administration and HR approval'),
    Dataset('departments', 'Departments', 'departments', ('id', 'name', 'head_id', 'location'), 'organization'),
    Dataset('office_locations', 'Office locations', 'organization_offices', ('id', 'code', 'name', 'city', 'country', 'address', 'timezone', 'is_active'), 'orgsettings', True),
    Dataset('service_categories', 'Request Desk service types', 'service_categories', ('id', 'name', 'description', 'active'), 'requestdesk', True),
    Dataset('hr_task_templates', 'HR task templates', 'hr_task_templates', ('id', 'title', 'guidance', 'priority', 'due_offset_days', 'active'), 'tasktemplates', True),
    Dataset('recruitment_jobs', 'Job openings', 'jobs', ('id', 'title', 'department', 'location', 'employment_type', 'openings', 'status', 'created_at'), 'recruitment'),
    Dataset('candidates', 'Candidate pipeline', 'candidates', ('id', 'name', 'job_title', 'stage', 'source', 'applied_at'), 'recruitment', note='Use Candidate Search for full-fidelity candidate Excel import'),
    Dataset('shift_templates', 'Shift templates', 'shifts', ('id', 'name', 'start_time', 'end_time', 'location'), 'shifts'),
    Dataset('holidays', 'Office holidays', 'holidays', ('id', 'name', 'day', 'location'), 'organization'),
    Dataset('training_courses', 'Learning courses', 'courses', ('id', 'title', 'category', 'duration_hours', 'description'), 'training'),
    Dataset('policy_register', 'Policy register', 'policies', ('id', 'title', 'category', 'revision', 'last_updated'), 'policies', note='Policy contents and versions are managed only in Policies & Handbook'),
    Dataset('leave_register', 'Leave request status', 'leave_requests', ('id', 'employee_id', 'start_date', 'end_date', 'leave_type', 'days', 'status', 'created_at'), 'leave', note='Leave reasons excluded from bulk export'),
    Dataset('attendance_register', 'Attendance register', 'attendance', ('id', 'employee_id', 'day', 'check_in', 'check_out', 'status'), 'attendance'),
    Dataset('asset_register', 'Assigned assets', 'assets', ('id', 'employee_id', 'asset_name', 'serial_number', 'status', 'assigned_at'), 'assets'),
    Dataset('expense_register', 'Expense status', 'expenses', ('id', 'employee_id', 'title', 'amount', 'currency', 'category', 'status', 'created_at'), 'expenses'),
    Dataset('hr_tasks', 'HR task assignments', 'hr_tasks', ('id', 'title', 'assignee_id', 'created_by', 'due_date', 'priority', 'status', 'created_at'), 'tasks'),
    Dataset('shift_roster', 'Shift allocations', 'shift_assignments', ('id', 'employee_id', 'shift_id', 'work_day'), 'shifts'),
    Dataset('onboarding_items', 'Onboarding checklists', 'onboarding', ('id', 'employee_id', 'title', 'due_date', 'status'), 'onboarding'),
    Dataset('goal_progress', 'Development goal progress', 'goals', ('id', 'employee_id', 'title', 'due_date', 'progress', 'status'), 'performance'),
    Dataset('course_enrollments', 'Learning enrollments', 'enrollments', ('id', 'employee_id', 'course_id', 'status', 'enrolled_at'), 'training'),
    Dataset('interview_schedule', 'Interview schedule', 'interviews', ('id', 'candidate_id', 'interviewer_id', 'scheduled_at', 'duration_minutes', 'mode', 'status', 'created_at'), 'interviews'),
    Dataset('time_entries', 'Project timesheets', 'timesheet_entries', ('id', 'employee_id', 'work_day', 'project', 'hours', 'status', 'created_at'), 'timesheets'),
    Dataset('benefits_catalog', 'Benefit plans', 'benefit_plans', ('id', 'name', 'category', 'active'), 'benefits'),
    Dataset('benefits_enrollments', 'Benefit enrollments', 'benefit_enrollments', ('id', 'employee_id', 'plan_id', 'status', 'enrolled_at'), 'benefits'),
    Dataset('policy_acknowledgements', 'Policy acknowledgements', 'policy_acknowledgements', ('id', 'policy_id', 'employee_id', 'revision', 'acknowledged_at'), 'compliance'),
    Dataset('offboarding_status', 'Offboarding status', 'offboarding', ('id', 'employee_id', 'last_working_day', 'status', 'created_at'), 'offboarding', note='Employee exit reasons excluded from bulk export'),
)
BY_KEY = {dataset.key: dataset for dataset in DATASETS}
IMPORT_COLUMNS = {
    'office_locations': ('code', 'name', 'city', 'country', 'address', 'timezone', 'is_active'),
    'service_categories': ('name', 'description'),
    'hr_task_templates': ('title', 'guidance', 'priority', 'due_offset_days'),
}


def dataset_or_404(key: str) -> Dataset:
    found = BY_KEY.get(key)
    if found is None:
        raise HTTPException(404, 'This module has no reviewed Excel dataset; use its existing feature workflow.')
    return found


def now():
    return datetime.now(timezone.utc).isoformat()


def clean_text(value: object, max_length: int = 32767):
    if value is None:
        return ''
    # Protect formula-like spreadsheet cells even when data is copied into Excel.
    s = str(value).replace('\x00', '')
    s = ''.join(c for c in s if ord(c) >= 32 or c in '\r\t\n')[:max_length]
    if s.lstrip().startswith(('=', '+', '-', '@')):
        s = "'" + s
    return s


def _col_name(index: int) -> str:
    text = ''
    while index:
        index, remainder = divmod(index - 1, 26)
        text = chr(65 + remainder) + text
    return text


def _sheet_xml(headers: list[str], data: list[list[object]]) -> str:
    rows = [headers, *data]
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
           '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>',
           '<sheetFormatPr defaultRowHeight="17"/>', '<cols>']
    for i in range(1, len(headers) + 1):
        out.append(f'<col min="{i}" max="{i}" width="{min(38, max(15, len(headers[i-1]) + 5))}" customWidth="1"/>')
    out += ['</cols>', '<sheetData>']
    for rindex, record in enumerate(rows, 1):
        out.append(f'<row r="{rindex}">')
        for cindex, value in enumerate(record, 1):
            ref = f'{_col_name(cindex)}{rindex}'
            style = 1 if rindex == 1 else (2 if rindex % 2 == 0 else 0)
            if isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value):
                out.append(f'<c r="{ref}" s="{style}"><v>{value}</v></c>')
            else:
                safe = escape(clean_text(value))
                out.append(f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{safe}</t></is></c>')
        out.append('</row>')
    out += ['</sheetData>', f'<autoFilter ref="A1:{_col_name(len(headers))}{len(rows)}"/>', '</worksheet>']
    return ''.join(out)


def build_xlsx(sheets: list[tuple[str, list[str], list[list[object]]]]) -> bytes:
    """Small self-contained OOXML writer; no Excel file or HR data touches disk."""
    if not sheets or len(sheets) > 35:
        raise ValueError('Invalid Excel sheet list')
    out = io.BytesIO()
    types = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
             '<Default Extension="xml" ContentType="application/xml"/>',
             '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
             '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>']
    wb = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>']
    links = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for i, (name, headers, data) in enumerate(sheets, 1):
            if not headers or not re.fullmatch(r'[A-Za-z0-9_ -]{1,31}', name):
                raise ValueError('Invalid worksheet name or headings')
            z.writestr(f'xl/worksheets/sheet{i}.xml', _sheet_xml(headers, data))
            types.append(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
            wb.append(f'<sheet name={quoteattr(name)} sheetId="{i}" r:id="rId{i}"/>')
            links.append(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>')
        wb += ['</sheets></workbook>']
        links += [f'<Relationship Id="rId{len(sheets)+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>', '</Relationships>']
        types += ['</Types>']
        z.writestr('[Content_Types].xml', ''.join(types))
        z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml', ''.join(wb))
        z.writestr('xl/_rels/workbook.xml.rels', ''.join(links))
        z.writestr('xl/styles.xml', '''<?xml version="1.0" encoding="UTF-8"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Aptos"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Aptos"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF24476E"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFill="1" applyFont="1"/><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>''')
    return out.getvalue()


def xlsx_response(binary: bytes, name: str):
    return Response(content=binary, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': f'attachment; filename="{name}"',
                             'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})


def _export_rows(conn, dataset: Dataset, limit: int):
    # Every identifier originates from a fixed server-side whitelist.
    sql = 'SELECT ' + ','.join(dataset.columns) + ' FROM ' + dataset.table + ' ORDER BY id DESC LIMIT ?'
    return [list(dict(r).get(col) for col in dataset.columns) for r in conn.execute(sql, (limit,)).fetchall()]


def _catalog():
    rows = []
    with (ROOT / 'docs' / 'FEATURE_SCREEN_DATABASE_CONTRACTS.csv').open(encoding='utf-8-sig', newline='') as fp:
        for row in csv.DictReader(fp):
            related = [x.key for x in DATASETS if x.feature == row['feature_key']]
            rows.append({'key': row['feature_key'], 'name': row['feature_name'], 'domain': row['domain'],
                         'url': row['feature_url'], 'settings': row['settings_page'],
                         'datasets': related, 'management': 'Open the existing feature for authorized create/edit/delete; not a generic table editor.'})
    return rows


@app.get('/api/admin/excel/catalog')
def excel_catalog(user=Depends(require_hr)):
    return {'features': _catalog(), 'datasets': [
        {'key': d.key, 'name': d.label, 'feature': d.feature, 'columns': list(d.columns),
         'importable': d.importable, 'note': d.note, 'import_fields': list(IMPORT_COLUMNS.get(d.key, ())) }
        for d in DATASETS], 'import_limit': MAX_ROWS, 'export_limit': MAX_EXPORT_ROWS,
        'existing_imports': [
            {'feature': 'employees', 'page': 'dataquality', 'label': 'Employee HRIS (approved preview/commit)'},
            {'feature': 'recruitment', 'page': 'recruitment', 'label': 'Job descriptions (ATS validation)'},
            {'feature': 'candidatesearch', 'page': 'candidatesearch', 'label': 'Candidate library (full-fidelity Excel)'}],
        'caveat': 'Curated, admin-only datasets. Other modules require their owning workflows; this is not an unrestricted database editor or backup.'}


@app.get('/api/admin/excel/export/{key}.xlsx')
def excel_export(key: str, limit: int = Query(1000, ge=1, le=MAX_EXPORT_ROWS), user=Depends(require_hr)):
    dataset = dataset_or_404(key)
    with db() as conn:
        data = _export_rows(conn, dataset, limit)
        audit(conn, user['id'], 'excel.export', f'dataset:{key}', f'rows={len(data)},cap={limit}')
    return xlsx_response(build_xlsx([(key[:31], list(dataset.columns), data)]), f'sass-hrm-{key}.xlsx')


@app.get('/api/admin/excel/database.xlsx')
def excel_database_workbook(limit: int = Query(1000, ge=1, le=2000), user=Depends(require_hr)):
    downloaded = now()
    sheets = [('README', ['Dataset', 'Details'], [
        ['Generated UTC', downloaded], ['Coverage', '26 curated non-secret table views'],
        ['Row limit per sheet', limit], ['Security', 'HR Administrator access only; no passwords or private document content'],
        ['Warning', 'This is a limited data export, NOT a full disaster-recovery MySQL backup.'],
        ['Updates', 'Do not import this snapshot to overwrite audited workflows. Use the module-specific create/edit controls.']])]
    counts = []
    with db() as conn:
        for dataset in DATASETS:
            data = _export_rows(conn, dataset, limit)
            sheets.append((dataset.key[:31], list(dataset.columns), data))
            counts.append(f'{dataset.key}:{len(data)}')
        audit(conn, user['id'], 'excel.export_workbook', 'curated_database', 'limit=' + str(limit) + ';' + ';'.join(counts))
    return xlsx_response(build_xlsx(sheets), 'sass-hrm-curated-database.xlsx')


@app.get('/api/admin/excel/template/{key}.xlsx')
def excel_template(key: str, user=Depends(require_hr)):
    dataset_or_404(key)
    if key not in IMPORT_COLUMNS:
        raise HTTPException(404, 'Excel import is not supported for this dataset; use the owning module.')
    return xlsx_response(build_xlsx([('Import', list(IMPORT_COLUMNS[key]), [])]), f'sass-hrm-{key}-import-template.xlsx')


class ImportPayload(BaseModel):
    filename: str = Field(min_length=5, max_length=160)
    file_base64: str = Field(min_length=4, max_length=3_000_000)
    preview_token: str | None = None


def _file_bytes(body: ImportPayload) -> bytes:
    if '/' in body.filename or '\\' in body.filename or '\x00' in body.filename:
        raise HTTPException(422, 'Invalid filename')
    if not body.filename.lower().endswith(('.csv', '.xlsx')):
        raise HTTPException(422, 'Please select a .csv or .xlsx spreadsheet')
    try:
        binary = base64.b64decode(body.file_base64, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(422, 'File is not valid base64') from exc
    if not binary or len(binary) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, 'Import files must contain 1 byte to 2 MB')
    return binary


def _preview_sign(uid: int, module: str, content: bytes) -> str:
    expiry = int(datetime.now(timezone.utc).timestamp()) + 600
    nonce = secrets.token_hex(8)
    message = f'{uid}:{module}:{hashlib.sha256(content).hexdigest()}:{expiry}:{nonce}'
    encoded = base64.urlsafe_b64encode(message.encode()).decode().rstrip('=')
    return encoded + '.' + hmac.new(JWT_SECRET.encode(), encoded.encode(), hashlib.sha256).hexdigest()


def _preview_check(token: str | None, uid: int, module: str, content: bytes):
    try:
        encoded, tag = (token or '').split('.', 1)
        expected = hmac.new(JWT_SECRET.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(tag, expected):
            raise ValueError('Bad signature')
        signed_uid, signed_module, digest, expiry, _nonce = base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)).decode().split(':')
        if (signed_uid != str(uid) or signed_module != module or digest != hashlib.sha256(content).hexdigest()
                or int(expiry) < int(datetime.now(timezone.utc).timestamp())):
            raise ValueError('Expired or modified')
    except (AttributeError, TypeError, ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(409, 'This import preview is expired or was changed. Preview the same file again.') from exc


def _import_records(module: str, filename: str, binary: bytes):
    if module not in IMPORT_COLUMNS:
        raise HTTPException(404, 'Create-only bulk import is unavailable for this module')
    # Existing safe CSV/XLSX parser checks decompressed size, formulas and row limits.
    from data_quality_import import _parse_file, ImportSettings
    columns, values = _parse_file(filename, binary, ImportSettings(max_rows=MAX_ROWS))
    canonical = list(IMPORT_COLUMNS[module])
    if [v.casefold().strip() for v in columns] != canonical:
        raise HTTPException(422, 'Expected exact column order: ' + ', '.join(canonical))
    from organization_settings_v26 import Office, validate_office
    from workforce_planning_v36 import TaskTemplateIn
    from culture_suite import ServiceCategoryCreate
    cls = {'office_locations': Office, 'hr_task_templates': TaskTemplateIn,
           'service_categories': ServiceCategoryCreate}[module]
    good, errors = [], []
    for index, row in enumerate(values, 2):
        if not any(str(v or '').strip() for v in row):
            continue
        if len(row) > len(canonical) and any(str(v or '').strip() for v in row[len(canonical):]):
            errors.append({'row': index, 'message': 'Unexpected extra columns'}); continue
        values_dict = {name: row[n] if n < len(row) else '' for n, name in enumerate(canonical)}
        if any(isinstance(v, str) and v.lstrip().startswith(('=', '+', '@')) for v in values_dict.values()):
            errors.append({'row': index, 'message': 'Formula cells are not permitted'}); continue
        if 'is_active' in values_dict:
            v_raw = values_dict['is_active']
            v = str('true' if v_raw is None or v_raw == '' else v_raw).strip().lower()
            if v not in ('true', 'false', 'yes', 'no', '1', '0'):
                errors.append({'row': index, 'message': 'is_active must be true/false or 1/0'}); continue
            values_dict['is_active'] = v in ('true', 'yes', '1')
        try:
            record = cls.model_validate(values_dict)
            if module == 'office_locations':
                validate_office(record)
            if module == 'hr_task_templates' and len(record.title.strip()) < 4:
                raise ValueError('Title must be at least 4 characters')
            if module == 'service_categories' and len(record.name.strip()) < 3:
                raise ValueError('Name must be at least 3 characters')
            good.append(record)
        except (ValidationError, ValueError, HTTPException) as exc:
            message = str(exc.detail if isinstance(exc, HTTPException) else exc)
            errors.append({'row': index, 'message': message[:240]})
    if not good and not errors:
        raise HTTPException(422, 'No non-empty records to import')
    if errors:
        good = []  # never partially accept a file containing bad records
    return good, errors


def _save_rows(conn, module: str, records, actor_id: int) -> int:
    from organization_settings_v26 import office_values, check_duplicates, now_utc
    if module == 'office_locations':
        seen = set()
        for row in records:
            vals = office_values(row)
            identifiers = (vals[0].casefold(), vals[1].casefold())
            if any(v in seen for v in identifiers):
                raise HTTPException(409, 'Duplicate office in spreadsheet')
            seen.update(identifiers)
            check_duplicates(conn, vals[0], vals[1])
        for row in records:
            vals = office_values(row)
            conn.execute('INSERT INTO organization_offices (code,name,city,country,address,timezone,is_active,updated_at,updated_by) VALUES(?,?,?,?,?,?,?,?,?)', (*vals, now_utc(), actor_id))
    elif module == 'hr_task_templates':
        seen = set()
        for row in records:
            key = row.title.strip().casefold()
            if key in seen or conn.execute('SELECT 1 FROM hr_task_templates WHERE lower(title)=lower(?)', (row.title.strip(),)).fetchone():
                raise HTTPException(409, 'Duplicate task template title in import or database')
            seen.add(key)
        for row in records:
            conn.execute('INSERT INTO hr_task_templates(title,guidance,priority,due_offset_days,created_by,created_at) VALUES(?,?,?,?,?,?)',
                         (row.title.strip(), row.guidance.strip(), row.priority, row.due_offset_days, actor_id, now()))
    elif module == 'service_categories':
        seen = set()
        for row in records:
            key = row.name.strip().casefold()
            if key in seen or conn.execute('SELECT 1 FROM service_categories WHERE lower(name)=lower(?)', (row.name.strip(),)).fetchone():
                raise HTTPException(409, 'Duplicate service category in import or database')
            seen.add(key)
        for row in records:
            conn.execute('INSERT INTO service_categories(name,description) VALUES(?,?)', (row.name.strip(), row.description.strip()))
    return len(records)


def _duplicates(conn, module: str, records) -> list[str]:
    """Read-only uniqueness check for preview, not authoritative (commit rechecks)."""
    if module == 'office_locations':
        sql = 'SELECT 1 FROM organization_offices WHERE lower(code)=lower(?) OR lower(name)=lower(?)'
        pairs = [(r.code.strip().upper(), r.name.strip()) for r in records]
        codes = [p[0].casefold() for p in pairs]
        names = [p[1].casefold() for p in pairs]
        in_file = len(codes) != len(set(codes)) or len(names) != len(set(names))
    elif module == 'hr_task_templates':
        sql = 'SELECT 1 FROM hr_task_templates WHERE lower(title)=lower(?)'
        pairs = [(r.title.strip(),) for r in records]
        keys = [p[0].casefold() for p in pairs]
        in_file = len(keys) != len(set(keys))
    else:
        sql = 'SELECT 1 FROM service_categories WHERE lower(name)=lower(?)'
        pairs = [(r.name.strip(),) for r in records]
        keys = [p[0].casefold() for p in pairs]
        in_file = len(keys) != len(set(keys))
    conflicts = ['Duplicate entry inside spreadsheet'] if in_file else []
    for p in pairs:
        if conn.execute(sql, p).fetchone():
            conflicts.append('A record already exists for ' + clean_text(p[0], 90))
    return conflicts[:20]


@app.post('/api/admin/excel/import/{module}/preview')
def preview_module_excel(module: str, body: ImportPayload, user=Depends(require_hr)):
    content = _file_bytes(body)
    records, errors = _import_records(module, body.filename, content)
    with db() as conn:
        if not errors:
            errors += [{'row': 0, 'message': x} for x in _duplicates(conn, module, records)]
    return {'module': module, 'valid_rows': len(records) if not errors else 0,
            'errors': errors[:40], 'sample': [r.model_dump() for r in records[:5]] if not errors else [],
            'preview_token': _preview_sign(user['id'], module, content) if not errors else None,
            'note': 'Creates NEW master records only; it never overwrites, deletes or assigns employees.'}


@app.post('/api/admin/excel/import/{module}/commit', status_code=201)
def commit_module_excel(module: str, body: ImportPayload, user=Depends(require_hr)):
    content = _file_bytes(body)
    _preview_check(body.preview_token, user['id'], module, content)
    records, errors = _import_records(module, body.filename, content)
    if errors:
        raise HTTPException(422, {'errors': errors[:40]})
    try:
        with db() as conn:
            count = _save_rows(conn, module, records, user['id'])
            audit(conn, user['id'], 'excel.import_create', f'dataset:{module}',
                  f'rows={count};sha256={hashlib.sha256(content).hexdigest()}')
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, 'Database conflict; no rows were imported. Preview a fresh file.') from exc
    return {'created': count, 'module': module, 'message': 'New master records created; existing records unchanged'}
