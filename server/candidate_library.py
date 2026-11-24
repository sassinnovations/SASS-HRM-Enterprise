"""Role-scoped MySQL candidate library; byte-perfect XLSX archive and lossless row JSON.

Uploads use the raw XLSX request body (not multipart) to avoid a global parser
configuration dependency. Existing ATS /api/candidates and interview IDs remain intact.
"""
from __future__ import annotations

import hashlib
import csv
import io
import json
import re
import sqlite3
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import Any, Literal

from fastapi import Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from main import app, audit, db, require_hr, require_manager

M = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
PKG_R = '{http://schemas.openxmlformats.org/package/2006/relationships}'
MAX_UPLOAD = 25 * 1024 * 1024
MAX_EXPANDED = 220 * 1024 * 1024
MAX_ROWS = 100_000
ARCHIVE_CHUNK = 256 * 1024

SQLITE_SCHEMA = '''
CREATE TABLE IF NOT EXISTS candidate_import_batches (
 id INTEGER PRIMARY KEY, sha256 TEXT NOT NULL UNIQUE, filename TEXT NOT NULL,
 sheet_name TEXT NOT NULL, rows_expected INTEGER NOT NULL, rows_imported INTEGER NOT NULL,
 file_size_bytes INTEGER NOT NULL, archive_chunks INTEGER NOT NULL,
 content_sha256 TEXT NULL,
 created_by INTEGER, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS candidate_import_chunks (
 batch_id INTEGER NOT NULL, part_number INTEGER NOT NULL, data BLOB NOT NULL,
 PRIMARY KEY(batch_id,part_number), FOREIGN KEY(batch_id) REFERENCES candidate_import_batches(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS candidate_profiles (
 candidate_id INTEGER PRIMARY KEY, import_batch_id INTEGER, source_sheet TEXT,
 source_row INTEGER, source_order INTEGER, email TEXT, phone TEXT,
 location TEXT, preferred_locations TEXT, education TEXT, degree TEXT,
 university TEXT, postgraduate TEXT, doctorate TEXT,
 experience_years REAL, experience_raw TEXT, company TEXT, designation TEXT,
 salary_raw TEXT, salary_lpa REAL, notice TEXT, resume_headline TEXT,
 skills_manual TEXT NOT NULL DEFAULT '', screening_answers TEXT,
 raw_fields TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
 FOREIGN KEY(import_batch_id) REFERENCES candidate_import_batches(id));
CREATE INDEX IF NOT EXISTS idx_candidate_profiles_import_order ON candidate_profiles(import_batch_id,source_order);
CREATE INDEX IF NOT EXISTS idx_candidate_profiles_experience ON candidate_profiles(experience_years);
'''

@app.on_event('startup')
def init_candidate_library():
    # MySQL uses the additive DDL in mysql_schema.sql, installed by mysql_backend.
    from main import DB_ENGINE
    if DB_ENGINE == 'sqlite':
        with db() as conn:
            conn.executescript(SQLITE_SCHEMA)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_value(s: Any) -> str:
    return '' if s is None else str(s)


def excel_date(v: str) -> str:
    if not v or v.upper() == 'NA':
        return ''
    if re.fullmatch(r'\d+(?:\.\d+)?', v):
        try:
            return (datetime(1899, 12, 30) + timedelta(days=float(v))).date().isoformat()
        except (ValueError, OverflowError):
            return v
    return v[:10] if re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:T.*)?', v) else v


def experience_years(v: str) -> float | None:
    if not v or v.upper() == 'NA':
        return None
    if 'fresher' in v.lower():
        return 0.0
    year = re.search(r'(\d+(?:\.\d+)?)\s*(?:years?|yrs?)', v, re.I)
    months = re.search(r'(\d+(?:\.\d+)?)\s*(?:months?|mos?)', v, re.I)
    if year or months:
        return round((float(year.group(1)) if year else 0) + (float(months.group(1)) if months else 0) / 12, 4)
    if re.fullmatch(r'\d+(?:\.\d+)?',v) and 0 <= float(v) <= 80:
        return float(v)
    return None


def salary_lpa(v: str) -> float | None:
    found = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakhs?|lacs?|lpa)', v, re.I)
    return float(found.group(1)) if found else None


def _col_index(ref: str) -> int:
    out = 0
    for ch in re.match(r'[A-Z]+', ref).group(0):
        out = out * 26 + ord(ch) - 64
    return out - 1


def _shared(z: zipfile.ZipFile) -> list[str]:
    if 'xl/sharedStrings.xml' not in z.namelist():
        return []
    result: list[str] = []
    with z.open('xl/sharedStrings.xml') as handle:
        for event, el in ET.iterparse(handle, events=('end',)):
            if el.tag == M + 'si':
                result.append(''.join(x.text or '' for x in el.iter(M + 't')))
                el.clear()
    return result


def lookup(raw: dict[str,str], *names: str) -> str:
    folded = {str(k).strip().lower():normalize_value(v) for k,v in raw.items()}
    for key in names:
        value = folded.get(key.lower(),'')
        if value:
            return value.strip()
    return ''


NAME_HEADERS = ('Name','Candidate Name','Full Name','Applicant Name')
ROLE_HEADERS = ('Job Title','Job Role','Role','Role Applied','Position','Position Applied For',
                'Applied Position','Designation Applied For')


def _sheet_names(z: zipfile.ZipFile) -> list[str]:
    root=ET.fromstring(z.read('xl/workbook.xml'))
    sheets = root.find(M+'sheets')
    if sheets is None:
        raise ValueError('The XLSX workbook does not contain any worksheets.')
    return [item.get('name','') for item in sheets]


def _sheet_path(z: zipfile.ZipFile, target_name: str) -> str:
    root = ET.fromstring(z.read('xl/workbook.xml'))
    sheets = root.find(M + 'sheets')
    if sheets is None:
        raise ValueError('The XLSX workbook does not contain any worksheets.')
    found = next((sh for sh in sheets if sh.get('name') == target_name), None)
    if found is None:
        raise ValueError(f'The Excel file is missing the "{target_name}" worksheet.')
    relid = found.get(R + 'id')
    relroot = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    rel = next((el for el in relroot if el.get('Id') == relid), None)
    if rel is None:
        raise ValueError('Broken Excel worksheet relationship.')
    target = rel.get('Target', '').lstrip('/')
    path = target if target.startswith('xl/') else 'xl/' + target
    path = str(PurePosixPath(path))
    if path not in z.namelist() or '..' in path.split('/'):
        raise ValueError('Missing or unsafe Excel worksheet path.')
    return path


