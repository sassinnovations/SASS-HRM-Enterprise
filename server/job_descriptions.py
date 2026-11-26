"""Audited job-description library and explainable, advisory candidate matching.

JD imports affect only JD tables. Existing candidates, ATS stages and hiring decisions
are never mutated by a match or import. No bundled candidate or JD seed data.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from difflib import SequenceMatcher
from heapq import heappush, heapreplace
from typing import Literal, Iterator, BinaryIO
from urllib.parse import unquote

from fastapi import Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, ValidationError

from main import app, audit, db, require_hr, require_manager

# Logical row ceiling. A million full-length JDs can still exceed host memory, disk,
# request timeout and MySQL storage quotas; see JD_MILLION_ROW_IMPORT_GUIDE.md.
MAX_IMPORT_ROWS = 1_000_000
MAX_UPLOAD = 512 * 1024 * 1024  # compressed .xlsx / raw .csv; server-side enforced
MAX_EXPANDED = 4 * 1024 * 1024 * 1024  # zip expansion bomb protection
IMPORT_DB_PAGE = 5_000
IMPORT_INSERT_BATCH = 500

FIELDS = ('title','description','department','location','employment_type',
          'required_skills','preferred_skills','min_experience','education','status','job_opening_id')
HEADERS = ('Job Posting Title','Description','Department','Location','Employment Type',
           'Required Skills','Preferred Skills','Minimum Experience (Years)','Education',
           'Status','Job Opening ID')
ALIASES = {
    'title': ('job posting title','job title','position title','role','title'),
    'description': ('description','job description','jd','responsibilities and requirements'),
    'department': ('department','team'), 'location': ('location','work location'),
    'employment_type': ('employment type','job type'),
    'required_skills': ('required skills','skills','must have skills'),
    'preferred_skills': ('preferred skills','nice to have skills'),
    'min_experience': ('minimum experience (years)','minimum experience','min experience','experience years'),
    'education': ('education','qualification','minimum qualification'),
    'status': ('status','job status'), 'job_opening_id': ('job opening id','opening id'),
}
SQLITE_SCHEMA = '''
CREATE TABLE IF NOT EXISTS jd_import_batches (
 id INTEGER PRIMARY KEY, filename TEXT NOT NULL, content_sha256 TEXT NOT NULL,
 rows_received INTEGER NOT NULL, rows_imported INTEGER NOT NULL, rows_skipped INTEGER NOT NULL,
 imported_by INTEGER NOT NULL REFERENCES employees(id), imported_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS recruitment_job_descriptions (
 id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL,
 department TEXT NOT NULL DEFAULT '', location TEXT NOT NULL DEFAULT '',
 employment_type TEXT NOT NULL DEFAULT 'Full-time', required_skills TEXT NOT NULL DEFAULT '',
 preferred_skills TEXT NOT NULL DEFAULT '', min_experience REAL NOT NULL DEFAULT 0,
 education TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'Open',
 job_opening_id INTEGER REFERENCES jobs(id) ON DELETE SET NULL,
 import_batch_id INTEGER REFERENCES jd_import_batches(id) ON DELETE SET NULL,
 dedup_key TEXT NOT NULL UNIQUE, created_by INTEGER NOT NULL REFERENCES employees(id),
 updated_by INTEGER NOT NULL REFERENCES employees(id),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_jd_status ON recruitment_job_descriptions(status);
CREATE INDEX IF NOT EXISTS idx_jd_title ON recruitment_job_descriptions(title);
CREATE INDEX IF NOT EXISTS idx_jd_batch ON recruitment_job_descriptions(import_batch_id);
'''

@app.on_event('startup')
def init_jd_tables():
    from main import DB_ENGINE
    if DB_ENGINE == 'sqlite':
        with db() as conn:
            conn.executescript(SQLITE_SCHEMA)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JDInput(BaseModel):
    title: str = Field(min_length=2, max_length=191)
    description: str = Field(min_length=10, max_length=30000)
    department: str = Field(default='', max_length=191)
    location: str = Field(default='', max_length=191)
    employment_type: Literal['Full-time','Part-time','Contract','Internship','Temporary'] = 'Full-time'
    required_skills: str = Field(default='', max_length=3500)
    preferred_skills: str = Field(default='', max_length=3500)
    min_experience: float = Field(default=0, ge=0, le=60)
    education: str = Field(default='', max_length=191)
    status: Literal['Open','Paused','Closed'] = 'Open'
    job_opening_id: int | None = Field(default=None, ge=1)


class ClearAll(BaseModel):
    confirmation: Literal['DELETE ALL JOB DESCRIPTIONS']
    reason: str = Field(min_length=8, max_length=500)
    expected_count: int = Field(ge=0)


def cleaned(body: JDInput) -> dict:
    result = body.model_dump()
    for key, val in result.items():
        if isinstance(val, str):
            result[key] = val.strip()
    if len(result['title']) < 2 or len(result['description']) < 10:
        raise HTTPException(422, 'Job posting title and a description of at least 10 characters are required.')
    return result


def fingerprint(item: dict) -> str:
    # Ignore status, links and import metadata: the same actual JD cannot be imported twice.
    keys = ('title','description','department','location','employment_type','required_skills',
            'preferred_skills','min_experience','education')
    material = [str(item.get(k, '')).strip().casefold() for k in keys]
    return hashlib.sha256(json.dumps(material, ensure_ascii=False).encode()).hexdigest()


def _verify_opening(conn, opening_id: int | None):
    if opening_id is not None and not conn.execute('SELECT id FROM jobs WHERE id=?', (opening_id,)).fetchone():
        raise HTTPException(422,'Linked recruitment job opening does not exist.')


def _get_jd(conn, jd_id: int) -> dict:
    row = conn.execute('SELECT * FROM recruitment_job_descriptions WHERE id=?',(jd_id,)).fetchone()
    if row is None:
        raise HTTPException(404,'Job description not found.')
    return dict(row)


def _audit_title(item: dict) -> str:
    return str(item.get('title',''))[:100]


@app.get('/api/job-descriptions')
def list_jds(q: str = Query('', max_length=160), status: str = Query(''),
             page: int = Query(1, ge=1), page_size: int = Query(30, ge=1, le=100),
             user=Depends(require_manager)):
    if status and status not in ('Open','Paused','Closed'):
        raise HTTPException(422,'Unsupported JD status.')
    clauses=[]; params=[]
    if q.strip():
        term = q.strip().lower().replace('!','!!').replace('%','!%').replace('_','!_')
        clauses.append("(LOWER(title) LIKE ? ESCAPE '!' OR LOWER(description) LIKE ? ESCAPE '!' OR LOWER(required_skills) LIKE ? ESCAPE '!')")
        params.extend(['%'+term+'%']*3)
    if status:
        clauses.append('status=?');params.append(status)
    where = ' WHERE '+' AND '.join(clauses) if clauses else ''
    with db() as conn:
        total = int(conn.execute('SELECT COUNT(*) AS n FROM recruitment_job_descriptions'+where,tuple(params)).fetchone()['n'])
        result = [dict(r) for r in conn.execute(
            'SELECT * FROM recruitment_job_descriptions'+where+' ORDER BY id DESC LIMIT ? OFFSET ?',
            (*params,page_size,(page-1)*page_size)).fetchall()]
    return {'items':result,'total':total,'page':page,'page_size':page_size,'pages':max(1,(total+page_size-1)//page_size)}


@app.get('/api/job-descriptions/imports')
def list_jd_imports(user=Depends(require_manager)):
    with db() as conn:
        return [dict(r) for r in conn.execute('''SELECT b.*,
            (SELECT COUNT(*) FROM recruitment_job_descriptions j WHERE j.import_batch_id=b.id) AS remaining
            FROM jd_import_batches b ORDER BY b.id DESC LIMIT 100''').fetchall()]


@app.get('/api/job-descriptions/clear-all/preview')
def clear_preview(user=Depends(require_hr)):
    with db() as conn:
        return {'job_descriptions':int(conn.execute('SELECT COUNT(*) AS n FROM recruitment_job_descriptions').fetchone()['n']),
                'import_batches':int(conn.execute('SELECT COUNT(*) AS n FROM jd_import_batches').fetchone()['n'])}


@app.post('/api/job-descriptions/clear-all')
def clear_all_jds(body: ClearAll, user=Depends(require_hr)):
    with db() as conn:
        n = int(conn.execute('SELECT COUNT(*) AS n FROM recruitment_job_descriptions').fetchone()['n'])
        if n != body.expected_count:
            raise HTTPException(409,'JD count changed. Refresh deletion preview before confirming.')
        conn.execute('DELETE FROM recruitment_job_descriptions')
        conn.execute('DELETE FROM jd_import_batches')
        audit(conn,user['id'],'recruitment.jd.clear_all','job-descriptions',
              json.dumps({'count':n,'reason':body.reason.strip()}))
    return {'deleted':n,'remaining':0}


@app.post('/api/job-descriptions', status_code=201)
def create_jd(body: JDInput, user=Depends(require_hr)):
    item=cleaned(body); key=fingerprint(item); timestamp=utc_now()
    with db() as conn:
        _verify_opening(conn,item['job_opening_id'])
        try:
            cur=conn.execute('''INSERT INTO recruitment_job_descriptions
                (title,description,department,location,employment_type,required_skills,preferred_skills,
                 min_experience,education,status,job_opening_id,dedup_key,created_by,updated_by,created_at,updated_at)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                tuple(item[k] for k in FIELDS)+(key,user['id'],user['id'],timestamp,timestamp))
        except sqlite3.IntegrityError as exc:
            raise HTTPException(409,'This exact job description already exists.') from exc
        audit(conn,user['id'],'recruitment.jd.created',f'job-description:{cur.lastrowid}',_audit_title(item))
        return {'id':cur.lastrowid,**item}


def _excel_safe(value) -> str:
    s=str(value if value is not None else '')
    # Prevent spreadsheet formula execution upon export, including leading whitespace.
    if s.lstrip().startswith(('=','+','-','@')) or s[:1] in ('\t','\r'):
        return "'"+s
    return s


def _export_pages(conn, page_size=1_000):
    """Keyset pagination avoids loading a million rows into application memory."""
    last_id = 0
    while True:
        group = [dict(r) for r in conn.execute(
            'SELECT id,'+','.join(FIELDS)+',created_at FROM recruitment_job_descriptions '
            'WHERE id>? ORDER BY id LIMIT ?', (last_id, page_size)).fetchall()]
        if not group:
            break
        yield group
        last_id = group[-1]['id']


@app.get('/api/job-descriptions/export.csv')
def export_jds_csv(user=Depends(require_manager)):
    """Stream CSV in bounded groups instead of producing one enormous string."""
    def stream():
        buf=io.StringIO(newline=''); writer=csv.writer(buf)
        writer.writerow(['JD ID',*HEADERS,'Created At'])
        yield '\ufeff'+buf.getvalue()
        with db() as conn:
            for group in _export_pages(conn):
                buf.seek(0);buf.truncate(0)
                for row in group:
                    writer.writerow([row['id'],*[_excel_safe(row[k]) for k in FIELDS],row['created_at']])
                yield buf.getvalue()
    return StreamingResponse(stream(),media_type='text/csv; charset=utf-8',
            headers={'Content-Disposition':'attachment; filename="sass-hrm-job-descriptions.csv"'})


def _xlsx_result(rows, template=False) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb=Workbook(write_only=True);sheet=wb.create_sheet('Job Descriptions')
    headers=list(HEADERS) if template else ['JD ID',*HEADERS,'Created At']
    from openpyxl.cell import WriteOnlyCell
    titles=[]
    for value in headers:
        cell=WriteOnlyCell(sheet,value=value)
        cell.fill=PatternFill('solid',fgColor='193A65');cell.font=Font(color='FFFFFF',bold=True)
        titles.append(cell)
    sheet.freeze_panes='A2'
    sheet.append(titles)
    from openpyxl.utils import get_column_letter
    for idx,h in enumerate(headers,1):
        sheet.column_dimensions[get_column_letter(idx)].width=(68 if h=='Description' else 27 if 'Skills' in h else 23 if h=='Job Posting Title' else 20)
    for row in rows:
        sheet.append([_excel_safe(row[k]) for k in FIELDS] if template else
                     [row['id'],*[_excel_safe(row[k]) for k in FIELDS],row['created_at']])
    output=io.BytesIO();wb.save(output);return output.getvalue()


@app.get('/api/job-descriptions/export.xlsx')
def export_jds_xlsx(user=Depends(require_manager)):
    # Uses an on-disk temporary workbook; handles millions of cells without large RAM lists.
    from openpyxl import Workbook
    from openpyxl.cell import WriteOnlyCell
    from openpyxl.styles import PatternFill, Font
    from openpyxl.utils import get_column_letter
    output=tempfile.TemporaryFile(mode='w+b')
    try:
        wb=Workbook(write_only=True);sheet=wb.create_sheet('Job Descriptions')
        sheet.freeze_panes='A2'
        for idx,h in enumerate(['JD ID',*HEADERS,'Created At'],1):
            sheet.column_dimensions[get_column_letter(idx)].width=(68 if h=='Description' else 27 if 'Skills' in h else 23 if h=='Job Posting Title' else 20)
        cells=[]
        for h in ['JD ID',*HEADERS,'Created At']:
            cell=WriteOnlyCell(sheet,value=h)
            cell.fill=PatternFill('solid',fgColor='193A65');cell.font=Font(color='FFFFFF',bold=True)
            cells.append(cell)
        sheet.append(cells)
        with db() as conn:
            count=int(conn.execute('SELECT COUNT(*) AS n FROM recruitment_job_descriptions').fetchone()['n'])
            sheet.auto_filter.ref=f'A1:M{count+1}'
            for group in _export_pages(conn):
                for row in group:
                    sheet.append([row['id'],*[_excel_safe(row[k]) for k in FIELDS],row['created_at']])
        wb.save(output);output.seek(0)
    except Exception:
        output.close()
        raise
    def chunks():
        try:
            while True:
                part=output.read(1024*1024)
                if not part:break
                yield part
        finally:
            output.close()
    return StreamingResponse(chunks(),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition':'attachment; filename="sass-hrm-job-descriptions.xlsx"'})


@app.get('/api/job-descriptions/template.xlsx')
def jd_template(user=Depends(require_manager)):
    return Response(content=_xlsx_result([],template=True),
       media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
       headers={'Content-Disposition':'attachment; filename="sass-hrm-jd-import-template.xlsx"'})


def _normalize_header(value: str) -> str:
    return re.sub(r'[^a-z0-9]+',' ',str(value or '').strip().lower()).strip()


def _upload_rows(filename: str, source: BinaryIO) -> Iterator[dict]:
    """Yield normalized JD rows incrementally from an XLSX/CSV; no full row lists."""
    if not filename.lower().endswith(('.xlsx','.csv')) or len(filename)>180:
        raise HTTPException(422,'Upload a .xlsx or .csv job-description file.')
    source.seek(0)
    if filename.lower().endswith('.csv'):
        try:
            wrapper=io.TextIOWrapper(source,encoding='utf-8-sig',newline='',errors='strict')
            values=csv.reader(wrapper,strict=True)
            header=next(values,[])
        except (csv.Error,UnicodeDecodeError) as exc:
            raise HTTPException(422,'Invalid UTF-8 CSV file.') from exc
        def csv_rows():
            try:
                yield from values
            finally:
                wrapper.detach()  # the caller owns source, needed by the checksum verification
        rows=csv_rows()
    else:
        try:
            if not zipfile.is_zipfile(source):
                raise HTTPException(422,'Invalid XLSX file.')
            source.seek(0)
            with zipfile.ZipFile(source) as archive:
                members=archive.infolist()
                if len(members)>1_500 or sum(info.file_size for info in members)>MAX_EXPANDED:
                    raise HTTPException(413,'XLSX file exceeds the decompression safety limits (4 GB).')
                if any(info.filename.lower().endswith(('.bin','.xlsm','.exe')) for info in members):
                    raise HTTPException(422,'Macro-enabled Excel files are not accepted.')
            source.seek(0)
            from openpyxl import load_workbook
            wb=load_workbook(source,read_only=True,data_only=False)
            sheet=wb['Job Descriptions'] if 'Job Descriptions' in wb.sheetnames else wb.worksheets[0]
            values=iter(sheet.iter_rows(values_only=False))
            header=[cell.value for cell in next(values,[])]
        except HTTPException:
            raise
        except (ValueError,KeyError,IndexError,OSError,EOFError,zipfile.BadZipFile) as exc:
            raise HTTPException(422,'Invalid or unsupported XLSX file.') from exc
        def excel_rows():
            try:
                for excel_row in values:
                    yield [('='+str(cell.value) if cell.data_type=='f' else cell.value) for cell in excel_row]
            finally:
                wb.close()
        rows=excel_rows()
    if len(header)>70 or not header or not any(str(h or '').strip() for h in header):
        rows.close()
        raise HTTPException(422,'Expected a header row with at most 70 columns.')
    headings=[_normalize_header(str(h or '')) for h in header]
    if len(set(x for x in headings if x))!=len([x for x in headings if x]):
        rows.close()
        raise HTTPException(422,'Duplicate Excel column names are not allowed.')
    normalized_aliases={name:set(map(_normalize_header,ALIASES[name])) for name in FIELDS}
    mapped={field:next((idx for idx,h in enumerate(headings) if h in normalized_aliases[field]),None) for field in FIELDS}
    if mapped['title'] is None or mapped['description'] is None:
        rows.close()
        raise HTTPException(422,'File must contain Job Posting Title and Description columns.')
    count=0
    try:
        for i,row in enumerate(rows,2):
            count+=1
            if count>MAX_IMPORT_ROWS:
                raise HTTPException(413,f'JD import supports at most {MAX_IMPORT_ROWS:,} rows per worksheet.')
            if not any(str(v or '').strip() for v in row):continue
            record={}
            for field,col in mapped.items():
                value=row[col] if col is not None and col<len(row) else ''
                record[field]=str(value).strip() if value is not None else ''
            for field in ('min_experience','job_opening_id'):
                if not record[field]:record[field]=0 if field=='min_experience' else None
            for field,default in (('employment_type','Full-time'),('status','Open')):
                if not record[field]:record[field]=default
            try:
                model=JDInput.model_validate(record)
                item=cleaned(model)
                yield {'row':i,'jd':item,'dedup_key':fingerprint(item)}
            except (ValidationError,HTTPException) as exc:
                if isinstance(exc, ValidationError):
                    first=exc.errors()[0]
                    issue=f'{".".join(str(x) for x in first["loc"])}: {first["msg"]}'
                else:
                    issue=str(exc.detail)
                yield {'row':i,'problem':issue[:160]}
    except (csv.Error,UnicodeDecodeError) as exc:
        raise HTTPException(422,'Invalid UTF-8 CSV file.') from exc
    finally:
        rows.close()


async def _read_upload(request: Request):
    """Spool a large upload on disk and hash while streaming; bounded Python RAM."""
    filename=unquote(request.headers.get('x-filename','job-descriptions.xlsx')).rsplit('/',1)[-1].rsplit('\\',1)[-1]
    if not filename.lower().endswith(('.csv','.xlsx')) or len(filename)>180:
        raise HTTPException(422,'Upload a .xlsx or .csv job-description file.')
    size=0;digest=hashlib.sha256()
    source=tempfile.TemporaryFile(mode='w+b')
    try:
        async for piece in request.stream():
            size+=len(piece)
            if size>MAX_UPLOAD:
                raise HTTPException(413,'JD files must be at most 512 MB. Split larger files.')
            source.write(piece);digest.update(piece)
        if not size:
            raise HTTPException(422,'The uploaded JD file is empty.')
        source.seek(0)
        return filename,source,digest.hexdigest()
    except Exception:
        source.close()
        raise


def _known_dedup_keys(conn, scratch):
    """Build a disk-backed membership index in pages; bounded MySQL query result sizes."""
    last_id=0
    while True:
        records=conn.execute('SELECT id,dedup_key FROM recruitment_job_descriptions '
                             'WHERE id>? ORDER BY id LIMIT ?', (last_id,IMPORT_DB_PAGE)).fetchall()
        if not records:break
        scratch.executemany('INSERT OR IGNORE INTO dedup (key, first_row) VALUES (?,0)',
                            [(r['dedup_key'],) for r in records])
        last_id=records[-1]['id']
    scratch.commit()


def _scan_jds(conn, filename: str, source: BinaryIO, scratch, duplicate_mode: str,
              opening_ids: bool = False) -> dict:
    """Scan without collecting valid JD dictionaries; disk-backed duplicate tracking."""
    scratch.execute('CREATE TABLE dedup (key TEXT PRIMARY KEY, first_row INTEGER NOT NULL) WITHOUT ROWID')
    _known_dedup_keys(conn,scratch)
    counts={'valid':0,'invalid':0,'duplicates':0,'first_issue':None}
    samples=[];issues=[]
    opener_cache={}
    for row in _upload_rows(filename,source):
        if 'problem' in row:
            counts['invalid']+=1
            if len(issues)<50:issues.append({'row':row['row'],'problem':row['problem']})
            continue
        counts['valid']+=1
        if len(samples)<20:
            item=row['jd']
            samples.append({'row':row['row'],'title':item['title'],
                            'department':item['department'],'location':item['location']})
        if opening_ids and row['jd']['job_opening_id'] is not None:
            opening_id=row['jd']['job_opening_id']
            if opening_id not in opener_cache:
                opener_cache[opening_id]=bool(conn.execute('SELECT 1 FROM jobs WHERE id=?', (opening_id,)).fetchone())
            if not opener_cache[opening_id]:
                counts['invalid']+=1
                counts['valid']-=1
                if len(issues)<50:
                    issues.append({'row':row['row'],'problem':'Linked recruitment job opening does not exist.'})
                continue
        present=scratch.execute('SELECT first_row FROM dedup WHERE key=?',(row['dedup_key'],)).fetchone()
        if present is not None:
            counts['duplicates']+=1
            if duplicate_mode=='reject' and counts['first_issue'] is None:
                counts['first_issue']=row['row']
        else:
            scratch.execute('INSERT INTO dedup (key,first_row) VALUES (?,?)',
                            (row['dedup_key'],row['row']))
    scratch.commit()
    if not counts['valid'] and not counts['invalid']:
        raise HTTPException(422,'The job-description workbook has no data rows.')
    return {**counts,'issues':issues,'preview':samples}


def _insert_jd_chunk(conn, chunk):
    """A modest insert batch avoids unbounded queues and huge SQL packets."""
    sql="""INSERT INTO recruitment_job_descriptions
             (title,description,department,location,employment_type,required_skills,preferred_skills,
              min_experience,education,status,job_opening_id,import_batch_id,dedup_key,
              created_by,updated_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
    # The SQLite and MySQL adapters both support chunked parameterized executemany().
    # These writes belong to the enclosing transaction; any error rolls it back.
    conn.executemany(sql,chunk)


def _preview_jd_file(filename: str, source: BinaryIO, sha: str):
    with tempfile.TemporaryDirectory(prefix='sass-jd-scan-') as folder:
        scratch = sqlite3.connect(str(__import__('pathlib').Path(folder)/'dedup.sqlite'))
        try:
            with db() as conn:
                result=_scan_jds(conn,filename,source,scratch,'skip',opening_ids=True)
        finally:
            scratch.close()
    return {'filename':filename,'sha256':sha,
            'total_rows':result['valid']+result['invalid'],
            'valid_rows':result['valid'],'invalid_rows':result['invalid'],
            'duplicates':result['duplicates'],'issues':result['issues'],
            'preview':result['preview'],'requires_confirmation':True,
            'max_rows':MAX_IMPORT_ROWS}


@app.post('/api/job-descriptions/import/preview')
async def preview_jd_import(request: Request, user=Depends(require_hr)):
    filename,source,sha=await _read_upload(request)
    try:
        return await run_in_threadpool(_preview_jd_file,filename,source,sha)
    finally:
        source.close()


def _commit_jd_file(filename: str, source: BinaryIO, sha: str, duplicate_mode: str,
                    invalid_mode: str, actor_id: int):
    with tempfile.TemporaryDirectory(prefix='sass-jd-import-') as folder:
        scratch = sqlite3.connect(str(__import__('pathlib').Path(folder)/'dedup.sqlite'))
        try:
            with db() as conn:
                preflight=_scan_jds(conn,filename,source,scratch,duplicate_mode,opening_ids=True)
                if preflight['invalid'] and invalid_mode=='reject':
                    raise HTTPException(422,{'message':'Correct invalid spreadsheet rows before importing.',
                                             'invalid_rows':preflight['invalid'],
                                             'issues':preflight['issues']})
                if duplicate_mode=='reject' and preflight['duplicates']:
                    raise HTTPException(409,f'Duplicate job description at row {preflight["first_issue"]}. No records imported.')
                stamp=utc_now();insert_count=0;chunk=[]
                batch=conn.execute("""INSERT INTO jd_import_batches
                  (filename,content_sha256,rows_received,rows_imported,rows_skipped,imported_by,imported_at)
                  VALUES(?,?,?,?,?,?,?)""",
                  (filename,sha,preflight['valid']+preflight['invalid'],0,
                   preflight['duplicates']+preflight['invalid'],actor_id,stamp))
                for row in _upload_rows(filename,source):
                    # Only first occurrence of each key is accepted; 0 means it existed in the database.
                    if 'problem' in row:continue
                    first=scratch.execute('SELECT first_row FROM dedup WHERE key=?',(row['dedup_key'],)).fetchone()
                    if not first or first[0]!=row['row']:continue
                    item=row['jd']
                    chunk.append(tuple(item[k] for k in FIELDS)+
                                 (batch.lastrowid,row['dedup_key'],actor_id,actor_id,stamp,stamp))
                    if len(chunk)>=IMPORT_INSERT_BATCH:
                        _insert_jd_chunk(conn,chunk);insert_count+=len(chunk);chunk.clear()
                if chunk:
                    _insert_jd_chunk(conn,chunk);insert_count+=len(chunk)
                conn.execute('UPDATE jd_import_batches SET rows_imported=? WHERE id=?',
                             (insert_count,batch.lastrowid))
                audit(conn,actor_id,'recruitment.jd.imported',f'jd-import:{batch.lastrowid}',
                      json.dumps({'filename':filename,'imported':insert_count,
                                  'skipped':preflight['duplicates']+preflight['invalid'],
                                  'invalid_skipped':preflight['invalid'],'sha256':sha}))
                result={'batch_id':batch.lastrowid,'imported':insert_count,
                        'skipped':preflight['duplicates']+preflight['invalid'],
                        'invalid_skipped':preflight['invalid'],'rows':preflight['valid']+preflight['invalid']}
        finally:
            scratch.close()
    return result


@app.post('/api/job-descriptions/import')
async def import_jds(request: Request,
                     duplicate_mode: Literal['skip','reject'] = Query('skip'),
                     invalid_mode: Literal['reject','skip'] = Query('reject'),
                     user=Depends(require_hr)):
    filename,source,sha=await _read_upload(request)
    try:
        if request.headers.get('x-confirm-sha256','').lower()!=sha:
            raise HTTPException(409,'Preview this exact file first and confirm its SHA-256 checksum.')
        return await run_in_threadpool(_commit_jd_file,filename,source,sha,
                                       duplicate_mode,invalid_mode,user['id'])
    finally:
        source.close()


# Advisory scoring uses ONLY job-related inputs. No stage, gender, age, contact details,
# disability, nationality, or other protected/private traits enter the score.
TECH_TERMS=(
 'Python','Java','JavaScript','TypeScript','React','Angular','Vue','Node.js','Spring Boot',
 'SQL','MySQL','PostgreSQL','MongoDB','Redis','AWS','Azure','GCP','Docker','Kubernetes',
 'Linux','Git','REST API','FastAPI','Django','Flask','C++','C#','.NET','Go','Rust',
 'Machine Learning','Data Science','Pandas','PyTorch','TensorFlow','Power BI','Tableau',
 'Excel','SAP','Salesforce','Workday','Recruitment','Payroll','HRIS','ATS',
 'Communication','Customer Service','Project Management','Accounting','Financial Analysis',
 'SEO','Marketing','Sales','Cybersecurity','Networking','Testing','Automation','Agile',
 'Figma','UI/UX','Oracle','Excel VBA','ETL','Airflow','Snowflake','Spark','Hadoop',
)
STOP_WORDS={
 'and','the','with','for','from','have','that','this','into','will','should','must','your','our','you',
 'are','able','work','years','year','required','preferred','responsibilities','skills','experience',
 'role','job','position','candidate','strong','ability','good','team','including','knowledge',
 'using','develop','development','solutions','support','business','about','their','them','other',
 'excellent','understanding','requirements','across','projects','tasks','professional','minimum',
 'description','essential','software','company','looking','working','plus','degree','education',
 'qualification','building','design','services','systems','people','related','include','based',
 'through','effective','proven','best','practice','technologies','application','engineer','senior',
 'junior','developer','manager','specialist','years','year','month','months','hands','tools','such',
 'more','than','would','beneficial','communication','skills','skills',
 'age','birth','birthday','gender','male','female','man','woman','women','men',
 'marital','married','single','pregnant','pregnancy','religion','religious',
 'caste','race','ethnic','ethnicity','nationality','citizenship','disability',
 'disabled','handicap','salary','phone','contact','email','address','passport',
 'mother','father','family','children','orientation','pronoun','pronouns'
}


def skill_list(raw: str) -> list[str]:
    seen=set();return [s for v in re.split(r'[,;\n|]+',raw or '') if (s:=v.strip()) and not (s.casefold() in seen or seen.add(s.casefold()))][:35]


def _text_has(text: str, phrase: str) -> bool:
    return bool(re.search(r'(?<![\w])'+re.escape(phrase.casefold())+r'(?![\w])',text.casefold()))


def _candidate_text(row: dict) -> str:
    # Only job-relevant public professional profile fields; NOT email, phones, notes or private data.
    raw=row.get('raw_fields')
    try: fields=json.loads(raw or '{}') if isinstance(raw,str) else (raw or {})
    except (ValueError,TypeError):fields={}
    skill_fields=' '.join(str(v) for k,v in fields.items() if any(label in str(k).lower() for label in
                          ('skill','technology','technical stack','expertise')))
    return ' '.join(str(row.get(k) or '') for k in ('job_title','designation','resume_headline',
                 'skills_manual','education','degree','postgraduate'))+' '+skill_fields


def _tokens(text: str) -> set[str]:
    return {tok for tok in re.findall(r'[a-z][a-z0-9+#.]{2,}',text.casefold()) if tok not in STOP_WORDS}


def _matching_skill_set(jd: dict):
    required=skill_list(jd.get('required_skills',''));preferred=skill_list(jd.get('preferred_skills',''))
    if not required:
        # Titles plus descriptions work without filling another mandatory field.
        required=[s for s in TECH_TERMS if _text_has(jd['description'],s)]
    return required,preferred


def score_candidate(jd: dict, candidate: dict, context: dict | None = None) -> dict:
    """Deterministic 0–100 match estimate; individual components are inspectable."""
    text=_candidate_text(candidate)
    required,preferred=(context['required'],context['preferred']) if context else _matching_skill_set(jd)
    matched=[s for s in required if _text_has(text,s)]
    missing=[s for s in required if s not in matched]
    pref_found=[s for s in preferred if _text_has(text,s)]
    rname=str(candidate.get('job_title') or candidate.get('designation') or '')
    title_words=context['title_words'] if context else _tokens(jd['title'])
    role_words=_tokens(rname)
    # Job-title similarity is only a heuristic and never a hiring decision.
    token_overlap=len(title_words & role_words)/len(title_words) if title_words else 0
    title_similarity=SequenceMatcher(None,jd['title'].casefold(),rname.casefold()).ratio() if rname else 0
    role_match=min(1.0,max(token_overlap,title_similarity*0.85))
    jd_keywords=_tokens(jd['description'])-set(s.casefold() for s in required+preferred) if context is None else set()
    # Limit long unrelated boilerplate by keeping only a modest keyword sample.
    keywords=context['keywords'] if context else sorted(jd_keywords)[:45]
    candidate_tokens=_tokens(text)
    keyword_score=len(candidate_tokens & set(keywords))/len(keywords) if keywords else 0
    criteria=[('Job title alignment',25,role_match)]
    if required:criteria.append(('Required skills',45,len(matched)/len(required)))
    if preferred:criteria.append(('Preferred skills',10,len(pref_found)/len(preferred)))
    if keywords:criteria.append(('JD keyword evidence',10,keyword_score))
    exp=jd.get('min_experience') or 0
    if float(exp)>0:
        experience=candidate.get('experience_years')
        criteria.append(('Minimum experience',10,min(1.0,max(0.0,float(experience or 0))/float(exp))))
    education=str(jd.get('education') or '').strip()
    if education:
        qualifications=' '.join(str(candidate.get(k) or '') for k in ('education','degree','postgraduate','doctorate'))
        criteria.append(('Education evidence',5,float(_text_has(qualifications,education))))
    weight=sum(weight for _,weight,_ in criteria)
    score=round(100*sum(w*v for _,w,v in criteria)/weight) if weight else 0
    return {'candidate_id':candidate['id'],'name':candidate['name'],'job_title':candidate['job_title'],
            'stage':candidate['stage'],'location':candidate.get('location') or '',
            'experience_years':candidate.get('experience_years'),
            'score_percent':max(0,min(100,score)),'matched_skills':matched,
            'missing_skills':missing,'preferred_skills_matched':pref_found,
            'components':[{'name':name,'weight':w,'evidence_percent':round(100*v)} for name,w,v in criteria]}


@app.get('/api/job-descriptions/{jd_id}')
def jd_detail(jd_id: int, user=Depends(require_manager)):
    with db() as conn:
        return _get_jd(conn,jd_id)


@app.put('/api/job-descriptions/{jd_id}')
def update_jd(jd_id: int, body: JDInput, user=Depends(require_hr)):
    item=cleaned(body)
    with db() as conn:
        previous=_get_jd(conn,jd_id)
        _verify_opening(conn,item['job_opening_id'])
        changes=[k for k in FIELDS if item[k]!=previous[k]]
        if changes:
            try:
                conn.execute('''UPDATE recruitment_job_descriptions SET
                 title=?,description=?,department=?,location=?,employment_type=?,required_skills=?,
                 preferred_skills=?,min_experience=?,education=?,status=?,job_opening_id=?,
                 dedup_key=?,updated_by=?,updated_at=? WHERE id=?''',
                 tuple(item[k] for k in FIELDS)+(fingerprint(item),user['id'],utc_now(),jd_id))
            except sqlite3.IntegrityError as exc:
                raise HTTPException(409,'This exact job description already exists.') from exc
            audit(conn,user['id'],'recruitment.jd.updated',f'job-description:{jd_id}',
                  json.dumps({'changed_fields':changes,'title':_audit_title(item)}))
    return {'id':jd_id,**item,'updated':bool(changes)}


@app.delete('/api/job-descriptions/{jd_id}')
def delete_jd(jd_id: int, confirm: str = Query(''), user=Depends(require_hr)):
    if confirm != 'DELETE':
        raise HTTPException(422,'Permanent JD deletion requires confirm=DELETE.')
    with db() as conn:
        previous=_get_jd(conn,jd_id)
        conn.execute('DELETE FROM recruitment_job_descriptions WHERE id=?',(jd_id,))
        audit(conn,user['id'],'recruitment.jd.deleted',f'job-description:{jd_id}',_audit_title(previous))
    return {'deleted':jd_id,'permanent':True}



@app.get('/api/job-descriptions/{jd_id}/matches')
def match_jd_candidates(jd_id: int, limit: int=Query(50,ge=1,le=100),
                        min_score: int=Query(0,ge=0,le=100),
                        user=Depends(require_manager)):
    with db() as conn:
        jd=_get_jd(conn,jd_id)
        required,preferred=_matching_skill_set(jd)
        context={'required':required,'preferred':preferred,
                 'title_words':_tokens(jd['title']),
                 'keywords':sorted(_tokens(jd['description'])-set(
                     term.casefold() for term in required+preferred))[:45]}
        # Keyset paging bounds DB rows and memory even for large candidate libraries.
        columns='''SELECT c.id,c.name,c.job_title,c.stage,p.location,p.designation,
              p.resume_headline,p.skills_manual,p.raw_fields,p.education,p.degree,
              p.postgraduate,p.doctorate,p.experience_years
              FROM candidates c LEFT JOIN candidate_profiles p ON p.candidate_id=c.id'''
        best=[]; scanned=0;passed=0;last_id=0
        while True:
            batch=conn.execute(columns+' WHERE c.id>? ORDER BY c.id ASC LIMIT 1000', (last_id,)).fetchall()
            if not batch:
                break
            for record in batch:
                candidate=dict(record)
                scanned+=1
                scored=score_candidate(jd,candidate,context)
                if scored['score_percent']>=min_score:
                    passed+=1
                    rank=(scored['score_percent'],-int(scored['candidate_id']))
                    if len(best)<limit:
                        heappush(best,(rank,scored))
                    elif rank>best[0][0]:
                        heapreplace(best,(rank,scored))
            last_id=int(batch[-1]['id'])
        matches=sorted((entry for _,entry in best),
                       key=lambda item:(-item['score_percent'],item['name'].casefold(),item['candidate_id']))
    return {'jd_id':jd_id,'job_title':jd['title'],'total_candidates':scanned,
            'matches_in_range':passed,'min_score':min_score,'items':matches,
            'method':'Advisory rule-based JD text, skill, title, experience and education evidence. Missing candidate data is not verified.',
            'disclaimer':'Match percentages are estimates, not a commercial ATS score, selection decision or eligibility determination. Human review required.'}
