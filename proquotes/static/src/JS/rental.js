/** @odoo-module **/
// 2026-02-25 - Brainecrew Apps

//odoo.define("proquotes.rental", function (require) {
//  "use strict";
//  var publicWidget = require("web.public.widget");
//
import { jsonrpc } from "@web/core/network/rpc_service";
import { renderToFragment } from "@web/core/utils/render";
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
            this._btnDefaultLabel = btn.textContent.trim();
            this._btnRequestedLabel = btn.dataset.requestedLabel || "Dates requested";
        }
    },

    _onRentalDatesChanged() {
        // Changing either rental date unlocks the "Request dates" button so the
        // customer can request the newly-chosen window, then persists the dates.
        this._resetRequestButton();
        return this._saveRentalDates();
    },

    _onRequestDates(ev) {
        ev.preventDefault();
        // Optimistically lock the button, then ask the backend to post the
        // salesperson-tagged availability note. Revert if the call fails.
        this._setRequestButtonPressed();
        jsonrpc(
            "/my/orders/" + this.orderDetail.orderId + "/request_rental_dates",
            { access_token: this.orderDetail.token }
        )
            .then((res) => {
                if (!res || res.error) {
                    this._resetRequestButton();
                }
            })
            .catch(() => {
                this._resetRequestButton();
            });
    },

    _setRequestButtonPressed() {
        const btn = document.getElementById("request-dates-btn");
        if (!btn) return;
        btn.classList.add("is-requested");
        btn.setAttribute("disabled", "disabled");
        btn.setAttribute("aria-pressed", "true");
        if (this._btnRequestedLabel) {
            btn.textContent = this._btnRequestedLabel;
        }
    },

    _resetRequestButton() {
        const btn = document.getElementById("request-dates-btn");
        if (!btn) return;
        btn.classList.remove("is-requested");
        btn.removeAttribute("disabled");
        btn.setAttribute("aria-pressed", "false");
        if (this._btnDefaultLabel) {
            btn.textContent = this._btnDefaultLabel;
        }
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
//});
