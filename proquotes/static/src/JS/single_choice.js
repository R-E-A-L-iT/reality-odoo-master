/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { SaleOrderLineListRenderer } from "@sale/js/sale_order_line_field/sale_order_line_field";

// Adds a "Set/Unset Single Choice" action to the section-options dropdown on the
// sale order line editor, and greys out the Hide Prices/Hide Composition items for
// single-choice sections (same way the native optional sections disable them).
// Mirrors the pattern in section_translate.js (its own object literal so the
// super-chain stays intact).
patch(SaleOrderLineListRenderer.prototype, {
    setup() {
        super.setup();
        this.singleChoiceOrm = useService("orm");
    },

    async onToggleSingleChoice(record) {
        // Mutually exclusive with the native optional mode: block setting single
        // choice on an optional section (the item is greyed for that case too).
        if (record.data.is_optional && !record.data.x_single_choice) {
            return;
        }
        // Persist pending edits so the section and its product lines have database
        // ids, run the server-side set/unset, then reload the form to reflect the
        // new quantities/highlight.
        const root = record.model.root;
        await root.save();
        const method = record.data.x_single_choice
            ? "action_unset_single_choice"
            : "action_make_single_choice";
        await this.singleChoiceOrm.call("sale.order.line", method, [record.resId]);
        await root.load();
    },

    // Disable (grey out) the price/composition collapse actions on a single-choice
    // section — hiding prices/composition doesn't apply there, matching how the
    // native optional sections disable these same two items. These getters drive
    // the `disabled` class on the collapse DropdownItems (via `attrs`), so no
    // template change is needed.
    get disablePricesButton() {
        return super.disablePricesButton || !!this.record?.data?.x_single_choice;
    },

    get disableCompositionButton() {
        return super.disableCompositionButton || !!this.record?.data?.x_single_choice;
    },

    // Grey out the native "Set Optional" item on a single-choice section (the two
    // modes are mutually exclusive). The native item already binds its disabled
    // class to this getter, so overriding it is all that's needed.
    get disableOptionalButton() {
        return super.disableOptionalButton || !!this.record?.data?.x_single_choice;
    },
});
