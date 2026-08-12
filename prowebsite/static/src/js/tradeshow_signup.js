/** @odoo-module **/
import { jsonrpc } from "@web/core/network/rpc_service";
import { whenReady } from "@odoo/owl";

// ─────────────────────────────────────────────────────────────────────────────
// Tradeshow / "stay in the loop" contact signup form.
//
// Simpler sibling of rtc_demo_request.js / product_lead.js: no week picker and
// no in-person/virtual toggle — just the contact details, an optional product
// of interest and event name. Reuses the .o_rtc_demo_* look (so the same CSS,
// including the .is-done success state, applies) but is keyed on the dedicated
// marker class `.o_rtc_signup_form` and POSTs to /tradeshow_signup/submit, which
// creates a CRM opportunity assigned round-robin to the Sales team.
//
// The marker class also lets rtc_demo_request.js skip this form (see the guard
// there), so the two scripts never fight over the same page.
// ─────────────────────────────────────────────────────────────────────────────

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

function wireForm(form) {
    if (form.dataset.signupWired === "1") return;
    form.dataset.signupWired = "1";

    const status = form.querySelector(".o_rtc_demo_status");
    const btn = form.querySelector(".o_rtc_demo_btn");

    function setStatus(msg, kind) {
        if (!status) return;
        status.textContent = msg || "";
        status.classList.toggle("is-error", kind === "error");
        status.classList.toggle("is-ok", kind === "ok");
    }

    function fieldVal(name) {
        const el = form.querySelector(`[name="${name}"]`);
        return el ? (el.value || "").trim() : "";
    }

    function markInvalid(name, bad) {
        const el = form.querySelector(`[name="${name}"]`);
        if (el) el.classList.toggle("is-invalid", !!bad);
    }

    form.addEventListener("submit", (ev) => {
        ev.preventDefault();
        setStatus("", null);

        const data = {
            full_name: fieldVal("full_name"),
            company: fieldVal("company"),
            email: fieldVal("email"),
            phone: fieldVal("phone"),
            product: fieldVal("product"),
            event: fieldVal("event"),
            notes: fieldVal("notes"),
            lang: document.documentElement.getAttribute("lang") || "",
        };

        // ── Client-side validation of required fields ──
        const required = ["full_name", "email", "phone"];
        let firstBad = null;
        required.forEach((name) => {
            const bad = !data[name];
            markInvalid(name, bad);
            if (bad && !firstBad) firstBad = name;
        });
        if (!EMAIL_RE.test(data.email)) {
            markInvalid("email", true);
            if (!firstBad) firstBad = "email";
        }
        if (firstBad) {
            setStatus("Please fill in your name, phone and a valid email.", "error");
            const el = form.querySelector(`[name="${firstBad}"]`);
            if (el) el.focus();
            return;
        }

        btn.disabled = true;
        const original = btn.textContent;
        btn.textContent = "Sending…";

        jsonrpc("/tradeshow_signup/submit", data)
            .then((res) => {
                if (res && res.success) {
                    form.classList.add("is-done");
                } else {
                    const err = res && res.error;
                    setStatus(
                        err === "invalid_email"
                            ? "That email address doesn't look right — please check it."
                            : "Something went wrong. Please try again.",
                        "error"
                    );
                    btn.disabled = false;
                    btn.textContent = original;
                }
            })
            .catch(() => {
                setStatus("Network error — please try again in a moment.", "error");
                btn.disabled = false;
                btn.textContent = original;
            });
    });
}

whenReady(() => {
    document.querySelectorAll(".o_rtc_signup_form").forEach(wireForm);
});
