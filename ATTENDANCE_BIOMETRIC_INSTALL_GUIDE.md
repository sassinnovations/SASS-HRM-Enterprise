# SASS HRM — Time & Attendance: manual / photo / fingerprint / iris

This is an additive release based on the 16 November **Zero Candidates** HRM package. Candidate library stays empty by default, while all recruiting/payroll/profile modules remain in place.

## Capabilities

- **Manual:** Existing employee check-in/out continues to work. Authorized HR administrators can now create a missing day manually by selecting employee, date, HH:MM times and audit reason. Existing entries cannot be overwritten; use Attendance Corrections.
- **Photo:** An employee can start the browser camera, choose check-in or check-out, explicitly consent, and record encrypted, EXIF-stripped JPEG evidence. This is **not facial recognition**, identity matching, or automatic biometric identification. The owner and HR admins can preview/delete that evidence; event metadata remains. Photos expire in 30 days and are purged when capture history or new photos are accessed.
- **Fingerprint and iris:** Integration endpoint for a **compatible device gateway**. A trusted scanner performs enrollment/matching and sends a signed attendance event; SASS HRM saves only a method, time, device ID and employee link, **never fingerprint/iris images or templates**. There is no browser-only fingerprint/iris scanning, built-in device driver, or vendor enrollment screen.
- **Logs:** Both manual and device/photo submissions generate auditable capture events. Existing attendance records/exports remain supported.

## Deployment — preserve existing MySQL data

1. Back up MySQL and your old application configuration. Never delete MySQL volumes; **do not run `docker compose down -v`**.
2. Extract the full ZIP as your updated SASS HRM source. Preserve your existing `.env` values and secrets.
3. The `server/mysql_schema.sql` and `database/01_application_schema.sql` add three new tables using only `CREATE TABLE IF NOT EXISTS`: `attendance_capture_events`, `attendance_photo_evidence`, and `attendance_device_nonces`. The API schema installer applies them at startup. Do not drop existing attendance tables.
4. On the HRM server, edit `server/.env` with `ATTENDANCE_TIMEZONE=Asia/Kolkata`. Set `ATTENDANCE_PHOTO_ENABLED=1` only when ready to use the privacy-controlled photo workflow.
5. Generate a **new secret** on the HRM server (never publish it):

   ```powershell
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

   Save the output as `ATTENDANCE_PHOTO_FERNET_KEY=` in `server/.env`. **Back up this key securely**, because losing it makes existing photos unreadable. Do not rotate without a ciphertext migration.
6. For fingerprint/iris, supply `ATTENDANCE_DEVICE_ENABLED=1` and a private mapping `ATTENDANCE_DEVICE_SECRETS_JSON` in `server/.env` for your actual scanner gateway IDs and 32+ character random unique secrets. **Do not enable this until the vendor gateway is integrated.** The default is disabled.
7. In the deployment directory with Docker Desktop running:

   ```powershell
   docker compose -f docker-compose.full.yml up -d --build
   docker compose -f docker-compose.full.yml ps
   ```

   The existing named MySQL volume is reused. Use `CHECK_BIOMETRIC_ATTENDANCE.bat` to run the isolated regression test first.
8. Open **Compensation → Time & attendance**. Employee check-in/out buttons remain. New panels show camera and device status; HR administrators also see **HR manual attendance entry**.
9. Verify that normal check-in/out, manual entry, photo capture, protected photo retrieval, and signed scanner gateway events work on real Chrome and live MySQL. None of those live checks were possible inside the build environment.

## Device gateway contract

`POST /api/attendance/biometric/device-event` accepts **a trusted device gateway**, not an employee browser. The gateway must use HTTPS, verify biometric matching and liveness on the device, and send JSON with:

```json
{
  "device_id": "registered-device-id",
  "employee_code": "employee-code",
  "modality": "fingerprint",
  "action": "check-in",
  "matched": true,
  "observed_at": "2026-11-16T09:30:00+05:30",
  "nonce": "unique-random-value-at-least-16-chars"
}
```

It sends header `X-SASS-Device-Signature: <lowercase hex HMAC-SHA256>` calculated over the **exact bytes of the JSON body**, using that registered device's secret. Device and server timestamps must differ by no more than three minutes. Each `(device_id, nonce)` may only be used once; duplicate punches are rejected. The server takes its own recorded time using `ATTENDANCE_TIMEZONE` rather than trusting a device-supplied attendance date. Tested gateway events are available via authenticated `/api/attendance/capture-events`.

**Security:** Protect the gateway in a trusted local network, rate-limit the public ingress, and never expose its HMAC secrets in frontend code. Coordinate employee notices, retention, alternatives, access policies and local legal requirements with HR/security/privacy specialists before biometric rollout.

## Important limitations

- Fingerprint and iris scanning need compatible vendor hardware, SDK/gateway, supported server driver and on-device enrollment/matching. This source provides the **secure API integration**, not those device drivers or biometric template storage.
- Photos are evidence only, **not proof that the correct employee is pictured**. Attendance policies should retain an accessible non-biometric alternative.
- Photo recording needs camera permission and HTTPS (or localhost).
- Full Vite production build, Docker/MySQL connectivity and live hardware checks must be completed on your installation; this release only includes isolated API tests and static frontend checks.
