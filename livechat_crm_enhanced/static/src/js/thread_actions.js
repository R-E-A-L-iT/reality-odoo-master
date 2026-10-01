/* @odoo-module */

import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

threadActionsRegistry.add("create-lead", {
    condition({ thread, owner }) {
        return (
            thread?.model === "discuss.channel" &&
            thread?.channel_type === "livechat" &&
            !owner.props.chatWindow
        );
    },
    setup() {
        this.notification = useService("notification");
        this.actionService = useService("action");
    },
    icon: "fa fa-fw fa-handshake-o",
    name: _t("Create Lead"),
    open({ thread }) {
        const notification = this.notification;
        const actionService = this.actionService;
        const channelId = thread.id;
        (async () => {
            try {
                const statusResult = await rpc("/web/dataset/call_kw", {
                    model: "discuss.channel",
                    method: "get_livechat_lead_status",
                    args: [[channelId]],
                    kwargs: {},
                });

                let method;
                let successMsg;
                if (statusResult.status === "lead_exists") {
                    method = "execute_command_update_lead_enhanced";
                    successMsg = _t("Lead updated successfully");
                } else if (statusResult.status === "can_create_lead") {
                    method = "execute_command_create_lead_enhanced";
                    successMsg = _t("Lead created successfully");
                } else if (statusResult.status === "no_permission") {
                    notification.add(_t("You don't have permission to create leads"), {
                        type: "warning",
                    });
                    return;
                } else {
                    notification.add(_t("Cannot create lead for this channel"), {
                        type: "warning",
                    });
                    return;
                }

                const result = await rpc("/web/dataset/call_kw", {
                    model: "discuss.channel",
                    method,
                    args: [[channelId]],
                    kwargs: {},
                });

                if (result && result.success) {
                    notification.add(successMsg, { type: "success" });
                    if (result.lead_id) {
                        notification.add(_t("Opening lead..."), { type: "info" });
                        setTimeout(() => {
                            actionService.doAction({
                                type: "ir.actions.act_window",
                                res_model: "crm.lead",
                                res_id: result.lead_id,
                                views: [[false, "form"]],
                                target: "current",
                            });
                        }, 800);
                    }
                } else {
                    notification.add(_t("Error: %s", result?.message || "Unknown error"), {
                        type: "danger",
                    });
                }
            } catch (_error) {
                notification.add(_t("An error occurred while processing the request"), {
                    type: "danger",
                });
            }
        })();
    },
    sequence: 15,
});
