odoo.define("proquotes.ponumber", function (require) {
	"use strict";
	var publicWidget = require("web.public.widget");

	publicWidget.registry.ponumber = publicWidget.Widget.extend({
		selector: ".o_portal_sale_sidebar",
		events: {
			"change .poNumber": "_update_po_number",
			"change #poFile": "_update_po_file",
		},

		async start() {
			await this._super(...arguments);
			this.orderDetail = this.$el.find("table#sales_order_table").data();
		},

		_update_po_number: function (ev) {
			var target = ev.currentTarget;
			var poNumber = target.value;
			return this._rpc({
				route: "/my/orders/" + this.orderDetail.orderId + "/ponumber",
				params: {
					access_token: this.orderDetail.token,
					ponumber: poNumber,
				},
			});
		},

		_update_po_file: function (ev) {
			var target = ev.currentTarget;
			var poFile = target.files;
			reader = FileReader();
			return this._rpc({
				route: "/my/orders/" + this.orderDetail.orderId + "/poFile",
				params: {
					access_token: this.orderDetail.token,
					poFile: reader.readAsBinaryString(poFile[0]),
				},
			});
		},
	});
});
