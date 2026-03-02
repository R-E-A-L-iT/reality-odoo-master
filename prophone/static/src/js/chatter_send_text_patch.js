/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Chatter } from "@mail/core/common/chatter";
import { useService } from "@web/core/utils/hooks";

patch(Chatter.prototype, "prophone_chatter_send_text", {
    setup() {
        this._super(...arguments);
        this.orm = useService("orm");
        this.action = useService("action");

        // Our state flag (default false)
        this.state.prophoneCanSendText = false;

        // Compute once when chatter is on crm.lead
        this._prophoneRefreshSendTextVisibility();
    },

    async _prophoneRefreshSendTextVisibility() {
        try {
            if (this.state.thread?.model !== "crm.lead" || !this.props.threadId) {
                this.state.prophoneCanSendText = false;
                return;
            }
            const res = await this.orm.call(
                "crm.lead",
                "quo_send_text_button_info",
                [this.props.threadId],
                {}
            );
            this.state.prophoneCanSendText = !!(res && res.can_send);
        } catch (e) {
            // fail closed
            this.state.prophoneCanSendText = false;
        }
    },

    async prophoneOpenSendTextWizard() {
        // Server action does final validation and returns the wizard action dict
        const action = await this.orm.call(
            "crm.lead",
            "action_send_quo_text",
            [this.props.threadId]
        );
        await this.action.doAction(action);
    },
});