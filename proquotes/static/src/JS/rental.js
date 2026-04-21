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
        "change #rental-start": "_saveRentalDates",
        "change #rental-end": "_saveRentalDates",
        // Invoice address - auto-save on each field change
        "change #invoice-name": "_saveInvoiceAddress",
        "change #invoice-street": "_saveInvoiceAddress",
        "change #invoice-city": "_saveInvoiceAddress",
        "change #invoice-state-text": "_onInvoiceStateChange",
        "change #invoice-country-text": "_onInvoiceCountryChange",
        "change #invoice-zip": "_saveInvoiceAddress",
        // Delivery address - auto-save on each field change
        "change #delivery-name": "_saveDeliveryAddress",
        "change #delivery-street": "_saveDeliveryAddress",
        "change #delivery-city": "_saveDeliveryAddress",
        "change #delivery-state-text": "_onDeliveryStateChange",
        "change #delivery-country-text": "_onDeliveryCountryChange",
        "change #delivery-zip": "_saveDeliveryAddress",
    },

    async start() {
        await this._super(...arguments);
        this.orderDetail = this.$el.find("table#sales_order_table").data();
        this._filterStates("invoice");
        this._filterStates("delivery");
    },

    _filterStates(prefix) {
        const countrySelect = document.getElementById(`${prefix}-country-text`);
        const stateSelect = document.getElementById(`${prefix}-state-text`);
        if (!countrySelect || !stateSelect) return;
        const countryId = countrySelect.value;
        Array.from(stateSelect.options).forEach(opt => {
            if (!opt.value) return;
            opt.hidden = !!(countryId && opt.dataset.countryId != countryId);
        });
    },

    _onInvoiceCountryChange() {
        this._filterStates("invoice");
        const countryId = document.getElementById("invoice-country-text")?.value;
        const stateSelect = document.getElementById("invoice-state-text");
        const sel = stateSelect?.options[stateSelect.selectedIndex];
        if (sel?.value && countryId && sel.dataset.countryId != countryId) {
            stateSelect.value = "";
        }
        return this._saveInvoiceAddress();
    },

    _onInvoiceStateChange() {
        const stateSelect = document.getElementById("invoice-state-text");
        const sel = stateSelect?.options[stateSelect.selectedIndex];
        if (sel?.value && sel.dataset.countryId) {
            document.getElementById("invoice-country-text").value = sel.dataset.countryId;
            this._filterStates("invoice");
        }
        return this._saveInvoiceAddress();
    },

    _onDeliveryCountryChange() {
        this._filterStates("delivery");
        const countryId = document.getElementById("delivery-country-text")?.value;
        const stateSelect = document.getElementById("delivery-state-text");
        const sel = stateSelect?.options[stateSelect.selectedIndex];
        if (sel?.value && countryId && sel.dataset.countryId != countryId) {
            stateSelect.value = "";
        }
        return this._saveDeliveryAddress();
    },

    _onDeliveryStateChange() {
        const stateSelect = document.getElementById("delivery-state-text");
        const sel = stateSelect?.options[stateSelect.selectedIndex];
        if (sel?.value && sel.dataset.countryId) {
            document.getElementById("delivery-country-text").value = sel.dataset.countryId;
            this._filterStates("delivery");
        }
        return this._saveDeliveryAddress();
    },

    _saveInvoiceAddress() {
        return jsonrpc(
            "/my/orders/" + this.orderDetail.orderId + "/update_invoice_address",
            {
                access_token: this.orderDetail.token,
                name: document.getElementById("invoice-name")?.value || "",
                street: document.getElementById("invoice-street")?.value || "",
                city: document.getElementById("invoice-city")?.value || "",
                state: document.getElementById("invoice-state-text")?.value || "",
                zip: document.getElementById("invoice-zip")?.value || "",
                country: document.getElementById("invoice-country-text")?.value || "",
            }
        );
    },

    _saveDeliveryAddress() {
        return jsonrpc(
            "/my/orders/" + this.orderDetail.orderId + "/update_delivery_address",
            {
                access_token: this.orderDetail.token,
                name: document.getElementById("delivery-name")?.value || "",
                street: document.getElementById("delivery-street")?.value || "",
                city: document.getElementById("delivery-city")?.value || "",
                state: document.getElementById("delivery-state-text")?.value || "",
                zip: document.getElementById("delivery-zip")?.value || "",
                country: document.getElementById("delivery-country-text")?.value || "",
            }
        );
    },

    _saveRentalDates() {
        return jsonrpc(
            "/my/orders/" + this.orderDetail.orderId + "/update_rental_dates",
            {
                access_token: this.orderDetail.token,
                rental_start: document.getElementById("rental-start")?.value || "",
                rental_end: document.getElementById("rental-end")?.value || "",
            }
        ).then(() => {
            // After dates are saved, collect current line selection state and re-render
            // so that the Multiplier column and Amount update to reflect the new dates.
            const vpList = document.querySelectorAll(".priceChange");
            const line_ids = [];
            const targetsChecked = [];
            vpList.forEach((el) => {
                let p = el;
                while (p.tagName !== "TR") p = p.parentNode;
                targetsChecked.push(el.checked ? "true" : "false");
                line_ids.push(p.querySelector(".line_id").id);
            });
            if (!line_ids.length) return;
            return jsonrpc(
                "/my/orders/" + this.orderDetail.orderId + "/select",
                {
                    access_token: this.orderDetail.token,
                    line_ids: line_ids,
                    selected: targetsChecked,
                }
            ).then((data) => {
                if (data && data["sale_inner_template"]) {
                    this.$("#portal_sale_content").html(
                        $(data["sale_inner_template"])
                    );
                }
            });
        });
    },
});
//});
