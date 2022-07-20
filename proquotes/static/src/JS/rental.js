odoo.define("proquotes.rental", function (require) {
	"use strict";
	var publicWidget = require("web.public.widget");

	publicWidget.registry.rental = publicWidget.Widget.extend({
		selector: ".o_portal_sale_sidebar",
		async start() {
			await this._super(...arguments);
			this.orderDetail = this.$el.find("table#sales_order_table").data();
		},
	});
});
