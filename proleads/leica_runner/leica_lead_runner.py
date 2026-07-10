#!/usr/bin/env python3
"""Leica portal lead-registration runner.

Listens for HMAC-signed webhook calls from Odoo (proleads module), then drives
a Chromium browser through the Leica Business Resource Portal to fill in the
Reality Capture "Add Sales Lead" form.

    Odoo "Register with Leica" button
        -> POST /leica/register-lead  (JSON, X-REAL-Signature: hmac-sha256)
        -> this script logs in, navigates, fills the form
        -> responds {"ok": true/false, "message": "..."}

!!! TESTING MODE !!!
The click on the portal's Submit button is COMMENTED OUT below (search for
"SUBMIT BUTTON") so no real leads are created while testing. The runner
responds with ok=true and a "TEST MODE" message once the form is fully filled.

Configuration (environment variables):
    LEICA_RUNNER_SECRET       (required) shared secret; must match the
                              "Leica Runner Webhook Secret" in Odoo settings
    LEICA_RUNNER_PORT         listen port                    (default: 8478)
    LEICA_RUNNER_HOST         bind address                   (default: 0.0.0.0)
    LEICA_RUNNER_HEADLESS     "1" to hide the browser        (default: 0)
    LEICA_RUNNER_SCREENSHOTS  dir for filled-form screenshots (default: ./screenshots)
    LEICA_RUNNER_HOLD_SECONDS seconds to keep the browser open after filling,
                              so you can eyeball the result   (default: 20)

Setup:
    pip install -r requirements.txt
    python -m playwright install chromium
    export LEICA_RUNNER_SECRET="the-same-secret-as-in-odoo"
    python leica_lead_runner.py
"""

import hashlib
import hmac
import json
import logging
import os
import re
import threading
import time
import unicodedata
from datetime import datetime

from flask import Flask, jsonify, request
from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PORTAL_URL = "https://portal.leicaus.com"
SALES_LEADS_MAIN = PORTAL_URL + "/salesleads/main.cfm?SubResourceID=357"
LEAD_ADD_URL = PORTAL_URL + "/salesleads/lead_add.cfm?SubResourceID=357"

