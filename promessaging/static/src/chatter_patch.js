/** @odoo-module **/

import { Chatter } from "@mail/core/web/chatter";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { session } from "@web/session";
import { useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

patch(Chatter.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.promessagingDialog = useService("dialog");
        this.promessagingDraft = useState({
            draft: false,
            editing: false,
            value: "",
            regenerating: false,
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

    promessagingSendDraft() {
        const draft = this.promessagingDraft.draft;
        if (!draft) {
            return;
        }
        this.promessagingDialog.add(ConfirmationDialog, {
            title: _t("Send draft as message"),
            body: _t(
                "This draft will be posted as a message and emailed to the followers of this document, customers included. This cannot be undone."
            ),
            confirmLabel: _t("Send message"),
            confirm: () => this.promessagingConfirmSendDraft(draft),
            cancelLabel: _t("Cancel"),
            cancel: () => {},
        });
    },

    async promessagingConfirmSendDraft(draft) {
        await this.orm.call("promessaging.draft", "action_send_draft", [[draft.id]]);
        this.promessagingResetDraft();
        this.load(this.state.thread, ["messages"]);
    },

    async promessagingRegenerateDraft() {
        const draft = this.promessagingDraft.draft;
        if (!draft || this.promessagingDraft.regenerating) {
            return;
        }
        this.promessagingDraft.regenerating = true;
        try {
            const result = await this.orm.call("promessaging.draft", "action_regenerate", [
                [draft.id],
            ]);
            await this.promessagingLoadDraft(this.props.threadModel, this.props.threadId);
            if (result && !result.ok) {
                this.notification.add(
                    _t("Could not reach %s (%s).", draft.author, result.error || _t("unknown error")),
                    { type: "warning" }
                );
            } else if (result && !result.updated) {
                this.notification.add(
                    _t("%s was asked to rewrite the draft and will update it shortly.", draft.author),
                    { type: "info" }
                );
            }
        } finally {
            this.promessagingDraft.regenerating = false;
        }
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
