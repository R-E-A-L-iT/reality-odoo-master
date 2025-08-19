/** @odoo-module **/

import { Chatter } from "@mail/core/web/chatter";
import { patch } from "@web/core/utils/patch";

patch(Chatter.prototype, {
    /**
     * Toggle Google composer for simple email layout
     */
    async toggleGoogleComposer() {
        // Check if current record is crm.lead
        if (this.state.thread.model === 'crm.lead' && this.props.threadId) {
            // Prepare the lead for Google message (set simple_email_layout to true)
            const result = await this.orm.call('crm.lead', 'prepare_google_message', [[this.props.threadId]]);
            
            // Store the original value for restoration later
            this._google_message_original_value = result.original_value;
            this._is_google_message = true;
            
            // Open the normal composer
            this.toggleComposer('message');
        }
    },

    /**
     * Override post callback to restore settings after Google message
     */
    async onPostCallback(data) {
        const result = await super.onPostCallback(data);
        
        // If this was a Google message, restore the original settings
        if (this._is_google_message && this.state.thread.model === 'crm.lead' && this.props.threadId) {
            await this.orm.call('crm.lead', 'restore_google_message_settings', 
                [[this.props.threadId], this._google_message_original_value]
            );
            
            // Clean up
            this._is_google_message = false;
            this._google_message_original_value = null;
        }
        
        return result;
    }
});