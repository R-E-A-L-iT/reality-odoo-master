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
