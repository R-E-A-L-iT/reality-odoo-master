import assert from "node:assert/strict";
import { guardSignModalShow, parsePortalDate, signBlockKind, validateRentalDates } from "../static/src/JS/rental_dates.js";
import { autoSignNameBlocked } from "../static/src/JS/signer_name.js";

function check(start, end) {
    return validateRentalDates(start, end);
}

assert.equal(parsePortalDate("2026-02-31"), null);
assert.equal(parsePortalDate("2026-9-17"), null);
assert.ok(parsePortalDate("2026-09-17"));

assert.equal(check("", "2026-09-20").reason, "incomplete");
assert.equal(check("2026-09-17", "").reason, "incomplete");
assert.equal(check("2026-02-31", "2026-03-02").reason, "invalid");

// The quote bug: end 2026-09-29, typing "20", passes through 2026-09-02
// while the start is already 2026-09-17. That must not be saved.
assert.equal(check("2026-09-17", "2026-09-02").ok, false);
assert.equal(check("2026-09-17", "2026-09-02").reason, "order");
assert.equal(check("2026-09-17", "2026-09-20").ok, true);
assert.equal(check("2026-09-17", "2026-09-17").ok, true);

// Typing the start "17" passes through 2026-09-01, which is still before the end.
assert.equal(check("2026-09-01", "2026-09-20").ok, true);
assert.equal(check("2026-09-17", "2026-09-20").ok, true);

const sequence = ["2026-09-29", "2026-09-02", "2026-09-20"];
const saved = [];
for (const end of sequence) {
    const verdict = check("2026-09-17", end);
    if (verdict.ok) {
        saved.push(end);
    }
}
assert.deepEqual(saved, ["2026-09-29", "2026-09-20"]);

// Auto signature rejects the website public user and accepts a real customer.
// The prefill is the order partner in both cases, so a logged-in portal
// user ("Jane Portal") and an anonymous visitor signing as "Jane Customer"
// both pass. Draw mode is not this check.
const publicUser = "Public user for R-E-A-L.iT Solutions";
assert.equal(autoSignNameBlocked(publicUser, "auto"), true);
assert.equal(autoSignNameBlocked("Public User", "auto"), true);
assert.equal(autoSignNameBlocked("Jane Customer", "auto"), false);
assert.equal(autoSignNameBlocked("Jane Portal", "auto"), false);
assert.equal(autoSignNameBlocked(publicUser, "draw"), false);
assert.equal(autoSignNameBlocked("", "auto"), false);

// Accept & Sign: a cleared date is a missing-date block, not a quiet incomplete.
assert.equal(signBlockKind(null), null);
assert.equal(signBlockKind("order"), "order");
assert.equal(signBlockKind("invalid"), "invalid");
assert.equal(signBlockKind("incomplete"), "missing");
assert.equal(signBlockKind(check("", "2026-09-20").reason), "missing");
assert.equal(signBlockKind(check("2026-09-17", "2026-09-02").reason), "order");
assert.equal(signBlockKind(check("2026-09-17", "2026-09-20").reason), null);

// Bootstrap's data-api ignores click preventDefault. show.bs.modal does not.
function showEvent(id) {
    let prevented = false;
    return {
        target: { id },
        preventDefault() {
            prevented = true;
        },
        get defaultPrevented() {
            return prevented;
        },
    };
}

function opening(id, verdict) {
    const event = showEvent(id);
    const blocked = guardSignModalShow(event, verdict);
    return { blocked, defaultPrevented: event.defaultPrevented };
}

const missing = check("", "2026-09-20");
const reversed = check("2026-09-20", "2026-09-17");
const impossible = check("2026-02-31", "2026-03-02");
const valid = check("2026-09-17", "2026-09-20");

let result = opening("modalaccept", missing);
assert.equal(result.blocked, true);
assert.equal(result.defaultPrevented, true);

result = opening("modalaccept", reversed);
assert.equal(result.blocked, true);
assert.equal(result.defaultPrevented, true);

result = opening("modalaccept", impossible);
assert.equal(result.blocked, true);
assert.equal(result.defaultPrevented, true);

result = opening("modalaccept", valid);
assert.equal(result.blocked, false);
assert.equal(result.defaultPrevented, false);

// Not a rental, or the inputs are disabled: verdict is null, dialog opens.
result = opening("modalaccept", null);
assert.equal(result.blocked, false);
assert.equal(result.defaultPrevented, false);

// Decline and any other dialog are left alone.
result = opening("modaldecline", missing);
assert.equal(result.blocked, false);
assert.equal(result.defaultPrevented, false);

console.log("rental date checks ok");
