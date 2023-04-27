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
		},

		async start() {
			await this._super(...arguments);
			this.orderDetail = this.$el.find("table#sales_order_table").data();
			console.log("Started");
		},

		_newAddress: function (ev) {
			var target = ev.currentTarget;
			var newAdd = target.checked ? true : false;
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

			if (state != "Select") {
				document.getElementById("state-select").style.display = "none";
			}

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
			var iOps = undefined;
			var eOps = undefined;

			document.getElementById("state").value = "Select";
			document.getElementById("state-select").style.display = "block";

			if (country == "Canada") {
				iOps = document.getElementsByClassName("can-op");
				eOps = document.getElementsByClassName("us-op");
			} else {
				iOps = document.getElementsByClassName("us-op");
				eOps = document.getElementsByClassName("can-op");
			}

			for (var i = 0; i < iOps.length; i++) {
				iOps[i].style.display = "block";
			}

			for (var i = 0; i < eOps.length; i++) {
				eOps[i].style.display = "none";
			}
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
	});
});
