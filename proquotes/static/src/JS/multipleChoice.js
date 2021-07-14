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
                    for(var m = 0; m < y.children.length; m++){
                        var l = document.createElement("label");
                        l.setAttribute("for", ("multipleChoice" + i.toString() + "R" + k.toString()));
                        l.prepend(y.children[m]);
                        
                        y.prepend(l);
                    }
                    /*for(var j = 0; j < y.children.length; j++){
                        l.appendChild(y.children[j]);
                        console.log(y.children[j]);
                    }
                    y.children[0].prepend(l);*/
                    
                    
                }
            k++;
            y = y.nextElementSibling;
            }
        }
    },
});
});
