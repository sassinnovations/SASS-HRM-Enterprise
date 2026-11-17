# SASS HRM — Country Tax Calculator update (16 Nov 2026)

## What changed

`Compensation → Tax calculator · Global` now offers reference salary-income-tax estimates for:

| Country | Currency | Rule year | Available options |
| --- | --- | --- | --- |
| India | INR | FY 2026–27 | New or old regime (old: under 60) |
| United Kingdom | GBP | 2026–27 | England/Wales/Northern Ireland or Scotland |
| United States | USD | 2026 | Single, married filing jointly, head of household, married filing separately (federal only) |
| Australia | AUD | FY 2026–27 | Full-year resident entitled to tax-free threshold |
| United Arab Emirates | AED | 2026 | Employment salary (0 federal personal income tax) |

The form accepts annual or monthly input (the latter is multiplied by 12), conditionally allows annual deductions, and gives annual and illustrative monthly income-tax estimates, gross less income tax, effective income-tax percentage, a progressive bracket breakdown, local-currency formatting and client-side CSV export. The tax breakdown, included limitations, rule date and official sources are surfaced in the interface. Every operation requires a logged-in SASS HRM session; calculations are not saved to MySQL.

### Scope limits

These results **cannot be used as official payroll withholding, payslips or tax filings**. No state or province tax, national-insurance/social-security deductions, Medicare levy, VAT, tax credits or international tax treaties are modeled. India high-income salaries above INR 50 lakh are deliberately blocked because of surcharge complexity. US extra deductions are disabled rather than silently combining the standard deduction with unsupported itemization. UK other deductions are assumed eligible and are only indicative; actual relief varies. Australia assumes a full-year tax resident. The UAE result is **only** UAE federal personal income tax on employment salary; other obligations can arise.

The existing Indian payroll workbench has **not** been extended to run US, UK, Australian or UAE payroll, and it has not been connected to this estimate screen. Rules apply to the named fixed year only; revise and revalidate them before future tax years.

## Safe installation

1. Back up your running HRM deployment and MySQL database. **Do not reset MySQL volumes.**
2. Deploy the updated application source, retaining your existing environment variables and data volumes.
3. Rebuild and restart the frontend and API for the new calculator routes: `docker compose -f docker-compose.full.yml up -d --build` from the project root *only if this matches your current deployment*. If the service names/compose file differ, follow your existing deployment procedure.
4. Hard-refresh the browser. Open `Compensation → Tax calculator · Global` and verify the five country choices.
5. Run `CHECK_COUNTRY_TAX_CALCULATOR.bat` on Windows or `python server/country_tax_calculator_test.py` with the server requirements installed. Check the MySQL schema with `python server/full_mysql_schema_test.py`.
6. Complete `npm ci && npm run build` in `web/` with internet access and perform actual browser and deployed-API smoke tests before production use.

**MySQL migration:** None required for this update. It adds no tables, does not import candidate data and does not alter any existing employee, salary or payroll records.

## Source references / rule date

- India — government income-tax estimator / Finance Act tax rate guidance: https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/income-and-tax-estimator-um
- UK, including Scotland rates — HMRC 2026–27: https://www.gov.uk/government/publications/rates-and-allowances-income-tax/income-tax-rates-and-allowances-current-and-past
- US 2026 federal brackets / standard deductions — IRS Revenue Procedure 2025-32: https://www.irs.gov/irb/2025-45_IRB
- Australia 2026–27 full-year resident ordinary taxable income — ATO: https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents
- UAE — UAE Government taxation reference: https://u.ae/en/information-and-services/finance-and-investment/taxation

Official rates were cross-checked on 16 November 2026. Exact personal liability requires case-specific advice and current legal review.
