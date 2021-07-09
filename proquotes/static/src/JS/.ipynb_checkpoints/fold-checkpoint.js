odoo.define('proquotes.proquotes', function (require) {
'use strict';
var publicWidget = require('web.public.widget')

publicWidget.registry.fold = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar',
    events: {
        'change .foldInput': '_onChange',
        'onLoad body':'onLoad',
    },
    init: function (parent) {
        alert("start");
        this._super(parent);
    },
    
    _onLoad: function () {
        console.log("Loaded");
    },
    _onChange: function (cb) {
        console.log(cb.currentTarget.checked)
        var TRstyle
        if(cb.currentTarget.checked){
            TRstyle = "none";
        } else {
            TRstyle = "table-row";
        }
        var x = cb.currentTarget.parentNode.parentNode;
        var y = x.nextElementSibling;
        while(y != null && y != undefined){
            if(y.className.includes("is-subtotal")){
                break;
            } else {
                if(y.style != undefined && y.style != null){
                    y.style.display = TRstyle;
                }
            }
            y = y.nextElementSibling;
        }
    },
});
});
