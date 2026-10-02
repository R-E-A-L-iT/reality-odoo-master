/** @odoo-module **/
// 2026-02-25 - Brainecrew Apps

import { jsonrpc } from "@web/core/network/rpc_service";
import publicWidget from "@web/legacy/js/public/public_widget";
import { guardSignModalShow, runRentalStartEdit, signBlockKind, validateRentalDates } from "./rental_dates";

const SAVE_DELAY_MS = 600;

// Accept & Sign flushes a pending date edit before the signature is written.
let flushSave = null;

export function flushPortalRentalDates() {
    if (typeof flushSave === "function") {
        return flushSave();
    }
    return Promise.resolve({ skipped: true });
}

const SIGN_DATASET = {
    order: "msgOrder",
    invalid: "msgInvalid",
    missing: "msgMissing",
};

function signFallback(kind) {
    const french = (document.documentElement.lang || "").toLowerCase().startsWith("fr");
    if (kind === "order") {
        return french
            ? "La date de début de location doit être antérieure ou égale à la date de fin de location."
            : "The rental start date must be on or before the rental end date.";
    }
    if (kind === "invalid") {
        return french
            ? "Veuillez saisir une date de début et une date de fin de location valides."
            : "Enter a valid rental start date and a valid rental end date.";
    }
    return french
        ? "Veuillez choisir une date de début et une date de fin de location avant de signer."
        : "Please choose both rental start and end dates before signing.";
}

/**
 * Block Accept & Sign when the rental inputs are editable but not a usable period.
 * Returns the inline message, or null when signing may continue (not a rental,
 * inputs disabled, or both dates valid). Shows the same #rental-dates-error
 * treatment used while editing.
 */
export function portalRentalSignBlock() {
    const start = document.getElementById("rental-start");
    const end = document.getElementById("rental-end");
    if (!start || !end || start.disabled || end.disabled) {
        return null;
    }
    const verdict = validateRentalDates(start.value, end.value);
    if (verdict.ok) {
        return null;
    }
    const kind = signBlockKind(verdict.reason);
    const err = document.getElementById("rental-dates-error");
    const message = (err && err.dataset[SIGN_DATASET[kind]]) || signFallback(kind);
    if (err) {
        err.textContent = message;
        err.hidden = false;
    }
    start.classList.add("is-invalid");
    end.classList.add("is-invalid");
    if (err && typeof err.scrollIntoView === "function") {
        err.scrollIntoView({ block: "center" });
    }
    return message;
}

/**
 * Bootstrap opens #modalaccept from a document click listener that ignores
 * preventDefault. show.bs.modal is the event it does cancel.
 */
function onSignModalShow(ev) {
    const start = document.getElementById("rental-start");
    const end = document.getElementById("rental-end");
    const verdict = start && end && !start.disabled && !end.disabled
        ? validateRentalDates(start.value, end.value)
        : null;
    if (!guardSignModalShow(ev, verdict)) {
        return;
    }
    portalRentalSignBlock();
}

if (typeof document !== "undefined" && !document.__proquotesSignModalGuard) {
    document.__proquotesSignModalGuard = true;
    document.addEventListener("show.bs.modal", onSignModalShow);
}

// True while the shifted end input's own input/change events are firing.
// Those events refresh the live price. They must not schedule a second save;
// the start-date handler schedules the one debounced save afterwards.
let autoshiftRefreshing = false;

/**
 * Move the end to start + 1 before bubble listeners read the inputs, and
 * run the end-date refresh. A missing end is not filled, so Accept & Sign
 * still sees an empty end and keeps the dialog closed.
 * @param {Event} ev
 * @returns {boolean} true when the end day changed
 */
function autoshiftEndForStartEvent(ev) {
    if (autoshiftRefreshing) {
        return false;
    }
    const target = ev && ev.target;
    if (!target || target.id !== "rental-start" || target.disabled) {
        return false;
    }
    const end = document.getElementById("rental-end");
    if (!end || end.disabled) {
        return false;
    }
    let shifted = false;
    runRentalStartEdit(target.value, end.value, {
        setEnd(value) {
            end.value = value;
            if (target.value) {
                end.min = target.value;
            }
        },
        refreshLivePrice() {
            shifted = true;
            autoshiftRefreshing = true;
            try {
                // Same listeners as a hand edit of the end date. Programmatic
                // value assignment does not fire these, so the live total and
                // multiplier never moved. ``change`` commits the date value
                // so the later save reads the shifted day.
                end.dispatchEvent(new Event("input", { bubbles: true }));
                end.dispatchEvent(new Event("change", { bubbles: true }));
            } finally {
                autoshiftRefreshing = false;
            }
        },
    });
    return shifted;
}

