"""Reference-only 2026 tax estimators. Not statutory tax computation or payroll filing.
No external side effects. Decimal monetary arithmetic and explicit year/jurisdiction.
See docs/PAYROLL_TAX_SCOPE.md and URLs returned in response.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

D=lambda n: Decimal(str(n))
CENT=D('0.01')
def money(n): return float(D(n).quantize(CENT,rounding=ROUND_HALF_UP))
def progressive(taxable, bands):
    remaining=max(D(0),D(taxable)); previous=D(0); total=D(0)
    for cap,rate in bands:
        cap=D(cap) if cap is not None else None
        width=remaining if cap is None else max(D(0),min(remaining,cap-previous))
        total+=width*D(rate)
        remaining-=width
        if not remaining: break
        if cap is not None: previous=cap
    return total

INDIA_NEW=[(400000,0),(800000,'.05'),(1200000,'.10'),(1600000,'.15'),(2000000,'.20'),(2400000,'.25'),(None,'.30')]
INDIA_OLD=[(250000,0),(500000,'.05'),(1000000,'.20'),(None,'.30')]
UK_ENG=[(37700,'.20'),(125140,'.40'),(None,'.45')]
US_SINGLE=[(12400,'.10'),(50400,'.12'),(105700,'.22'),(201775,'.24'),(256225,'.32'),(640600,'.35'),(None,'.37')]
SOURCES={
 'IN':'https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/income-and-tax-estimator-um',
 'GB':'https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027',
 'US':'https://www.irs.gov/newsroom/irs-releases-tax-inflation-adjustments-for-tax-year-2026-including-amendments-from-the-one-big-beautiful-bill',
 'PF':'https://www.epfindia.gov.in/site_en/For_Employers.php/Disablitity.php',
 'ESI':'https://www.esic.gov.in/attachments/circularfile/7a6e3189a5201812e4c067e5286a1c1e.pdf'
}

def estimate_tax(country:Literal['IN','GB','US'], annual_gross:float, regime:str='new', deductions:float=0, resident:bool=True):
    gross=D(annual_gross); deductions=D(deductions)
    if gross<0 or deductions<0: raise ValueError('Gross pay and deductions cannot be negative')
    if country=='IN':
        if gross>5000000: raise ValueError('Indian salary over INR 50 lakh requires a surcharge-aware specialist engine; this calculator does not support it.')
        if regime not in ('new','old'): raise ValueError('India regime must be new or old')
        std=D(75000 if regime=='new' else 50000)
        allowed=D(0) if regime=='new' else deductions
        taxable=max(D(0),gross-std-allowed)
        raw=progressive(taxable,INDIA_NEW if regime=='new' else INDIA_OLD)
        rebate=D(0)
        if resident and regime=='new' and taxable<=1200000: rebate=min(raw,D(60000))
        elif resident and regime=='new' and taxable>1200000:
            # Approximate 87A marginal relief for eligible ordinary income above 12 lakh.
            rebate=max(D(0),raw-(taxable-D(1200000)))
        elif resident and regime=='old' and taxable<=500000: rebate=min(raw,D(12500))
        income_tax=max(D(0),raw-rebate)
        cess=income_tax*D('.04')
        final=income_tax+cess
        return {'country':'IN','currency':'INR','tax_year':'2026-27','regime':regime,'taxable_income':money(taxable),
                'standard_deduction':money(std),'other_deductions_used':money(allowed),'rebate':money(rebate),
                'base_tax':money(income_tax),'cess':money(cess),'estimated_annual_tax':money(final),
                'estimated_monthly_tax':money(final/D(12)),'sources':[SOURCES['IN']],
                'limitations':['Employment salary only; tax on special-rate income, residency nuances, exemptions, and actual TDS are excluded.',
                               'Age-specific old-regime slabs, surcharge, marginal-relief edge cases and detailed declarations require professional review.']}
    if country=='GB':
        if regime!='standard': raise ValueError('GB supports standard illustrative rates only')
        allowance=max(D(0),D(12570)-max(D(0),gross-D(100000))/D(2))
        taxable=max(D(0),gross-allowance-deductions)
        # higher tax band boundary is on taxable income (threshold at £125140 gross when allowance tapers)
        result=progressive(taxable,UK_ENG)
        return {'country':'GB','currency':'GBP','tax_year':'2026-27','regime':'England/Wales/Northern Ireland illustrative','taxable_income':money(taxable),
                'standard_deduction':money(allowance),'other_deductions_used':money(deductions),'rebate':0,
                'base_tax':money(result),'cess':0,'estimated_annual_tax':money(result),'estimated_monthly_tax':money(result/D(12)),
                'sources':[SOURCES['GB']],'limitations':['Not a PAYE withholding calculation; excludes National Insurance, benefits and tax codes.', 'Scotland is not supported; Welsh rates assumed same as the published main rates.']}
    if country=='US':
        if regime!='single': raise ValueError('US reference estimator supports only single federal filers')
        taxable=max(D(0),gross-D(16100)-deductions)
        result=progressive(taxable,US_SINGLE)
        return {'country':'US','currency':'USD','tax_year':'2026','regime':'single/federal','taxable_income':money(taxable),
                'standard_deduction':16100,'other_deductions_used':money(deductions),'rebate':0,'base_tax':money(result),'cess':0,
                'estimated_annual_tax':money(result),'estimated_monthly_tax':money(result/D(12)),
                'sources':[SOURCES['US']],'limitations':['Not Form W-4 withholding or statutory net pay.', 'Excludes FICA, state/local tax, credits, additional deductions, AMT and filing statuses other than single.']}
    raise ValueError('Unsupported jurisdiction; configure a reviewed country adapter before processing payroll')


def estimate_india_monthly_pay(basic, hra, allowance, bonus=0, reimbursements=0, pf_enabled=False, esi_enabled=False,
                              pf_wage_cap=15000, professional_tax=0, other_deductions=0, tds=0, earned_fraction=1):
    for value in (basic,hra,allowance,bonus,reimbursements,professional_tax,other_deductions,tds):
        if D(value)<0: raise ValueError('Salary items and deductions cannot be negative')
    if not D(0)<=D(earned_fraction)<=D(1):raise ValueError('Earned fraction must be between 0 and 1')
    if not D(0)<=D(pf_wage_cap)<=D(1000000):raise ValueError('PF wage cap outside supported reference range')
    frac=D(earned_fraction)
    earned_basic=D(basic)*frac
    gross=(D(basic)+D(hra)+D(allowance))*frac+D(bonus)
    pay_total=gross+D(reimbursements)
    pf= min(earned_basic,D(pf_wage_cap))*D('.12') if pf_enabled else D(0)
    # ESI coverage/continuation/exemptions vary; only calculates percentage when payroll admin explicitly opts in.
    esi= gross*D('.0075') if esi_enabled else D(0)
    employer_pf=pf
    employer_esi=gross*D('.0325') if esi_enabled else D(0)
    deducted=pf+esi+D(professional_tax)+D(other_deductions)+D(tds)
    if deducted>pay_total: raise ValueError('Deductions exceed payable compensation')
    return {'gross':money(gross),'reimbursements':money(reimbursements),'employee_pf':money(pf),
            'employer_pf':money(employer_pf),'employee_esi':money(esi),'employer_esi':money(employer_esi),
            'professional_tax':money(professional_tax),'other_deductions':money(other_deductions),
            'income_tax_tds':money(tds),'deductions':money(deducted),'net':money(pay_total-deducted),
            'employer_total_estimate':money(pay_total+employer_pf+employer_esi)}
