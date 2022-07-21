odoo.define("proquotes.rental", function (require) {
	"use strict";
	var publicWidget = require("web.public.widget");

	publicWidget.registry.rental = publicWidget.Widget.extend({
		selector: ".o_portal_sale_sidebar",
		events: {
			"change #new-address": "_newAddress",
			"change #street": "_street",
			"change #city": "_city",
			"change #zip": "_zip",
			"change #rental-start": "_start",
			"change #rental-end": "_end",
			"change #insUpload": "_inssurance",
		},

		async start() {
			await this._super(...arguments);
			this.orderDetail = this.$el.find("table#sales_order_table").data();
			document.getElementById("rental-address").style.display =
				document.getElementById("new-address").checked
					? "block"
					: "none";
		},

		_newAddress: function (ev) {
			var target = ev.currentTarget;
			var newAdd = target.checked ? true : false;
			document.getElementById("rental-address").style.display =
				target.checked ? "block" : "none";
			return this._rpc({
				route: "/my/orders/" + this.orderDetail.orderId + "/newAddress",
				params: {
					access_token: this.orderDetail.token,
					newAdd: newAdd,
				},
			});
		},

		_street: function (ev) {
			var target = ev.currentTarget;
			var street = target.value;
			console.log(street);
		},

		_city: function (ev) {
			var target = ev.currentTarget;
			var city = target.value;
			console.log(city);
		},

		_zip: function (ev) {
			var target = ev.currentTarget;
			var zip = target.value;
			console.log(zip);
		},

		_start: function (ev) {
			var target = ev.currentTarget;
			var start = target.value;
			console.log(start);
		},

		_end: function (ev) {
			var target = ev.currentTarget;
			var end = target.value;
			console.log(end);
		},
		_inssurance: function (ev) {
			var target = ev.currentTarget;
			var inssurance = target.files;
			console.log(inssurance);
		},
	});
});
