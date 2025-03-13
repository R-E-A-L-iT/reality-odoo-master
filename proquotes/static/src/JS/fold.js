/** @odoo-module **/
import { jsonrpc } from "@web/core/network/rpc_service";
import { renderToFragment } from "@web/core/utils/render";
import publicWidget from "@web/legacy/js/public/public_widget";

// odoo.define('proquotes.fold', function (require) {
// 	'use strict';
// 	var publicWidget = require('web.public.widget')

publicWidget.registry.fold = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar',
    events: {
        'change .foldInput': '_onChange',
        'change .product_foldI': '_productFoldChange',
    },

    async start() {
        await this._super(...arguments);
        this.orderDetail = this.$el.find('table#sales_order_table').data();
        this._onLoad();
    },

    _onLoad: function () {
        var TRstyle;
        var expandHTML;
        var cbl = document.querySelectorAll(".foldInput");
        for (var i = 0; i < cbl.length; i++) {
            var cb = cbl[i];
            console.log('---ccccbbbbb----')
            if (cb.checked == true) {
                console.log(cb);
                TRstyle = "none";
                expandHTML = "+";
            } else {
                TRstyle = "table-row";
                expandHTML = "&#215;";
            }
            var x = cb;
            while (x.tagName != "TR") {
                x = x.parentNode;
            }
            x.querySelector('.quote-folding-arrow').innerHTML = expandHTML;
            var y = x.nextElementSibling;
            while (y != null && y != undefined) {
                if (y.className.includes("is-subtotal")) {
                    break;
                } else {
                    if (y.style != undefined && y.style != null) {
                        y.style.display = TRstyle;
                        console.log(y.style.display);
                    }
                }
                y = y.nextElementSibling;
            }
        }
        var subTotalList = document.getElementsByClassName("subtotal-destination");
        for (var i = 0; i < subTotalList.length; i++) {
            var subTotal = subTotalList[i];
            var source = document.getElementsByClassName("subtotal-source")[i]
            if(source != undefined){
                subTotal.innerHTML = source.innerHTML;
            } else {
                subTotal.innerHTML = '';
            }
        }
    },
    _onChange: function (cb) {
        var TRstyle;
        var expandHTML;
        if (cb.currentTarget.checked == true) {
            TRstyle = "none";
            expandHTML = "+";
        } else {
            TRstyle = "table-row";
            expandHTML = "&#215;";
        }
        var x = cb.currentTarget;
        console.log('---xxxxxxx----', x)
        while (x.tagName != "TR") {
            x = x.parentNode;
        }
        x.querySelector('.quote-folding-arrow').innerHTML = expandHTML;
        var y = x.nextElementSibling;
        while (y != null && y != undefined) {
            if (y.className.includes("is-subtotal")) {
                break;
            } else if (y.style != undefined && y.style != null) {
                y.style.display = TRstyle;
            }
            y = y.nextElementSibling;
        }
        this._saveFoldStatus(cb.currentTarget);
    },

    _productFoldChange: function (cb) {
        this._saveFoldStatus(cb.currentTarget);
    },

    _saveFoldStatus: function (target) {
        var p = target;
        while (p.tagName != "TR") {
            p = p.parentNode
        }
        var s = p.querySelector(".line_id").id;
        return jsonrpc("/my/orders/" + this.orderDetail.orderId + "/fold/" + s, {
            "access_token": this.orderDetail.token,
            "checked": target.checked ,
        });
        // return this._rpc({
        //     route: "/my/orders/" + this.orderDetail.orderId + "/fold/" + s,
        //     params: {
        //         access_token: this.orderDetail.token,
        //         checked: target.checked
        //     }
        // });
    },
});
// });
