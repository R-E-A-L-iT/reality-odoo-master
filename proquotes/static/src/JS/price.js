/** @odoo-module **/

//odoo.define("proquotes.price", function (require) {
//	"use strict";

import { jsonrpc } from "@web/core/network/rpc_service";
import { renderToFragment } from "@web/core/utils/render";
import publicWidget from "@web/legacy/js/public/public_widget";

//	var publicWidget = require("web.public.widget");

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
			this.orderDetail = this.$el.find("table#sales_order_table").data();
			this._onLoad();
			await this._super(...arguments);
		},

		_onLoad: function () {
			this._updatePriceTotalsEvent();
			this._rentalValueTotal();
		},

		_updateQuantityEvent: function (t) {
            setTimeout(() => {
			//Update Quantity for Product
    			let self = this;
    			var target = t.currentTarget;
    			var p = target;
    			while (p.tagName != "TR") {
    				p = p.parentNode;
    			}

                var closestChecked = target.closest('.quoteLineRow');
                var checkbox = closestChecked.querySelector('.priceChange');

                // if (checkbox.checked === true) {
                    // Log the checkbox checked state
                var lineId = p.querySelector(".line_id").id;
                var qty = Math.round(target.value);
                //			return this._rpc({
                //				route: "/my/orders/" + this.orderDetail.orderId + "/changeQuantity/" + lineId,
                //				params: {
                //					access_token: this.orderDetail.token,
                //					line_id: lineId,
                //					quantity: qty,
                //				},
                //			})
                return jsonrpc("/my/orders/" + this.orderDetail.orderId + "/changeQuantity/" + lineId, {
                        "access_token": this.orderDetail.token,
                        "line_id": lineId,
                        "quantity": qty,
                    },
                ).then((data) => {
                    if (data) {
                        self.$("#portal_sale_content").html(
                            $(data["sale_inner_template"])
                        );
                        this._updateView(data["order_amount_total"]);
                    }
                });
            }, 800);

		},

		_updatePriceTotalsEvent: function (ev) {
            setTimeout(() => {
    			//Find All Products that Might Change the Price
                // var $link = $(ev.currentTarget);
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
             }, 800);
		},


		_rentalValueTotal: function () {
			const totalLandingEnglish = document.getElementById("total-rental-value-english");
			const totalLandingFrench  = document.getElementById("total-rental-value-french");

			// robust number parser from a node's text
			const toNumber = (node) => {
				if (!node) return 0;
				const raw = (node.textContent || "").replace(/\u00A0/g, ""); // NBSP
				const cleaned = raw.replace(/[^0-9.-]/g, ""); // keep digits, dot, minus
				const n = Number(cleaned);
				return Number.isFinite(n) ? n : 0;
			};

			// prefer .oe_currency_value if present (Odoo), else whole node text
			const getDailyPrice = (rateNode) => {
				if (!rateNode) return 0;
				// If your markup ever sets data-daily, prefer it:
				const dataDaily = rateNode.getAttribute && rateNode.getAttribute("data-daily");
				if (dataDaily) {
					const n = Number(String(dataDaily).replace(/[^0-9.-]/g, ""));
					if (Number.isFinite(n)) return n;
				}
				const currencyNode = rateNode.querySelector && rateNode.querySelector(".oe_currency_value");
				let price = toNumber(currencyNode || rateNode);
				return Number.isFinite(price) ? price : 0;
			};

			// exact cap rule: 30-day blocks = 12×daily; 7-day blocks = 4×daily; leftover days min(days×daily, 4×daily)
			const chargeForDays = (days, daily) => {
				if (!daily || days <= 0) return 0;
				let remaining = Math.floor(days);
				let total = 0;

				while (remaining >= 30) { total += 12 * daily; remaining -= 30; }
				while (remaining >= 7)  { total +=  4 * daily; remaining -= 7;  }

				// leftover (0..6) days capped at 4×daily
				total += Math.min(remaining * daily, 4 * daily);
				return total;
			};

			// ---- 1) Sum of selected line "itemValue" (unchanged logic, but safer parsing)
			let total = 0;
			const rows = document.getElementsByClassName("quoteLineRow");
			for (let i = 0; i < rows.length; i++) {
				const row = rows[i];
				const checkbox = row.querySelector('input[type="checkbox"]');
				if (checkbox && !checkbox.checked) continue;

				const valueNode = row.getElementsByClassName("itemValue")[0];
				total += toNumber(valueNode);
			}

			if (totalLandingEnglish) {
				totalLandingEnglish.textContent = '$ ' + Intl.NumberFormat('en-US', { style: "decimal", minimumFractionDigits: 2 }).format(total);
			}
			if (totalLandingFrench) {
				totalLandingFrench.textContent = Intl.NumberFormat('en-US', { style: "decimal", minimumFractionDigits: 2 }).format(total) + ' $';
			}

			// ---- 2) Rental estimate using tiered caps
			const rentalEstimateEnglish = document.getElementById("rental-estimate-total-english");
			const rentalEstimateFrench  = document.getElementById("rental-estimate-total-french");
			const startDateEl = document.getElementById("rental-start");
			const endDateEl = document.getElementById("rental-end");

			if (!rentalEstimateEnglish && !rentalEstimateFrench) return;

			if (!startDateEl || !endDateEl || !startDateEl.value || !endDateEl.value) {
				if (rentalEstimateEnglish) rentalEstimateEnglish.textContent = "$ 0.00";
				if (rentalEstimateFrench)  rentalEstimateFrench.textContent  = "0.00 $";
				return;
			}

			// timezone-safe day count (ignore time-of-day/DST)
			const vStart = startDateEl.valueAsDate || new Date(startDateEl.value);
			const vEnd = endDateEl.valueAsDate   || new Date(endDateEl.value);
			const startUTC = Date.UTC(vStart.getFullYear(), vStart.getMonth(), vStart.getDate());
			const endUTC = Date.UTC(vEnd.getFullYear(), vEnd.getMonth(), vEnd.getDate());
			const dayMs = 24 * 60 * 60 * 1000;

			let durationDays = Math.floor((endUTC - startUTC) / dayMs) + 1; // inclusive
			if (!Number.isFinite(durationDays) || durationDays < 0) durationDays = 0;

			// Sum each selected line's daily rate with the capped formula
			let rentalEstimateTotal = 0;
			const rates = document.getElementsByClassName("rental_rate_calc");
			for (let i = 0; i < rates.length; i++) {
				const rateNode = rates[i];
				const row = rateNode.closest(".quoteLineRow") || rateNode.parentNode;
				const checkbox = row ? row.querySelector('input[type="checkbox"]') : null;
				if (checkbox && !checkbox.checked) continue;

				const dailyPrice = getDailyPrice(rateNode); // DAILY rate expected here
				if (!dailyPrice) continue;

				rentalEstimateTotal += chargeForDays(durationDays, dailyPrice);
			}

			if (rentalEstimateEnglish) {
				rentalEstimateEnglish.textContent = '$ ' + Intl.NumberFormat('en-US', { style: "decimal", minimumFractionDigits: 2 }).format(rentalEstimateTotal);
			}
			if (rentalEstimateFrench) {
				rentalEstimateFrench.textContent = Intl.NumberFormat('en-US', { style: "decimal", minimumFractionDigits: 2 }).format(rentalEstimateTotal) + ' $';
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

//			return this._rpc({
//				route:
//					"/my/orders/" + this.orderDetail.orderId + "/sectionSelect",
//				params: {
//					access_token: this.orderDetail.token,
//					section_id: section_id,
//					line_ids: line_ids,
//					selected: checked,
//				},
//			})
            return jsonrpc("/my/orders/" + this.orderDetail.orderId + "/sectionSelect", {
					access_token: this.orderDetail.token,
					'section_id': section_id,
					'line_ids': line_ids,
					'selected': checked
				}
			).then((data) => {
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
            //            return this._rpc({
            //				route: "/my/orders/" + this.orderDetail.orderId + "/select",
            //				params: {
            //					access_token: this.orderDetail.token,
            //					line_ids: line_ids,
            //					selected: targetsChecked,
            //				},
            //			})
            return jsonrpc("/my/orders/" + this.orderDetail.orderId + "/select", {
					'access_token': this.orderDetail.token,
					'line_ids': line_ids,
					'selected': targetsChecked
				}
			).then((data) => {
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
			for (var i = 0; i < cbl.length; i++) {
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
						}
					}
					y = y.nextElementSibling;
				}
			}
			var subTotalList = document.getElementsByClassName(
				"subtotal-destination"
			);
            console.log("PRICE.JS subTotalList", subTotalList)
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
             // Get all spans with the class 'is-section-subtotal'
            document.querySelectorAll('span.is-section-subtotal').forEach(function(subtotalSpan) {
                // Get the section_id and amount from the current span
                var sectionId = subtotalSpan.getAttribute('data-section_id');
                var amount = $(subtotalSpan).text();  // Get the inner HTML (amount) of the current span

                // Find the span with class 'subtotal-destination-span' that matches the current section_id
                var destinationSpan =
                    document.querySelector('span.subtotal-destination-span[data-section_id="' + sectionId + '"]');
                // If the destination span exists, update its inner HTML with the amount
                if (destinationSpan) {
                    destinationSpan.innerHTML = amount;
                }
            });
		},

		_updateView: function (total) {
			this._multipleChoiceView();
			this._optionalView();
			this._updateFoldDisplay();
			this._rentalValueTotal();
			this._updateTotal(total);
		},
	});
//});
