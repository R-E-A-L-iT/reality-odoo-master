/** @odoo-module **/

const DATE_RE = /^(\d{4})-(\d{2})-(\d{2})$/;

/**
 * A real calendar day, or null. ``YYYY-MM-DD`` only; ``2026-02-31`` is rejected.
 * @param {string} value
 * @returns {Date|null}
 */
export function parsePortalDate(value) {
    if (typeof value !== "string" || !DATE_RE.test(value)) {
        return null;
    }
    const year = Number(value.slice(0, 4));
    const month = Number(value.slice(5, 7));
    const day = Number(value.slice(8, 10));
    const date = new Date(Date.UTC(year, month - 1, day));
    if (
        date.getUTCFullYear() !== year ||
        date.getUTCMonth() !== month - 1 ||
        date.getUTCDate() !== day
    ) {
        return null;
    }
    return date;
}

/**
 * ``YYYY-MM-DD`` for a calendar day held the same way as ``parsePortalDate``
 * (UTC year/month/day). Do not format with local getters: a UTC midnight
 * is the previous evening in timezones behind UTC.
 * @param {Date} date
 * @returns {string}
 */
function formatPortalDate(date) {
    const year = date.getUTCFullYear();
    const month = String(date.getUTCMonth() + 1).padStart(2, "0");
    const day = String(date.getUTCDate()).padStart(2, "0");
    return year + "-" + month + "-" + day;
}

/**
 * Add calendar days to a portal ``YYYY-MM-DD`` value.
 * Uses the UTC calendar day from ``parsePortalDate`` and ``setUTCDate``,
 * not ``new Date("YYYY-MM-DD")``, so the result does not depend on the
 * browser timezone.
 * @param {string} value
 * @param {number} days
 * @returns {string|null}
 */
export function addPortalDays(value, days) {
    const date = parsePortalDate(value);
    if (!date || typeof days !== "number" || !Number.isFinite(days)) {
        return null;
    }
    const next = new Date(date.getTime());
    next.setUTCDate(next.getUTCDate() + days);
    return formatPortalDate(next);
}

/**
 * Decide whether the portal may save the rental period.
 * Incomplete dates are not an error to show — the customer is still typing.
 * @param {string} startValue
 * @param {string} endValue
 * @returns {{ok: boolean, reason: (string|null)}}
 */
export function validateRentalDates(startValue, endValue) {
    const start = (startValue || "").trim();
    const end = (endValue || "").trim();
    if (!start || !end) {
        return { ok: false, reason: "incomplete" };
    }
    const startDate = parsePortalDate(start);
    const endDate = parsePortalDate(end);
    if (!startDate || !endDate) {
        return { ok: false, reason: "invalid" };
    }
    if (startDate.getTime() > endDate.getTime()) {
        return { ok: false, reason: "order" };
    }
    return { ok: true, reason: null };
}

/**
 * Apply a start-date edit.
 *
 * When the new start is after the current end, the end moves to the next
 * calendar day and there is no order error. The customer does not have to
 * move the end first. Equal or earlier starts are left as they are.
 *
 * This is only for a start edit. An end date typed before the start still
 * fails ``validateRentalDates`` with ``order``.
 *
 * The portal end input has no ``max`` and there is no maximum rental
 * length on this path. The only bound is ``min`` = the start day, and
 * start + 1 day always satisfies it.
 *
 * @param {string} startValue new start
 * @param {string} endValue current end
 * @returns {{start: string, end: string, error: (string|null)}}
 */
export function resolveRentalStartEdit(startValue, endValue) {
    const start = (startValue || "").trim();
    const end = (endValue || "").trim();
    const verdict = validateRentalDates(start, end);
    if (verdict.reason !== "order") {
        return { start, end, error: verdict.ok ? null : verdict.reason };
    }
    const shifted = addPortalDays(start, 1);
    if (!shifted) {
        return { start, end, error: "invalid" };
    }
    return { start, end: shifted, error: null };
}

/**
 * Start-date edit plus whether the live price refresh must run.
 *
 * ``refreshLivePrice`` is true only when the end day actually moves to
 * start + 1. The portal then has to run the same refresh a manual end
 * edit runs (the end input's listeners). A missing or unchanged end does
 * not. Callers must save the returned pair at most once.
 *
 * @param {string} startValue
 * @param {string} endValue current end, before the edit is applied
 * @param {{setEnd?: function(string): void, refreshLivePrice?: function(string, string): void}=} hooks
 * @returns {{start: string, end: string, error: (string|null), refreshLivePrice: boolean}}
 */
export function runRentalStartEdit(startValue, endValue, hooks) {
    const adjusted = resolveRentalStartEdit(startValue, endValue);
    const previousEnd = (endValue || "").trim();
    const refreshLivePrice = adjusted.error === null && adjusted.end !== previousEnd;
    if (refreshLivePrice && hooks) {
        if (typeof hooks.setEnd === "function") {
            hooks.setEnd(adjusted.end);
        }
        if (typeof hooks.refreshLivePrice === "function") {
            hooks.refreshLivePrice(adjusted.start, adjusted.end);
        }
    }
    return {
        start: adjusted.start,
        end: adjusted.end,
        error: adjusted.error,
        refreshLivePrice,
    };
}

