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
    },

    _onRentalDatesChanged() {
        // Changing either rental date unlocks the "Request dates" button so the
        // customer can request the newly-chosen window, then persists the dates.
        this._resetRequestButton();
        return this._saveRentalDates();
    },

    _onRequestDates(ev) {
        ev.preventDefault();
        // No backend action yet — just lock the button into its pressed state.
        // It stays pressed/disabled until a rental date changes.
        this._setRequestButtonPressed();
    },

    _setRequestButtonPressed() {
        const btn = document.getElementById("request-dates-btn");
        if (!btn) return;
        btn.classList.add("is-requested");
        btn.setAttribute("disabled", "disabled");
        btn.setAttribute("aria-pressed", "true");
    },

    _resetRequestButton() {
        const btn = document.getElementById("request-dates-btn");
        if (!btn) return;
        btn.classList.remove("is-requested");
        btn.removeAttribute("disabled");
        btn.setAttribute("aria-pressed", "false");
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
