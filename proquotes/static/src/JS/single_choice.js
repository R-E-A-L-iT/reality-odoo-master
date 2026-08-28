/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { SaleOrderLineListRenderer } from "@sale/js/sale_order_line_field/sale_order_line_field";
import { SaleOrderTemplateLineListRenderer } from "@sale_management/fields/sale_order_template_line_field/sale_order_template_line_field";

// Adds a "Set/Unset Single Choice" action to the section-options dropdown, on BOTH
// the sale order line editor and the quotation TEMPLATE line editor — the template
// editor is a different renderer/template pair, so patching only the order one (as
// this file used to) left the item missing entirely on quotation templates.
//
// NOTE: each patch() call needs its OWN object literal — Odoo's patch reparents the
// patch object's prototype so `super` resolves, so sharing one object across two
// patch() calls corrupts the super-chain of whichever class was patched first. Hence
// the factory (same rule as section_translate.js). The getters must also be written
// directly in the literal: defining them via Object.defineProperties would strip
// their [[HomeObject]] and break `super`.
function makeSingleChoicePatch() {
    return {
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
            // Persist pending edits so the section and its product lines have
            // database ids, run the server-side set/unset, then reload the form.
            const root = record.model.root;
            await root.save();
            const method = record.data.x_single_choice
                ? "action_unset_single_choice"
                : "action_make_single_choice";
            // Derived from the record rather than hardcoded, so the same handler
            // drives sale.order.line and sale.order.template.line.
            await this.singleChoiceOrm.call(record.resModel, method, [record.resId]);
            await root.load();
        },

        async onToggleOptional(record) {
            // Custom "Set/Unset Optional" for SUBSECTIONS. Native optional is only
            // offered on top-level sections. Blocked on a single-choice line (the two
            // modes are mutually exclusive).
            if (record.data.x_single_choice) {
                return;
            }
            const root = record.model.root;
            await root.save();
            const method = record.data.is_optional
                ? "action_unset_optional"
                : "action_make_optional";
            await this.singleChoiceOrm.call(record.resModel, method, [record.resId]);
            await root.load();
        },

        // Grey out the price/composition collapse actions on a single-choice section,
        // matching how native optional sections disable the same two items. These
        // getters drive the `disabled` class via `attrs`, so no template change is
        // needed. On the template renderer the parent defines no such getters, so
        // `super.X` is simply undefined and these fall through harmlessly.
        get disablePricesButton() {
            return super.disablePricesButton || !!this.record?.data?.x_single_choice;
        },

        get disableCompositionButton() {
            return super.disableCompositionButton || !!this.record?.data?.x_single_choice;
        },

        // Grey out the native "Set Optional" item on a single-choice section (the two
        // modes are mutually exclusive).
        get disableOptionalButton() {
            return super.disableOptionalButton || !!this.record?.data?.x_single_choice;
        },
    };
}

patch(SaleOrderLineListRenderer.prototype, makeSingleChoicePatch());
patch(SaleOrderTemplateLineListRenderer.prototype, makeSingleChoicePatch());
