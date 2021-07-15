odoo.define('proquotes.optional', function (require) {
'use strict';
var publicWidget = require('web.public.widget')

publicWidget.registry.optional = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar',
    events: {
    },
    init: function (parent) {
        this._super(parent);
        this._onLoad();
    },
    
    _onLoad: function () {
        var cbl = document.querySelectorAll("input[type=checkbox].priceChange");
        for(var i = 0; i < cbl.length; i++){
            var cb = cbl[i];
            var x = cb.parentNode.parentNode;
            var y = x.nextElementSibling;
            var k = 0;
            while(y != null && y != undefined){
                if(y.className.includes("is-subtotal")){
                    break;
                } else {
                    var z = y.querySelector("input[type='radio']");
                    z.name = ("optional" + i.toString());
                    z.id = ("optional" + i.toString() + "O");
                    
                    
                    
                    var tdList = y.querySelectorAll("td");

                    for(var j = 0; j < tdList.length; j++){
                        var inner = tdList[j].innerHTML;
                        var l = document.createElement("label");
                        l.setAttribute("for", ("optional" + i.toString() + "O"));
                        l.style.width = "100%";
                        l.innerHTML = inner;
                        tdList[j].innerHTML = "";
                        tdList[j].append(l);
                    }
                }
            k++;
            y = y.nextElementSibling;
            }
        }
    },
});
});
