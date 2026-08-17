/** @odoo-module **/

//odoo.define("proquotes.price", function (require) {
//	"use strict";

import { rpc } from "@web/core/network/rpc";
import { renderToFragment } from "@web/core/utils/render";
import publicWidget from "@web/legacy/js/public/public_widget";

//	var publicWidget = require("web.public.widget");

	publicWidget.registry.price = publicWidget.Widget.extend({
		selector: ".o_portal_sale_sidebar",
		events: {
			"change .quantityChange": "_updateQuantityEvent",
			"change .singleChoiceRadio": "_singleChoiceSelectEvent",
			"change .optionalCheckbox": "_optionalSelectEvent",
			"change #rental-start": "_updatePriceTotalsEvent",
			"change #rental-end": "_updatePriceTotalsEvent",
		},

		async start() {
			this.orderDetail = this.$el.find("table#sales_order_table").data();
			// Get order state from table data attribute
			const table = document.getElementById('sales_order_table');
			this.orderState = table ? table.getAttribute('data-order-state') : null;
			console.log('Order state:', this.orderState);
			this._onLoad();
			await this._super(...arguments);
		},

		_isOrderLocked: function () {
			// Check if order is in a locked state (confirmed, done, or cancelled)
			return this.orderState === 'sale' || this.orderState === 'done' || this.orderState === 'cancel';
		},

		_onLoad: function () {
			this._updatePriceTotalsEvent();
			this._rentalValueTotal();
			this._revealSkeletons();
		},

		// Hide each product-image shimmer once its thumbnail has loaded (add the
		// .loaded class). Runs on initial load and after any partial re-render, and
		// handles already-cached images that won't fire a fresh load event.
		_revealSkeletons: function () {
			document.querySelectorAll(".img-skeleton").forEach(function (sk) {
				var img = sk.querySelector("img");
				if (!img) {
					sk.classList.add("loaded");
					return;
				}
				if (img.complete && img.naturalHeight !== 0) {
					sk.classList.add("loaded");
				} else {
					var done = function () { sk.classList.add("loaded"); };
					img.addEventListener("load", done, { once: true });
					img.addEventListener("error", done, { once: true });
				}
			});
		},

		_updateQuantityEvent: function (t) {
			// Check if order is locked before processing
			if (this._isOrderLocked()) {
				console.log('Order is locked - quantity changes not allowed');
				return;
			}

            setTimeout(() => {
			//Update Quantity for Product
    			let self = this;
    			var target = t.currentTarget;
    			var p = target;
    			while (p.tagName != "TR") {
    				p = p.parentNode;
    			}

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
                return rpc("/my/orders/" + this.orderDetail.orderId + "/changeQuantity/" + lineId, {
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
            }, 300);

		},

		_updatePriceTotalsEvent: function (ev) {
			// Now only used to refresh the rental value/estimate totals when the
			// rental dates change (line selection was removed).
			this._rentalValueTotal();
		},

		// Single-choice section: picking a product's radio selects it (qty 1). The
		// server-side write() rule zeroes the other members of the section, so one
		// changeQuantity call fully switches the selection; then we re-render.
		_singleChoiceSelectEvent: function (ev) {
			if (this._isOrderLocked()) {
				return;
			}
			let self = this;
			var radio = ev.currentTarget;
			var groupName = radio.getAttribute("name");

			// Optimistic feedback: immediately dim the now-unselected members and
			// un-dim the chosen one, so the switch feels instant. The RPC below
			// persists it (the server zeroes the section's other members) and the
			// re-render reconciles quantities/subtotals.
			document.querySelectorAll(".singleChoiceRadio").forEach(function (r) {
				if (r.getAttribute("name") !== groupName) {
					return;
				}
				var tr = r;
				while (tr && tr.tagName != "TR") {
					tr = tr.parentNode;
				}
				var info = tr ? tr.querySelector(".single-choice-info") : null;
				if (info) {
					info.classList.toggle("single-choice-unselected", r !== radio);
				}
			});

			var p = radio;
			while (p.tagName != "TR") {
				p = p.parentNode;
			}
			var lineId = p.querySelector(".line_id").id.replace(/\D/g, "");
			return rpc("/my/orders/" + this.orderDetail.orderId + "/singleChoiceSelect/" + lineId, {
				"access_token": this.orderDetail.token,
				"line_id": lineId,
			}).then((data) => {
				if (data && data.single_choice) {
					self._applySingleChoiceUpdate(data);
				}
			});
		},

		// Apply the single-choice selection result (JSON) to just the affected
		// rows + totals, instead of re-rendering the whole quote.
		_applySingleChoiceUpdate: function (data) {
			var self = this;
			(data.lines || []).forEach(function (ld) {
				var tr = self._findRowByLineId(ld.id);
				if (!tr) {
					return;
				}
				// Quantity cell: input only when selected and unlocked.
				var qtyBox = tr.querySelector(".quote_qty");
				if (qtyBox) {
					if (!ld.selected) {
						qtyBox.innerHTML = '<span class="qtySpan">0</span>';
					} else if (ld.locked) {
						qtyBox.innerHTML = '<span class="qtySpan">' + ld.qty + "</span>";
					} else {
						qtyBox.innerHTML =
							'<input type="number" class="quantityChange" min="1" value="' +
							ld.qty + '" style="display: inline; width: 60px;"/>';
					}
				}
				// Line amount.
				var sub = tr.querySelector(".proquotesLineTotal");
				if (sub) {
					sub.textContent = ld.subtotal;
				}
				// Radio + dimming.
				var radio = tr.querySelector(".singleChoiceRadio");
				if (radio) {
					radio.checked = ld.selected;
				}
				var info = tr.querySelector(".single-choice-info");
				if (info) {
					info.classList.toggle("single-choice-unselected", !ld.selected);
				}
			});
			// Section subtotal.
			if (data.section_id) {
				var secSpan = document.querySelector(
					'span[data-section_id="' + data.section_id + '"]'
				);
				if (secSpan) {
					secSpan.textContent = data.section_subtotal;
				}
			}
			// Totals table (Untaxed / taxes / Total): swap in the freshly rendered
			// fragment so the bottom totals reflect the new selection.
			if (data.totals_html) {
				var totalDiv = document.querySelector("#total");
				if (totalDiv) {
					totalDiv.innerHTML =
						'<div class="col-xs-7 col-md-5 ms-auto">' + data.totals_html + "</div>";
				}
			}
			// Sidebar total + rental estimate.
			this._updateTotal(data.amount_total);
			this._rentalValueTotal();
		},

		_findRowByLineId: function (lineId) {
			var els = document.querySelectorAll(".line_id");
			for (var i = 0; i < els.length; i++) {
				if ((els[i].id || "").replace(/\D/g, "") === String(lineId)) {
					var tr = els[i];
					while (tr && tr.tagName != "TR") {
						tr = tr.parentNode;
					}
					return tr;
				}
			}
			return null;
		},

		// Optional section: ticking a product's checkbox selects it (real qty set
		// to its preset, min 1); unticking drops the real qty to 0. Each line is
		// independent, so — unlike single choice — no siblings are affected. The
		// server does the write and returns just the changed numbers.
		_optionalSelectEvent: function (ev) {
			if (this._isOrderLocked()) {
				return;
			}
			let self = this;
			var checkbox = ev.currentTarget;

			// Optimistic feedback: dim/un-dim the row's product info immediately so
			// the toggle feels instant; the RPC + partial re-render reconcile it.
			var tr = checkbox;
			while (tr && tr.tagName != "TR") {
				tr = tr.parentNode;
			}
			var info = tr ? tr.querySelector(".optional-info") : null;
			if (info) {
				info.classList.toggle("optional-unselected", !checkbox.checked);
			}

			var lineId = tr.querySelector(".line_id").id.replace(/\D/g, "");
			return rpc("/my/orders/" + this.orderDetail.orderId + "/optionalSelect/" + lineId, {
				"access_token": this.orderDetail.token,
				"line_id": lineId,
				"select": checkbox.checked,
			}).then((data) => {
				if (data && data.optional) {
					self._applyOptionalUpdate(data);
				}
			});
		},

		// Apply the optional-select result (JSON) to just the toggled row + totals,
		// instead of re-rendering the whole quote. Parallels _applySingleChoiceUpdate,
		// but the unselected quantity cell shows the PRESET (what the line would be
		// if selected), not 0.
		_applyOptionalUpdate: function (data) {
			var ld = data.line;
			if (!ld) {
				return;
			}
			var tr = this._findRowByLineId(ld.id);
			if (tr) {
				// Quantity cell: editable input only when selected and unlocked;
				// preset (greyed) when unselected.
				var qtyBox = tr.querySelector(".quote_qty");
				if (qtyBox) {
					if (!ld.selected) {
						qtyBox.innerHTML = '<span class="qtySpan">' + ld.preset + "</span>";
					} else if (ld.locked) {
						qtyBox.innerHTML = '<span class="qtySpan">' + ld.qty + "</span>";
					} else {
						qtyBox.innerHTML =
							'<input type="number" class="quantityChange" min="1" value="' +
							ld.qty + '" style="display: inline; width: 60px;"/>';
					}
				}
				// Line amount.
				var sub = tr.querySelector(".proquotesLineTotal");
				if (sub) {
					sub.textContent = ld.subtotal;
				}
				// Checkbox + dimming.
				var checkbox = tr.querySelector(".optionalCheckbox");
				if (checkbox) {
					checkbox.checked = ld.selected;
				}
				var info = tr.querySelector(".optional-info");
				if (info) {
					info.classList.toggle("optional-unselected", !ld.selected);
				}
			}
			// Section subtotal.
			if (data.section_id) {
				var secSpan = document.querySelector(
					'span[data-section_id="' + data.section_id + '"]'
				);
				if (secSpan) {
					secSpan.textContent = data.section_subtotal;
				}
			}
			// Totals table (Untaxed / taxes / Total).
			if (data.totals_html) {
				var totalDiv = document.querySelector("#total");
				if (totalDiv) {
					totalDiv.innerHTML =
						'<div class="col-xs-7 col-md-5 ms-auto">' + data.totals_html + "</div>";
				}
			}
			// Sidebar total + rental estimate.
			this._updateTotal(data.amount_total);
			this._rentalValueTotal();
		},


		_rentalValueTotal: function () {
			const text = (el) => el ? (el.textContent || el.innerText || el.innerHTML || "") : "";

			const normalizeNumeric = (s) => {
				let raw = String(s).trim().replace(/\u00A0/g, "");
				raw = raw.replace(/[^\d,.\-]/g, "");

				const comma = raw.indexOf(",") !== -1;
				const dot   = raw.indexOf(".") !== -1;

				if (comma && dot) {
					if (raw.lastIndexOf(",") > raw.lastIndexOf(".")) {
						raw = raw.replace(/\./g, "").replace(",", ".");
					} else {
						raw = raw.replace(/,/g, "");
					}
				} else if (comma && !dot) {
					raw = raw.replace(",", ".");
				}
				return raw;
			};

			const toIntOr0 = (s) => {
				const n = parseInt(normalizeNumeric(s), 10);
				return Number.isFinite(n) ? n : 0;
			};
			const toNumOr0 = (s) => {
				const n = Number(normalizeNumeric(s));
				return Number.isFinite(n) ? n : 0;
			};

			// NEW: get quantity from the current quote line row
			const getLineQty = (rowEl) => {
				if (!rowEl) return 1;

				// 1) Editable quantity input
				const qtyInput = rowEl.querySelector("input.quantityChange[type='number']");
				if (qtyInput) {
					let qty = toNumOr0(qtyInput.value);
					qty = Math.round(qty);
					if (!Number.isFinite(qty) || qty <= 0) qty = 1;
					return qty;
				}

				// 2) Locked quantity span
				const qtySpan = rowEl.querySelector("span.qtySpan");
				if (qtySpan) {
					let qty = toNumOr0(text(qtySpan));
					qty = Math.round(qty);
					if (!Number.isFinite(qty) || qty <= 0) qty = 1;
					return qty;
				}

				// Fallback
				return 1;
			};

			var totalLandingEnglish = document.getElementById("total-rental-value-english");
			var totalLandingFrench  = document.getElementById("total-rental-value-french");
			if (totalLandingEnglish == undefined && totalLandingFrench == undefined) {
				return;
			}

			// TOTAL RENTAL VALUE (now quantity-aware)
			var total = 0;
			var items = document.getElementsByClassName("quoteLineRow");
			for (var i = 0; i < items.length; i++) {
				var vals = items[i].getElementsByClassName("itemValue");
				if (vals.length > 0) {
					total += toIntOr0(text(vals[0])) * getLineQty(items[i]);
				}
			}

			if (totalLandingEnglish != undefined) {
				totalLandingEnglish.innerHTML =
					'$ ' + Intl.NumberFormat('en-US', { style: "decimal", minimumFractionDigits: 2 }).format(total);
			}
			if (totalLandingFrench != undefined) {
				totalLandingFrench.innerHTML =
					Intl.NumberFormat('en-US', { style: "decimal", minimumFractionDigits: 2 }).format(total) + ' $';
			}

			var rentalEstimateEnglish = document.getElementById("rental-estimate-total-english");
			var rentalEstimateFrench  = document.getElementById("rental-estimate-total-french");
			var startDate = document.getElementById("rental-start");
			var endDate   = document.getElementById("rental-end");

			if (rentalEstimateEnglish == undefined && rentalEstimateFrench == undefined) {
				return;
			}

			if (!startDate || !endDate || startDate.value == "" || endDate.value == "") {
				if (rentalEstimateEnglish != undefined) {
					rentalEstimateEnglish.innerHTML = "$ 0.00";
				} else if (rentalEstimateFrench != undefined) {
					rentalEstimateFrench.innerHTML = "0.00 $";
				}
				return;
			}

			var startDateDate = new Date(startDate.value);
			var endDateDate   = new Date(endDate.value);
			if (!Number.isFinite(startDateDate.getTime()) || !Number.isFinite(endDateDate.getTime())) {
				if (rentalEstimateEnglish != undefined) {
					rentalEstimateEnglish.innerHTML = "$ 0.00";
				} else if (rentalEstimateFrench != undefined) {
					rentalEstimateFrench.innerHTML = "0.00 $";
				}
				return;
			}

			let milliInSeconds = 1000, secondsInMinute = 60, minuteInHour = 60, hourInDay = 24;
			var rentalLength = Math.max(1, (endDateDate.getTime() - startDateDate.getTime()) / (milliInSeconds * secondsInMinute * minuteInHour * hourInDay));
			if (!Number.isFinite(rentalLength)) rentalLength = 1;

			var months = 0, weeks = 0, days = 0;
			while (rentalLength >= 30) { months += 1; rentalLength -= 30; }
			while (rentalLength >= 7)  { weeks  += 1; rentalLength -= 7;  }
			while (rentalLength >= 1)  { days   += 1; rentalLength -= 1;  }

			// RENTAL ESTIMATE (now quantity-aware)
			var rentalEstimateTotal = 0;
			var productPrices = document.getElementsByClassName("rental_rate_calc");
			for (var j = 0; j < productPrices.length; j++) {
				var price = toNumOr0(text(productPrices[j])); // value shown on the line

				var rentalEstimateSubTotal = 0;

				// so do NOT multiply again by qty here.
				rentalEstimateSubTotal += 1 * days * price;
				if (rentalEstimateSubTotal > 4 * price) {
					rentalEstimateSubTotal = 4 * price;
				}
				rentalEstimateSubTotal += 4 * weeks * price;
				if (rentalEstimateSubTotal > 12 * price) {
					rentalEstimateSubTotal = 12 * price;
				}
				rentalEstimateSubTotal += 12 * months * price;

				rentalEstimateTotal += rentalEstimateSubTotal;
			}

			if (rentalEstimateEnglish != undefined) {
				rentalEstimateEnglish.innerHTML =
					'$ ' + Intl.NumberFormat('en-US', { style: "decimal", minimumFractionDigits: 2 }).format(rentalEstimateTotal);
			} else if (rentalEstimateFrench != undefined) {
				rentalEstimateFrench.innerHTML =
					Intl.NumberFormat('en-US', { style: "decimal", minimumFractionDigits: 2 }).format(rentalEstimateTotal) + ' $';
			}
		},

		_updateFoldDisplay: function () {
			var TRstyle;
			var cbl = document.querySelectorAll(".foldInput");
			for (var i = 0; i < cbl.length; i++) {
				var cb = cbl[i];

				if (cb.checked == true) {
					TRstyle = "none";
				} else {
					TRstyle = "table-row";
				}
				var x = cb;
				while (x.tagName != "TR") {
					x = x.parentNode;
				}
				var icon = x.querySelector(".quote-folding-icon");
				if (icon) {
					icon.classList.toggle("is-open", cb.checked == false);
				}
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
			this._updateFoldDisplay();
			this._rentalValueTotal();
			this._updateTotal(total);
			this._revealSkeletons();
		},
	});
//});
