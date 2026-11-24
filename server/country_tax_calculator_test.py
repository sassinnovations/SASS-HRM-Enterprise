"""Offline validation of five 2026 salary-tax reference calculators and authenticated API."""
import os
import tempfile
from pathlib import Path
from math import isfinite

os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite',
 JWT_SECRET='country-tax-regression-secret-with-minimum-forty-characters')

from payroll_engine import estimate_tax, progressive, US_FILING
from fastapi.testclient import TestClient

cases=[
 ('IN','new',1275000,0), ('IN','old',1000000,106600),
 ('GB','standard',65000,13432),('GB','scotland',65000,15282.05),
 ('US','single',90000,10970), ('US','married_joint',90000,6440),
 ('US','head_household',90000,7548),('US','married_separate',90000,10970),
 ('AU','resident',90000,17520),('AE','salary',90000,0)
]
for country,status,gross,expected in cases:
 result=estimate_tax(country,gross,status)
 assert abs(result['estimated_annual_tax']-expected)<.01,(country,status,result)
 assert result['estimated_annual_net']==round(gross-expected,2)
 assert result['currency'] in ('INR','GBP','USD','AUD','AED')
 assert result['estimate_only'] is True
 assert result['sources'][0].startswith('https://')
 assert len(result['limitations'])>=1
 assert abs(sum(row['tax_in_band'] for row in result['bracket_breakdown']) -
            sum(float(row['taxable_in_band'])*float(row['rate_percent'])/100 for row in result['bracket_breakdown']))<.06
for country,status in [('IN','new'),('IN','old'),('GB','standard'),('GB','scotland'),('US','single'),
                       ('US','married_joint'),('US','head_household'),('US','married_separate'),('AU','resident'),('AE','salary')]:
 for salary in [0,100,1000,10000,50000,100000,300000]:
  r=estimate_tax(country,salary,status)
  assert all(isfinite(r[field]) for field in ('estimated_annual_tax','estimated_monthly_tax','effective_tax_rate_percent'))
  assert r['estimated_annual_tax']>=0
  assert r['estimated_annual_tax']==round(r['base_tax']+r['cess'],2)
  assert 0<=r['estimated_annual_net']<=salary

for country,status,deduction in [('IN','new',100),('US','single',100),('AE','salary',100)]:
 try: estimate_tax(country,100000,status,deduction)
 except ValueError: pass
 else: raise AssertionError(f'{country} accepted unsupported deductions')
for bad in [("IN",5000001,"new",0),('AU',100000,'unknown',0),('GB',1000,'invalid',0),
            ('US',1000,'invalid',0),('AE',1000,'invalid',0),('IN',-1,'new',0),('IN',100, 'old',101)]:
 try:estimate_tax(*bad)
 except ValueError:pass
 else:raise AssertionError(f'Expected invalid estimate rejection: {bad}')

assert estimate_tax('IN',1200000,'new')['estimated_annual_tax']==0
assert estimate_tax('AU',18200,'resident')['estimated_annual_tax']==0
assert estimate_tax('AU',45000,'resident')['estimated_annual_tax']==4020
assert estimate_tax('AU',135000,'resident')['estimated_annual_tax']==31020
assert estimate_tax('GB',12570,'standard')['estimated_annual_tax']==0
assert estimate_tax('AE',1000000,'salary')['estimated_annual_tax']==0
assert estimate_tax('US',0,'single')['estimated_annual_tax']==0
assert estimate_tax('IN',1300000,'new')['estimated_annual_tax']>0

with tempfile.TemporaryDirectory(prefix='sass-tax-api-') as home:
 os.environ['DATABASE_PATH']=str(Path(home)/'tax_api.db')
 import main
 with TestClient(main.app) as client:
  unauth=client.get('/api/payroll-v2/rules')
  assert unauth.status_code==401,unauth.text
  unauth=client.post('/api/payroll-v2/tax-estimate',json={'country':'AE','regime':'salary','annual_gross':60000})
  assert unauth.status_code==401,unauth.text
  with main.db() as connection:
   connection.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,account_active)
                      VALUES(?,?,?,?,?,?,?,?,?,1)''',('TAX01','Tax Tester','tax@invalid.test','employee','Tester','HR','Remote','2026-01-01',main.hash_password('CountryTax123!')))
  login=client.post('/api/auth/login',json={'email':'tax@invalid.test','password':'CountryTax123!'})
  assert login.status_code==200,login.text
  headers={'Authorization':'Bearer '+login.json()['token']}
  rules=client.get('/api/payroll-v2/rules',headers=headers)
  assert rules.status_code==200,rules.text
  assert rules.json()['supported_tax_calculators']==['IN','GB','US','AU','AE']
  assert set(rules.json()['country_options'])=={'IN','GB','US','AU','AE'}
  for country,status,gross,expected in cases:
   response=client.post('/api/payroll-v2/tax-estimate',json={'country':country,'regime':status,'annual_gross':gross},headers=headers)
   assert response.status_code==200,response.text
   assert abs(response.json()['estimated_annual_tax']-expected)<.01
  for payload in [
     {'country':'AU','regime':'resident','annual_gross':-1},
     {'country':'AU','regime':'resident','annual_gross':500,'deductions':501},
     {'country':'US','regime':'single','annual_gross':50000,'deductions':100},
     {'country':'IN','regime':'new','annual_gross':50000,'deductions':100},
     {'country':'AE','regime':'salary','annual_gross':50000,'deductions':100},
     {'country':'XX','regime':'resident','annual_gross':50000},
     {'country':'AU','regime':'single','annual_gross':50000},
   ]:
   resp=client.post('/api/payroll-v2/tax-estimate',json=payload,headers=headers)
   assert resp.status_code==422,(payload,resp.status_code,resp.text)

ui=(Path(__file__).resolve().parent.parent/'web/src/PayrollExtra.tsx').read_text()
assert all(x in ui for x in ['Australia','United Arab Emirates','head_household','scotland','Export estimate CSV','Progressive tax-band breakdown'])
print('PASS: ten tax status examples, boundary checks, negative/input validation, five country authenticated API configurations, and frontend options.')
