odoo.define('proquotes.multipleChoice', function (require) {
'use strict';
var publicWidget = require('web.public.widget')

publicWidget.registry.multipleChoice = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar',
    events: {
    },
    init: function (parent) {
        this._super(parent);
        this._onLoad();
    },
    
    _onLoad: function () {
        var cbl = document.querySelectorAll(".multipleChoice");
        for(var i = 0; i < cbl.length; i++){
            var cb = cbl[i];
            var x = cb.parentNode.parentNode;
            var y = x.nextElementSibling;
            var k = 0;
            var firstChecked;
            while(y != null && y != undefined){
                if(y.className.includes("is-subtotal")){
                    break;
                } else {
                    var z = y.querySelector("input[type='radio']");
                    if(z.checked){
                        if(firstChecked == undefined || firstChecked == null){
                            firstChecked = z;
                        }
                    }
                    z.className = "priceChange";
                    z.type = "radio";
                    z.name = ("multipleChoice" + i.toString());
                    z.id = ("multipleChoice" + i.toString() + "R" + k.toString());
                    z.style.display="";
                    
                    
                    
                    var tdList = y.querySelectorAll("td");

                    for(var j = 0; j < tdList.length; j++){
                        var inner = tdList[j].innerHTML;
                        var l = document.createElement("label");
                        l.setAttribute("for", ("multipleChoice" + i.toString() + "R" + k.toString()));
                        l.style.width = "100%";
                        l.innerHTML = inner;
                        tdList[j].innerHTML = "";
                        tdList[j].append(l);
                    }
                }
            k++;
            y = y.nextElementSibling;
            }
            if(firstChecked != null || firstChecked != undefined){
                firstChecked.checked = true;
            }
        }
    },
});
});
