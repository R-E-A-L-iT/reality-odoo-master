/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { SaleOrderLineListRenderer } from "@sale/js/sale_order_line_field/sale_order_line_field";

// Adds a "Make single choice" action to the section-options dropdown on the sale
// order line editor. It marks the section as single-choice and auto-selects its
// first product (server-side `action_make_single_choice`). Mirrors the pattern in
// section_translate.js (its own object literal so the super-chain stays intact).
patch(SaleOrderLineListRenderer.prototype, {
    setup() {
        super.setup();
        this.singleChoiceOrm = useService("orm");
    },

    async onMakeSingleChoice(record) {
        // Persist pending edits so the section and its product lines have database
        // ids, run the server-side initialisation, then reload the form to reflect
        // the new quantities/highlight.
        const root = record.model.root;
        await root.save();
        await this.singleChoiceOrm.call(
            "sale.order.line",
            "action_make_single_choice",
            [record.resId]
        );
        await root.load();
    },
});
