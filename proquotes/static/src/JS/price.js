odoo.define('proquotes.price', function (require) {
'use strict';
var publicWidget = require('web.public.widget')

publicWidget.registry.price = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar',
    events: {
        'click .priceChange': '_updatePriceTotals',
    },
    init: function (parent) {
        this._super(parent);
        this._onLoad();
    },
    
    _onLoad: function () {
        this._updatePriceTotals();
    },
    
    _updatePriceTotals: function () {
        alert("Price Total Changed");
        console.log("Change");
        
    },
});
});
