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
        this._initCountryStateFilter();
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

    _initCountryStateFilter: function () {
        var pairs = [
            { country: 'invoice-country-text',  state: 'invoice-state-text'  },
            { country: 'delivery-country-text', state: 'delivery-state-text' },
        ];

        pairs.forEach(function (pair) {
            var countryEl = document.getElementById(pair.country);
            var stateEl   = document.getElementById(pair.state);
            if (!countryEl || !stateEl) return;

            // Snapshot every state option with its country association
            var allStateOptions = Array.from(stateEl.querySelectorAll('option')).map(function (opt) {
                return {
                    value:     opt.value,
                    text:      opt.text,
                    countryId: opt.getAttribute('data-country-id'),
                    selected:  opt.selected,
                };
            });

            function applyFilter() {
                var countryId     = countryEl.value;
                var currentState  = stateEl.value;

                // Rebuild the select with only matching options
                stateEl.innerHTML = '';

                var placeholder = document.createElement('option');
                placeholder.value = '';
                placeholder.text  = 'Select';
                stateEl.appendChild(placeholder);

                allStateOptions.forEach(function (optData) {
                    if (!optData.value) return; // skip original placeholder
                    if (optData.countryId !== countryId) return;
                    var opt = document.createElement('option');
                    opt.value = optData.value;
                    opt.text  = optData.text;
                    opt.setAttribute('data-country-id', optData.countryId);
                    if (optData.value === currentState) opt.selected = true;
                    stateEl.appendChild(opt);
                });
            }

            applyFilter();
            countryEl.addEventListener('change', applyFilter);
        });
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
