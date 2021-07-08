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
    _onChange: function (c) {
        if(true){        
            var classSearch = c.currentTarget.attributes.id.nodeValue;
            var x = document.getElementsByClassName(classSearch);
            for(var i = 0; i < x.length; i++){
                x[i].style.display = "none";
            }
        }
    },
});
});