def choose_sheet(z: zipfile.ZipFile, shared: list[str]) -> tuple[str,int,str]:
    names=_sheet_names(z)
    if 'All Candidates' in names:
        return _sheet_path(z,'All Candidates'),1,'All Candidates'
    for name in names[:150]:
        path=_sheet_path(z,name)
        with z.open(path) as probe:
            checked=0
            for _, row in ET.iterparse(probe,events=('end',)):
                if row.tag != M + 'row':
                    continue
                checked += 1
                values=[]
                for cell in row.iter(M+'c'):
                    typ=cell.get('t','')
                    if typ=='inlineStr':
                        inline=cell.find(M+'is')
                        v=''.join(t.text or '' for t in inline.iter(M+'t')) if inline is not None else ''
                    else:
                        elem=cell.find(M+'v')
                        v=elem.text or '' if elem is not None else ''
                        if typ=='s' and v.isdecimal():
                            idx=int(v)
                            v=shared[idx] if idx<len(shared) else ''
                    values.append(v.strip().lower())
                if any(h.lower() in values for h in NAME_HEADERS) and any(h.lower() in values for h in ROLE_HEADERS):
                    return path,int(row.get('r','1')),name
                if checked >= 8:
                    break
                row.clear()
    raise ValueError('No candidate worksheet with Name and Job Role headers was found.')


def imported_sheet_name(binary: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(binary)) as z:
        return choose_sheet(z,_shared(z))[2]


def read_candidate_rows(binary: bytes):
    """Iterate (actual Excel row, all header/value pairs) without dropping duplicates.

    Preserve original raw cell representations in raw_fields; Excel numeric date
    serials are only normalized in the searchable columns.
    """
    if len(binary) > MAX_UPLOAD or len(binary) < 100 or not zipfile.is_zipfile(io.BytesIO(binary)):
        raise ValueError('Upload a valid XLSX file of at most 25 MB.')
    with zipfile.ZipFile(io.BytesIO(binary)) as z:
        infos = z.infolist()
        if len(infos) > 4000 or sum(x.file_size for x in infos) > MAX_EXPANDED:
            raise ValueError('The Excel workbook exceeds safe extraction limits.')
        if any(x.filename.lower().endswith(('.xlsm', '.bin', '.exe')) for x in infos):
            raise ValueError('Macro-enabled or executable Excel files are not supported.')
        shared = _shared(z)
        path, header_row, sheet_name = choose_sheet(z,shared)
        headers: dict[int, str] = {}
        seen: set[str] = set()
        count = 0
        with z.open(path) as stream:
            for event, row in ET.iterparse(stream, events=('end',)):
                if row.tag != M + 'row':
                    continue
                pos = int(row.get('r', '0'))
                cells: dict[int, str] = {}
                for c in row.iter(M + 'c'):
                    ref = c.get('r', '')
                    if not re.match(r'^[A-Z]+\d+$', ref):
                        continue
                    kind = c.get('t', '')
                    if kind == 'inlineStr':
                        inline = c.find(M + 'is')
                        val = ''.join(x.text or '' for x in inline.iter(M + 't')) if inline is not None else ''
                    else:
                        elem = c.find(M + 'v')
                        val = elem.text or '' if elem is not None else ''
                        if kind == 's' and val:
                            idx = int(val)
                            val = shared[idx] if idx < len(shared) else ''
                    cells[_col_index(ref)] = val
                if pos == header_row:
                    for idx, label in cells.items():
                        label = label.strip() or f'Unnamed Column {idx + 1}'
                        original = label
                        suffix = 2
                        while label in seen:
                            label = f'{original} ({suffix})'
                            suffix += 1
                        headers[idx] = label
                        seen.add(label)
                    lowered={h.lower() for h in seen}
                    if not any(x.lower() in lowered for x in NAME_HEADERS) or not any(x.lower() in lowered for x in ROLE_HEADERS):
                        raise ValueError('The candidate worksheet requires name and job role columns.')
                elif pos > header_row and cells:
                    # Every physically populated candidate row is retained, including duplicate people.
                    extra = {i: f'Unlabeled Column {i+1}' for i in cells if i not in headers}
                    original = {headers[i]: normalize_value(cells.get(i, '')) for i in sorted(headers)}
                    # Preserve blank source columns as well as any data outside the header.
                    original.update({extra[i]: normalize_value(cells[i]) for i in sorted(extra)})
                    count += 1
                    if count > MAX_ROWS:
                        raise ValueError('The workbook has more than 100,000 candidate rows.')
                    yield pos, original
                row.clear()
        if not headers or count == 0:
            raise ValueError('The candidate worksheet has no candidate records.')


def _row_profile(raw: dict[str, str]) -> dict[str, Any]:
    g = lambda *keys: lookup(raw,*keys)
    education = ' | '.join(x for x in [g('Under Graduation degree','Education','Highest Qualification','Degree'), g('UG Specialization'),
                  g('Post graduation degree'), g('PG specialization'), g('Doctorate degree'), g('Doctorate specialization')]
                  if x and x.upper() != 'NA')
    exp = g('Total Experience','Experience','Experience Years','Years of Experience')
    salary = g('Annual Salary','Current Salary','Current CTC','CTC')
    return dict(email=g('Email ID','Email','Email Address'), phone=g('Phone Number','Phone','Mobile Number','Contact Number'), location=g('Current Location','Location','City'),
                preferred_locations=g('Preferred Locations','Preferred Location'), education=education,
                degree=g('Under Graduation degree','Education','Highest Qualification','Degree'), university=g('UG University/institute Name','University','Institute'),
                postgraduate=g('Post graduation degree'), doctorate=g('Doctorate degree'),
                experience_years=experience_years(exp), experience_raw=exp,
                company=g('Curr. Company name','Current Company','Company'), designation=g('Curr. Company Designation','Current Designation','Designation'),
                salary_raw=salary, salary_lpa=salary_lpa(salary),
                notice=g('Notice period/ Availability to join','Notice Period','Availability'),
                resume_headline=g('Resume Headline','Summary','Profile Summary'), screening_answers=g('Screening answers','Screening Answers'))

