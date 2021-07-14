odoo.define('proquotes.price', function (require) {
'use strict';
var publicWidget = require('web.public.widget')

publicWidget.registry.price = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar',
    events: {
        'change .priceChange': '_updatePriceTotals',
    },
    
    async start() {
        await this._super(...arguments);
        this.orderDetail = this.$el.find('table#sales_order_table').data();
        console.log(this.orderDetail);
        this.elems = this._getUpdatableElements();
    },
    
    init: function (parent) {
        this._super(parent);
        this._onLoad();
    },
    
    _onLoad: function () {
        this._updatePriceTotals();
    },
    
    _updatePriceTotals: function () {
        //Find All Products that Might Change the Price
        var vpList = document.querySelectorAll(".priceChange");
        
        for(var i = 0; i < vpList.length; i++){
            console.log(vpList[i].checked);
        }
        console.log("Change");
        
    },
    
    _getUpdatableElements() {
        let $orderAmountUntaxed = $('[data-id="total_untaxed"]').find('span, b'),
            $orderAmountTotal = $('[data-id="total_amount"]').find('span, b'),
            $orderAmountUndiscounted = $('[data-id="amount_undiscounted"]').find('span, b');

        if (!$orderAmountUntaxed.length) {
            $orderAmountUntaxed = $orderAmountTotal.eq(1);
            $orderAmountTotal = $orderAmountTotal.eq(0).add($orderAmountTotal.eq(2));
        }

        return {
            $orderAmountUntaxed: $orderAmountUntaxed,
            $orderAmountTotal: $orderAmountTotal,
            $orderTotalsTable: $('#total'),
            $orderAmountUndiscounted: $orderAmountUndiscounted,
        };
    },
});
});
