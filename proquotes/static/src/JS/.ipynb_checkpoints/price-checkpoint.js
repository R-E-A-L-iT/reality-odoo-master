odoo.define('proquotes.price', function (require) {
'use strict';
var publicWidget = require('web.public.widget')

publicWidget.registry.price = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar',
    events: {
        'change .priceChange': '_updatePriceTotalsEvent',
    },
    
    async start() {
        await this._super(...arguments);
        this.orderDetail = this.$el.find('table#sales_order_table').data();
        console.log(this._rpc);
        this.elems = this._getUpdatableElements();
    },
    
    init: function (parent) {
        this._super(parent);
        this._onLoad();
    },
    
    _onLoad: function () {
        //Find All Products that Might Change the Price
        var vpList = document.querySelectorAll(".priceChange");
        //this._updatePriceTotals();
    },
    
    _updatePriceTotalsEvent: function (ev) {
        ev.preventDefault();
        console.log(ev.preventDefault);
        var target = ev.currentTarget;
        var line_id = target.parentNode.parentNode.parentNode.querySelector("div").dataset["oeId"];
        console.log(target.parentNode.parentNode.parentNode.querySelector("div").dataset);

        
        
        this._rpc({
            route: "/my/orders/" + this.orderDetail.orderId + "/select/" + line_id,
            params: {access_token: this.orderDetail.token}})
        
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
