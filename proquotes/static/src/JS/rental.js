/** @odoo-module **/
// 2026-02-25 - Brainecrew Apps

import { jsonrpc } from "@web/core/network/rpc_service";
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.rental = publicWidget.Widget.extend({
    selector: ".o_portal_sale_sidebar",
    events: {
        "change #rental-start": "_onRentalDatesChanged",
        "change #rental-end": "_onRentalDatesChanged",
        "click #request-dates-btn": "_onRequestDates",
    },

    async start() {
        await this._super(...arguments);
        this.orderDetail = this.$el.find("table#sales_order_table").data();

        const btn = document.getElementById("request-dates-btn");
        if (btn) {
            // Server-provided state so the button survives page reloads.
            this.reqState = btn.dataset.requestState || "none";
            this.reqStart = btn.dataset.requestedStart || "";
            this.reqEnd = btn.dataset.requestedEnd || "";
            this.labels = {
                request: btn.dataset.labelRequest || "Request dates",
                requested: btn.dataset.labelRequested || "Dates requested",
                update: btn.dataset.labelUpdate || "Update request",
            };
            this._refreshRequestButton();
        }
    },

    _curDates() {
        return {
            start: document.getElementById("rental-start")?.value || "",
            end: document.getElementById("rental-end")?.value || "",
        };
    },

    // Decide the button's label / pressed / disabled state from the request
    // state and whether the current dates still match the requested ones.
    _refreshRequestButton() {
        const btn = document.getElementById("request-dates-btn");
        if (!btn) return;
        const { start, end } = this._curDates();
        const pendingUnchanged =
            this.reqState === "pending" && start === this.reqStart && end === this.reqEnd;

        if (pendingUnchanged) {
            // Requested and not since changed → locked in the pressed state.
            btn.classList.add("is-requested");
            btn.setAttribute("disabled", "disabled");
            btn.setAttribute("aria-pressed", "true");
            btn.textContent = this.labels.requested;
        } else if (this.reqState === "pending") {
            // Pending but dates were changed → offer to update the request.
            btn.classList.remove("is-requested");
            btn.removeAttribute("disabled");
            btn.setAttribute("aria-pressed", "false");
            btn.textContent = this.labels.update;
        } else {
            // No request, or already answered → a fresh request can be made.
            btn.classList.remove("is-requested");
            btn.removeAttribute("disabled");
            btn.setAttribute("aria-pressed", "false");
            btn.textContent = this.labels.request;
        }
    },

    _onRentalDatesChanged() {
        // Persist the new dates, then re-evaluate the button (may flip to
        // "Update request" if a request is already pending).
        this._saveRentalDates();
        this._refreshRequestButton();
    },

    _onRequestDates(ev) {
        ev.preventDefault();
        const btn = document.getElementById("request-dates-btn");
        if (!btn || btn.hasAttribute("disabled")) return;

        // Optimistically lock the button while the request is in flight.
        btn.setAttribute("disabled", "disabled");
        jsonrpc(
            "/my/orders/" + this.orderDetail.orderId + "/request_rental_dates",
            { access_token: this.orderDetail.token }
        )
            .then((res) => {
                if (res && res.success) {
                    const { start, end } = this._curDates();
                    this.reqState = "pending";
                    this.reqStart = start;
                    this.reqEnd = end;
                }
                this._refreshRequestButton();
            })
            .catch(() => {
                this._refreshRequestButton();
            });
    },

    _saveRentalDates() {
        return jsonrpc(
            "/my/orders/" + this.orderDetail.orderId + "/update_rental_dates",
            {
                access_token: this.orderDetail.token,
                rental_start: document.getElementById("rental-start")?.value || "",
                rental_end: document.getElementById("rental-end")?.value || "",
            }
        );
    },
});
