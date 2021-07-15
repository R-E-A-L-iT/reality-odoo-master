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
        let self = this;       
        var vpList = document.querySelectorAll(".priceChange");
        for(var i = 0; i < vpList.length; i++){
            self._updatePriceTotals(vpList[i])
        }
    },
    
    _updatePriceTotalsEvent: function () {
        
        //Find All Products that Might Change the Price
        let self = this;
        var vpList = document.querySelectorAll(".priceChange");
        var result;
        for(var i = 0; i < vpList.length; i++){
            result = self._updatePriceTotals(vpList[i]);
        }
        if(result){
            self.$('#portal_sale_content').html($(result['sale_template']));
        }
        //this._updateView();
    },
    
    _updatePriceTotals: function (target){
        let self = this;
        var line_id = target.parentNode.parentNode.parentNode.querySelector("div").dataset["oeId"];        
        
        return this._rpc({
            route: "/my/orders/" + this.orderDetail.orderId + "/select/" + line_id,
            params: {access_token: this.orderDetail.token, 'selected': target.checked ? 'true' : 'false'}});
    },
    
    _updateView: function () {
        //location.reload();
    },
});
});
