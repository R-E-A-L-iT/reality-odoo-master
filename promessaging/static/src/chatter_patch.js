/** @odoo-module **/

import { Chatter } from "@mail/core/web/chatter";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

patch(Chatter.prototype, {
    get canSendMessage() {
        return session.can_send_message !== false;
    },

    toggleComposer(mode = false) {
        // also blocks the "m" hotkey and any other code path opening the message composer
        if (mode === "message" && !this.canSendMessage) {
            return;
        }
        return super.toggleComposer(mode);
    },
});
