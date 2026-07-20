/** @odoo-module **/
import { rpc } from "@web/core/network/rpc";
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
        var cbl = document.querySelectorAll(".foldInput");
        for (var i = 0; i < cbl.length; i++) {
            var cb = cbl[i];
            if (cb.checked == true) {
                TRstyle = "none";
            } else {
                TRstyle = "table-row";
            }
            var x = cb;
            while (x.tagName != "TR") {
                x = x.parentNode;
            }
            var icon = x.querySelector('.quote-folding-icon');
            if (icon) {
                icon.classList.toggle('is-open', cb.checked == false);
            }
            var y = x.nextElementSibling;
            while (y != null && y != undefined) {
                if (y.className.includes("is-subtotal") || y.className.includes("quoteLineRowSection")) {
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
        if (cb.currentTarget.checked == true) {
            TRstyle = "none";
        } else {
            TRstyle = "table-row";
        }
        var x = cb.currentTarget;
        while (x.tagName != "TR") {
            x = x.parentNode;
        }
        var icon = x.querySelector('.quote-folding-icon');
        if (icon) {
            icon.classList.toggle('is-open', cb.currentTarget.checked == false);
        }
        var y = x.nextElementSibling;
        while (y != null && y != undefined) {
            if (y.className.includes("is-subtotal") || y.className.includes("quoteLineRowSection")) {
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
        return rpc("/my/orders/" + this.orderDetail.orderId + "/fold/" + s, {
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
