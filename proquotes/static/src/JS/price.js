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
        
        //Find All Products that Might Change the Price
        this._updatePriceTotalsEvent();
    },
    
    _updatePriceTotalsEvent: function () {
        
        //Find All Products that Might Change the Price
        let self = this;
        var vpList = document.querySelectorAll(".priceChange");
        var result = null;
        var line_ids = [];
        for(var i = 0; i < vpList.length; i++){
            line_ids.push(vpList[i].parentNode.parentNode.parentNode.querySelector("div").dataset["oeId"]);
        }
        this._updatePriceTotals(vpList, line_ids);
    },
    
    _updatePriceTotals: function (targets, line_ids){
        let self = this;
        
        return this._rpc({
            route: "/my/orders/" + this.orderDetail.orderId + "/select",
            params: {access_token: this.orderDetail.token, line_ids: line_ids,'selected': targets}}).then((data) => {
            if (data) {
                self.$('#portal_sale_content').html($(data['sale_template']));
            }
        });
    },
    
    _updateView: function () {
        //location.reload();
    },
});
});
