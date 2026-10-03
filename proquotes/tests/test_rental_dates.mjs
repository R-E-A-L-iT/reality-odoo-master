import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { autoshiftSavePayloads, guardSignModalShow, modalAmountAfterFlush, parsePortalDate, priceGateAfterSave, rentalDatesSavePayload, resolveRentalStartEdit, runRentalStartEdit, signBlockKind, signClickAction, signFlowFromPendingSave, updatingPriceMessage, validateRentalDates } from "../static/src/JS/rental_dates.js";
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

// Start moved past the current end: end becomes start + 1 calendar day,
// with no order error. Arithmetic is UTC calendar days (same as
// parsePortalDate), so these boundaries do not depend on the process timezone.
const startAfterEnd = [
    ["2026-01-31", "2026-01-15", "2026-02-01"],
    ["2026-02-28", "2026-02-01", "2026-03-01"],
    ["2024-02-28", "2024-02-01", "2024-02-29"],
    ["2024-02-29", "2024-02-01", "2024-03-01"],
    ["2026-04-30", "2026-04-01", "2026-05-01"],
    ["2026-12-31", "2026-12-15", "2027-01-01"],
];
for (const [start, end, shifted] of startAfterEnd) {
    const adjusted = resolveRentalStartEdit(start, end);
    assert.deepEqual(adjusted, { start, end: shifted, error: null });
    assert.equal(check(adjusted.start, adjusted.end).ok, true);
}

// The day before each boundary still shifts to that same next day.
assert.deepEqual(resolveRentalStartEdit("2026-01-31", "2026-01-30"), {
    start: "2026-01-31",
    end: "2026-02-01",
    error: null,
});
assert.deepEqual(resolveRentalStartEdit("2026-02-28", "2026-02-27"), {
    start: "2026-02-28",
    end: "2026-03-01",
    error: null,
});
assert.deepEqual(resolveRentalStartEdit("2024-02-28", "2024-02-27"), {
    start: "2024-02-28",
    end: "2024-02-29",
    error: null,
});
assert.deepEqual(resolveRentalStartEdit("2024-02-29", "2024-02-28"), {
    start: "2024-02-29",
    end: "2024-03-01",
    error: null,
});
assert.deepEqual(resolveRentalStartEdit("2026-04-30", "2026-04-29"), {
    start: "2026-04-30",
    end: "2026-05-01",
    error: null,
});
assert.deepEqual(resolveRentalStartEdit("2026-12-31", "2026-12-30"), {
    start: "2026-12-31",
    end: "2027-01-01",
    error: null,
});

// Start equal to end, and start before end, stay as they are.
assert.deepEqual(resolveRentalStartEdit("2026-09-17", "2026-09-17"), {
    start: "2026-09-17",
    end: "2026-09-17",
    error: null,
});
assert.deepEqual(resolveRentalStartEdit("2026-09-17", "2026-09-20"), {
    start: "2026-09-17",
    end: "2026-09-20",
    error: null,
});

// An incomplete or impossible start does not invent a new end.
assert.deepEqual(resolveRentalStartEdit("", "2026-09-20"), {
    start: "",
    end: "2026-09-20",
    error: "incomplete",
});
assert.deepEqual(resolveRentalStartEdit("2026-02-31", "2026-03-02"), {
    start: "2026-02-31",
    end: "2026-03-02",
    error: "invalid",
});

// End edited to before the start is not this helper. The order error stays.
assert.equal(check("2026-09-20", "2026-09-17").ok, false);
assert.equal(check("2026-09-20", "2026-09-17").reason, "order");
assert.equal(check("2026-01-31", "2026-01-30").reason, "order");
assert.equal(check("2024-03-01", "2024-02-29").reason, "order");

// The invalid pair is not what gets saved. One valid shifted pair is.
const posted = [];
function editStart(start, end) {
    const adjusted = resolveRentalStartEdit(start, end);
    const verdict = check(adjusted.start, adjusted.end);
    if (verdict.ok) {
        posted.push([adjusted.start, adjusted.end]);
    }
    return adjusted;
}
const shiftedOnce = editStart("2026-10-15", "2026-10-01");
assert.equal(shiftedOnce.error, null);
assert.deepEqual(posted, [["2026-10-15", "2026-10-16"]]);

// Auto-shift runs the live price refresh once and saves the shifted pair once.
// The previous end is not saved.
const refreshes = [];
const autoshiftSaves = [];
const autoshift = runRentalStartEdit("2026-09-18", "2026-09-16", {
    setEnd(value) {
        refreshes.push(["setEnd", value]);
    },
    refreshLivePrice(start, end) {
        refreshes.push(["refresh", start, end]);
    },
});
assert.equal(autoshift.refreshLivePrice, true);
assert.equal(autoshift.error, null);
assert.equal(autoshift.end, "2026-09-19");
if (check(autoshift.start, autoshift.end).ok) {
    autoshiftSaves.push([autoshift.start, autoshift.end]);
}
assert.deepEqual(refreshes, [
    ["setEnd", "2026-09-19"],
    ["refresh", "2026-09-18", "2026-09-19"],
]);
assert.deepEqual(autoshiftSaves, [["2026-09-18", "2026-09-19"]]);

