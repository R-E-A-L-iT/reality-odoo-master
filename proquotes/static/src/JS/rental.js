/** @odoo-module **/
// 2026-02-25 - Brainecrew Apps

import { jsonrpc } from "@web/core/network/rpc_service";
import publicWidget from "@web/legacy/js/public/public_widget";
import { validateRentalDates } from "./rental_dates";

const SAVE_DELAY_MS = 600;

// Accept & Sign flushes a pending date edit before the signature is written.
let flushSave = null;

export function flushPortalRentalDates() {
    if (typeof flushSave === "function") {
        return flushSave();
    }
    return Promise.resolve({ skipped: true });
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

    _onRentalDateEdited() {
        this._syncEndMin();
        const start = document.getElementById("rental-start");
        const end = document.getElementById("rental-end");
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
        if (data.order_amount_total) {
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
