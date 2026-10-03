/** @odoo-module **/
// 2026-02-25 - Brainecrew Apps

import { jsonrpc } from "@web/core/network/rpc_service";
import publicWidget from "@web/legacy/js/public/public_widget";
import { guardSignModalShow, modalAmountAfterFlush, plainDisplayedAmount, priceGateAfterSave, rentalDatesSavePayload, runRentalStartEdit, signBlockKind, signClickAction, updatingPriceMessage, validateRentalDates } from "./rental_dates";

const SAVE_DELAY_MS = 600;

// Accept & Sign flushes a pending date edit before the signature is written.
// The function lives on document so a second copy of this file (it is in
// both asset bundles) flushes the widget that actually saves.
export function flushPortalRentalDates() {
    const flush = typeof document !== "undefined" && document.__proquotesFlushRentalDates;
    if (typeof flush === "function") {
        return flush();
    }
    return Promise.resolve({ skipped: true });
}

export function readPriceGate() {
    const root = typeof document !== "undefined" && document.documentElement;
    const gate = root && root.dataset.proquotesPriceGate;
    return gate || "ready";
}

/**
 * Block the signature submit while the total on screen is not the total
 * for the dates on screen. ``null`` when signing may continue.
 */
export function portalPriceSignBlock() {
    const action = signClickAction(readPriceGate());
    if (action.open) {
        return null;
    }
    if (readPriceGate() === "error") {
        const err = document.getElementById("rental-dates-error");
        if (err && !err.hidden && err.textContent) {
            return err.textContent;
        }
    }
    return updatingPriceMessage(document.documentElement.lang);
}

/**
 * Remember the server total the customer is looking at, and write it into
 * the sign dialog. ``formatted`` is the currency string; ``amount`` is the
 * plain number sent back with Accept & Sign.
 */
