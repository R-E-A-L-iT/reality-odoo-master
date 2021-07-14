odoo.define('proquotes.price', function (require) {
'use strict';
var publicWidget = require('web.public.widget')

publicWidget.registry.price = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar',
    events: {
        'change .priceChange': '_updatePriceTotals',
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
});
});
