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
			"change #state": "_state",
			"change #country": "_country",
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
			return this._rpc({
				route: "/my/orders/" + this.orderDetail.orderId + "/street",
				params: {
					access_token: this.orderDetail.token,
					street: street,
				},
			});
		},

		_city: function (ev) {
			var target = ev.currentTarget;
			var city = target.value;
			return this._rpc({
				route: "/my/orders/" + this.orderDetail.orderId + "/city",
				params: {
					access_token: this.orderDetail.token,
					city: city,
				},
			});
		},

		_zip: function (ev) {
			var target = ev.currentTarget;
			var zip = target.value;
			return this._rpc({
				route: "/my/orders/" + this.orderDetail.orderId + "/zip",
				params: {
					access_token: this.orderDetail.token,
					zip: zip,
				},
			});
		},

		_state: function (ev) {
			var target = ev.currentTarget;
			var state = target.value;
			return this._rpc({
				route: "/my/orders/" + this.orderDetail.orderId + "/state",
				params: {
					access_token: this.orderDetail.token,
					state: state,
				},
			});
		},

		_country: function (ev) {
			var target = ev.currentTarget;
			var country = target.value;
			return this._rpc({
				route: "/my/orders/" + this.orderDetail.orderId + "/country",
				params: {
					access_token: this.orderDetail.token,
					country: country,
				},
			});
		},

		_start: function (ev) {
			var target = ev.currentTarget;
			var start = target.value;
			return this._rpc({
				route: "/my/orders/" + this.orderDetail.orderId + "/start_date",
				params: {
					access_token: this.orderDetail.token,
					start: start,
				},
			});
		},

		_end: function (ev) {
			var target = ev.currentTarget;
			var end = target.value;
			return this._rpc({
				route: "/my/orders/" + this.orderDetail.orderId + "/end_date",
				params: {
					access_token: this.orderDetail.token,
					end: end,
				},
			});
		},
		_inssurance: function (ev) {
			var target = ev.currentTarget;
			var inssurance = target.files;
			console.log(inssurance);
		},
	});
});
