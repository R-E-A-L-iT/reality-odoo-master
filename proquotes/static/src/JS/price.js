odoo.define("proquotes.price", function (require) {
	"use strict";
	var publicWidget = require("web.public.widget");

	publicWidget.registry.price = publicWidget.Widget.extend({
		selector: ".o_portal_sale_sidebar",
		events: {
			"change .optionalSectionCheckbox": "_updateSectionSelectionEvent",
			"change .priceChange": "_updatePriceTotalsEvent",
			"change .quantityChange": "_updateQuantityEvent",
			"change #rental-start": "_updatePriceTotalsEvent",
			"change #rental-end": "_updatePriceTotalsEvent",
		},

		async start() {
			console.log("Start");
			this.orderDetail = this.$el.find("table#sales_order_table").data();
			this._onLoad();
			await this._super(...arguments);
		},

		_onLoad: function () {
			console.log("load");
			this._updatePriceTotalsEvent();
			this._rentalValueTotal();
		},

		_updateQuantityEvent: function (t) {
			//Update Quantity for Product
			let self = this;
			var target = t.currentTarget;
			var p = target;
			while (p.tagName != "TR") {
				p = p.parentNode;
			}
			var lineId = p.querySelector(".line_id").id;
			var qty = Math.round(target.value);
			return this._rpc({
				route: "/my/orders/" + this.orderDetail.orderId + "/changeQuantity/" + lineId,
				params: {
					access_token: this.orderDetail.token,
					line_id: lineId,
					quantity: qty,
				},
			}).then((data) => {
				if (data) {
					self.$("#portal_sale_content").html(
						$(data["sale_inner_template"])
					);
					this._updateView(data["order_amount_total"]);
				}
			});
		},

		_updatePriceTotalsEvent: function () {
			//Find All Products that Might Change the Price
			let self = this;
			var vpList = document.querySelectorAll(".priceChange");
			var result = null;
			var line_ids = [];
			var targetsChecked = [];
			for (var i = 0; i < vpList.length; i++) {
				var p = vpList[i];
				while (p.tagName != "TR") {
					p = p.parentNode;
				}
				targetsChecked.push(
					vpList[i].checked == true ? "true" : "false"
				);
				line_ids.push(p.querySelector(".line_id").id);
			}
			this._updatePriceTotals(targetsChecked, line_ids);
		},

		_rentalValueTotal: function () {
			var totalLandingEnglish = document.getElementById("total-rental-value-english");
			var totalLandingFrench = document.getElementById("total-rental-value-french");
			if (totalLandingEnglish == undefined && totalLandingFrench == undefined) {
				return;
			}
			var total = 0;
			var items = document.getElementsByClassName("quoteLineRow");
			for (var i = 0; i < items.length; i++) {
				var input = items[i].getElementsByTagName("input");
				var include = true;
				if (input.length > 0) {
					if (input[0].type == "checkbox") {
						if (input[0].checked != true) {
							include = false;
						}
					}
				}

				if (include) {
					if (
						items[i].getElementsByClassName("itemValue").length > 0
					) {
						total += parseInt(
							items[i].getElementsByClassName("itemValue")[0]
								.innerHTML.replace(",", "").replace("$", "").replace(" ", "")
						);
					}
				}
			}
			if (totalLandingEnglish != undefined) {
				totalLandingEnglish.innerHTML = '$ ' + Intl.NumberFormat('en-US', { style: "decimal", minimumFractionDigits: 2 }).format(total);
			}

			if (totalLandingFrench != undefined) {
				totalLandingFrench.innerHTML = Intl.NumberFormat('en-US', { style: "decimal", minimumFractionDigits: 2 }).format(total) + ' $';
			}

			var rentalEstimateEnglish = document.getElementById("rental-estimate-total-english")
			var rentalEstimateFrench = document.getElementById("rental-estimate-total-french")
			var startDate = document.getElementById("rental-start");
			var endDate = document.getElementById("rental-end");

			if (rentalEstimateEnglish == undefined && rentalEstimateFrench == undefined) {
				return;
			}

			if (startDate.value == "" || endDate.value == "") {
				if (rentalEstimateEnglish != undefined) {
					rentalEstimateEnglish.innerHTML = "$ 0.00"
				} else if (rentalEstimateFrench != undefined) {
					rentalEstimateFrench.innerHTML = "0.00 $"
				}
				return;
			}

			// var startDateDate = new Date(startDate.value);
			// var endDateDate = new Date(endDate.value);
			//
			// let milliInSeconds = 1000
			// let secondsInMinute = 60
			// let minuteInHour = 60
			// let hourInDay = 24
			// var rentalLength = (endDateDate.getTime() - startDateDate.getTime()) / (milliInSeconds * secondsInMinute * minuteInHour * hourInDay);
			// var months = 0;
			// var weeks = 0;
			// var days = 0;
			//
			// while (rentalLength >= 30) {
			// 	months += 1
			// 	rentalLength -= 30;
			// }
			// while (rentalLength >= 7) {
			// 	weeks += 1
			// 	rentalLength -= 7
			// }
			// while (rentalLength >= 1) {
			// 	days += 1;
			// 	rentalLength -= 1;
			// }

			var rentalEstimateTotal = 0
			var productPrices = document.getElementsByClassName("rental_rate_calc")

			for (var i = 0; i < productPrices.length; i++) {
				var node = productPrices[i]
				while (node.classList.contains("quoteLineRow") == false) {
					node = node.parentNode;
				}
				var inputs = node.getElementsByTagName("input");
				if (inputs.length > 0) {
					if (inputs[0].type == "checkbox") {
						if (inputs[0].checked != true) {
							continue;
						}
					}
				}
				//console.log(productPrices[i])
				// var price = productPrices[i].innerHTML.replace(",", "").replace("$", "").replace(" ", "");
				// console.log("Rental Estimate Total" + rentalEstimateTotal)
				// var rentalEstimateSubTotal = 0;
				// rentalEstimateSubTotal += 1 * days * price;
				// if(rentalEstimateSubTotal > 4 * price) {
				// 	console.log(rentalEstimateSubTotal)
				// 	console.log(price * 4)
				// 	rentalEstimateSubTotal = 4 * price
				// }
				// rentalEstimateSubTotal += 4 * weeks * price;
				// if(rentalEstimateSubTotal > 12 * price) {
				// 	console.log(rentalEstimateSubTotal)
				// 	console.log(price * 12)
				// 	rentalEstimateSubTotal = 12 * price
				// }
				// rentalEstimateSubTotal += 12 * months * price;
				//rentalEstimateTotal += rentalEstimateSubTotal
				rentalEstimateTotal = productPrices[i].innerHTML.replace(",", "").replace("$", "").replace(" ", "")
			}
			if (rentalEstimateEnglish != undefined) {
				rentalEstimateEnglish.innerHTML = '$ ' + Intl.NumberFormat('en-US', { style: "decimal", minimumFractionDigits: 2 }).format(rentalEstimateTotal);
			} else if (rentalEstimateFrench != undefined) {
				rentalEstimateFrench.innerHTML = Intl.NumberFormat('en-US', { style: "decimal", minimumFractionDigits: 2 }).format(rentalEstimateTotal) + ' $';
			}
		},

		_updateSectionSelectionEvent: function (ev) {
			var target = ev.currentTarget;
			var checked = target.checked;
			var p = target;
			var line_ids = [];
			while (p.tagName != "TR") {
				p = p.parentNode;
			}
			var y = p.nextElementSibling;
			var section_id = p.querySelector(".line_id").id;
			while (y != null && y != undefined) {
				if (y.className.includes("is-subtotal")) {
					break;
				}
				line_ids.push(y.querySelector(".line_id").id);
				y = y.nextElementSibling;
			}
			let self = this;

			return this._rpc({
				route:
					"/my/orders/" + this.orderDetail.orderId + "/sectionSelect",
				params: {
					access_token: this.orderDetail.token,
					section_id: section_id,
					line_ids: line_ids,
					selected: checked,
				},
			}).then((data) => {
				if (data) {
					self.$("#portal_sale_content").html(
						$(data["sale_inner_template"])
					);
					this._updateView(data["order_amount_total"]);
				}
			});
		},

		_updatePriceTotals: function (targetsChecked, line_ids) {
			let self = this;

			return this._rpc({
				route: "/my/orders/" + this.orderDetail.orderId + "/select",
				params: {
					access_token: this.orderDetail.token,
					line_ids: line_ids,
					selected: targetsChecked,
				},
			}).then((data) => {
				if (data) {
					self.$("#portal_sale_content").html(
						$(data["sale_inner_template"])
					);
					this._updateView(data["order_amount_total"]);
				}
			});
		},

		_multipleChoiceView: function () {
			var cbl = document.querySelectorAll(".multipleChoice");
			console.log("Multiple");
			for (var i = 0; i < cbl.length; i++) {
				console.log(cbl[i]);
				var cb = cbl[i];
				var x = cb;
				while (x.tagName != "TR") {
					x = x.parentNode;
				}
				var y = x.nextElementSibling;
				var k = 0;
				var firstChecked = null;
				while (y != null && y != undefined) {
					if (y.className.includes("is-subtotal")) {
						break;
					} else {
						var z = y.querySelector("input[type='radio']");
						if (z == undefined) {
							if (
								y.querySelector("input[type='checkbox']") ==
								undefined
							) {
								y = y.nextElementSibling;
								continue;
							} else {
								break;
							}
						}
						if (z.checked) {
							if (firstChecked == null) {
								firstChecked =
									"multipleChoice" +
									i.toString() +
									"R" +
									k.toString();
							}
						}
						z.className = "priceChange";
						z.name = "multipleChoice" + i.toString();
						z.id =
							"multipleChoice" +
							i.toString() +
							"R" +
							k.toString();
						z.style.display = "";

						var tdList = y.querySelectorAll("td");

						for (var j = 0; j < tdList.length; j++) {
							console.log(tdList[j])
							var inner = tdList[j].innerHTML;
							var l = document.createElement("label");
							l.setAttribute(
								"for",
								"multipleChoice" +
								i.toString() +
								"R" +
								k.toString()
							);
							l.style.width = "100%";
							l.innerHTML = inner;
							tdList[j].innerHTML = "";
							tdList[j].append(l);
						}
					}
					k++;
					y = y.nextElementSibling;
				}
				if (firstChecked != null) {
					document.getElementById(firstChecked).checked = true;
				}
			}
		},

		_optionalView: function () {
			var cbl = document.querySelectorAll(
				"input[type=checkbox].priceChange"
			);
			for (var i = 0; i < cbl.length; i++) {
				var cb = cbl[i];
				var row = cb.parentNode.parentNode;
				cb.name = "optional" + i.toString();
				cb.id = "optional" + i.toString() + "O";

				var tdList = row.querySelectorAll("td");

				for (var j = 0; j < tdList.length; j++) {
					var inner = tdList[j].innerHTML;
					var l = document.createElement("label");
					l.setAttribute("for", "optional" + i.toString() + "O");
					l.style.width = "100%";
					l.innerHTML = inner;
					tdList[j].innerHTML = "";
					tdList[j].append(l);
				}
			}
		},

		_updateFoldDisplay: function () {
			var TRstyle;
			var expandHTML;
			var cbl = document.querySelectorAll(".foldInput");
			for (var i = 0; i < cbl.length; i++) {
				var cb = cbl[i];

				if (cb.checked == true) {
					console.log(cb);
					TRstyle = "none";
					expandHTML = "+";
				} else {
					TRstyle = "table-row";
					expandHTML = "&#215;";
				}
				var x = cb;
				while (x.tagName != "TR") {
					x = x.parentNode;
				}
				x.querySelector(".quote-folding-arrow").innerHTML = expandHTML;
				var y = x.nextElementSibling;
				while (y != null && y != undefined) {
					if (y.className.includes("is-subtotal")) {
						break;
					} else {
						if (y.style != undefined && y.style != null) {
							y.style.display = TRstyle;
							console.log(y.style.display);
						}
					}
					y = y.nextElementSibling;
				}
			}
			var subTotalList = document.getElementsByClassName(
				"subtotal-destination"
			);

			for (var i = 0; i < subTotalList.length; i++) {
				var subTotal = subTotalList[i];
				var inner_html = ""
				var subtotal_source = document.getElementsByClassName("subtotal-source")
				if(subtotal_source.length > i){
					inner_html = subtotal_source[i].innerHTML;
				}
				subTotal.innerHTML = inner_html;
			}
		},

		_updateTotal: function (total) {
			var div = document.querySelector("#portalTotal b");
			if (div != null) {
				document.querySelector("#portalTotal b").innerHTML = total;
			}
		},

		_updateView: function (total) {
			console.log("view");
			this._multipleChoiceView();
			this._optionalView();
			this._updateFoldDisplay();
			this._rentalValueTotal();
			this._updateTotal(total);
		},

		// _testCommOdoo: function(orderId, startDate, endDate) {
		// 	var rpc = require('web.rpc');		
		// 	rpc.query({		
		// 		model: 'sale.order',		
		// 		method: 'odoo_test_comm',
		// 		args: [{
		// 			'orderId': orderId,
		// 			'p_startDateValue': startDate,
		// 			'p_endDateValue': endDate
		// 		}]
		//
		// 	}).then(function (data) {		
		// 		console.log(data);		
		// 	});
		//
		// }		
	});
});
