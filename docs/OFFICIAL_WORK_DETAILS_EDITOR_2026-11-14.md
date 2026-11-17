# SASS HRM — HR-managed official work details editor

## Feature location

Go to **Workspace → My profile → My details → Official work details**.

For an authenticated **HR administrator**, the section now displays **Edit official details**. This is not offered to employees or managers. The editor updates the **existing employee record** in the database; it does not create a second employee or modify any actual records during installation.

Editable fields: **Employee code, Official name, Work email, Department, Designation, Office, Work mode, Joined**. A reason is required in the form to document the change. The **Role** field appears as read-only; role and developer-access changes must be performed through **People Management → Account administration** by an authorized administrator. An administrator cannot change their own access role through that separate role endpoint.

To save: choose **Edit official details**, update the desired values, enter a short reason, select **Save official details**, and inspect the updated information and success notification. Use **Cancel** to discard the form without saving.

## Security and compatibility

- Reuses the existing `PATCH /api/admin/accounts/{employee_id}/profile` HR-only endpoint. The new `code`, `join_date` and `change_reason` fields are optional for compatibility with older Account Administration forms.
- Code, work email, joining date, and other fields have server-side validation. Duplicate code or conflicting email gives an error without writing changes.
- Changes use parameterized SQL, and an `identity.profile_updated` audit record lists changed fields and the supplied reason.
- A changed work or sign-in email revokes old JWT sessions. The editor warns before saving and logs the current user out to sign in again.
- Role, password, identity ID, payroll runs and existing candidate records cannot be edited through the official-details endpoint. No MySQL schema migration is needed.
- No employee record is created or changed by the included test: isolated tests use a temporary SQLite database.

## Local verification

On Windows, run `VERIFY_OFFICIAL_WORK_DETAILS_EDIT.bat`. Then start the updated HRM Docker frontend and API, sign in as an HR administrator, test the form with a safe test account, and check the database audit trail. The test does not prove that your production MySQL server or browser is working.

For production deployment, back up MySQL, redeploy the updated frontend and server files and rebuild frontend assets. **Do not reset MySQL volumes.** Your live account remains unchanged until an HR administrator saves the form.