PROFILE_KEYS = ('email', 'phone', 'location', 'preferred_locations', 'education', 'degree',
                'university', 'postgraduate', 'doctorate', 'experience_years', 'experience_raw',
                'company', 'designation', 'salary_raw', 'salary_lpa', 'notice', 'resume_headline',
                'skills_manual', 'screening_answers', 'source_sheet', 'source_row', 'source_order',
                'import_batch_id', 'raw_fields', 'created_at', 'updated_at')


def workbook_content_signature(content: bytes) -> tuple[int, str]:
    """Fingerprint *values and row positions*, not XLSX ZIP metadata/formatting.

    This keeps already-imported candidates from being duplicated when Excel
    rewrites or compresses an otherwise identical workbook.
    Duplicate candidate rows INSIDE one file are still imported separately.
    """
    digest = hashlib.sha256()
    count = 0
    for row_number, original in read_candidate_rows(content):
        encoded = json.dumps([row_number, original], sort_keys=True,
                             ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        digest.update(len(encoded).to_bytes(8, 'big'))
        digest.update(encoded)
        count += 1
    return count, digest.hexdigest()


def _store_archive(conn, batch_id: int, content: bytes):
    """Restore or initially store one workbook, without changing imported rows."""
    for i in range((len(content) + ARCHIVE_CHUNK - 1) // ARCHIVE_CHUNK):
        conn.execute('INSERT INTO candidate_import_chunks(batch_id,part_number,data) VALUES(?,?,?)',
                     (batch_id, i, content[i*ARCHIVE_CHUNK:(i+1)*ARCHIVE_CHUNK]))


def _restore_missing_archive(conn, batch_id: int, content: bytes, filename: str,
                             digest: str, rows: int, *, equivalent: bool) -> dict[str, Any]:
    sha = hashlib.sha256(content).hexdigest()
    chunk_count = (len(content) + ARCHIVE_CHUNK - 1) // ARCHIVE_CHUNK
    conn.execute("""UPDATE candidate_import_batches
                    SET filename=?, sha256=?, sheet_name=?, file_size_bytes=?,
                        archive_chunks=?, content_sha256=? WHERE id=? AND archive_chunks=0""",
                 (filename, sha, imported_sheet_name(content), len(content), chunk_count, digest, batch_id))
    _store_archive(conn, batch_id, content)
    return dict(batch_id=batch_id, imported=0, total=rows, already_imported=True,
                restored_archive=True, content_equivalent=equivalent,
                archived_workbook=True, sha256=sha)


def _matching_previous_batch(conn, expected_rows: int, digest: str) -> dict[str, Any] | None:
    """Do not duplicate imports after removing the archived Excel file.

    A durable content checksum survives archive deletion. Legacy batches with
    archives are verified then upgraded lazily without changing imported rows.
    """
    batches = conn.execute("""SELECT id, sha256, rows_imported, file_size_bytes,
                                     archive_chunks, content_sha256
                              FROM candidate_import_batches
                              WHERE rows_imported=? ORDER BY id DESC""", (expected_rows,)).fetchall()
    for batch in batches:
        if batch['content_sha256'] == digest:
            return dict(batch_id=batch['id'], imported=0, total=expected_rows,
                        already_imported=True, content_equivalent=True,
                        archive_available=bool(batch['archive_chunks']), sha256=batch['sha256'])
        if batch['content_sha256'] or not batch['archive_chunks']:
            continue
        parts = conn.execute("""SELECT data FROM candidate_import_chunks
                                WHERE batch_id=? ORDER BY part_number""", (batch['id'],)).fetchall()
        previous = b''.join(part['data'] for part in parts)
        if len(previous) != batch['file_size_bytes'] or hashlib.sha256(previous).hexdigest() != batch['sha256']:
            continue  # Never trust a corrupt archive as evidence for deduplication.
        try:
            _, old_signature = workbook_content_signature(previous)
        except (ValueError, zipfile.BadZipFile, ET.ParseError):
            continue
        conn.execute('UPDATE candidate_import_batches SET content_sha256=? WHERE id=?',
                     (old_signature, batch['id']))
        if old_signature == digest:
            return dict(batch_id=batch['id'], imported=0, total=expected_rows,
                        already_imported=True, content_equivalent=True,
                        archive_available=True, sha256=batch['sha256'])
    return None


def import_workbook(conn, content: bytes, filename: str, actor_id: int | None = None) -> dict[str, Any]:
    if not filename.lower().endswith('.xlsx'):
        raise ValueError('Only .xlsx Excel files are supported.')
    sha = hashlib.sha256(content).hexdigest()
    filename = filename.split('/')[-1].split('\\')[-1][:255]
    if len(content) > MAX_UPLOAD:
        raise ValueError('The workbook exceeds the 25 MB upload limit.')
    existing = conn.execute("""SELECT id,rows_imported,archive_chunks,content_sha256
                               FROM candidate_import_batches WHERE sha256=?""", (sha,)).fetchone()
    if existing and existing['archive_chunks']:
        return dict(batch_id=existing['id'], imported=0, total=existing['rows_imported'],
                    already_imported=True, archived_workbook=True, sha256=sha)
    # Preflight before any write; a bad XLSX cannot partly create records.
    validation_count, content_signature = workbook_content_signature(content)
    if existing:  # File-only deletion: restore the archive; keep the existing candidates.
        if existing['rows_imported'] != validation_count:
            raise ValueError('Stored import count does not match the re-uploaded Excel file.')
        return _restore_missing_archive(conn, existing['id'], content, filename,
                                        content_signature, validation_count, equivalent=False)
    same_records = _matching_previous_batch(conn, validation_count, content_signature)
    if same_records:
        if not same_records['archive_available']:
            return _restore_missing_archive(conn, same_records['batch_id'], content, filename,
                                            content_signature, validation_count, equivalent=True)
        return same_records
    when = now()
    chunks = (len(content) + ARCHIVE_CHUNK - 1) // ARCHIVE_CHUNK
    sheet_used = imported_sheet_name(content)  # The full original workbook is always archived.
    b = conn.execute('''INSERT INTO candidate_import_batches
       (sha256,filename,sheet_name,rows_expected,rows_imported,file_size_bytes,archive_chunks,created_by,created_at,content_sha256)
       VALUES(?,?,?,?,?,?,?,?,?,?)''',
       (sha,filename,sheet_used,validation_count,0,len(content),chunks,actor_id,when,content_signature))
    batch_id = b.lastrowid
    _store_archive(conn, batch_id, content)
    inserted = 0
    for source_order, (source_row, original) in enumerate(read_candidate_rows(content), start=1):
        profile = _row_profile(original)
        name = lookup(original, *NAME_HEADERS) or f'[Name missing in Excel row {source_row}]'
        role = lookup(original, *ROLE_HEADERS) or original.get('Role Worksheet', '').strip() or '[Job role not provided]'
        stage = lookup(original,'Latest Pipeline Stage','Stage','Status')
        if not stage or stage.upper() == 'NA':
            stage = 'Applied'
        source = lookup(original,'Candidate Source','Source') or 'Excel import'
        applied = excel_date(lookup(original,'Date of application','Application Date','Applied Date')) or when[:10]
        created = conn.execute('INSERT INTO candidates(name,job_title,stage,source,applied_at) VALUES(?,?,?,?,?)',
                               (name,role,stage,source,applied))
        details = {**profile, 'skills_manual':lookup(original,'Skills','Key Skills','Technical Skills','Primary Skills','Skill Set'), 'source_sheet':original.get('Role Worksheet','') or sheet_used,
                   'source_row':source_row, 'source_order':source_order,
                   'import_batch_id':batch_id, 'raw_fields':json.dumps(original,ensure_ascii=False),
                   'created_at':when, 'updated_at':when}
        conn.execute('INSERT INTO candidate_profiles(candidate_id,' + ','.join(PROFILE_KEYS) + ') VALUES(' +
                     ','.join('?' for _ in range(len(PROFILE_KEYS)+1)) + ')',
                     (created.lastrowid,) + tuple(details[k] for k in PROFILE_KEYS))
        inserted += 1
    if inserted != validation_count:
        raise ValueError('Candidate count changed during import; transaction rolled back.')
    conn.execute('UPDATE candidate_import_batches SET rows_imported=? WHERE id=?', (inserted,batch_id))
    if actor_id is not None:
        audit(conn, actor_id, 'candidate.excel.import', f'candidate_import:{batch_id}', f'{inserted} rows')
    return dict(batch_id=batch_id, imported=inserted, total=inserted, already_imported=False,
                sha256=sha, archived_workbook=True)


class CandidateEdit(BaseModel):
    name: str = Field(min_length=1, max_length=191)
    job_title: str = Field(min_length=1, max_length=191)
    stage: str = Field(default='Applied', max_length=191)
    source: str = Field(default='Manual', max_length=191)
    applied_at: str = Field(default='', max_length=191)
    skills_manual: str = Field(default='', max_length=6000)
    raw_fields: dict[str, str] = Field(default_factory=dict)


def _validate_candidate_edit(body: CandidateEdit):
    _validate_raw(body.raw_fields)
    if not body.name.strip() or not body.job_title.strip():
        raise HTTPException(422,'Candidate name and job role are required.')
    if body.applied_at:
        try:
            date.fromisoformat(body.applied_at)
        except ValueError as error:
            raise HTTPException(422,'Application date must be YYYY-MM-DD.') from error


def row_detail(row: dict[str, Any]):
    result = dict(row)
    try:
        result['raw_fields'] = json.loads(result.get('raw_fields') or '{}')
    except json.JSONDecodeError:
        result['raw_fields'] = {}
    return result


@app.get('/api/candidate-library')
def candidate_search(q: str = Query('', max_length=160), skills: str = Query('', max_length=350),
    education: str = Query('', max_length=160), role: str = Query('', max_length=160),
    location: str = Query('', max_length=160), company: str = Query('', max_length=160),
    stage: str = Query('', max_length=120), source: str = Query('', max_length=160),
    min_experience: float | None = Query(None, ge=0, le=80),
    max_experience: float | None = Query(None, ge=0, le=80),
    notice: str = Query('', max_length=160),
    preferred_location: str = Query('', max_length=160),
    designation: str = Query('', max_length=160),
    min_salary: float | None = Query(None, ge=0, le=1000),
    max_salary: float | None = Query(None, ge=0, le=1000),
    skill_mode: str = Query('all', pattern='^(all|any)$'),
    include_raw: bool = Query(False),
    applied_from: str = Query('', max_length=10),
    applied_to: str = Query('', max_length=10),
    sort: str = Query('original'), direction: str = Query('asc'),
    page: int = Query(1, ge=1, le=100000), page_size: int = Query(30, ge=1, le=100),
    user=Depends(require_manager)):
    parts = []
    values: list[Any] = []
    def like_term(value: str) -> str:
        # A user's percent, underscore or escape character is literal search text,
        # not an accidental SQL LIKE wildcard. Works on SQLite and MySQL.
        escaped = value.strip().lower().replace('!', '!!').replace('%', '!%').replace('_', '!_')
        return '%' + escaped + '%'
    def contains(expression: str, value: str):
        if value.strip():
            parts.append('LOWER(COALESCE(' + expression + ",'')) LIKE ? ESCAPE '!'")
            values.append(like_term(value))
    if q.strip():
        fields = ['c.name','c.job_title','c.source','p.email','p.phone','p.location','p.company',
                  'p.designation','p.resume_headline','p.education','p.screening_answers','p.skills_manual','p.raw_fields']
        parts.append('(' + ' OR '.join('LOWER(COALESCE(' + x + ",'')) LIKE ? ESCAPE '!'" for x in fields) + ')')
        values.extend([like_term(q)] * len(fields))
    skill_groups = []
    for s in [x.strip() for x in re.split(r'[,;\n]', skills) if x.strip()]:
        if len(s) > 100:
            raise HTTPException(422,'Each skill must be 100 characters or fewer.')
        fields = ['p.skills_manual', 'p.resume_headline', 'p.screening_answers','c.job_title','p.designation']
        skill_groups.append('(' + ' OR '.join('LOWER(COALESCE(' + x + ",'')) LIKE ? ESCAPE '!'" for x in fields) + ')')
        values.extend([like_term(s)] * len(fields))
    if skill_groups:
        parts.append('(' + (' AND ' if skill_mode == 'all' else ' OR ').join(skill_groups) + ')')
    if education.strip():
        fields = ['p.education','p.degree','p.university','p.postgraduate','p.doctorate']
        parts.append('(' + ' OR '.join('LOWER(COALESCE(' + x + ",'')) LIKE ? ESCAPE '!'" for x in fields) + ')')
        values.extend([like_term(education)] * len(fields))
    if role.strip():
        parts.append('LOWER(c.job_title)=?'); values.append(role.strip().lower())
    contains('p.location',location)
    contains('p.company',company)
    if stage.strip():
        parts.append('LOWER(c.stage)=?'); values.append(stage.strip().lower())
    if source.strip():
        parts.append('LOWER(c.source)=?'); values.append(source.strip().lower())
    contains('p.notice',notice)
    contains('p.preferred_locations', preferred_location)
    contains('p.designation', designation)
    for date_param, comparator in ((applied_from, '>='), (applied_to, '<=')):
        if date_param:
            try: date.fromisoformat(date_param)
            except ValueError as error: raise HTTPException(422,'Application date must be YYYY-MM-DD.') from error
            parts.append('c.applied_at '+comparator+' ?'); values.append(date_param)
    if min_salary is not None:
        parts.append('p.salary_lpa >= ?'); values.append(min_salary)
    if max_salary is not None:
        parts.append('p.salary_lpa <= ?'); values.append(max_salary)
    if min_experience is not None:
        parts.append('p.experience_years >= ?'); values.append(min_experience)
    if max_experience is not None:
        parts.append('p.experience_years <= ?'); values.append(max_experience)
    where = (' WHERE ' + ' AND '.join(parts)) if parts else ''
    sort_map = {
        'original':'CASE WHEN p.source_order IS NULL THEN 1 ELSE 0 END ASC, p.import_batch_id ASC, p.source_order ASC, c.id ASC',
        'name':'c.name', 'role':'c.job_title', 'date':'c.applied_at', 'experience':'p.experience_years',
        'salary':'p.salary_lpa', 'education':'p.education', 'location':'p.location',
        'stage':'c.stage', 'company':'p.company', 'id':'c.id',
    }
    if sort not in sort_map or direction.lower() not in ('asc','desc'):
        raise HTTPException(422,'Unsupported candidate sorting field or direction.')
    direction = direction.upper()
    # Honor descending Excel order too; preserve a stable ordering on every page.
    order = (f'CASE WHEN p.source_order IS NULL THEN 1 ELSE 0 END ASC, '
             f'p.import_batch_id {direction}, p.source_order {direction}, c.id {direction}'
             if sort == 'original' else f'{sort_map[sort]} {direction}, c.id ASC')
    join = ' FROM candidates c LEFT JOIN candidate_profiles p ON p.candidate_id=c.id '
    select = '''SELECT c.id,c.name,c.job_title,c.stage,c.source,c.applied_at,
           p.email,p.phone,p.location,p.preferred_locations,p.education,p.degree,p.university,
           p.postgraduate,p.doctorate,p.experience_years,p.experience_raw,p.company,
           p.designation,p.salary_raw,p.salary_lpa,p.notice,p.resume_headline,p.skills_manual,
           p.source_sheet,p.source_row,p.source_order,p.import_batch_id'''
    if include_raw:
        select += ',p.raw_fields'
    with db() as conn:
        total = conn.execute('SELECT COUNT(*) AS n' + join + where, tuple(values)).fetchone()['n']
        data = [dict(r) for r in conn.execute(select + join + where + ' ORDER BY ' + order + ' LIMIT ? OFFSET ?',
                                             tuple(values) + (page_size, (page-1)*page_size)).fetchall()]
    if include_raw:
        data = [row_detail(item) for item in data]
    return dict(total=total,page=page,page_size=page_size,pages=max(1,(total+page_size-1)//page_size),items=data)


@app.get('/api/candidate-library/options')
def candidate_filters(user=Depends(require_manager)):
    with db() as conn:
        result = {}
        for key,expr in {'roles':'job_title','stages':'stage','sources':'source'}.items():
            # Do not truncate job roles: every distinct imported role must be selectable.
            result[key] = [r['item'] for r in conn.execute(
                f'SELECT DISTINCT {expr} AS item FROM candidates WHERE {expr} IS NOT NULL AND {expr}<>\'\' ORDER BY {expr}').fetchall()]
        result['role_counts'] = {r['job_title']:r['count'] for r in conn.execute(
            '''SELECT job_title,COUNT(*) AS count FROM candidates
               WHERE job_title IS NOT NULL AND job_title<>'' GROUP BY job_title''').fetchall()}
        result['educations'] = [r['item'] for r in conn.execute(
            "SELECT DISTINCT degree AS item FROM candidate_profiles WHERE degree IS NOT NULL AND degree<>'' ORDER BY degree").fetchall()]
        # Role options must reflect ONLY actual candidate rows. Never merge
        # historical job-title suggestions: empty database => zero available roles.
        result['total'] = conn.execute('SELECT COUNT(*) AS n FROM candidates').fetchone()['n']
        result['can_delete_imports'] = user['role'] == 'admin'
        result['imports'] = [dict(r) for r in conn.execute('''
            SELECT b.id,b.filename,b.rows_imported,b.created_at,b.archive_chunks,
                   (SELECT COUNT(*) FROM candidate_profiles p WHERE p.import_batch_id=b.id) AS candidates_remaining
            FROM candidate_import_batches b ORDER BY b.id DESC LIMIT 100''').fetchall()]
        for item in result['imports']:
            item['archive_available'] = item.pop('archive_chunks') > 0
    return result


# The empty-library action is deliberately separate from per-import removal.
# No seed is ever loaded when this endpoint is called.
def _clear_preview(conn) -> dict[str, int]:
    sources = {
        'candidates': 'candidates',
        'candidate_profiles': 'candidate_profiles',
        'import_batches': 'candidate_import_batches',
        'import_chunks': 'candidate_import_chunks',
        'interviews': 'interviews',
        'recruitment_activity': 'candidate_activity',
        'hiring_reviews': 'hiring_stage_reviews',
        'hiring_events': 'hiring_stage_events',
    }
    return {name: int(conn.execute(f'SELECT COUNT(*) AS n FROM {table}').fetchone()['n'])
            for name, table in sources.items()}


class ClearCandidatesRequest(BaseModel):
    confirmation: Literal['CLEAR ALL CANDIDATES']
    reason: str = Field(min_length=10, max_length=500)
    expected_candidates: int = Field(ge=0)
    expected_import_batches: int = Field(ge=0)


@app.get('/api/candidate-library/clear-all/preview')
def preview_clear_all_candidates(user=Depends(require_hr)):
    """Read-only administrator preflight; never touches employee or job records."""
    with db() as conn:
        counts = _clear_preview(conn)
    return {'counts': counts, 'blocked': bool(counts['interviews'] or counts['recruitment_activity']),
            'message': ('Resolve linked interviews or recruitment activity first; no candidates were deleted.'
                        if counts['interviews'] or counts['recruitment_activity']
                        else 'Eligible for administrator-confirmed deletion; take a MySQL backup first.')}


@app.post('/api/candidate-library/clear-all')
def clear_all_candidates(body: ClearCandidatesRequest, user=Depends(require_hr)):
    """Remove all applicants, imported archives and hiring-stage draft history atomically.

    Existing interviews and recruitment notes are protected rather than silently deleted.
    The HR audit trail, employees, job openings and other HR modules are untouched.
    """
    try:
        with db() as conn:
            before = _clear_preview(conn)
            if (before['candidates'] != body.expected_candidates or
                    before['import_batches'] != body.expected_import_batches):
                raise HTTPException(409,'Candidate data changed since preview. Refresh and review the counts again.')
            if before['interviews'] or before['recruitment_activity']:
                raise HTTPException(409, 'Linked interviews or recruitment activity must be resolved before clearing candidates. No data deleted.')
            if before['candidate_profiles']:
                conn.execute('DELETE FROM candidate_profiles')
            if before['candidates']:
                # InnoDB and SQLite cascade the stage reviews and event records.
                conn.execute('DELETE FROM candidates')
            if before['import_chunks']:
                conn.execute('DELETE FROM candidate_import_chunks')
            if before['import_batches']:
                conn.execute('DELETE FROM candidate_import_batches')
            after = _clear_preview(conn)
            if any(after.values()):
                raise HTTPException(409,'Unable to clear candidate-related records safely. Database transaction rolled back.')
            audit(conn,user['id'],'candidate.library.cleared','candidate_library',
                  'reason='+body.reason.strip()+f'; candidate_count={before["candidates"]}; import_batches={before["import_batches"]}')
            return {'cleared':True, 'deleted_candidates':before['candidates'],
                    'deleted_import_batches':before['import_batches'], 'total_candidates':0}
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409,'Linked candidate records prevented deletion; all changes rolled back.') from exc


@app.get('/api/candidate-library/imports/{batch_id}/original')
def download_original(batch_id: int, user=Depends(require_manager)):
    with db() as conn:
        meta = conn.execute('SELECT filename,sha256,file_size_bytes,archive_chunks FROM candidate_import_batches WHERE id=?',(batch_id,)).fetchone()
        if not meta:
            raise HTTPException(404,'Candidate workbook import not found')
        if not meta['archive_chunks']:
            raise HTTPException(410,'This original Excel archive has been removed. Imported candidates remain searchable.')
        original = b''.join(r['data'] for r in conn.execute(
            'SELECT data FROM candidate_import_chunks WHERE batch_id=? ORDER BY part_number',(batch_id,)).fetchall())
    if len(original) != meta['file_size_bytes'] or hashlib.sha256(original).hexdigest() != meta['sha256']:
        raise HTTPException(500,'The archived workbook failed its checksum verification')
    filename = re.sub(r'[^\w .()-]','_',meta['filename'])
    return Response(content=original,media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition':f'attachment; filename="{filename}"', 'Cache-Control':'no-store'})


@app.delete('/api/candidate-library/imports/{batch_id}')
def remove_candidate_import(batch_id: int,
                            mode: Literal['archive', 'all'] = Query('archive'),
                            confirm: str = Query('', max_length=12),
                            user=Depends(require_hr)):
    """Remove archived XLSX only, or atomically remove its imported candidate rows.

    Admin-only and audited. 'all' is refused when referenced by hiring workflows.
    Does not alter independently added ATS or manually entered candidate rows.
    """
    try:
        with db() as conn:
            batch = conn.execute("""SELECT id,sha256,file_size_bytes,archive_chunks,content_sha256
                                    FROM candidate_import_batches WHERE id=?""", (batch_id,)).fetchone()
            if not batch:
                raise HTTPException(404, 'Excel import batch not found')
            candidate_count = conn.execute("""SELECT COUNT(*) AS n FROM candidate_profiles
                                              WHERE import_batch_id=?""", (batch_id,)).fetchone()['n']
            if mode == 'archive':
                if not batch['archive_chunks']:
                    raise HTTPException(409, 'Excel file has already been removed; candidate data remains available.')
                # Legacy/preloaded imports did not store a semantic checksum. Save it
                # before dropping the file, so future reformatted XLSX uploads dedupe.
                if not batch['content_sha256']:
                    original = b''.join(part['data'] for part in conn.execute(
                        'SELECT data FROM candidate_import_chunks WHERE batch_id=? ORDER BY part_number',
                        (batch_id,)).fetchall())
                    if len(original) != batch['file_size_bytes'] or hashlib.sha256(original).hexdigest() != batch['sha256']:
                        raise HTTPException(409, 'Original Excel archive is damaged; unable to verify safe removal.')
                    try:
                        _, digest = workbook_content_signature(original)
                    except (ValueError, zipfile.BadZipFile, ET.ParseError, KeyError, EOFError) as exc:
                        raise HTTPException(409, 'Original Excel archive is invalid; unable to verify safe removal.') from exc
                    conn.execute('UPDATE candidate_import_batches SET content_sha256=? WHERE id=?',
                                 (digest, batch_id))
                conn.execute('DELETE FROM candidate_import_chunks WHERE batch_id=?', (batch_id,))
                conn.execute('UPDATE candidate_import_batches SET archive_chunks=0 WHERE id=?', (batch_id,))
                audit(conn, user['id'], 'candidate.excel.archive.deleted',
                      f'candidate_import:{batch_id}', f'file removed; {candidate_count} candidates retained')
                return dict(batch_id=batch_id, mode=mode, archive_deleted=True,
                            candidates_deleted=0, candidates_retained=candidate_count)
            if confirm != 'DELETE':
                raise HTTPException(400, 'Type DELETE to confirm removing the Excel import and its candidate records.')
            for dependent in ('interviews', 'candidate_activity'):
                linked = conn.execute(f"""SELECT 1 FROM {dependent} d JOIN candidate_profiles p
                                          ON p.candidate_id=d.candidate_id
                                          WHERE p.import_batch_id=? LIMIT 1""", (batch_id,)).fetchone()
                if linked:
                    raise HTTPException(409, 'Cannot delete imported candidates with linked interview or recruitment activity. Resolve those records first, or remove only the Excel file.')
            # InnoDB/SQLite reject unexpected future relationships, so the whole
            # transaction rolls back without partially deleting the import.
            deleted = conn.execute("""DELETE FROM candidates WHERE id IN
                                      (SELECT candidate_id FROM candidate_profiles WHERE import_batch_id=?)""",
                                   (batch_id,)).rowcount
            conn.execute('DELETE FROM candidate_import_batches WHERE id=?', (batch_id,))
            audit(conn, user['id'], 'candidate.excel.import.deleted',
                  f'candidate_import:{batch_id}', f'{deleted} imported candidates and file removed')
            return dict(batch_id=batch_id, mode=mode, archive_deleted=True,
                        candidates_deleted=deleted, candidates_retained=0)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, 'Import has linked HR records. Deletion cancelled without changes.') from exc


@app.get('/api/candidate-library/export.csv')
def export_candidate_csv(request: Request, user=Depends(require_manager)):
    """Export all filtered rows in current sort order, with EVERY original Excel field.

    Escape spreadsheet formula prefixes to prevent formula execution on CSV open.
    """
    params = request.query_params
    selected = {k: params.get(k,'') for k in
                ('q','skills','education','role','location','company','stage','source','notice',
                 'preferred_location','designation','applied_from','applied_to','skill_mode')}
    selected['skill_mode'] = selected['skill_mode'] or 'all'
    if selected['skill_mode'] not in ('all','any'):
        raise HTTPException(422,'Unsupported skill matching mode.')
    if len(selected['q']) > 160 or len(selected['skills']) > 350 or any(len(v)>160 for k,v in selected.items() if k not in ('q','skills')):
        raise HTTPException(422,'Filter text is too long.')
    limits = {}
    for k in ('min_experience','max_experience','min_salary','max_salary'):
        v = params.get(k,'')
        try:
            limits[k] = float(v) if v else None
        except ValueError as error:
            raise HTTPException(422,'Invalid experience filter.') from error
        upper = 80 if 'experience' in k else 1000
        if limits[k] is not None and not 0 <= limits[k] <= upper:
            raise HTTPException(422,'Numeric filter is out of range.')
    sort = params.get('sort','original')
    direction = params.get('direction','asc')
    ordered = []
    original_headers: list[str] = []
    encountered = set()
    page_no = 1
    while True:
        listing = candidate_search(**selected, **limits, sort=sort, direction=direction,
                                   page=page_no,page_size=100,include_raw=False,user=user)
        ids = [x['id'] for x in listing['items']]
        if not ids:
            break
        with db() as conn:
            marks = ','.join('?' for _ in ids)
            details = conn.execute('SELECT candidate_id,raw_fields FROM candidate_profiles WHERE candidate_id IN ('+marks+')',
                                   tuple(ids)).fetchall()
        by_id = {x['candidate_id']:json.loads(x['raw_fields'] or '{}') for x in details}
        for x in listing['items']:
            raw = by_id.get(x['id'],{})
            for field in raw:
                if field not in encountered:
                    encountered.add(field);original_headers.append(field)
            ordered.append((x,raw))
        if page_no >= listing['pages']:
            break
        page_no += 1
    out = io.StringIO(newline='')
    writer = csv.writer(out)
    columns = ('Candidate ID','Excel order','Job Title','Name','Stage','Source','Applied Date',
               'Confirmed Skills','Experience (years)','Current Location','Education')
    writer.writerow([*columns,*original_headers])
    def safe(v):
        cell = '' if v is None else str(v)
        # Excel/Sheets can interpret + - = @ as formulas even in quoted CSV cells.
        return "'" + cell if cell.lstrip().startswith(('=','+','-','@')) else cell
    for x,raw in ordered:
        writer.writerow([safe(v) for v in (x['id'],x['source_order'],x['job_title'],x['name'],x['stage'],
                         x['source'],x['applied_at'],x['skills_manual'],x['experience_years'],
                         x['location'],x['education'])] + [safe(raw.get(k,'')) for k in original_headers])
    return Response(content='\ufeff'+out.getvalue(),media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition':'attachment; filename="candidate-search-results.csv"',
                             'Cache-Control':'no-store'})


@app.get('/api/candidate-library/{candidate_id}')
def get_candidate(candidate_id: int, user=Depends(require_manager)):
    with db() as conn:
        result = conn.execute('SELECT c.*,p.* FROM candidates c LEFT JOIN candidate_profiles p ON p.candidate_id=c.id WHERE c.id=?',(candidate_id,)).fetchone()
        if not result:
            raise HTTPException(404,'Candidate not found')
    return row_detail(dict(result))


@app.post('/api/candidate-library',status_code=201)
def add_candidate(body: CandidateEdit, user=Depends(require_manager)):
    _validate_candidate_edit(body)
    if body.stage.strip() in ('Offer','Hired') and user['role']!='admin':
        raise HTTPException(403,'Only HR administrators can set Offer or Hired stage')
    with db() as conn:
        when=now()
        created=conn.execute('INSERT INTO candidates(name,job_title,stage,source,applied_at) VALUES(?,?,?,?,?)',
                             (body.name.strip(),body.job_title.strip(),body.stage.strip() or 'Applied',
                              body.source.strip() or 'Manual', body.applied_at or when[:10]))
        raw = dict(body.raw_fields)
        raw.update({'Name':body.name.strip(),'Job Title':body.job_title.strip(),
                    'Latest Pipeline Stage':body.stage.strip() or 'Applied'})
        profile = {**_row_profile(raw), 'skills_manual':body.skills_manual, 'source_sheet':'Manual',
                   'source_row':None, 'source_order':None, 'import_batch_id':None,
                   'raw_fields':json.dumps(raw,ensure_ascii=False), 'created_at':when, 'updated_at':when}
        conn.execute('INSERT INTO candidate_profiles(candidate_id,' + ','.join(PROFILE_KEYS) + ') VALUES(' +
                     ','.join('?' for _ in range(len(PROFILE_KEYS)+1)) + ')',
                     (created.lastrowid,) + tuple(profile[k] for k in PROFILE_KEYS))
        audit(conn,user['id'],'candidate.created',f'candidate:{created.lastrowid}')
    return {'id':created.lastrowid}


def _validate_raw(raw: dict[str,str]):
    if len(raw) > 250:
        raise HTTPException(422,'Too many candidate fields')
    for k,v in raw.items():
        if not isinstance(v,str) or len(k)>180 or len(v)>16000:
            raise HTTPException(422,'Invalid or oversized candidate field')


@app.put('/api/candidate-library/{candidate_id}')
def edit_candidate(candidate_id: int, body: CandidateEdit, user=Depends(require_manager)):
    _validate_candidate_edit(body)
    if body.stage.strip() in ('Offer','Hired') and user['role']!='admin':
        raise HTTPException(403,'Only HR administrators can set Offer or Hired stage')
    with db() as conn:
        old=conn.execute('SELECT c.id,c.stage,p.created_at,p.source_sheet,p.source_row,p.source_order,p.import_batch_id FROM candidates c LEFT JOIN candidate_profiles p ON p.candidate_id=c.id WHERE c.id=?',(candidate_id,)).fetchone()
        if not old:
            raise HTTPException(404,'Candidate not found')
        if old['stage'] in ('Offer','Hired') and user['role']!='admin':
            raise HTTPException(403,'Only HR administrators can change an offer or hired candidate')
        raw = dict(body.raw_fields)
        raw.update({'Name':body.name.strip(),'Job Title':body.job_title.strip(),
                    'Latest Pipeline Stage':body.stage.strip() or 'Applied'})
        conn.execute('UPDATE candidates SET name=?,job_title=?,stage=?,source=?,applied_at=? WHERE id=?',
            (body.name.strip(),body.job_title.strip(),body.stage.strip() or 'Applied',
             body.source.strip() or 'Manual', body.applied_at or now()[:10],candidate_id))
        profile = {**_row_profile(raw),'skills_manual':body.skills_manual,
                   'source_sheet':old['source_sheet'] or 'Manual','source_row':old['source_row'],
                   'source_order':old['source_order'],'import_batch_id':old['import_batch_id'],
                   'raw_fields':json.dumps(raw,ensure_ascii=False),
                   'created_at':old['created_at'] or now(),'updated_at':now()}
        if old['created_at']:
            conn.execute('UPDATE candidate_profiles SET '+','.join(f'{k}=?' for k in PROFILE_KEYS)+' WHERE candidate_id=?',
                         tuple(profile[k] for k in PROFILE_KEYS) + (candidate_id,))
        else:
            conn.execute('INSERT INTO candidate_profiles(candidate_id,'+','.join(PROFILE_KEYS)+') VALUES('+','.join('?' for _ in range(len(PROFILE_KEYS)+1))+')',
                         (candidate_id,)+tuple(profile[k] for k in PROFILE_KEYS))
        audit(conn,user['id'],'candidate.updated',f'candidate:{candidate_id}')
    return {'id':candidate_id,'updated':True}


@app.delete('/api/candidate-library/{candidate_id}')
def delete_candidate(candidate_id: int, user=Depends(require_manager)):
    try:
        with db() as conn:
            if not conn.execute('SELECT id FROM candidates WHERE id=?',(candidate_id,)).fetchone():
                raise HTTPException(404,'Candidate not found')
            # Existing interviews/related hiring records must not be silently discarded.
            if conn.execute('SELECT 1 FROM interviews WHERE candidate_id=? LIMIT 1',(candidate_id,)).fetchone():
                raise HTTPException(409,'Candidate has interview history. Remove dependent records using the authorized workflow first.')
            conn.execute('DELETE FROM candidate_profiles WHERE candidate_id=?',(candidate_id,))
            conn.execute('DELETE FROM candidates WHERE id=?',(candidate_id,))
            audit(conn,user['id'],'candidate.deleted',f'candidate:{candidate_id}')
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409,'Candidate has linked HR records and cannot be deleted until those are resolved.') from exc
    return {'id':candidate_id,'deleted':True}


@app.post('/api/candidate-library/import')
async def upload_candidate_xlsx(request: Request, user=Depends(require_manager)):
    try:
        if int(request.headers.get('content-length','0')) > MAX_UPLOAD:
            raise HTTPException(413,'Excel upload must be 25 MB or smaller.')
    except ValueError:
        raise HTTPException(400,'Invalid content length')
    uploaded = bytearray()
    async for part in request.stream():
        if len(uploaded) + len(part) > MAX_UPLOAD:
            raise HTTPException(413,'Excel upload must be 25 MB or smaller.')
        uploaded.extend(part)
    contents = bytes(uploaded)
    filename = request.headers.get('x-filename','candidate-import.xlsx')
    try:
        filename = __import__('urllib.parse',fromlist=['unquote']).unquote(filename)
        def commit_import():
            with db() as conn:
                return import_workbook(conn,contents,filename,user['id'])
        return await run_in_threadpool(commit_import)
    except ValueError as error:
        raise HTTPException(422,str(error)) from error
    except (zipfile.BadZipFile, ET.ParseError, KeyError, EOFError) as error:
        # A corrupt .xlsx is a client validation error, not an internal server error.
        raise HTTPException(422,'Invalid or damaged XLSX workbook structure.') from error
    except sqlite3.IntegrityError as error:
        raise HTTPException(409,'An identical candidate import is currently being processed.') from error
