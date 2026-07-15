/** @odoo-module **/
import { jsonrpc } from "@web/core/network/rpc_service";
import { whenReady } from "@odoo/owl";

// ─────────────────────────────────────────────────────────────────────────────
// RTC Demo Request form.
// Activates only on pages that include the `.o_rtc_demo_page` wrapper (the XML
// snippet pasted into the website page). Populates the "week" selector with the
// next N upcoming weeks (Monday-based), validates the required contact fields,
// and POSTs to /rtc_demo/submit which creates a CRM opportunity assigned to a
// member of the Sales team.
// ─────────────────────────────────────────────────────────────────────────────

const WEEKS_AHEAD = 12;

function mondayOf(date) {
    const d = new Date(date);
    const day = d.getDay();               // 0 = Sun … 6 = Sat
    const diff = (day === 0 ? -6 : 1 - day);
    d.setDate(d.getDate() + diff);
    d.setHours(0, 0, 0, 0);
    return d;
}

function fmt(date) {
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function buildWeekOptions(select) {
    if (!select || select.dataset.populated === "1") return;
    let monday = mondayOf(new Date());
    // Start from *next* week so no one books the current, partly-gone week.
    monday.setDate(monday.getDate() + 7);
    for (let i = 0; i < WEEKS_AHEAD; i++) {
        const start = new Date(monday);
        const end = new Date(monday);
        end.setDate(end.getDate() + 4);   // Mon–Fri
        const label = `Week of ${fmt(start)} – ${fmt(end)}, ${start.getFullYear()}`;
        const opt = document.createElement("option");
        opt.value = label;
        opt.textContent = label;
        select.appendChild(opt);
        monday.setDate(monday.getDate() + 7);
    }
    select.dataset.populated = "1";
}

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

whenReady(() => {
    const page = document.querySelector(".o_rtc_demo_page");
    if (!page) return;

    const form = page.querySelector(".o_rtc_demo_form");
    if (!form) return;

    const weekSel = form.querySelector('[name="week"]');
    buildWeekOptions(weekSel);

    const status = form.querySelector(".o_rtc_demo_status");
    const btn = form.querySelector(".o_rtc_demo_btn");

    // ── In-person / virtual toggle: show the city field only for in-person ──
    const cityWrap = form.querySelector(".o_rtc_demo_city_wrap");
    function currentMode() {
        const checked = form.querySelector('[name="location_mode"]:checked');
        return checked ? checked.value : "in_person";
    }
    function syncModeUi() {
        if (cityWrap) cityWrap.classList.toggle("is-hidden", currentMode() !== "in_person");
    }
    form.querySelectorAll('[name="location_mode"]').forEach((r) =>
        r.addEventListener("change", syncModeUi)
    );
    syncModeUi();

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

        const inPerson = currentMode() === "in_person";
        const city = fieldVal("city");

        const data = {
            full_name: fieldVal("full_name"),
            company: fieldVal("company"),
            email: fieldVal("email"),
            phone: fieldVal("phone"),
            week: fieldVal("week"),
            location: inPerson ? city : "Virtual demo",
            product: fieldVal("product"),
            notes: fieldVal("notes"),
            lang: document.documentElement.getAttribute("lang") || "",
        };

        // ── Client-side validation of required fields ──
        const required = ["full_name", "company", "email", "phone", "week"];
        let firstBad = null;
        required.forEach((name) => {
            const bad = !data[name];
            markInvalid(name, bad);
            if (bad && !firstBad) firstBad = name;
        });
        // The city is required only for an in-person demo.
        if (inPerson) {
            markInvalid("city", !city);
            if (!city && !firstBad) firstBad = "city";
        } else {
            markInvalid("city", false);
        }
        if (!EMAIL_RE.test(data.email)) {
            markInvalid("email", true);
            if (!firstBad) firstBad = "email";
        }
        if (firstBad) {
            setStatus("Please fill in all required fields with a valid email.", "error");
            const el = form.querySelector(`[name="${firstBad}"]`);
            if (el) el.focus();
            return;
        }

        btn.disabled = true;
        const original = btn.textContent;
        btn.textContent = "Sending…";

        jsonrpc("/rtc_demo/submit", data)
            .then((res) => {
                if (res && res.success) {
                    form.classList.add("is-done");
                } else {
                    const err = res && res.error;
                    setStatus(
                        err === "invalid_email"
                            ? "That email address doesn't look right — please check it."
                            : "Something went wrong sending your request. Please try again.",
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
});
