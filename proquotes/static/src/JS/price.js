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
        this._onLoad();
    },
    
    _onLoad: function () {
               
        this._updatePriceTotalsEvent();
    },
    
    _updatePriceTotalsEvent: function () {
        
        //Find All Products that Might Change the Price
        var vpList = document.querySelectorAll(".priceChange");
        for(var i = 0; i < vpList.length; i++){
            this._updatePriceTotals(vpList[i])
        }
        this._updateView();
    },
    
    _updatePriceTotals: function (target){
        var line_id = target.parentNode.parentNode.parentNode.querySelector("div").dataset["oeId"];        
        
        var res = this._rpc({
            route: "/my/orders/" + this.orderDetail.orderId + "/select/" + line_id,
            params: {access_token: this.orderDetail.token, 'selected': target.checked ? 'true' : 'false'}})
        console.log(this.$el.html)
    },
    
    _updateView: function () {
    
    },
});
});
