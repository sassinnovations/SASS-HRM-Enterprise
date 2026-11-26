#!/usr/bin/env python3
"""Source-only SASS HRM feature/API/schema coverage and guarded CRUD inventories.

This intentionally does not use any production database credentials or perform SQL.
It does not claim that a client page, API handler, RBAC, or MySQL write works.
"""
import argparse
import ast
import csv
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
CONTRACTS=ROOT/'docs/FEATURE_SCREEN_DATABASE_CONTRACTS.csv'
APIS=ROOT/'docs/FEATURE_API_ROUTES_INVENTORY.csv'
CRUD=ROOT/'docs/FEATURE_CRUD_ENDPOINT_MATRIX.csv'
CHECK=ROOT/'docs/FEATURE_UI_DATABASE_STATIC_CHECKLIST.csv'


def read_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))


def api_routes():
    items=[]
    for f in (ROOT/'server').glob('*.py'):
        if f.name.endswith('_test.py'): continue
        for node in ast.walk(ast.parse(f.read_text(encoding='utf-8'),filename=str(f))):
            if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)): continue
            for deco in node.decorator_list:
                if not isinstance(deco,ast.Call) or not isinstance(deco.func,ast.Attribute): continue
                if deco.func.attr not in ('get','post','put','patch','delete') or not deco.args: continue
                try: route=ast.literal_eval(deco.args[0])
                except (ValueError,TypeError): continue
                items.append({'method':deco.func.attr.upper(),'route':route,'backend_module':f.name,
                              'handler':node.name,'source_line':node.lineno})
    return sorted(items,key=lambda row:(row['backend_module'],row['source_line'],row['method']))


def write_csv(path,fields,items):
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(items)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check',action='store_true',help='Validate without overwriting exports')
    args=ap.parse_args()
    contracts=read_csv(CONTRACTS)
    inventory=read_csv(ROOT/'docs/FEATURE_PAGES_INVENTORY.csv')
    if len(contracts)!=len(inventory) or {r['feature_key'] for r in contracts}!={r['feature_key'] for r in inventory}:
        raise SystemExit('FAILED: missing or duplicate frontend contracts')
    tables={r['Table'] for r in read_csv(ROOT/'database/ALL_MYSQL_TABLES.csv')}
    endpoints=api_routes()
    ids=Counter((r['method'],r['route']) for r in endpoints)
    if max(ids.values(),default=0)>1:raise SystemExit('FAILED: duplicate method/path registration in backend source')
    registered=set(ids)
    records=[];checks=[]
    for c in contracts:
        label=c['feature_name']; route=c['representative_get_route']; names=list(filter(None,c['key_tables'].split(';')))
        api_ok=('GET',route) in registered
        missing=[t for t in names if t not in tables]
        if not api_ok or missing:
            raise SystemExit(f'FAILED: {label} reference absent: route={api_ok}, schema missing={missing}')
        # Only paths with the representative GET's exact prefix are shown.
        # This is an indicative route listing, NOT guaranteed CRUD for the page.
        actions={m:sorted(e['route'] for e in endpoints if e['method']==m and (
            e['route']==route or e['route'].startswith(route.rstrip('/')+'/')))
                 for m in ('GET','POST','PUT','PATCH','DELETE')}
        records.append({'feature_key':c['feature_key'],'feature_name':label,'domain':c['domain'],
                        'feature_url':c['feature_url'],'canonical_settings_page':c['settings_page'],
                        'GET_paths':' | '.join(actions['GET']),
                        'POST_paths':' | '.join(actions['POST']),
                        'PUT_paths':' | '.join(actions['PUT']),
                        'PATCH_paths':' | '.join(actions['PATCH']),
                        'DELETE_paths':' | '.join(actions['DELETE']),
                        'CRUD_certified':'No — declared routes are not validated operations'})
        checks.append({'feature_key':c['feature_key'],'feature_name':label,'domain':c['domain'],
                       'representative_GET_api_registered':'Yes','key_tables_in_268_table_source_schema':'Yes' if names else 'N/A — no stored table mapped',
                       'key_tables':', '.join(names),'runtime_MySQL_table_presence':'Not tested',
                       'runtime_MySQL_table_access':'Not tested','end_to_end_save_edit_delete':'Not tested',
                       'complete_feature_coverage':'Not established'})
    outputs=[(APIS,['method','route','backend_module','handler','source_line'],endpoints),
             (CRUD,list(records[0]),records),(CHECK,list(checks[0]),checks)]
    if args.check:
        for path,fields,data in outputs:
            if read_csv(path)!=[{k:str(v) for k,v in r.items()} for r in data]:
                raise SystemExit(f'FAILED: stale inventory at {path.name}')
    else:
        for path,fields,data in outputs:write_csv(path,fields,data)
    print(f'PASS: {len(inventory)} frontend pages, {len(endpoints)} unique backend method/path endpoints, {len(tables)} MySQL tables; no live database verification')


if __name__=='__main__':main()
