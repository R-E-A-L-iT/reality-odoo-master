odoo.define('proquotes.proquotes', function (require) {
'use strict';
var publicWidget = require('web.public.widget')

publicWidget.registry.fold = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar',
    events: {
        'change .foldInput': '_onChange',
    },
    init: function (parent) {
        this._super(parent);
    },
    _onChange: function (cb) {
        var classSearch = cb.currentTarget.attributes.id.nodeValue;
        var style;
        if(cb.currentTarget.checked){
            style="none";
        } else {
            style="table-cell"
        }
        alert("click");
        var x = cb.currentTarget.parentNode.parentNode;
        console.log(x);
        var y = x.nextSibling;
        console.log(y);
        while(y != null && y != undefined){
            if(y.class=="is-subtotal"){
                break;
            } else {
                y.style.display = style;
            }
            y = y.nextSibling;
            console.log(y);
        }
    },
});
});
