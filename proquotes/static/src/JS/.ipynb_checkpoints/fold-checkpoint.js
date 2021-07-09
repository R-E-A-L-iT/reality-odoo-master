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
        this._onLoad();
    },
    
    _onLoad: function () {
        var TRstyle;
        var cbl = document.getElementsByClassName("foldInput");
        for(var i = 0; i < cbl.length; i++){
            var cb = cbl[i];
            if(cb.checked){
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
            var sourceRow = document.getElementsByClassName("is-subtotal")[i];
            console.log(sourceRow);
            var sourceCell = sourceRow.childNodes[0];
            console.log(sourceCell);
            var sourceSpan = sourceCell.childNodes[1];
            console.log(sourceSpan);
            //subTotal.innerHTML = sourceSpan.innerHTML;
            
        }
    },
    _onChange: function (cb) {
        var TRstyle;
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
