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
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

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

# The portal is an old ColdFusion site that keeps a spinner going forever (a
# resource that never finishes loading), so the "load"/"domcontentloaded"
# lifecycle events may never fire. We therefore navigate with wait_until="commit"
# (resolves as soon as the server returns the HTML) and then wait for the
# specific element we need to appear. This is how long we'll wait for that
# element / for a navigation to commit.
NAV_TIMEOUT = int(os.environ.get("LEICA_RUNNER_NAV_TIMEOUT", "60000"))

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


def safe_goto(page, url, attempts=4):
    """page.goto that tolerates net::ERR_ABORTED.

    On this portal a navigation often collides with an in-flight one (e.g. the
    login POST's index.cfm -> main.cfm redirect still settling), which aborts
    our goto. That's transient — retrying after a short pause succeeds once the
    competing navigation has finished.
    """
    last_err = None
    for i in range(attempts):
        try:
            resp = page.goto(url, wait_until="commit", timeout=NAV_TIMEOUT)
            if resp is not None:
                log.info("goto %s -> HTTP %s", url, resp.status)
            return resp
        except Exception as e:
            last_err = e
            if "ERR_ABORTED" in str(e):
                log.info("goto %s aborted (attempt %d), retrying ...", url, i + 1)
                page.wait_for_timeout(1500)
                continue
            raise
    raise last_err


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
        page.set_default_timeout(NAV_TIMEOUT)

        def _on_dialog(d):
            # Accept "leave page?" (beforeunload) prompts, otherwise dismissing
            # them cancels our navigation and we get stuck on the page. Capture
            # and dismiss the portal's own validation alert()s.
            if d.type == "beforeunload":
                d.accept()
            else:
                dialogs.append(d.message)
                d.dismiss()

        page.on("dialog", _on_dialog)

        try:
            # --- 1. Login page -------------------------------------------------
            # wait_until="commit" so we don't hang on the portal's never-ending
            # spinner; then wait for the actual username field to appear.
            log.info("Opening portal login page ...")
            safe_goto(page, PORTAL_URL)
            # Fail fast (and clearly) if the portal serves a blank page instead
            # of the login form — that's typically a soft rate-limit / block.
            try:
                page.wait_for_selector('form[name="LoginForm"] input[name="username"]', timeout=25000)
            except PWTimeoutError:
                body_len = page.evaluate(
                    "() => (document.body ? document.body.innerText.trim().length : 0)"
                )
                if not body_len:
                    return False, (
                        "The portal returned a blank login page (empty body). This usually means "
                        "portal.leicaus.com is temporarily rate-limiting or blocking automated "
                        "logins after too many attempts. Wait ~20-30 minutes, then try again — and "
                        "avoid rapid repeated runs."
                    )
                return False, "The portal login form did not appear (unexpected page content)."

            # Cookie banner, if present (force=True: skip the actionability
            # checks that hang on this perpetually-loading portal)
            try:
                banner = page.locator("a.wpcc-btn")
                if banner.count() and banner.first.is_visible():
                    banner.first.click(force=True)
            except Exception:
                pass

            log.info("Logging in as %s (%s) ...", payload["portal_username"], sales_region_label)

            # Submit the login form directly in the page. This bypasses two
            # things that were stopping the login:
            #   1. Playwright's click() — its actionability checks (stable,
            #      hit-testable) spin forever because this portal never stops
            #      loading.
            #   2. The form's onsubmit="return CheckForm(this)" handler, which
            #      calls jQuery ($.trim); if jQuery hasn't finished loading the
            #      handler throws and cancels the submit.
            # We add a hidden CheckLogin field so the button's value is still
            # POSTed even though form.submit() has no "submitter", then call
            # submit() (which does not run onsubmit).
            #
            # The submit's POST navigation is sometimes aborted by the login
            # page's own perpetual loading, silently leaving us on the login
            # page — so we retry, re-filling the fields each time, until a Log
            # Out link appears (or the login form is gone). We're logged in when
            # either happens; wait_for_function survives the navigation.
            logged_in = False
            for attempt in range(3):
                if attempt > 0:
                    # Gentle spacing between attempts so we don't hammer the
                    # portal (which appears to soft-block rapid automated logins).
                    page.wait_for_timeout(3000)
                # If the login form has disappeared, either we're already in or
                # the portal served a blank page — stop resubmitting either way.
                if not page.locator('form[name="LoginForm"] input[name="username"]').count():
                    break
                page.fill('form[name="LoginForm"] input[name="username"]', payload["portal_username"])
                page.fill('form[name="LoginForm"] input[name="password"]', payload["portal_password"])
                log.info("Submitting login form (attempt %d) ...", attempt + 1)
                page.evaluate(
                    """() => {
                        const f = document.forms['LoginForm'];
                        if (!f) return;
                        if (!f.querySelector('input[type=hidden][name=CheckLogin]')) {
                            const h = document.createElement('input');
                            h.type = 'hidden'; h.name = 'CheckLogin'; h.value = 'Logon';
                            f.appendChild(h);
                        }
                        f.submit();
                    }"""
                )
                try:
                    page.wait_for_function(
                        """() => !!document.querySelector('a[href*="logout.cfm"]')
                                || !document.querySelector('form[name="LoginForm"] input[name="password"]')""",
                        timeout=15000,
                    )
                    logged_in = True
                    break
                except PWTimeoutError:
                    log.info("Still on the login page after attempt %d; retrying ...", attempt + 1)
                    continue

            if not logged_in:
                if page.locator('input[name="password"]').count():
                    return False, ("Login did not complete after several tries — the portal kept "
                                   "returning to the sign-in page. Check the credentials in Odoo.")
                return False, "Login did not complete after several tries."

            # --- 2. Navigate to the Add Sales Lead form ------------------------
            log.info("Logged in. Navigating to Reality Capture Sales Leads ...")
            safe_goto(page, SALES_LEADS_MAIN)

            # Follow the real "Add Sales Lead" link via a native JS click (same
            # reasoning as the login button). The CompanyName field only exists
            # on the form page, so it confirms we arrived; fall back to the
            # known form URL if the link path doesn't land.
            try:
                log.info("Waiting for the Add Sales Lead link ...")
                page.wait_for_selector('a[href*="lead_add.cfm"]', timeout=NAV_TIMEOUT)
                log.info("Clicking Add Sales Lead ...")
                page.eval_on_selector('a[href*="lead_add.cfm"]', "el => el.click()")
                page.wait_for_selector('input[name="CompanyName"]', timeout=NAV_TIMEOUT)
            except PWTimeoutError:
                log.info("Add Sales Lead link path did not land; going to the form URL directly ...")
                safe_goto(page, LEAD_ADD_URL)
                page.wait_for_selector('input[name="CompanyName"]', timeout=NAV_TIMEOUT)

            if not page.locator('input[name="CompanyName"]').count():
                return False, "Could not reach the Add Sales Lead form (session or permissions problem?)."
            log.info("Reached the Add Sales Lead form.")

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

            # force=True skips the hit-test actionability checks that hang on
            # this perpetually-loading portal.
            if payload.get("demo_requested"):
                page.check('input[name="Answer2"]', force=True)
            if payload.get("pricing_requested"):
                page.check('input[name="Answer3"]', force=True)
            if payload.get("meeting_requested"):
                page.check('input[name="Answer4"]', force=True)

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
            # # Native JS click (same reasoning as the login button) so we don't
            # # hang on actionability. This runs the portal's CheckForm(), which
            # # may alert() and stay on the page if it dislikes a field.
            # page.eval_on_selector('input[name="Add"]', "el => el.click()")
            # page.wait_for_timeout(2000)
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
