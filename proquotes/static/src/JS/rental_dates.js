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
