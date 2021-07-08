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
        var y = x.nextElementSibling;
        while(y != null && y != undefined){
            if(y.class=="is-subtotal"){
                break;
            } else {
                var z = y.childNodes
                for(var i = 0; i < z.length; i++){
                    if(z[i].type == 1){
                        z[i].style.display = style;                        
                    }
                }
            }
            y = y.nextElementSibling;
            console.log(y);
        }
    },
});
});
