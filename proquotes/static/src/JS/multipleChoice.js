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
        var TRstyle;
        var cbl = document.querySelectorAll(".multipleChoice");
        for(var i = 0; i < cbl.length; i++){
            var cb = cbl[i];
            var x = cb.parentNode.parentNode;
            var y = x.nextElementSibling;
            var k = 0;
            while(y != null && y != undefined){
                if(y.className.includes("is-subtotal")){
                    break;
                } else {
                    var z = document.createElement("input");
                    z.type = "radio";
                    z.name = ("multipleChoice" + i.toString());
                    z.id = ("multipleChoice" + i.toString() + "R" + k.toString());
                    
                    
                    
                    if(y.children.length > 0){
                        y.children[0].prepend(z);
                    }
                    var spanList = y.getElementsByTagName("SPAN, DIV");
                    for(var j = 0; j < spanList.length; j++){
                        console.log(spanList[j].parentNode);
                        var l = document.createElement("label")
                        spanList[0].parentNode.append(l);
                        l.setAttribute("for", ("multipleChoice" + i.toString() + "R" + k.toString()));
                        l.append(spanList[j])
                    }
                }
            k++;
            y = y.nextElementSibling;
            }
        }
    },
});
});
