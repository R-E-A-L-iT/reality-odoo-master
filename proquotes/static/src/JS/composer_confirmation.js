/** @odoo-module **/

import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(Composer.prototype, {
    setup() {
        super.setup();
        this.dialog = this.env.services.dialog;
    },

    /**
     * Override _sendMessage to add confirmation dialog for sale orders with external followers
     */
    async _sendMessage(value, postData) {
        const thread = this.props.composer.thread;

        // Only check for sale.order model
        if (thread && thread.model === 'sale.order' && thread.id) {
            // Only show confirmation for messages that will be sent to followers (not notes)
            if (!postData.isNote) {
                try {
                    // Check if the sale order has external followers
                    const hasExternalFollowers = await this.rpc('/web/dataset/call_kw', {
                        model: 'sale.order',
                        method: 'has_external_followers',
                        args: [[thread.id]],
                        kwargs: {},
                    });

                    if (hasExternalFollowers) {
                        // Show confirmation dialog
                        const confirmed = await this._showConfirmationDialog();

                        if (!confirmed) {
                            // User cancelled, don't send the message
                            return;
                        }
                    }
                } catch (error) {
                    console.error('Error checking external followers:', error);
                    // If there's an error, continue with sending to be safe
                }
            }
        }

        // Proceed with the original send message logic
        return super._sendMessage(value, postData);
    },

    /**
     * Show confirmation dialog to user
     * Returns true if user confirms, false if they cancel
     */
    async _showConfirmationDialog() {
        return new Promise((resolve) => {
            this.dialog.add(
                ConfirmationDialog,
                {
                    title: _t("Confirm Send Message"),
                    body: _t("Are you sure you want to send this message to all followers of the document?"),
                    confirm: () => resolve(true),
                    cancel: () => resolve(false),
                },
            );
        });
    },
});

/**
 * Simple confirmation dialog component
 */
import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

class ConfirmationDialog extends Component {
    static template = "proquotes.ConfirmationDialog";
    static components = { Dialog };
    static props = {
        title: String,
        body: String,
        confirm: Function,
        cancel: Function,
        close: Function,
    };

    onConfirm() {
        this.props.confirm();
        this.props.close();
    }

    onCancel() {
        this.props.cancel();
        this.props.close();
    }
}
