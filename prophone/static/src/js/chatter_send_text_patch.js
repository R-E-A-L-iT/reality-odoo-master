/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Chatter } from "@mail/chatter/web_portal/chatter";
import { useService } from "@web/core/utils/hooks";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);

        this.orm = useService("orm");
        this.action = useService("action");

        this.state.prophoneCanSendTextLead = false;
        this.state.prophoneCanSendTextQuote = false;
        this.state.prophoneCanSendTextTicket = false;
        this.state.prophoneCanSendTextPartner = false;

        this._prophoneRefreshSendTextVisibility();
    },

    async _prophoneRefreshSendTextVisibility() {
        try {
            const model = this.state.thread?.model;
            const id = this.props.threadId;

            this.state.prophoneCanSendTextLead = false;
            this.state.prophoneCanSendTextQuote = false;
            this.state.prophoneCanSendTextTicket = false;
            this.state.prophoneCanSendTextPartner = false;

            if (!id) return;

            if (model === "crm.lead") {
                const res = await this.orm.call("crm.lead", "quo_send_text_button_info", [id], {});
                this.state.prophoneCanSendTextLead = !!(res && res.can_send);
            } else if (model === "sale.order") {
                const res = await this.orm.call("sale.order", "quo_send_text_button_info", [id], {});
                this.state.prophoneCanSendTextQuote = !!(res && res.can_send);
            } else if (model === "helpdesk.ticket") {
                const res = await this.orm.call("helpdesk.ticket", "quo_send_text_button_info", [id], {});
                this.state.prophoneCanSendTextTicket = !!(res && res.can_send);
            } else if (model === "res.partner") {
                const res = await this.orm.call("res.partner", "quo_send_text_button_info", [id], {});
                this.state.prophoneCanSendTextPartner = !!(res && res.can_send);
            }
        } catch (e) {
            this.state.prophoneCanSendTextLead = false;
            this.state.prophoneCanSendTextQuote = false;
            this.state.prophoneCanSendTextTicket = false;
            this.state.prophoneCanSendTextPartner = false;
        }
    },

    async prophoneOpenSendTextWizard() {
        const model = this.state.thread?.model;
        const id = this.props.threadId;
        if (!id) return;

        let action;
        if (model === "crm.lead") {
            action = await this.orm.call("crm.lead", "action_send_quo_text", [id], {});
        } else if (model === "sale.order") {
            action = await this.orm.call("sale.order", "action_send_quo_text", [id], {});
        } else if (model === "helpdesk.ticket") {
            action = await this.orm.call("helpdesk.ticket", "action_send_quo_text", [id], {});
        } else if (model === "res.partner") {
            action = await this.orm.call("res.partner", "action_send_quo_text", [id], {});
        } else {
            return;
        }
        await this.action.doAction(action);
    },
});