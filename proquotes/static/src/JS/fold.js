var Widget = require(web.widget)

var fold = Widget.extend({
    template: 'proquotes.sale_order_portal_content',
    events: {
        'change .fold': '_onChange',
    },
    init: function (parent, value) {
        this._super(parent);
        this.count = value;
    },
    _onChange: function () {
        alert("Clicked");
    },
});
