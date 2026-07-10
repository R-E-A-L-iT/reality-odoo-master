# Leica Lead Runner

Companion script for the **proleads** Odoo module. It runs on any always-on
machine, listens for webhook calls from Odoo's "Register with Leica" button,
and drives a Chromium browser through the Leica Business Resource Portal
(`portal.leicaus.com`) to fill in the Reality Capture *Add Sales Lead* form.

> ⚠️ **TEST MODE**: the click on the portal's Submit button is commented out
> in `leica_lead_runner.py` (search for `SUBMIT BUTTON`). The runner fills the
> whole form, takes a screenshot, and reports success **without submitting**.
> Uncomment that block only once you've verified everything is correct.

## Setup

```bash
cd proleads/leica_runner
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium

export LEICA_RUNNER_SECRET="pick-a-long-random-secret"
python leica_lead_runner.py
```

The runner listens on port `8478` by default and shows the browser window
(headless off) so you can watch it work during testing.

## Odoo configuration

In **Settings → CRM → Leica Lead Registration**, fill in:

| Setting | Value |
|---|---|
| Runner Webhook URL | `http://<this-machine>:8478/leica/register-lead` |
| Runner Webhook Secret | the same value as `LEICA_RUNNER_SECRET` |
| Runner Timeout | 120s is a good default |
| Canada / U.S. credentials | the two portal logins |

The portal credentials live in Odoo and are sent to the runner inside each
(HMAC-signed) webhook payload — nothing is hard-coded here.

Since Odoo (odoo.sh) must be able to reach this machine over the internet, put
the runner behind a tunnel for testing — e.g. `cloudflared tunnel`, `ngrok http
8478`, or a Tailscale funnel — and use that HTTPS URL in the Odoo setting.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `LEICA_RUNNER_SECRET` | *(required)* | shared HMAC secret, must match Odoo |
| `LEICA_RUNNER_PORT` | `8478` | listen port |
| `LEICA_RUNNER_HOST` | `0.0.0.0` | bind address |
| `LEICA_RUNNER_HEADLESS` | `0` | `1` hides the browser window |
| `LEICA_RUNNER_SCREENSHOTS` | `./screenshots` | filled-form screenshots (audit trail) |
| `LEICA_RUNNER_HOLD_SECONDS` | `20` | keep the browser open after filling (test mode, headful only) |

## Flow

1. Odoo POSTs the lead payload to `/leica/register-lead`, signed with
   `X-REAL-Signature` (HMAC-SHA256 of the raw body).
2. The runner verifies the signature, opens the portal, logs in with the
   region-appropriate credentials (CA vs US), navigates *Other/Links →
   Reality Capture Sales Leads → Add Sales Lead*, and fills every field.
3. It responds `{"ok": true/false, "message": "..."}`. Odoo marks the lead
   registered on success, or stores the error and lets the user retry.

A screenshot of the filled form is saved for every attempt, plus an extra one
on errors. Requests are processed one at a time; concurrent webhooks queue.

## Going live

1. Run a few test registrations and check the screenshots / browser window.
2. Uncomment the `SUBMIT BUTTON` block in `leica_lead_runner.py`.
3. Optionally set `LEICA_RUNNER_HEADLESS=1` and `LEICA_RUNNER_HOLD_SECONDS=0`.
