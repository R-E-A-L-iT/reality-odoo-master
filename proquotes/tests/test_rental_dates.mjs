import assert from "node:assert/strict";
import { parsePortalDate, validateRentalDates } from "../static/src/JS/rental_dates.js";

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

console.log("rental date checks ok");
