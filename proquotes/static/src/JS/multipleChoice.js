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
                    
                    
                    var l = document.createElement("label");
                    l.for = ("multipleChoice" + i.toString() + "R" + k.toString());
                    l.style.backgroundColor = "red";
                    l.style.display = "inline-block";
                    l.style.width = "100%";
                    l.style.height = "50px";
                    y.childNodes[1].prepend(l);
                    y.childNodes[1].prepend(z);
                    
                    
                }
            k++;
            y = y.nextElementSibling;
            }
        }
    },
});
});
