/** @odoo-module **/

import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(Composer.prototype, {
    async sendMessage() {
        const thread = this.props.composer.thread;
        const isNote = this.props.type === "note";

        if (thread?.model === "crm.lead" && !isNote) {
            const records = await this.env.services.orm.read(
                "crm.lead",
                [thread.id],
                ["ba_email_subject", "type"]
            );
            const record = records[0];
            if (record && record.type === "opportunity" && !record.ba_email_subject) {
                this.env.services.notification.add(
                    _t("Please set an Email Subject on this opportunity before sending an email."),
                    { type: "warning", sticky: true }
                );
                // Return early — processMessage is never called, composer content preserved
                return;
            }
        }
        return super.sendMessage();
    },
});
