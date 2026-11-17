"""Import an Excel workbook into configured live MySQL (command-line operator tool).

Run from server/: python import_candidates.py /path/to/your/new_candidates.xlsx
The API upload button is a simpler alternative when the web app is running.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from main import DB_ENGINE, db, init_db
from candidate_library import import_workbook, MAX_UPLOAD

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import all All Candidates Excel rows into HRM MySQL')
    parser.add_argument('workbook', type=Path, help='XLSX workbook path')
    args = parser.parse_args()
    if DB_ENGINE != 'mysql':
        parser.error('This command requires DB_ENGINE=mysql; configure server/.env first.')
    if not args.workbook.is_file() or args.workbook.stat().st_size > MAX_UPLOAD:
        parser.error('The workbook is missing or too large (maximum 25 MB).')
    contents = args.workbook.read_bytes()
    init_db()  # Reuse existing schema and tables; no database reset or new admin account.
    with db() as conn:
        outcome = import_workbook(conn, contents, args.workbook.name)
    print(json.dumps(outcome,indent=2))
