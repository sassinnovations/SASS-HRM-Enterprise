# SASS HRM Enterprise v0.8: payroll and tax rules (reference-only)

**Rule snapshot checked: 2026-10-13.** This release supports a simulated Indian salary-payroll **draft → reviewed → published** workflow for **April 2026–March 2027**. It does **not** perform statutory withholding, bank payment, remittances, challan generation, government submissions, tax returns, Form 16, US W-2, UK RTI, or jurisdictional regulatory compliance. Use synthetic data until qualified payroll/legal/security validation has been completed.

## Implemented features

- Role-based salary packages (HR only): Basic, HRA, allowances, optional PF/ESI flags, configurable PF wage base, manually entered state professional tax, other deductions, old/new tax regime and optional manual TDS.
- Per-employee/per-month adjustments: bonus, reimbursements, additional deductions, partial-pay period fraction, manual TDS override, purpose note. Locked after a pay run snapshot exists.
- Monthly snapshot records: exact salary and adjustment values captured as immutable JSON; payroll run is `Draft` → `Reviewed` → `Published` (only HR administrator can move status). A reviewed run is **not** permission-separated from its creator; a second reviewer is required for production.
- Payslip preview: gross, employee PF/ESI, illustrative TDS, deductions, net, employer contribution estimates, employer cost. HR can export a CSV. Employees see only their own **published** statements.
- Three **independent annual income-tax estimators**: India (old/new, resident rebate), UK (England/Wales/Northern Ireland, standard rate), US (federal individual *single* filing status only). All are illustrative and manually reviewed. They do **not** automatically enable UK/US payroll processing.
- AI assistant: may provide an authenticated employee's **own** latest published simulated payslip summary and links to the tax calculator; no colleague's salary detail.

## India 2026–27 income tax assumptions

Annual salary only, no salary exemptions or special-rate capital gains, no self-employment or other income. New regime: ₹4L 0%, ₹4–8L 5%, ₹8–12L 10%, ₹12–16L 15%, ₹16–20L 20%, ₹20–24L 25%, above ₹24L 30%; ₹75K salary standard deduction; Section 87A resident rebate on eligible ordinary income up to taxable ₹12L, capped at ₹60K; illustrative marginal-relief handling; 4% cess. Old regime: ₹2.5L 0%, ₹2.5–5L 5%, ₹5–10L 20%, over ₹10L 30%; ₹50K salary standard deduction and manually entered permitted deductions; basic resident rebate up to taxable ₹5L. No age-specific old-regime relief, disability, agricultural income, tax treaties, capital gains, complex deductions, surcharge, or Form 12BB validation. Amounts above ₹50L are rejected to avoid unhandled surcharge.

The **Income-tax Act, 2025** applies to tax year 2026–27; the prior Income-tax Act, 1961 assessments can have different tax-year labels. Validate the 2026–27 implementation against the **official Income and Tax Estimator** for actual circumstances before any payroll deployment.

Official references:
- [Income Tax Department, TY 2026–27 estimator and applicable Act](https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/income-and-tax-estimator-um)
- [Income Tax Department, new-regime slabs and Section 87A for AY 2026–27](https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/file-itr-2-online)
- [Income Tax Department calculator](https://www.incometax.gov.in/iec/foportal/income-tax-calculator)

PF/ESI **do not mean eligibility is automatic.** PF is a simplified 12% of the *manually configured capped basic-wage base*; it does not implement EPS and employer-cost splits, voluntary options, international workers, changes to statutory ceilings, or ECR. ESI, when explicitly enabled after eligibility review, computes 0.75% employee and 3.25% employer of illustrative monthly wage; it does not capture all wage-component eligibility, contribution period continuity, low-daily-wage exemptions, or ESIC returns. Backend blocks opting in to ESI for fixed pay above INR 21,000; this is only an initial safeguard, **not** an authoritative eligibility test. State professional tax is a **manual numeric amount**, never an auto-calculated all-India rate. No tax or PF/ESI remittance is performed.

- [EPFO official employer information and contribution-rate downloads](https://www.epfindia.gov.in/site_en/For_Employers.php/Disablitity.php)
- [ESIC official employer/employee contribution rates](https://www.esic.gov.in/attachments/circularfile/7a6e3189a5201812e4c067e5286a1c1e.pdf)

## International tax estimates, NOT international payroll

**United Kingdom:** 2026–27 ordinary employment earnings, standard Personal Allowance of £12,570 with the £1 per £2 taper over £100K, and 20%/40%/45% bands for England/Wales/Northern Ireland. Does not support Scotland's separate bands, tax codes, National Insurance, student loans, pension salary sacrifice, payroll cumulative PAYE or Real Time Information filing.
- [HMRC 2026–27 employer rates/thresholds](https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027)
- [UK 2026–27 tax bands](https://www.gov.uk/government/publications/rates-and-allowances-income-tax/income-tax-rates-and-allowances-current-and-past)

**United States:** Calendar **2026** ordinary income, federal **single** tax schedule and $16,100 standard deduction. Does not support Head of Household/joint filing, Form W-4, federal withholding worksheets, Social Security/Medicare, state/local payroll rules, tax credits, tips/overtime special deductions, unemployment taxes, benefits or IRS filings.
- [IRS 2026 tax adjustments and standard deduction](https://www.irs.gov/newsroom/irs-releases-tax-inflation-adjustments-for-tax-year-2026-including-amendments-from-the-one-big-beautiful-bill)
- [IRS 2026 Publication 505 federal schedules](https://www.irs.gov/publications/p505)

## Privacy, security and production checklist

1. **No real employee bank numbers, PAN, SSN, UK NI number or actual PII** in the development database; migrate SQLite to PostgreSQL with tenant and row-level controls and encrypted secrets before deployment.
2. Enforce maker–checker segregation on salary changes and pay runs; separate reviewer accounts and immutable approval logs, signed export trails, role provisioning, 2FA/SSO and privacy retention.
3. Implement jurisdiction-specific **versioned** rates keyed to actual effective dates and employee state/location, with legal change monitoring and payroll/legal sign-off. Never silently roll FY26–27 rates into FY27–28.
4. Build statutory withholding engines and government integrations per jurisdiction: Indian Form 24Q and challan generation, PF ECR, ESIC returns, state PT/LWF and labour-law entitlements; UK PAYE/NI/RTI; US W-4 withholding/FICA/state/local filings.
5. Make bonuses taxable in the actual annual projection, account for prior-year-to-date payroll and 87A relief reconciliation, recalculate retro-pay/arrears, and use payroll-specific earnings codes and validation.
6. Add bank transfer integration only after payment approval, double verification, audit, replay prevention, and security review.
7. Undertake payroll/legal review, security tests, cross-browser regression tests, accessibility tests, performance/load tests, and backup/restore validation.

## How to test and run

From extracted project directory, run `VERIFY_EVERYTHING.bat`, which executes backend suites and attempts `npm install` and `npm run build`. If npm packages cannot be installed because the registry is unreachable, the frontend has **not** been completely validated. `START_HERE.bat` launches backend and frontend on Windows. Backend API docs: `http://localhost:8000/docs`. New pages: **Payroll workbench** and **Tax calculator · Global** in the left menu.
