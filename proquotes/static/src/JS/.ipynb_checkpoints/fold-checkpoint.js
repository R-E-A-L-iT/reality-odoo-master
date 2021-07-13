odoo.define('proquotes.fold', function (require) {
'use strict';
var publicWidget = require('web.public.widget')

publicWidget.registry.fold = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar',
    events: {
        'change .foldInput': '_onChange',
    },
    init: function (parent) {
        this._super(parent);
        this._onLoad();
    },
    
    _onLoad: function () {
        var TRstyle;
        var cbl = document.querySelectorAll(".foldInput");
        for(var i = 0; i < cbl.length; i++){
            var cb = cbl[i];
            if(cb.checked == "true"){
                TRstyle = "none";
            } else {
                TRstyle = "table-row";
            }
            var x = cb.parentNode.parentNode;
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
        }
        var subTotalList = document.getElementsByClassName("subtotal-destination");
        for(var i = 0; i < subTotalList.length; i++){
            var subTotal = subTotalList[i];
            subTotal.innerHTML = document.getElementsByClassName("subtotal-source")[i].innerHTML;
            
        }
    },
    _onChange: function (cb) {
        var TRstyle;
        if(cb.currentTarget.checked == "true"){
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
