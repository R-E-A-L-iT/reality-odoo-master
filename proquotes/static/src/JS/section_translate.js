/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { SaleOrderLineListRenderer } from "@sale/js/sale_order_line_field/sale_order_line_field";
import { SaleOrderTemplateLineListRenderer } from "@sale_management/fields/sale_order_template_line_field/sale_order_template_line_field";

/**
 * Dialog listing every installed language with an input for the section title in
 * that language. Saves the map onto the line's ``section_name_translations`` Json
 * field (and mirrors the current-language value onto ``name``).
 */
export class SectionTranslateDialog extends Component {
    static template = "proquotes.SectionTranslateDialog";
    static components = { Dialog };
    static props = {
        record: Object,
        langs: Array,
        close: Function,
    };

    setup() {
        const translations = this.props.record.data.section_name_translations || {};
        const baseName = this.props.record.data.name || "";
        this._baseName = baseName;
        this.state = useState({
            values: Object.fromEntries(
                this.props.langs.map((l) => [
                    l.code,
                    translations[l.code] || (l.code === user.lang ? baseName : ""),
                ])
            ),
        });
    }

    get langs() {
        return this.props.langs;
    }

    onInput(code, ev) {
        this.state.values[code] = ev.target.value;
    }

    async onConfirm() {
        const values = {};
        for (const [code, val] of Object.entries(this.state.values)) {
            if (val && val.trim()) {
                values[code] = val.trim();
            }
        }
        const base = values[user.lang] || Object.values(values)[0] || this._baseName;
        await this.props.record.update({
            section_name_translations: values,
            name: base,
        });
        this.props.close();
    }

    onCancel() {
        this.props.close();
    }
}

// Add the "Translate" action to the section options dropdown, on both the sale
// order line editor (sol_o2m) and the quotation template line editor
// (so_template_line_o2m) so translations can be authored in either place.
//
// NOTE: each patch() call needs its OWN object literal — Odoo's patch reparents
// the patch object's prototype so `super` resolves, so a shared object would
// corrupt the super-chain of whichever class was patched first (breaking its
// setup(), e.g. leaving productColumns undefined).
function makeSectionTranslatePatch() {
    return {
        setup() {
            super.setup();
            this.translateDialog = useService("dialog");
            this.translateOrm = useService("orm");
        },

        async onTranslateSection(record) {
            const langs = await this.translateOrm.searchRead(
                "res.lang",
                [["active", "=", true]],
                ["code", "name"]
            );
            this.translateDialog.add(SectionTranslateDialog, { record, langs });
        },
    };
}
patch(SaleOrderLineListRenderer.prototype, makeSectionTranslatePatch());
patch(SaleOrderTemplateLineListRenderer.prototype, makeSectionTranslatePatch());