export function rememberDisplayedAmount(amount, formatted) {
    const root = document.documentElement;
    const plain = plainDisplayedAmount(amount);
    if (plain !== null && root) {
        root.dataset.proquotesDisplayedAmount = plain;
    }
    if (!formatted || formatted === "undefined") {
        return;
    }
    document.querySelectorAll('[data-id="total_amount"]').forEach((node) => {
        node.textContent = formatted;
    });
    const bold = document.querySelector("#portalTotal b");
    if (bold) {
        bold.textContent = formatted;
    }
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
export function readDisplayedAmount() {
    const root = document.documentElement;
    const stored = (root && root.dataset.proquotesDisplayedAmount) || "";
    return plainDisplayedAmount(stored) || "";
}

function openAcceptModal() {
    const modal = document.getElementById("modalaccept");
    const ModalApi = window.bootstrap && window.bootstrap.Modal;
    if (!modal || !ModalApi) {
        return;
    }
    ModalApi.getOrCreateInstance(modal).show();
}

function flushAndMaybeOpen() {
    if (document.__proquotesSignWait) {
        return document.__proquotesSignWait;
    }
    const flush = document.__proquotesFlushRentalDates;
    const run = Promise.resolve(
        typeof flush === "function" ? flush() : { skipped: true }
    ).then((result) => {
        document.__proquotesSignWait = null;
        if (result && result.superseded) {
            if (signClickAction(readPriceGate()).open) {
                openAcceptModal();
            }
            return result;
        }
        if (result && result.error) {
            return result;
        }
        const amount = modalAmountAfterFlush(
            null,
            result && (result.order_amount_total || result.amount_total)
        );
        if (amount !== null && result) {
            rememberDisplayedAmount(result.amount_total, result.order_amount_total || amount);
        }
        if (signClickAction(readPriceGate()).open) {
            openAcceptModal();
        }
        return result;
    }).catch((error) => {
        document.__proquotesSignWait = null;
        throw error;
    });
    document.__proquotesSignWait = run;
    return run;
}

function onAcceptClick(ev) {
    const target = ev.target && ev.target.closest && ev.target.closest("a, button");
    if (!target || target.getAttribute("data-bs-target") !== "#modalaccept") {
        return;
    }
    const action = signClickAction(readPriceGate());
    if (action.open) {
        return;
    }
    ev.preventDefault();
    ev.stopPropagation();
    if (action.flush && action.openAfterSuccess) {
        flushAndMaybeOpen();
    }
}

function onSignModalShow(ev) {
    const action = signClickAction(readPriceGate());
    if (ev && ev.target && ev.target.id === "modalaccept" && !action.open) {
        if (typeof ev.preventDefault === "function") {
            ev.preventDefault();
        }
        if (action.flush && action.openAfterSuccess) {
            flushAndMaybeOpen();
        }
        return;
    }
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
    document.addEventListener("click", onAcceptClick, true);
    document.addEventListener("show.bs.modal", onSignModalShow);
}

// The end input's refresh dispatches input/change so the live total updates.
// rental.js is bundled more than once, so a module-local flag is not enough:
// the widget that runs can be a different copy. The marker lives on
// documentElement, which every copy can see. While it is set, no copy may
// schedule a save. The start edit schedules the one save afterwards, and
// that save posts both days.
// rental.js is listed twice in each asset bundle. Each copy has its own
// widget instance, so the debounce timer, the request in flight, and the
// last saved pair have to live on document. Otherwise one copy can apply
// an older total after the other has already repriced.
function rentalSaveState() {
    if (!document.__proquotesRentalSave) {
        document.__proquotesRentalSave = {
            seq: 0,
            inflight: null,
            pending: null,
            lastStart: null,
            lastEnd: null,
        };
    }
    return document.__proquotesRentalSave;
}

const AUTOSHIFT_FLAG = "proquotesAutoshift";

function autoshiftRefreshingNow() {
    const root = document.documentElement;
    return !!(root && root.dataset[AUTOSHIFT_FLAG] === "1");
}

function setAutoshiftRefreshing(active) {
    const root = document.documentElement;
    if (!root) {
        return;
    }
    if (active) {
        root.dataset[AUTOSHIFT_FLAG] = "1";
    } else {
        delete root.dataset[AUTOSHIFT_FLAG];
    }
}

/**
 * Move the end to start + 1 before bubble listeners read the inputs, and
 * run the end-date refresh. A missing end is not filled, so Accept & Sign
 * still sees an empty end and keeps the dialog closed.
 * @param {Event} ev
 * @returns {boolean} true when the end day changed
 */
function autoshiftEndForStartEvent(ev) {
    if (autoshiftRefreshingNow()) {
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
            setAutoshiftRefreshing(true);
            try {
                // Same listeners as a hand edit of the end date. Programmatic
                // value assignment does not fire these, so the live total and
                // multiplier never moved. The document flag above stops every
                // copy of this widget from treating that as its own save.
                end.dispatchEvent(new Event("input", { bubbles: true }));
                end.dispatchEvent(new Event("change", { bubbles: true }));
            } finally {
                setAutoshiftRefreshing(false);
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
        const table = this.el.querySelector("table#sales_order_table");
        const fromJquery = this.$el.find("table#sales_order_table").data() || {};
        this.orderDetail = {
            orderId: fromJquery.orderId || (table && table.dataset.orderId),
            token: fromJquery.token || (table && table.dataset.token),
        };
        const start = document.getElementById("rental-start");
        const end = document.getElementById("rental-end");
        const shared = rentalSaveState();
        if (shared.lastStart === null || shared.lastEnd === null) {
            shared.lastStart = start ? start.value : "";
            shared.lastEnd = end ? end.value : "";
        }
        this._syncEndMin();
        const shown = document.getElementById("approve_total_var");
        if (shown && shown.textContent && !readDisplayedAmount()) {
            rememberDisplayedAmount(shown.textContent.trim(), "");
        }
        document.__proquotesFlushRentalDates = () => this._saveRentalDates();
        document.__proquotesFlushOwner = this;
        if (!document.documentElement.dataset.proquotesPriceGate) {
            this._setPriceGate("ready");
        }
    },

    destroy() {
        if (document.__proquotesFlushOwner === this) {
            this._cancelPendingSave();
            document.__proquotesFlushRentalDates = null;
            document.__proquotesFlushOwner = null;
        }
        return this._super(...arguments);
    },

    _setPriceGate(gate) {
        const root = document.documentElement;
        if (root) {
            root.dataset.proquotesPriceGate = gate;
        }
        const waiting = gate === "pending" || gate === "inflight";
        document.querySelectorAll("#total, #portalTotal").forEach((el) => {
            el.classList.toggle("proquotes-price-updating", waiting);
        });
        document.querySelectorAll("a, button").forEach((btn) => {
            if (btn.getAttribute("data-bs-target") !== "#modalaccept") {
                return;
            }
            btn.classList.toggle("proquotes-sign-waiting", gate !== "ready");
            btn.setAttribute("aria-disabled", gate === "ready" ? "false" : "true");
        });
        document.querySelectorAll("#modalaccept button").forEach((btn) => {
            btn.disabled = gate !== "ready";
        });
        this._priceStatusNodes().forEach((node) => {
            if (waiting) {
                node.hidden = false;
                node.textContent = updatingPriceMessage(root && root.lang);
            } else {
                node.hidden = true;
                node.textContent = "";
            }
        });
    },

    _priceStatusNodes() {
        const spots = [
            ["rental-price-status", document.querySelector("#portalTotal")],
            ["rental-price-status-quote", document.querySelector("#total")],
        ];
        return spots.map(([id, before]) => {
            let node = document.getElementById(id);
            if (!node) {
                node = document.createElement("p");
                node.id = id;
                node.className = "rental-price-status";
                node.setAttribute("role", "status");
                node.hidden = true;
            }
            if (before && before.parentNode && node.parentNode !== before.parentNode) {
                before.parentNode.insertBefore(node, before);
            }
            return node;
        });
    },

    _onRentalDateEdited(ev) {
        // The shifted end's synthetic input/change is only the live refresh.
        // Scheduling here would post a second pair, and a bundled second copy
        // of this file does not share a module-local flag.
        if (autoshiftRefreshingNow()) {
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
            if (!rentalSaveState().inflight) {
                this._setPriceGate(readPriceGate() === "error" ? "error" : "ready");
            }
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
        this._setPriceGate("pending");
        const shared = rentalSaveState();
        shared.pending = setTimeout(() => {
            shared.pending = null;
            this._saveRentalDates();
        }, SAVE_DELAY_MS);
    },

    _cancelPendingSave() {
        const shared = rentalSaveState();
        if (shared.pending) {
            clearTimeout(shared.pending);
            shared.pending = null;
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

    _saveRentalDates(allowFollowUp = true) {
        const shared = rentalSaveState();
        if (shared.pending) {
            clearTimeout(shared.pending);
            shared.pending = null;
        }
        if (shared.inflight) {
            return shared.inflight.then((prior) => {
                if (prior && prior.error) {
                    return prior;
                }
                return this._saveRentalDates(false);
            });
        }
        const startEl = document.getElementById("rental-start");
        const endEl = document.getElementById("rental-end");
        const start = startEl ? startEl.value : "";
        const end = endEl ? endEl.value : "";
        // Confirmed and locked orders render the inputs disabled. Do not
        // post a save, and do not block Accept & Sign: the dates cannot
        // have changed. A request that still arrives is rejected server-side
        // and shown from data.error below.
        if ((startEl && startEl.disabled) || (endEl && endEl.disabled)) {
            this._setPriceGate("ready");
            return Promise.resolve({ success: true, unchanged: true });
        }
        const payload = rentalDatesSavePayload(start, end);
        if (!payload) {
            const verdict = validateRentalDates(start, end);
            const kind = verdict.reason === "order" ? "order" : "invalid";
            const message = this._message(kind) || kind;
            this._showError(message);
            this._setPriceGate("error");
            return Promise.resolve({ error: message });
        }
        const savedStart = payload.rental_start;
        const savedEnd = payload.rental_end;
        if (savedStart === shared.lastStart && savedEnd === shared.lastEnd) {
            this._setPriceGate("ready");
            return Promise.resolve({
                success: true,
                unchanged: true,
                amount_total: readDisplayedAmount(),
                order_amount_total: (document.querySelector("#portalTotal b") || {}).textContent || "",
            });
        }
        if (!this.orderDetail || !this.orderDetail.orderId) {
            const message = this._message("save");
            this._showError(message);
            this._setPriceGate("error");
            return Promise.resolve({ error: message });
        }
        const seq = ++shared.seq;
        this._setPriceGate("inflight");
        const promise = jsonrpc(
            "/my/orders/" + this.orderDetail.orderId + "/update_rental_dates",
            {
                access_token: this.orderDetail.token,
                rental_start: savedStart,
                rental_end: savedEnd,
            }
        ).then((data) => {
            if (seq !== shared.seq) {
                return { superseded: true };
            }
            const currentStart = document.getElementById("rental-start")?.value || "";
            const currentEnd = document.getElementById("rental-end")?.value || "";
            if (currentStart !== savedStart || currentEnd !== savedEnd) {
                // The request already stored this pair. The inputs have since
                // moved (the dates the customer is looking at). Write those
                // next, or the stored start stays on the pair that was posted.
                if (allowFollowUp) {
                    shared.inflight = null;
                    return this._saveRentalDates(false);
                }
                this._setPriceGate("error");
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
                this._setPriceGate("error");
                return { error: message };
            }
            shared.lastStart = savedStart;
            shared.lastEnd = savedEnd;
            this._clearError();
            this._applyPriceUpdate(data);
            this._setPriceGate(priceGateAfterSave(data));
            return data;
        }).catch(() => {
            if (seq !== shared.seq) {
                return { superseded: true };
            }
            const message = this._message("save");
            this._showError(message);
            this._setPriceGate("error");
            return { error: message };
        }).finally(() => {
            if (shared.inflight === promise) {
                shared.inflight = null;
            }
        });
        shared.inflight = promise;
        return promise;
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
            rememberDisplayedAmount(data.amount_total, data.order_amount_total);
        } else if (data.amount_total !== undefined && data.amount_total !== null) {
            rememberDisplayedAmount(data.amount_total, "");
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
