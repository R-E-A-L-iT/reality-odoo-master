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
        var TDstyle;
        var DIVstyle;
        var TRstyle
        if(cb.currentTarget.checked){
            TDstyle="none";
            DIVstyle = "none";
            TRstyle = "none";
        } else {
            TDstyle="table-cell";
            DIVstyle = "block";
            TRstyle = "table-row";
        }
        var x = cb.currentTarget.parentNode.parentNode;
        var y = x.nextElementSibling;
        while(y != null && y != undefined){
            if(y.className.includes("is-subtotal")){
                break;
            } else {
                console.log(y.style);
                if(y.style != undefined && y.style != null){
                    y.style.display = TRstyle;
                }
                var z = y.childNodes
                for(var i = 0; i < z.length; i++){
                    if(z[i].tagName == "TD"){
                        z[i].style.display = TDstyle;
                        var w = z[i].childNodes;
                        if(w != undefined && w != null){
                            for(var j = 0; j < w.length; j++){
                                if(w[j].tagName == "DIV"){
                                    w[j].style.display = DIVstyle;
                                }
                            }
                        }
                    }
                }
            }
            y = y.nextElementSibling;
            
        }
    },
});
});
