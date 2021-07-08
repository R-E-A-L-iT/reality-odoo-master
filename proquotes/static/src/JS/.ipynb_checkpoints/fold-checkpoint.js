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
        var classSearch = c.currentTarget.attributes.id.nodeValue;
        var x = document.getElementsByClassName(classSearch);
        var style;
        if(c.currentTarget.checked){
            style="none";
        } else {
            style="table-cell"
        }
        console.log(x.parentNode)
        //var y = x.parent().parent();
        /*while(y != null){
            var i = y.firstChild()
            if(i.firstChild())
            y = y.nextSibling()
        }*/
    },
});
});
