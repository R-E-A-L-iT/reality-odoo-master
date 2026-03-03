/** @odoo-module **/
// 2026-02-25 - Brainecrew Apps

//odoo.define("proquotes.rental", function (require) {
//	"use strict";
//	var publicWidget = require("web.public.widget");
//
import { jsonrpc } from "@web/core/network/rpc_service";
import { renderToFragment } from "@web/core/utils/render";
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.rental = publicWidget.Widget.extend({
    selector: ".o_portal_sale_sidebar",
    events: {
        // Invoice address - auto-save on each field change
        "change #invoice-name": "_saveInvoiceAddress",
        "change #invoice-street": "_saveInvoiceAddress",
        "change #invoice-city": "_saveInvoiceAddress",
        "change #invoice-state-text": "_saveInvoiceAddress",
        "change #invoice-country-text": "_saveInvoiceAddress",
        "change #invoice-zip": "_saveInvoiceAddress",
        // Delivery address - auto-save on each field change
        "change #delivery-name": "_saveDeliveryAddress",
        "change #delivery-street": "_saveDeliveryAddress",
        "change #delivery-city": "_saveDeliveryAddress",
        "change #delivery-state-text": "_saveDeliveryAddress",
        "change #delivery-country-text": "_saveDeliveryAddress",
        "change #delivery-zip": "_saveDeliveryAddress",
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
});
//});
