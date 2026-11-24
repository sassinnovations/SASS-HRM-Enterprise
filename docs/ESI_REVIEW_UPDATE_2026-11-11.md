# ESI eligibility review — 2026-11-11

## What this update fixes

The payroll salary structure form now explains the ESI warning when the sum of
basic + HRA + allowance exceeds INR 21,000. When ESI is checked, it offers a
**Turn ESI off pending assessment (form only)** button. This button changes
only the unsaved form state. An authorized HR administrator must still click
**Save salary package** to persist the change. The backend's existing
conservative 422 validation remains in place, with clearer guidance about
continuing coverage and disability thresholds.

## How to use

1. Log in using an authorized HR administrator account.
2. Go to **Compensation > Payroll workbench > Salary structures**.
3. Select the employee and verify the wages, existing ESIC coverage, and
   contribution-period dates with a payroll specialist.
4. If ESI should not apply pending assessment, use the new button (or manually
   uncheck the **ESI eligible** box), then click **Save salary package**.
5. Check the saved package's `esi_enabled` value via the packages table. Do not
   assume any existing payroll snapshots have been updated; they are immutable.

## Important statutory and product limitations

- The INR 21,000 monthly threshold is a standard coverage limit, not a universal
  permission to end ESI contributions immediately.
- Employees already covered who cross the ceiling during a contribution period
  may remain covered through that period. A different threshold (INR 25,000)
  can apply to persons with disabilities.
- No automated determination of contribution-period continuation, disability
  coverage, exemptions, or specialist approval was added. There is currently no
  in-app reviewed-exception override to enable ESI above INR 21,000. Escalate
  genuine continuing-coverage cases rather than disabling contributions by
  default.
- This is a payroll simulation; it is **not** an ESIC filing or legal opinion.
- A deployment needs a restart/rebuild to pick up these changes. This ZIP does
  not update a running application automatically.

## Validation performed

- `cd server && python payroll_esi_review_test.py` — passed
- `cd server && python compensation_ops_test.py` — passed
- `python -m py_compile server/payroll_plus.py` — passed
- MySQL/live browser checks not performed; `npm ci --offline` could not finish
  in the provided environment, so a frontend production build was not certified.

## References

- Official ESIC FAQ (coverage across contribution period):
  https://www.esic.gov.in/attachments/files/faq.pdf
- Ministry of Labour and Employment announcement on INR 21,000 and INR 25,000:
  https://www.pib.gov.in/PressReleasePage.aspx?PRID=2149347
