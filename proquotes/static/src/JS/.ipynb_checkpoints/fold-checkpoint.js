odoo.define('proquotes.proquotes', function (require) {
'use strict';
var publicWidget = require(web.publicWidget)

publicWidget.registry.fold = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar',
    events: {
        'click .fold': '_onChange',
    },
    init: function (parent, value) {ss
        this._super(parent);
        this.count = value;
    },
    _onChange: function () {
        alert("Clicked");
    },
});
});