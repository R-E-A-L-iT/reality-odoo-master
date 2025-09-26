/* @odoo-module */

import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

console.log("LiveChat CRM Enhanced: JavaScript loaded");

// Register the "Create Lead" thread action
threadActionsRegistry.add("create-lead", {
    condition(component) {
        // Debug logging to understand what's available
        console.log("Create Lead Button Condition Check:", {
            hasThread: !!component.thread,
            thread: component.thread,
            threadModel: component.thread?.model,
            threadType: component.thread?.type,
            channelType: component.thread?.channel_type,
            threadChannelType: component.thread?.channel_type,
            isChatWindow: !!component.props.chatWindow,
            props: component.props,
            component: component
        });
        
        // Try multiple possible properties for livechat detection
        const isLivechat = (
            component.thread?.channel_type === "livechat" ||
            component.thread?.type === "livechat" ||
            component.thread?.livechat ||
            (component.thread?.model === "discuss.channel" && component.thread?.name?.includes("LiveChat"))
        );
        
        const isDiscussChannel = component.thread?.model === "discuss.channel";
        const notChatWindow = !component.props.chatWindow;
        
        console.log("Create Lead Condition Result:", {
            isDiscussChannel,
            isLivechat,
            notChatWindow,
            finalResult: isDiscussChannel && isLivechat && notChatWindow
        });
        
        // Show only for livechat channels
        return isDiscussChannel && isLivechat && notChatWindow;
    },
    setup(action) {
        console.log("Create Lead Button: Setup called");
        action.rpc = useService("rpc");
        action.notification = useService("notification");
    },
    icon: "fa fa-fw fa-handshake-o",
    iconLarge: "fa fa-fw fa-lg fa-handshake-o",
    name: _t("Create Lead"),
    open(component, action) {
        console.log("Create Lead Button: Clicked!", {component, action});
        
        // Use async function inside open
        (async () => {
            try {
                // Get current lead status
                const statusResult = await action.rpc("/web/dataset/call_kw", {
                    model: "discuss.channel",
                    method: "get_livechat_lead_status",
                    args: [component.thread.id],
                    kwargs: {}
                });
                
                console.log("Status result:", statusResult);
                
                let method;
                let successMsg;
                
                // Determine which action to take based on current status
                if (statusResult.status === 'lead_exists') {
                    method = 'execute_command_update_lead_enhanced';
                    successMsg = _t("Lead updated successfully");
                } else if (statusResult.status === 'can_create_lead') {
                    method = 'execute_command_create_lead_enhanced';
                    successMsg = _t("Lead created successfully");
                } else if (statusResult.status === 'no_permission') {
                    action.notification.add(_t("You don't have permission to create leads"), {
                        type: 'warning'
                    });
                    return;
                } else {
                    action.notification.add(_t("Cannot create lead for this channel"), {
                        type: 'warning'
                    });
                    return;
                }
                
                // Execute the action
                const result = await action.rpc("/web/dataset/call_kw", {
                    model: "discuss.channel",
                    method: method,
                    args: [component.thread.id],
                    kwargs: {}
                });
                
                console.log("Action result:", result);
                
                if (result && result.success) {
                    action.notification.add(successMsg, { type: 'success' });
                } else {
                    action.notification.add(_t("Error: %s", result?.message || "Unknown error"), {
                        type: 'danger'
                    });
                }
                
            } catch (error) {
                console.error("Error in create lead action:", error);
                action.notification.add(_t("An error occurred while processing the request"), {
                    type: 'danger'
                });
            }
        })();
    },
    sequence: 15,
});

console.log("LiveChat CRM Enhanced: Thread action registered");
console.log("Available thread actions:", threadActionsRegistry.content);