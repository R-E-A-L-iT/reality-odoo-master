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
    _onChange: function (cb) {
        var classSearch = cb.currentTarget.attributes.id.nodeValue;
        var x = document.getElementsByClassName(classSearch);
        var style;
        if(cb.currentTarget.checked){
            style="none";
        } else {
            style="table-cell"
        }
        console.log(cb.parentNode);
        //var y = x.parent().parent();
        /*while(y != null){
            var i = y.firstChild()
            if(i.firstChild())
            y = y.nextSibling()
        }*/
    },
});
});
