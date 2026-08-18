/** @odoo-module **/
// 2026-02-25 - Brainecrew Apps

//odoo.define("proquotes.rental", function (require) {
//  "use strict";
//  var publicWidget = require("web.public.widget");
//
import publicWidget from "@web/legacy/js/public/public_widget";

// NOTE: rental date saving now lives in price.js (_updateRentalDatesEvent), which
// persists the dates AND re-renders the quote so recalculated prices show instantly.
// This widget no longer binds the date inputs to avoid a duplicate save RPC.
publicWidget.registry.rental = publicWidget.Widget.extend({
    selector: ".o_portal_sale_sidebar",
    events: {},

    async start() {
        await this._super(...arguments);
        this.orderDetail = this.$el.find("table#sales_order_table").data();
    },
});
//});
