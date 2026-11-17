#!/usr/bin/env python3
"""Verify Developer Console version matches package.json and FastAPI without running Docker."""
import json
import pathlib
import re
import sys
root=pathlib.Path(__file__).resolve().parent.parent
frontend=json.loads((root/'web/package.json').read_text(encoding='utf-8'))['version']
backend=(root/'server/main.py').read_text(encoding='utf-8')
app=(root/'web/src/App.tsx').read_text(encoding='utf-8')
match=re.search(r"app\s*=\s*FastAPI\([^\n]*version\s*=\s*['\"]([^'\"]+)['\"]",backend)
if not match:
    sys.exit('FAIL: FastAPI app version not found in server/main.py')
api_version=match.group(1)
if frontend!=api_version:
    sys.exit(f'FAIL: web/package.json={frontend} but FastAPI={api_version}')
if "import webPackage from '../package.json';" not in app or 'status.app_version!==webPackage.version' not in app:
    sys.exit('FAIL: Developer Console does not compare against web/package.json')
if 'This browser expects SASS HRM API v4.6.0' in app:
    sys.exit('FAIL: old Developer Console warning remains')
print('PASS: Browser API expectation uses package.json and matches backend version '+frontend)
print('Note: live Docker, browser cache and network status require Windows deployment verification.')
