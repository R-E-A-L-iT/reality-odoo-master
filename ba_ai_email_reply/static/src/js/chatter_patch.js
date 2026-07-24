/** @odoo-module **/

import { Chatter } from "@mail/chatter/web_portal/chatter";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";

patch(Chatter.prototype, {
    setup() {
        super.setup();
        // Reactive object so the template re-renders on state change
        this.aiState = useState({ generating: false });
    },

    /**
     * Getter used by the template as `aiGenerating`.
     * OWL tracks reactive reads, so the button re-renders automatically.
     */
    get aiGenerating() {
        return this.aiState.generating;
    },

    /**
     * Called when the "Generate AI Reply" button is clicked.
     * 1. Calls the Python backend to collect messages + knowledge and call OpenAI.
     * 2. Opens the Send Message composer.
     * 3. Pre-fills the composer body with the generated reply.
     * The user must manually review, edit, and send.
     */
    async generateAiReply() {
        if (!this.props.threadId || this.state.thread?.model !== "crm.lead") {
            return;
        }
        this.aiState.generating = true;
        try {
            const result = await this.orm.call(
                "crm.lead",
                "action_generate_ai_reply",
                [[this.props.threadId]]
            );
            if (result && result.reply) {
                // Open the standard "Send message" composer
                this.toggleComposer("message");
                // One microtask tick so the composer component mounts
                await Promise.resolve();
                const composer = this.state.thread?.composer;
                if (composer) {
                    composer.textInputContent = result.reply;
                    // Increment autofocus to trigger the textarea focus+resize effect
                    composer.autofocus++;
                }
            }
        } catch (_err) {
            // UserError / ValidationError from Python are automatically shown
            // as Odoo error notifications by the ORM service — no extra handling needed.
        } finally {
            this.aiState.generating = false;
        }
    },
});
