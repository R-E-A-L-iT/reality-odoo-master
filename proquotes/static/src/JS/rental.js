/** @odoo-module **/

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
        "change #new-address": "_newAddress",
        "change #street": "_street",
        "change #city": "_city",
        "change #zip": "_zip",
        "change #state": "_state",
        "change #country": "_country",
        "change #rental-start": "_start",
        "change #rental-end": "_end",
        // Invoice address - auto-save on each field change
        "change #invoice-name":         "_saveInvoiceAddress",
        "change #invoice-street":       "_saveInvoiceAddress",
        "change #invoice-city":         "_saveInvoiceAddress",
        "change #invoice-state-text":   "_saveInvoiceAddress",
        "change #invoice-country-text": "_saveInvoiceAddress",
        "change #invoice-zip":          "_saveInvoiceAddress",
        // Delivery address - auto-save on each field change
        "change #delivery-name":         "_saveDeliveryAddress",
        "change #delivery-street":       "_saveDeliveryAddress",
        "change #delivery-city":         "_saveDeliveryAddress",
        "change #delivery-state-text":   "_saveDeliveryAddress",
        "change #delivery-country-text": "_saveDeliveryAddress",
        "change #delivery-zip":          "_saveDeliveryAddress",
    },

    async start() {
        await this._super(...arguments);
        this.orderDetail = this.$el.find("table#sales_order_table").data();
        console.log("Started");
    },

    _newAddress: function (ev) {
        var target = ev.currentTarget;
        var newAdd = target.checked ? true : false;
        return jsonrpc("/my/orders/" + this.orderDetail.orderId + "/newAddress", {
                        "access_token": this.orderDetail.token,
                        "newAdd": newAdd,
                    });
//        return this._rpc({
//            route: "/my/orders/" + this.orderDetail.orderId + "/newAddress",
//            params: {
//                access_token: this.orderDetail.token,
//                newAdd: newAdd,
//            },
//        });
    },

    _street: function (ev) {
        var target = ev.currentTarget;
        var street = target.value;
        return jsonrpc("/my/orders/" + this.orderDetail.orderId + "/street", {
                        "access_token": this.orderDetail.token,
                        "street": street,
                    });
//        return this._rpc({
//            route: "/my/orders/" + this.orderDetail.orderId + "/street",
//            params: {
//                access_token: this.orderDetail.token,
//                street: street,
//            },
//        });
    },

    _city: function (ev) {
        var target = ev.currentTarget;
        var city = target.value;
        return jsonrpc("/my/orders/" + this.orderDetail.orderId + "/city", {
                        "access_token": this.orderDetail.token,
                        "city": city,
                    });
//        return this._rpc({
//            route: "/my/orders/" + this.orderDetail.orderId + "/city",
//            params: {
//                access_token: this.orderDetail.token,
//                city: city,
//            },
//        });
    },

    _zip: function (ev) {
        var target = ev.currentTarget;
        var zip = target.value;
        return jsonrpc("/my/orders/" + this.orderDetail.orderId + "/zip", {
                        "access_token": this.orderDetail.token,
                        "zip": zip,
                    });
//        return this._rpc({
//            route: "/my/orders/" + this.orderDetail.orderId + "/zip",
//            params: {
//                access_token: this.orderDetail.token,
//                zip: zip,
//            },
//        });
    },

    _state: function (ev) {
        var target = ev.currentTarget;
        var state = target.value;

        if (state != "Select") {
            document.getElementById("state-select").style.display = "none";
        }
        return jsonrpc("/my/orders/" + this.orderDetail.orderId + "/state", {
                        "access_token": this.orderDetail.token,
                        "state": state,
                    });
//
//        return this._rpc({
//            route: "/my/orders/" + this.orderDetail.orderId + "/state",
//            params: {
//                access_token: this.orderDetail.token,
//                state: state,
//            },
//        });
    },

    _country: function (ev) {
        var target = ev.currentTarget;
        var country = target.value;
        var iOps = undefined;
        var eOps = undefined;

        document.getElementById("state").value = "Select";
        document.getElementById("state-select").style.display = "block";

        if (country == "Canada") {
            iOps = document.getElementsByClassName("can-op");
            eOps = document.getElementsByClassName("us-op");
        } else {
            iOps = document.getElementsByClassName("us-op");
            eOps = document.getElementsByClassName("can-op");
        }

        for (var i = 0; i < iOps.length; i++) {
            iOps[i].style.display = "block";
        }

        for (var i = 0; i < eOps.length; i++) {
            eOps[i].style.display = "none";
        }
        return jsonrpc("/my/orders/" + this.orderDetail.orderId + "/country", {
                        "access_token": this.orderDetail.token,
                        "country": country,
                    });
//        return this._rpc({
//            route: "/my/orders/" + this.orderDetail.orderId + "/country",
//            params: {
//                access_token: this.orderDetail.token,
//                country: country,
//            },
//        });
    },

    _start: function (ev) {
        var target = ev.currentTarget;
        var start = target.value;
        return jsonrpc("/my/orders/" + this.orderDetail.orderId + "/start_date", {
                        "access_token": this.orderDetail.token,
                        "start": start,
                    });
//        return this._rpc({
//            route: "/my/orders/" + this.orderDetail.orderId + "/start_date",
//            params: {
//                access_token: this.orderDetail.token,
//                start: start,
//            },
//        });
    },

    _end: function (ev) {
        var target = ev.currentTarget;
        var end = target.value;
         return jsonrpc("/my/orders/" + this.orderDetail.orderId + "/end_date", {
                        "access_token": this.orderDetail.token,
                        "end": end,
                    });
//        return this._rpc({
//            route: "/my/orders/" + this.orderDetail.orderId + "/end_date",
//            params: {
//                access_token: this.orderDetail.token,
//                end: end,
//            },
//        });
    },

    _saveInvoiceAddress: function () {
        return jsonrpc("/my/orders/" + this.orderDetail.orderId + "/update_invoice_address", {
            "access_token": this.orderDetail.token,
            "name":    (document.getElementById("invoice-name") || {value: ""}).value,
            "street":  (document.getElementById("invoice-street") || {value: ""}).value,
            "city":    (document.getElementById("invoice-city") || {value: ""}).value,
            "state":   (document.getElementById("invoice-state-text") || {value: ""}).value,
            "zip":     (document.getElementById("invoice-zip") || {value: ""}).value,
            "country": (document.getElementById("invoice-country-text") || {value: ""}).value,
        });
    },

    _saveDeliveryAddress: function () {
        return jsonrpc("/my/orders/" + this.orderDetail.orderId + "/update_delivery_address", {
            "access_token": this.orderDetail.token,
            "name":    (document.getElementById("delivery-name") || {value: ""}).value,
            "street":  (document.getElementById("delivery-street") || {value: ""}).value,
            "city":    (document.getElementById("delivery-city") || {value: ""}).value,
            "state":   (document.getElementById("delivery-state-text") || {value: ""}).value,
            "zip":     (document.getElementById("delivery-zip") || {value: ""}).value,
            "country": (document.getElementById("delivery-country-text") || {value: ""}).value,
        });
    },
});
//});