SECRET = os.environ.get("LEICA_RUNNER_SECRET", "")
PORT = int(os.environ.get("LEICA_RUNNER_PORT", "8478"))
HOST = os.environ.get("LEICA_RUNNER_HOST", "0.0.0.0")
HEADLESS = os.environ.get("LEICA_RUNNER_HEADLESS", "0") == "1"
SCREENSHOT_DIR = os.environ.get("LEICA_RUNNER_SCREENSHOTS", "./screenshots")
HOLD_SECONDS = int(os.environ.get("LEICA_RUNNER_HOLD_SECONDS", "20"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("leica-runner")

app = Flask(__name__)

# Only one browser automation at a time; concurrent requests queue up here.
_automation_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _norm(text):
    """Normalize for option matching: strip accents, keep alphanumerics, lower."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", text.lower())


# Portal state labels that don't match Odoo's state names even after
# normalization is handled by substring matching, but map the known oddballs
# explicitly by Odoo state code for safety.
STATE_LABEL_BY_CODE = {
    "NL": "New Foundland",        # Odoo: "Newfoundland and Labrador"
    "YT": "Yukon Territory",      # Odoo: "Yukon"
    "QC": "Quebec",               # Odoo: "Québec"
    "PE": "Prince Edward Island",
    "NT": "Northwest Territories",
}


def select_by_visible_text(page, select_name, text):
    """Select an <option> by (fuzzily) matching its visible label.

    The portal's option labels have stray whitespace and its values are opaque
    numeric IDs, so match on normalized text: exact first, then substring in
    either direction (handles 'Yukon' -> 'Yukon Territory' and
    'Newfoundland and Labrador' -> 'New Foundland').
    """
    value = page.evaluate(
        """([name, target]) => {
            const sel = document.querySelector(`select[name="${name}"]`);
            if (!sel) return null;
            const norm = s => (s || '')
                .normalize('NFKD')
                .replace(/[\\u0300-\\u036f]/g, '')
                .replace(/[^a-zA-Z0-9]/g, '')
                .toLowerCase();
            const t = norm(target);
            if (!t) return null;
            for (const opt of sel.options) {
                if (norm(opt.textContent) === t) return opt.value;
            }
            for (const opt of sel.options) {
                const o = norm(opt.textContent);
                if (!o || opt.value === '0' || opt.value === '') continue;
                if (o.includes(t) || t.includes(o)) return opt.value;
            }
            return null;
        }""",
        [select_name, text],
    )
    if value is None:
        raise RuntimeError(f"Option matching '{text}' not found in select '{select_name}'")
    page.select_option(f'select[name="{select_name}"]', value=value)


def resolve_state_label(payload):
    """Figure out which portal state/province label to select."""
    code = (payload.get("state_code") or "").strip().upper()
    if code in STATE_LABEL_BY_CODE:
        return STATE_LABEL_BY_CODE[code]
    return payload.get("state_name") or ""


def required_fields_present(payload):
    """Sanity-check the payload before touching the browser."""
    required = [
        "portal_username", "portal_password", "sales_region", "market_segment",
        "first_name", "last_name", "company_name", "email", "phone",
        "address", "city", "zip", "company_website", "product_interest",
        "quantity", "expected_purchase_date", "is_rfp",
    ]
    missing = [k for k in required if not str(payload.get(k) or "").strip()]
    if not (payload.get("state_name") or payload.get("state_code")):
        missing.append("state_name/state_code")
    if payload.get("product_interest") == "BLK ARC" and not str(payload.get("blk_arc_carrier") or "").strip():
        missing.append("blk_arc_carrier")
    return missing


# ---------------------------------------------------------------------------
# Browser automation
# ---------------------------------------------------------------------------

def register_lead(payload):
    """Drive the portal. Returns (ok: bool, message: str)."""
    region = payload.get("sales_region")
    sales_region_label = {"ca": "Canada", "us": "United States"}.get(region)
    if not sales_region_label:
        return False, f"Unknown sales region: {region!r}"

    dialogs = []  # any alert() the portal throws (its own validation)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(30000)
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        try:
            # --- 1. Login page -------------------------------------------------
            log.info("Opening portal login page ...")
            page.goto(PORTAL_URL, wait_until="domcontentloaded")

            # Cookie banner, if present
            try:
                banner = page.locator("a.wpcc-btn")
                if banner.count() and banner.first.is_visible():
                    banner.first.click()
            except Exception:
                pass

            if not page.locator('form[name="LoginForm"] input[name="username"]').count():
                return False, "Login form not found on the portal landing page."

            log.info("Logging in as %s (%s) ...", payload["portal_username"], sales_region_label)
            page.fill('form[name="LoginForm"] input[name="username"]', payload["portal_username"])
            page.fill('form[name="LoginForm"] input[name="password"]', payload["portal_password"])
            page.click('form[name="LoginForm"] input[name="CheckLogin"]')
            page.wait_for_load_state("domcontentloaded")

            # Still seeing a password box => credentials rejected
            if page.locator('input[name="password"]').count():
                return False, "Portal login failed — check the credentials configured in Odoo."

            # --- 2. Navigate to the Add Sales Lead form ------------------------
            log.info("Navigating to Reality Capture Sales Leads ...")
            page.goto(SALES_LEADS_MAIN, wait_until="domcontentloaded")

            add_link = page.locator('a[href*="lead_add.cfm"]')
            if add_link.count():
                add_link.first.click()
                page.wait_for_load_state("domcontentloaded")
            else:
                # Fallback: go straight to the form
                page.goto(LEAD_ADD_URL, wait_until="domcontentloaded")

            if not page.locator('input[name="CompanyName"]').count():
                return False, "Could not reach the Add Sales Lead form (session or permissions problem?)."

            # --- 3. Fill the form ----------------------------------------------
            log.info("Filling the Sales Lead form ...")
            select_by_visible_text(page, "SegmentID", payload["market_segment"])
            select_by_visible_text(page, "RegionID", sales_region_label)

            page.fill('input[name="Contact_FirstName"]', payload["first_name"])
            page.fill('input[name="Contact_LastName"]', payload["last_name"])
            page.fill('input[name="CompanyName"]', payload["company_name"])
            page.fill('input[name="Phone"]', payload["phone"])
            page.fill('input[name="Email"]', payload["email"])
            page.fill('input[name="Address"]', payload["address"])
            page.fill('input[name="City"]', payload["city"])

            state_label = resolve_state_label(payload)
            select_by_visible_text(page, "StateID", state_label)

            page.fill('input[name="Zip"]', payload["zip"])
            # Yes, the portal really stores the company website in "CustomerReason"
            page.fill('input[name="CustomerReason"]', payload["company_website"])

            # Product interest — may reveal the BLK ARC carrier question
            select_by_visible_text(page, "ProductID", payload["product_interest"])
            if payload.get("blk_arc_carrier"):
                page.fill('input[name="Answer1"]', payload["blk_arc_carrier"])

            # Quantity lives in a field the portal calls "LostTo"
            page.fill('input[name="LostTo"]', str(payload["quantity"]))

            # Expected purchase date (mm/dd/yyyy). fill() bypasses the onpaste
            # blocker and the popup calendar.
            page.fill('input[name="DateSold"]', payload["expected_purchase_date"])

            select_by_visible_text(page, "Question1", payload["is_rfp"])

            # Media & Entertainment category, only shown for that segment
            if payload.get("media_category"):
                select_by_visible_text(page, "Question2", payload["media_category"])

            if payload.get("demo_requested"):
                page.check('input[name="Answer2"]')
            if payload.get("pricing_requested"):
                page.check('input[name="Answer3"]')
            if payload.get("meeting_requested"):
                page.check('input[name="Answer4"]')

            if payload.get("discussion_notes"):
                page.fill('textarea[name="DiscussionNotes"]', payload["discussion_notes"])

            # --- 4. Screenshot of the filled form for the audit trail ----------
            os.makedirs(SCREENSHOT_DIR, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            shot = os.path.join(SCREENSHOT_DIR, f"lead_{payload.get('lead_id', 'x')}_{stamp}.png")
            page.screenshot(path=shot, full_page=True)
            log.info("Saved filled-form screenshot: %s", shot)

            # --- 5. SUBMIT BUTTON ----------------------------------------------
            # =====================================================================
            # !!! DISABLED FOR TESTING — DO NOT ENABLE UNTIL VERIFIED !!!
            # Uncomment the block below to actually submit leads to Leica.
            # =====================================================================
            # page.click('input[name="Add"]')
            # page.wait_for_load_state("domcontentloaded")
            #
            # # The portal's CheckForm() alert()s and stays on the page when it
            # # rejects the form; the dialog handler above captured the message.
            # if dialogs:
            #     return False, "Portal rejected the form: " + "; ".join(dialogs)
            #
            # # Still on the entry form with an empty CompanyName? Submission
            # # probably did not go through.
            # if page.locator('input[name="CompanyName"]').count() \
            #         and page.locator('input[name="CompanyName"]').first.input_value():
            #     return False, "Form did not appear to submit (still on the entry page)."
            #
            # stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # shot = os.path.join(SCREENSHOT_DIR, f"lead_{payload.get('lead_id', 'x')}_{stamp}_submitted.png")
            # page.screenshot(path=shot, full_page=True)
            # return True, "Lead submitted to the Leica portal."
            # =====================================================================

            if HOLD_SECONDS and not HEADLESS:
                log.info("Holding browser open for %ss so you can inspect the form ...", HOLD_SECONDS)
                time.sleep(HOLD_SECONDS)

            return True, (
                "TEST MODE: form filled successfully but NOT submitted "
                "(submit click is commented out in the runner). "
                f"Screenshot: {shot}"
            )

        except Exception as e:
            log.exception("Automation failed")
            msg = str(e)
            if dialogs:
                msg += " | portal alerts: " + "; ".join(dialogs)
            try:
                os.makedirs(SCREENSHOT_DIR, exist_ok=True)
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                shot = os.path.join(SCREENSHOT_DIR, f"lead_{payload.get('lead_id', 'x')}_{stamp}_error.png")
                page.screenshot(path=shot, full_page=True)
                msg += f" | error screenshot: {shot}"
            except Exception:
                pass
            return False, msg
        finally:
            context.close()
            browser.close()


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------

@app.post("/leica/register-lead")
def register_lead_endpoint():
    raw = request.get_data()

    signature = request.headers.get("X-REAL-Signature", "")
    expected = hmac.new(SECRET.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    if not signature or not hmac.compare_digest(signature, expected):
        log.warning("Rejected request with bad signature from %s", request.remote_addr)
        return jsonify(ok=False, message="Invalid signature"), 403

    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        return jsonify(ok=False, message="Invalid JSON payload"), 400

    missing = required_fields_present(payload)
    if missing:
        return jsonify(ok=False, message="Payload missing required fields: " + ", ".join(missing))

    log.info(
        "Registering lead %s (%s, %s) ...",
        payload.get("lead_id"), payload.get("company_name"), payload.get("sales_region"),
    )

    with _automation_lock:
        ok, message = register_lead(payload)

    log.info("Result for lead %s: ok=%s message=%s", payload.get("lead_id"), ok, message)
    return jsonify(ok=ok, message=message)


@app.get("/leica/health")
def health():
    return jsonify(ok=True, message="leica runner alive")


if __name__ == "__main__":
    if not SECRET:
        raise SystemExit("LEICA_RUNNER_SECRET environment variable is required.")
    log.info("Leica lead runner listening on %s:%s (headless=%s)", HOST, PORT, HEADLESS)
    app.run(host=HOST, port=PORT)
