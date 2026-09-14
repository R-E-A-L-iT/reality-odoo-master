/** @odoo-module **/

import { Chatter } from "@mail/core/web/chatter";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { useState } from "@odoo/owl";

patch(Chatter.prototype, {
    setup() {
        super.setup();
        this.promessagingDraft = useState({
            draft: false,
            editing: false,
            value: "",
        });
    },

    get canSendMessage() {
        return session.can_send_message !== false;
    },

    get promessagingShowDraft() {
        return Boolean(this.promessagingDraft.draft) || this.promessagingDraft.editing;
    },

    toggleComposer(mode = false) {
        // also blocks the "m" hotkey and any other code path opening the message composer
        if (mode === "message" && !this.canSendMessage) {
            return;
        }
        return super.toggleComposer(mode);
    },

    changeThread(threadModel, threadId, webRecord) {
        const res = super.changeThread(threadModel, threadId, webRecord);
        this.promessagingLoadDraft(threadModel, threadId);
        return res;
    },

    promessagingResetDraft() {
        Object.assign(this.promessagingDraft, { draft: false, editing: false, value: "" });
    },

    async promessagingLoadDraft(threadModel, threadId) {
        this.promessagingResetDraft();
        this._promessagingDraftToken = (this._promessagingDraftToken || 0) + 1;
        const token = this._promessagingDraftToken;
        if (!threadId || !threadModel || threadModel === "discuss.channel") {
            return;
        }
        const draft = await this.orm.call("promessaging.draft", "get_draft", [
            threadModel,
            threadId,
        ]);
        if (token !== this._promessagingDraftToken) {
            return; // the chatter moved to another record while loading
        }
        this.promessagingDraft.draft = draft || false;
    },

    promessagingEditDraft() {
        this.promessagingDraft.value = this.promessagingDraft.draft
            ? this.promessagingDraft.draft.body
            : "";
        this.promessagingDraft.editing = true;
    },

    promessagingCancelDraft() {
        this.promessagingDraft.editing = false;
        this.promessagingDraft.value = "";
    },

    async promessagingPostDraft() {
        if (!this.promessagingDraft.value.trim()) {
            return;
        }
        const draft = await this.orm.call("promessaging.draft", "set_draft", [
            this.props.threadModel,
            this.props.threadId,
            this.promessagingDraft.value,
        ]);
        this.promessagingDraft.draft = draft;
        this.promessagingDraft.editing = false;
        this.promessagingDraft.value = "";
    },

    async promessagingSendDraft() {
        const draft = this.promessagingDraft.draft;
        if (!draft) {
            return;
        }
        await this.orm.call("promessaging.draft", "action_send_draft", [[draft.id]]);
        this.promessagingResetDraft();
        this.load(this.state.thread, ["messages"]);
    },

    async promessagingDiscardDraft() {
        const draft = this.promessagingDraft.draft;
        if (!draft) {
            return;
        }
        await this.orm.call("promessaging.draft", "action_discard_draft", [[draft.id]]);
        this.promessagingResetDraft();
    },
});