// After an auto-shift the one save posts the new start and the shifted end.
// It does not post the previous start, and the end refresh is not a second save.
const shiftedPayloads = autoshiftSavePayloads("2026-10-15", "2026-10-12");
assert.deepEqual(shiftedPayloads, [
    { rental_start: "2026-10-15", rental_end: "2026-10-16" },
]);
const previousStart = rentalDatesSavePayload("2026-10-10", "2026-10-16");
assert.notDeepEqual(shiftedPayloads[0], previousStart);
assert.equal(shiftedPayloads[0].rental_start, "2026-10-15");
assert.equal(shiftedPayloads[0].rental_end, "2026-10-16");
assert.equal(rentalDatesSavePayload("", "2026-10-16"), null);
assert.equal(rentalDatesSavePayload("2026-10-15", ""), null);

const rentalSource = readFileSync(new URL("../static/src/JS/rental.js", import.meta.url), "utf8");
const editedHandler = rentalSource.split("_onRentalDateEdited(ev)")[1].split("\n    _syncEndMin()")[0];
assert.ok(editedHandler.indexOf("autoshiftRefreshingNow") < editedHandler.indexOf("_scheduleSave"));
assert.match(rentalSource, /rentalDatesSavePayload/);
assert.match(rentalSource, /proquotesAutoshift/);
assert.match(rentalSource, /dataset\[AUTOSHIFT_FLAG\] = "1"/);
const refreshBody = rentalSource.split("refreshLivePrice()")[1].split("setAutoshiftRefreshing(false)")[0];
assert.match(refreshBody, /setAutoshiftRefreshing\(true\)/);
assert.match(refreshBody, /dispatchEvent/);

// A start that does not move the end does not refresh.
const noRefresh = [];
const unchanged = runRentalStartEdit("2026-09-17", "2026-09-20", {
    refreshLivePrice() {
        noRefresh.push("refresh");
    },
});
assert.equal(unchanged.refreshLivePrice, false);
assert.deepEqual(noRefresh, []);

// Start edit with the end missing: do not invent an end, do not refresh,
// and Accept & Sign still blocks with the missing-date message.
const missingRefreshes = [];
const missingEnd = runRentalStartEdit("2026-09-17", "", {
    setEnd() {
        missingRefreshes.push("setEnd");
    },
    refreshLivePrice() {
        missingRefreshes.push("refresh");
    },
});
assert.deepEqual(missingRefreshes, []);
assert.equal(missingEnd.refreshLivePrice, false);
assert.equal(missingEnd.end, "");
assert.equal(missingEnd.error, "incomplete");
const missingAfterStart = check(missingEnd.start, missingEnd.end);
assert.equal(missingAfterStart.ok, false);
assert.equal(signBlockKind(missingAfterStart.reason), "missing");
result = opening("modalaccept", missingAfterStart);
assert.equal(result.blocked, true);
assert.equal(result.defaultPrevented, true);

// A pending date save blocks Accept & Sign. Flushing it opens the dialog
// only after the server total for the dates on screen is known, and that
// amount is the fresh total, not the one that was already on the page.
const pendingClick = signClickAction("pending");
assert.equal(pendingClick.open, false);
assert.equal(pendingClick.flush, true);
assert.equal(pendingClick.openAfterSuccess, true);
assert.equal(signClickAction("inflight").open, false);
assert.equal(signClickAction("error").open, false);
assert.equal(signClickAction("error").flush, false);
assert.equal(signClickAction("ready").open, true);
assert.equal(priceGateAfterSave({ error: "save" }), "error");
assert.equal(priceGateAfterSave({ success: true }), "ready");
const fastSign = signFlowFromPendingSave("previous-total", "fresh-total");
assert.equal(fastSign.blockedWhilePending, true);
assert.equal(fastSign.opensAfterFlush, true);
assert.equal(fastSign.modalAmount, "fresh-total");
assert.notEqual(fastSign.modalAmount, "previous-total");
assert.equal(modalAmountAfterFlush("previous-total", ""), null);
assert.equal(updatingPriceMessage("fr_CA"), "Mise à jour du prix…");
assert.equal(updatingPriceMessage("en_US"), "Updating price…");

const rentalGate = readFileSync(new URL("../static/src/JS/rental.js", import.meta.url), "utf8");
assert.match(rentalGate, /proquotesPriceGate/);
assert.match(rentalGate, /__proquotesFlushRentalDates/);
assert.match(rentalGate, /__proquotesRentalSave/);
assert.match(rentalGate, /signClickAction/);
assert.match(rentalGate, /data-id="total_amount"/);
const formSource = readFileSync(new URL("../static/src/JS/signature_form.js", import.meta.url), "utf8");
assert.match(formSource, /displayed_amount/);
const submitSource = formSource.split("async onClickSubmit")[1];
assert.ok(submitSource.indexOf("flushPortalRentalDates") < submitSource.indexOf("this.rpc"));
assert.ok(submitSource.indexOf("displayed_amount") < submitSource.indexOf("this.rpc"));

console.log("rental date checks ok");
