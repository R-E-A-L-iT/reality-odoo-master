/** @odoo-module **/

import { WebClient } from "@web/webclient/webclient";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

patch(WebClient.prototype, {
//        setup: function () {
//        this._super.apply(this, arguments);
        setup() {
            super.setup();

        super.setup(...arguments);
        const app_system_name = session.app_system_name || 'R-E-A-L';
        this.title.setParts({ zopenerp: app_system_name }); // zopenerp is easy to grep
    }
});

