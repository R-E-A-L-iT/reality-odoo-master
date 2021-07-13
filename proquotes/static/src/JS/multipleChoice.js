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
        alert("Hello");
        var TRstyle;
        var cbl = document.querySelector(".multipleChoice");
        for(var i = 0; i < cbl.length; i++){
            var cb = cbl[i];
            var x = cb.parentNode.parentNode;
            console.log(x);
            x.style.fontFamily = "serif";
        }
    },
});
});
