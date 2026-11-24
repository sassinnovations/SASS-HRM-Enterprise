"""Reference-only 2026 tax estimators. Not statutory tax computation or payroll filing.
No external side effects. Decimal monetary arithmetic and explicit year/jurisdiction.
See docs/PAYROLL_TAX_SCOPE.md and URLs returned in response.
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
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
US_JOINT=[(24800,'.10'),(100800,'.12'),(211400,'.22'),(403550,'.24'),(512450,'.32'),(768700,'.35'),(None,'.37')]
US_HEAD=[(17700,'.10'),(67450,'.12'),(105700,'.22'),(201750,'.24'),(256200,'.32'),(640600,'.35'),(None,'.37')]
US_SEPARATE=[(12400,'.10'),(50400,'.12'),(105700,'.22'),(201775,'.24'),(256225,'.32'),(384350,'.35'),(None,'.37')]
US_FILING={'single':(US_SINGLE,16100,'Single'), 'married_joint':(US_JOINT,32200,'Married filing jointly'),
           'head_household':(US_HEAD,24150,'Head of household'),
           'married_separate':(US_SEPARATE,16100,'Married filing separately')}
AU_RESIDENT=[(18200,0),(45000,'.15'),(135000,'.30'),(190000,'.37'),(None,'.45')]
UK_SCOTLAND=[(3967,'.19'),(16956,'.20'),(31092,'.21'),(62430,'.42'),(125140,'.45'),(None,'.48')]

SOURCES={
 'IN':'https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/income-and-tax-estimator-um',
 'GB':'https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027',
 'US':'https://www.irs.gov/irb/2025-45_IRB',
 'AU':'https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents',
 'AE':'https://u.ae/en/information-and-services/finance-and-investment/taxation',
 'PF':'https://www.epfindia.gov.in/site_en/For_Employers.php/Disablitity.php',
 'ESI':'https://www.esic.gov.in/attachments/circularfile/7a6e3189a5201812e4c067e5286a1c1e.pdf'
}

def progressive_details(taxable, bands):
    """Each taxable bracket is recorded so the displayed summary can be audited."""
    value=max(D(0),D(taxable)); previous=D(0); out=[]
    for cap, rate in bands:
        top=D(cap) if cap is not None else value
        amount=max(D(0),min(value,top)-previous)
        if amount>0:
            out.append({'from':money(previous),'to':money(min(value,top)),
                        'rate_percent':money(D(rate)*100),'taxable_in_band':money(amount),
                        'tax_in_band':money(amount*D(rate))})
        if cap is None or value<=top: break
        previous=top
    return out


def estimate_tax(country:Literal['IN','GB','US','AU','AE'], annual_gross:float,
                 regime:str='new', deductions:float=0, resident:bool=True):
    gross=D(annual_gross); claimed=D(deductions)
    if not gross.is_finite() or not claimed.is_finite() or gross<0 or claimed<0 or claimed>gross:
        raise ValueError('Annual salary and deductions must be finite and nonnegative; deductions cannot exceed salary.')
    if gross>D(100000000): raise ValueError('Annual salary exceeds the supported reference range')
    rebate=D(0); cess=D(0); allowance=D(0); allowed=claimed; limitations=[]; breakdown=[]
    if country=='IN':
        if regime=='new' and claimed>0:
            raise ValueError('India new regime: separate optional deductions are not implemented; enter zero.')
        if gross>5000000:
            raise ValueError('Indian salary above INR 50 lakh requires a surcharge-aware specialist calculation.')
        if regime not in ('new','old'): raise ValueError('India regime must be new or old')
        allowance=D(75000 if regime=='new' else 50000)
        allowed=D(0) if regime=='new' else claimed
        taxable=max(D(0),gross-allowance-allowed)
        bands=INDIA_NEW if regime=='new' else INDIA_OLD
        breakdown=progressive_details(taxable,bands)
        raw=progressive(taxable,bands)
        if resident and regime=='new' and taxable<=1200000:
            rebate=min(raw,D(60000))
        elif resident and regime=='new' and taxable>1200000:
            rebate=max(D(0),raw-(taxable-D(1200000)))
        elif resident and regime=='old' and taxable<=500000:
            rebate=min(raw,D(12500))
        base=max(D(0),raw-rebate)
        cess=base*D('.04')
        final=base+cess
        currency='INR'; tax_year='2026-27'
        limitations=['Ordinary salary only. Special-rate income, detailed exemptions, tax residency and actual TDS excluded.',
                     'Old regime uses below-60 slabs; surcharge and certain marginal-relief cases require specialist review.']
    elif country=='GB':
        if regime not in ('standard','scotland'): raise ValueError('UK region must be standard or scotland')
        # Approximate adjusted net income after assumed eligible deductions for allowance taper.
        adjusted_net=max(D(0),gross-claimed)
        allowance=max(D(0),D(12570)-max(D(0),adjusted_net-D(100000))/D(2))
        taxable=max(D(0),adjusted_net-allowance)
        bands=UK_SCOTLAND if regime=='scotland' else UK_ENG
        breakdown=progressive_details(taxable,bands)
        base=progressive(taxable,bands)
        final=base; currency='GBP'; tax_year='2026-27'
        limitations=['Illustrative UK employment income tax only, not PAYE; excludes National Insurance, tax codes and student loans.',
                     'Deductions assumed fully eligible for illustration; actual adjusted net income and pension treatment can differ.',
                     'Scotland option estimates Scottish non-savings employment rates; country of residence and reliefs must be verified.']
    elif country=='US':
        if claimed>0:
            raise ValueError('US additional deduction eligibility is not modeled; enter zero. The applicable standard deduction is included.')
        if regime not in US_FILING: raise ValueError('Unsupported US federal filing status')
        bands,standard,_=US_FILING[regime]
        allowance=D(standard)
        taxable=max(D(0),gross-allowance-claimed)
        breakdown=progressive_details(taxable,bands)
        base=progressive(taxable,bands)
        final=base; currency='USD'; tax_year='2026'
        limitations=['Federal ordinary salary income tax only; not Form W-4 withholding or an official Form 1040 calculation.',
                     'Excludes FICA, state/local income tax, credits, itemization rules, AMT and filing-status eligibility checks.',
                     'Standard deduction applied by filing status; itemization and other special deductions are not modeled.']
    elif country=='AU':
        if regime!='resident': raise ValueError('Australia supports only full-year tax residents')
        taxable=max(D(0),gross-claimed)
        bands=AU_RESIDENT
        breakdown=progressive_details(taxable,bands)
        base=progressive(taxable,bands)
        final=base; currency='AUD'; tax_year='2026-27'
        limitations=['Only the Australian resident ordinary income tax rates; excludes the Medicare levy and surcharge.',
                     'Assumes a full-year resident entitled to the tax-free threshold; excludes offsets, HELP/HECS and tax on special income.']
    elif country=='AE':
        if regime!='salary': raise ValueError('UAE supports only personal employment salary')
        if claimed>0: raise ValueError('UAE salary income tax does not require personal tax deductions; set deductions to zero.')
        taxable=gross
        base=D(0); final=D(0); currency='AED';tax_year='2026'
        limitations=['The UAE has no federal personal income tax on salary. This does not cover corporate tax, VAT, social contributions or foreign tax residency.',
                     'Employment income in other countries may be taxable elsewhere.']
    else:
        raise ValueError('Unsupported country; configure a reviewed country adapter before processing payroll')
    return {'country':country,'currency':currency,'tax_year':tax_year,'regime':regime,
            'annual_gross':money(gross),'taxable_income':money(taxable),
            'standard_deduction':money(allowance),'other_deductions_used':money(allowed),
            'rebate':money(rebate),'base_tax':money(base),'cess':money(cess),
            'estimated_annual_tax':money(final),'estimated_monthly_tax':money(final/D(12)),
            'estimated_annual_net':money(gross-final),'estimated_monthly_net':money((gross-final)/D(12)),
            'effective_tax_rate_percent':money(final/gross*100) if gross else 0,
            'bracket_breakdown':breakdown,'sources':[SOURCES[country]], 'limitations':limitations,
            'estimate_only':True,'ruleset_version':f'{country}-{tax_year}-reference-2026-11-16'}


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