/**
 * Body of ``/update_rental_dates``. Both days are required. An end-only
 * refresh, or a start that is still the previous day, is not a payload.
 * @param {string} startValue
 * @param {string} endValue
 * @returns {{rental_start: string, rental_end: string}|null}
 */
export function rentalDatesSavePayload(startValue, endValue) {
    const start = (startValue || "").trim();
    const end = (endValue || "").trim();
    if (!validateRentalDates(start, end).ok) {
        return null;
    }
    return { rental_start: start, rental_end: end };
}

/**
 * Saves posted after a start edit that may auto-shift the end.
 *
 * The live refresh is not a save. The one payload carries the edited
 * start and the shifted end. It must not carry an older start.
 * @param {string} startValue new start
 * @param {string} endValue end before the edit
 * @returns {Array<{rental_start: string, rental_end: string}>}
 */
export function autoshiftSavePayloads(startValue, endValue) {
    let end = (endValue || "").trim();
    const result = runRentalStartEdit(startValue, end, {
        setEnd(value) {
            end = value;
        },
        refreshLivePrice() {
            // The end input's refresh must not post its own save.
        },
    });
    const payload = rentalDatesSavePayload(result.start, end);
    return payload ? [payload] : [];
}

/**
 * Which message Accept & Sign should show.
 * Incomplete input is quiet while the customer is typing, and a block at sign time.
 * @param {string|null} reason
 * @returns {"order"|"invalid"|"missing"|null}
 */
export function signBlockKind(reason) {
    if (!reason) {
        return null;
    }
    if (reason === "order" || reason === "invalid") {
        return reason;
    }
    return "missing";
}

/**
 * Cancel Bootstrap's ``show.bs.modal`` for ``#modalaccept``.
 *
 * The Accept & Sign buttons use ``data-bs-toggle="modal"``. That data-api
 * listener lives on ``document`` and does not look at ``defaultPrevented``
 * on the click, so a click handler cannot keep the dialog closed. Bootstrap
 * does honor ``preventDefault`` on ``show.bs.modal``.
 *
 * ``verdict`` is null when there is nothing to block (not a rental quote, or
 * the date inputs are disabled). A usable period is ``verdict.ok``.
 *
 * @param {Event|{target?: {id?: string}, preventDefault?: function}} event
 * @param {{ok: boolean}|null} verdict
 * @returns {boolean} true when the dialog must stay closed
 */
/**
 * What Accept & Sign should do while the rental total may be stale.
 *
 * ``pending`` and ``inflight`` are a date save that has not yet applied
 * the server total for the dates on screen. The dialog stays closed, the
 * save runs immediately, and the dialog opens only after that save
 * succeeds. ``error`` stays closed. ``ready`` may open.
 *
 * @param {"ready"|"pending"|"inflight"|"error"|string} gate
 * @returns {{open: boolean, flush: boolean, openAfterSuccess: boolean}}
 */
export function signClickAction(gate) {
    if (gate === "pending" || gate === "inflight") {
        return { open: false, flush: true, openAfterSuccess: true };
    }
    if (gate === "error") {
        return { open: false, flush: false, openAfterSuccess: false };
    }
    return { open: true, flush: false, openAfterSuccess: false };
}

/**
 * Gate after the save for the dates now on screen finishes.
 * @param {{error?: string}|null|undefined} result
 * @returns {"ready"|"error"}
 */
export function priceGateAfterSave(result) {
    if (!result || result.error) {
        return "error";
    }
    return "ready";
}

/**
 * Amount shown in the sign dialog after a flushed save.
 * The server total, never the total that was on screen before this save.
 * @param {string|number|null} previousAmount
 * @param {string|number|null} serverAmount
 * @returns {string|number|null}
 */
export function modalAmountAfterFlush(previousAmount, serverAmount) {
    if (serverAmount === undefined || serverAmount === null || serverAmount === "") {
        return null;
    }
    return serverAmount;
}

/**
 * Pending save blocks the dialog. After the flush succeeds, the dialog
 * may open and its amount is the server total.
 * @param {string|number} previousAmount
 * @param {string|number} serverAmount
 */
export function signFlowFromPendingSave(previousAmount, serverAmount) {
    const during = signClickAction("pending");
    const after = signClickAction(priceGateAfterSave({ success: true }));
    return {
        blockedWhilePending: during.open === false && during.flush === true && during.openAfterSuccess === true,
        opensAfterFlush: after.open === true,
        modalAmount: modalAmountAfterFlush(previousAmount, serverAmount),
    };
}

/**
 * @param {string} [lang]
 * @returns {string}
 */
export function updatingPriceMessage(lang) {
    const french = (lang || "").toLowerCase().startsWith("fr");
    return french ? "Mise à jour du prix…" : "Updating price…";
}

export function guardSignModalShow(event, verdict) {
    const id = event && event.target ? event.target.id : "";
    if (id !== "modalaccept" || !verdict || verdict.ok) {
        return false;
    }
    if (typeof event.preventDefault === "function") {
        event.preventDefault();
    }
    return true;
}
