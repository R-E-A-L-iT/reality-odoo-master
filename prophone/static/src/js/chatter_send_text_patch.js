/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Chatter } from "@mail/core/web/chatter";
import { useService } from "@web/core/utils/hooks";

patch(Chatter.prototype, {
    setup() {
        // Call parent
        super.setup(...arguments);

        // Services
        this.orm = useService("orm");
        this.action = useService("action");

        // State flag used by the XML template t-if
        this.state.prophoneCanSendText = false;

        // Initial refresh
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
        const action = await this.orm.call(
            "crm.lead",
            "action_send_quo_text",
            [this.props.threadId],
            {}
        );
        await this.action.doAction(action);
    },
});