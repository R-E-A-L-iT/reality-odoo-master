/** @odoo-module **/

import { Chatter } from "@mail/chatter/web_portal/chatter";
import { patch } from "@web/core/utils/patch";

patch(Chatter.prototype, {
    /**
     * Override toggleComposer to automatically set simple_email_layout
     * before opening the message composer on crm.lead records.
     */
    async toggleComposer(mode = false, options = {}) {
        if (mode === 'message' && this.state.thread.model === 'crm.lead' && this.props.threadId) {
            const result = await this.orm.call('crm.lead', 'prepare_google_message', [[this.props.threadId]]);
            this._google_message_original_value = result.original_value;
            this._is_google_message = true;
        } else {
            this._is_google_message = false;
        }
        return super.toggleComposer(mode, options);
    },

    /**
     * Override post callback to restore settings after sending on crm.lead.
     */
    async onPostCallback() {
        const result = await super.onPostCallback();
        if (this._is_google_message && this.state.thread.model === 'crm.lead' && this.props.threadId) {
            await this.orm.call('crm.lead', 'restore_google_message_settings',
                [[this.props.threadId], this._google_message_original_value]
            );
            this._is_google_message = false;
            this._google_message_original_value = null;
        }
        return result;
    }
});
