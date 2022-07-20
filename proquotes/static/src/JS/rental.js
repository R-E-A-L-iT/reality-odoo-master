odoo.define("proquotes.rental", function (require) {
	"use strict";
	var publicWidget = require("web.public.widget");

	publicWidget.registry.rental = publicWidget.Widget.extend({
		selector: ".o_portal_sale_sidebar",
		events: {
			"change #street": "_street",
			"change #city": "_city",
			"change #zip": "_zip",
			"change #rental_start": "_start",
			"change #rental_end": "_end",
			"change #insUpload": "_inssurance",
		},

		async start() {
			await this._super(...arguments);
			this.orderDetail = this.$el.find("table#sales_order_table").data();
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
