var Widget = require(web.widget)

var Counter = Widget.extend({
    template: 'some.template',
    events: {
        'fold': '_onClick',
    },
    init: function (parent, value) {
        this._super(parent);
        this.count = value;
    },
    _onChange: function () {
        alert("Clicked");
    },
});