if (typeof document !== "undefined" && !document.__proquotesRentalAutoshift) {
    document.__proquotesRentalAutoshift = true;
    document.addEventListener("input", autoshiftEndForStartEvent, true);
    document.addEventListener("change", autoshiftEndForStartEvent, true);
}

publicWidget.registry.rental = publicWidget.Widget.extend({
    selector: ".o_portal_sale_sidebar",
    events: {
        "input #rental-start": "_onRentalDateEdited",
        "input #rental-end": "_onRentalDateEdited",
        "change #rental-start": "_onRentalDateEdited",
        "change #rental-end": "_onRentalDateEdited",
    },

    async start() {
        await this._super(...arguments);
        this._saveSeq = 0;
        this._pendingSave = null;
        const table = this.el.querySelector("table#sales_order_table");
        const fromJquery = this.$el.find("table#sales_order_table").data() || {};
        this.orderDetail = {
            orderId: fromJquery.orderId || (table && table.dataset.orderId),
            token: fromJquery.token || (table && table.dataset.token),
        };
        const start = document.getElementById("rental-start");
        const end = document.getElementById("rental-end");
        this._lastSavedStart = start ? start.value : "";
        this._lastSavedEnd = end ? end.value : "";
        this._syncEndMin();
        flushSave = () => this._saveRentalDates();
    },

    destroy() {
        this._cancelPendingSave();
        if (flushSave) {
            flushSave = null;
        }
        return this._super(...arguments);
    },

    _onRentalDateEdited(ev) {
        // The shifted end's synthetic input/change is only the live refresh.
        // Scheduling here as well as on the start event would post twice.
        if (autoshiftRefreshing) {
            return;
        }
        const start = document.getElementById("rental-start");
        const end = document.getElementById("rental-end");
        // Capture already shifted a real browser event. This covers a
        // listener that did not go through document, and does not dispatch
        // again once the end day is already start + 1.
        autoshiftEndForStartEvent(ev);
        this._syncEndMin();
        const verdict = validateRentalDates(start && start.value, end && end.value);
        if (!verdict.ok) {
            this._cancelPendingSave();
            if (verdict.reason === "order" || verdict.reason === "invalid") {
                this._showError(this._message(verdict.reason));
            } else {
                this._clearError();
            }
            return;
        }
        this._clearError();
        this._scheduleSave();
    },

    _syncEndMin() {
        const start = document.getElementById("rental-start");
        const end = document.getElementById("rental-end");
        if (!start || !end) {
            return;
        }
        if (start.value) {
            end.min = start.value;
        } else {
            end.removeAttribute("min");
        }
    },

    _scheduleSave() {
        this._cancelPendingSave();
        this._pendingSave = setTimeout(() => {
            this._pendingSave = null;
            this._saveRentalDates();
        }, SAVE_DELAY_MS);
    },

    _cancelPendingSave() {
        if (this._pendingSave) {
            clearTimeout(this._pendingSave);
            this._pendingSave = null;
        }
    },

    _message(kind) {
        const el = document.getElementById("rental-dates-error");
        if (!el) {
            return "";
        }
        if (kind === "order") {
            return el.dataset.msgOrder || "";
        }
        if (kind === "invalid") {
            return el.dataset.msgInvalid || "";
        }
        if (kind === "save") {
            return el.dataset.msgSave || "";
        }
        if (kind === "locked") {
            return el.dataset.msgLocked || "";
        }
        return kind || "";
    },

    _showError(text) {
        const el = document.getElementById("rental-dates-error");
        if (el) {
            el.textContent = text || "";
            el.hidden = !text;
        }
        document.getElementById("rental-start")?.classList.add("is-invalid");
        document.getElementById("rental-end")?.classList.add("is-invalid");
    },

    _clearError() {
        const el = document.getElementById("rental-dates-error");
        if (el) {
            el.textContent = "";
            el.hidden = true;
        }
        document.getElementById("rental-start")?.classList.remove("is-invalid");
        document.getElementById("rental-end")?.classList.remove("is-invalid");
    },

    _saveRentalDates() {
        this._cancelPendingSave();
        const startEl = document.getElementById("rental-start");
        const endEl = document.getElementById("rental-end");
        const start = startEl ? startEl.value : "";
        const end = endEl ? endEl.value : "";
        // Confirmed and locked orders render the inputs disabled. Do not
        // post a save, and do not block Accept & Sign: the dates cannot
        // have changed. A request that still arrives is rejected server-side
        // and shown from data.error below.
        if ((startEl && startEl.disabled) || (endEl && endEl.disabled)) {
            return Promise.resolve({ success: true, unchanged: true });
        }
        const verdict = validateRentalDates(start, end);
        if (!verdict.ok) {
            const kind = verdict.reason === "order" ? "order" : "invalid";
            const message = this._message(kind) || kind;
            this._showError(message);
            return Promise.resolve({ error: message });
        }
        if (start === this._lastSavedStart && end === this._lastSavedEnd) {
            return Promise.resolve({ success: true, unchanged: true });
        }
        if (!this.orderDetail || !this.orderDetail.orderId) {
            return Promise.resolve({ error: this._message("save") });
        }
        const seq = ++this._saveSeq;
        return jsonrpc(
            "/my/orders/" + this.orderDetail.orderId + "/update_rental_dates",
            {
                access_token: this.orderDetail.token,
                rental_start: start,
                rental_end: end,
            }
        ).then((data) => {
            if (seq !== this._saveSeq) {
                return { error: this._message("save") };
            }
            const currentStart = document.getElementById("rental-start")?.value || "";
            const currentEnd = document.getElementById("rental-end")?.value || "";
            if (currentStart !== start || currentEnd !== end) {
                return { error: this._message("save") };
            }
            if (!data || data.error) {
                const message = (data && data.error) || this._message("save");
                this._showError(message);
                const lockedMessage = this._message("locked");
                if (lockedMessage && message === lockedMessage) {
                    if (startEl) {
                        startEl.disabled = true;
                    }
                    if (endEl) {
                        endEl.disabled = true;
                    }
                }
                return { error: message };
            }
            this._lastSavedStart = start;
            this._lastSavedEnd = end;
            this._clearError();
            this._applyPriceUpdate(data);
            return data;
        }).catch(() => {
            if (seq !== this._saveSeq) {
                return { error: this._message("save") };
            }
            const message = this._message("save");
            this._showError(message);
            return { error: message };
        });
    },

    /**
     * Refresh multiplier, line amounts, section subtotals and the totals
     * block from the re-rendered quote. The date inputs stay put so a
     * save cannot wipe what the customer is editing.
     */
    _applyPriceUpdate(data) {
        const parsed = document.createElement("div");
        if (data.sale_inner_template) {
            parsed.innerHTML = data.sale_inner_template;
        }
        this._copyNodes(parsed, ".proquotesLineTotal[data-line-id]", "data-line-id");
        this._copyNodes(parsed, ".subtotal-label[data-sec-line]", "data-sec-line");
        this._applyMultipliers(parsed, data.paid_days);
        const newTotal = parsed.querySelector("#total");
        const oldTotal = document.querySelector("#total");
        if (newTotal && oldTotal) {
            oldTotal.innerHTML = newTotal.innerHTML;
        }
        if (data.order_amount_total && data.order_amount_total !== "undefined") {
            const bold = document.querySelector("#portalTotal b");
            if (bold) {
                bold.textContent = data.order_amount_total;
            }
        }
    },

    _copyNodes(parsed, selector, attr) {
        parsed.querySelectorAll(selector).forEach((node) => {
            const key = node.getAttribute(attr);
            if (!key) {
                return;
            }
            document.querySelectorAll(selector).forEach((live) => {
                if (live.getAttribute(attr) === key) {
                    live.innerHTML = node.innerHTML;
                }
            });
        });
    },

    _applyMultipliers(parsed, paidDays) {
        const next = parsed.querySelectorAll(".proquotes-multiplier-cell");
        const live = document.querySelectorAll(".proquotes-multiplier-cell");
        if (next.length && next.length === live.length) {
            live.forEach((cell, index) => {
                cell.innerHTML = next[index].innerHTML;
            });
            return;
        }
        const label = paidDays > 0 ? "x" + paidDays : "—";
        live.forEach((cell) => {
            const span = cell.querySelector("span");
            if (span) {
                span.textContent = label;
            }
        });
    },
});
