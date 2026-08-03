/** @odoo-module **/

import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

// Register the "Create Lead" thread action
threadActionsRegistry.add("create-lead", {
    condition({ owner, thread }) {
        // Show only for livechat channels, and not inside a chat window popup.
        return (
            thread?.model === "discuss.channel" &&
            thread.channel_type === "livechat" &&
            !owner.props.chatWindow
        );
    },
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.actionService = useService("action");
    },
    icon: "fa fa-fw fa-handshake-o",
    iconLarge: "fa fa-fw fa-lg fa-handshake-o",
    name: _t("Create Lead"),
    async open({ action, thread }) {
        try {
            // Get current lead status
            const statusResult = await action.orm.call(
                "discuss.channel", "get_livechat_lead_status", [thread.id]
            );

            let method;
            let successMsg;

            // Determine which action to take based on current status
            if (statusResult.status === "lead_exists") {
                method = "execute_command_update_lead_enhanced";
                successMsg = _t("Lead updated successfully");
            } else if (statusResult.status === "can_create_lead") {
                method = "execute_command_create_lead_enhanced";
                successMsg = _t("Lead created successfully");
            } else if (statusResult.status === "no_permission") {
                action.notification.add(_t("You don't have permission to create leads"), {
                    type: "warning",
                });
                return;
            } else {
                action.notification.add(_t("Cannot create lead for this channel"), {
                    type: "warning",
                });
                return;
            }

            // Execute the action
            const result = await action.orm.call("discuss.channel", method, [thread.id]);

            if (result?.success) {
                action.notification.add(successMsg, { type: "success" });

                // Auto-redirect to lead form if lead_id is provided
                if (result.lead_id) {
                    action.actionService.doAction({
                        type: "ir.actions.act_window",
                        res_model: "crm.lead",
                        res_id: result.lead_id,
                        views: [[false, "form"]],
                        target: "current",
                    });
                }
            } else {
                action.notification.add(_t("Error: %s", result?.message || "Unknown error"), {
                    type: "danger",
                });
            }
        } catch (error) {
            console.error("Error in create lead action:", error);
            action.notification.add(_t("An error occurred while processing the request"), {
                type: "danger",
            });
        }
    },
    sequence: 15,
});
