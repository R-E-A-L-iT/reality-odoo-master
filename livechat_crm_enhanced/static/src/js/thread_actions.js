/* @odoo-module */

import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

console.log("LiveChat CRM Enhanced: JavaScript loaded");

// Register the "Create Lead" thread action with smart detection
threadActionsRegistry.add("create-lead", {
    condition(component) {
        // Debug logging to understand what's available
        console.log("Create Lead Button Condition Check:", {
            hasThread: !!component.thread,
            threadModel: component.thread?.model,
            threadType: component.thread?.type,
            channelType: component.thread?.channel_type,
            isChatWindow: !!component.props.chatWindow
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
        action.state = useState({ 
            leadStatus: null,
            loading: false 
        });
        
        // Load lead status on setup
        action.loadLeadStatus = async (threadId) => {
            if (!threadId || action.state.loading) return;
            
            try {
                const result = await action.rpc("/web/dataset/call_kw", {
                    model: "discuss.channel",
                    method: "get_livechat_lead_status",
                    args: [threadId],
                    kwargs: {}
                });
                console.log("Lead status loaded:", result);
                action.state.leadStatus = result;
            } catch (error) {
                console.error("Error loading lead status:", error);
                action.state.leadStatus = { status: 'error' };
            }
        };
    },
    
    icon(component) {
        const action = component.threadActions.actions.find(a => a.id === "create-lead");
        if (!action) return "fa fa-fw fa-handshake-o text-muted";
        
        // Load status if not loaded yet
        if (!action.state.leadStatus && component.thread?.id) {
            action.loadLeadStatus(component.thread.id);
            return "fa fa-fw fa-handshake-o text-muted";
        }
        
        if (!action.state.leadStatus) {
            return "fa fa-fw fa-handshake-o text-muted";
        }
        
        switch (action.state.leadStatus.status) {
            case 'lead_exists':
                return "fa fa-fw fa-edit text-primary";  // Edit icon for update
            case 'can_create_lead':
                return "fa fa-fw fa-handshake-o text-success";  // Handshake for create
            case 'no_permission':
                return "fa fa-fw fa-handshake-o text-muted";
            default:
                return "fa fa-fw fa-handshake-o text-muted";
        }
    },
    
    iconLarge(component) {
        const action = component.threadActions.actions.find(a => a.id === "create-lead");
        if (!action?.state.leadStatus) {
            return "fa fa-fw fa-lg fa-handshake-o text-muted";
        }
        
        switch (action.state.leadStatus.status) {
            case 'lead_exists':
                return "fa fa-fw fa-lg fa-edit text-primary";  // Edit icon for update
            case 'can_create_lead':
                return "fa fa-fw fa-lg fa-handshake-o text-success";  // Handshake for create
            case 'no_permission':
                return "fa fa-fw fa-lg fa-handshake-o text-muted";
            default:
                return "fa fa-fw fa-lg fa-handshake-o text-muted";
        }
    },
    
    name(component) {
        const action = component.threadActions.actions.find(a => a.id === "create-lead");
        if (!action?.state.leadStatus) {
            return _t("Create Lead");
        }
        
        switch (action.state.leadStatus.status) {
            case 'lead_exists':
                return _t("Update Lead");  // Update for existing leads
            case 'can_create_lead':
                return _t("Create Lead");  // Create for new customers
            case 'no_permission':
                return _t("No Permission");
            default:
                return _t("Create Lead");
        }
    },
    
    open(component, action) {
        console.log("Create Lead Button: Clicked!", {component, action});
        
        // Use async function inside open
        (async () => {
            if (action.state.loading) {
                return;
            }
            
            action.state.loading = true;
            
            try {
                // Get current lead status (refresh)
                const statusResult = await action.rpc("/web/dataset/call_kw", {
                    model: "discuss.channel",
                    method: "get_livechat_lead_status",
                    args: [component.thread.id],
                    kwargs: {}
                });
                
                console.log("Status result:", statusResult);
                action.state.leadStatus = statusResult;
                
                let method;
                let processingMsg;
                
                // Determine which action to take based on current status
                if (statusResult.status === 'lead_exists') {
                    method = 'execute_command_update_lead_enhanced';
                    processingMsg = _t("Updating lead...");
                } else if (statusResult.status === 'can_create_lead') {
                    method = 'execute_command_create_lead_enhanced';
                    processingMsg = _t("Creating lead...");
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
                
                // Show processing message
                action.notification.add(processingMsg, { type: 'info' });
                
                // Execute the action
                const result = await action.rpc("/web/dataset/call_kw", {
                    model: "discuss.channel",
                    method: method,
                    args: [component.thread.id],
                    kwargs: {}
                });
                
                console.log("Action result:", result);
                
                if (result && result.success) {
                    // Refresh lead status after successful action
                    await action.loadLeadStatus(component.thread.id);
                    
                    // Show appropriate success message
                    let successMsg;
                    if (result.action === 'linked_existing') {
                        successMsg = _t("Linked to existing lead successfully");
                    } else if (result.action === 'created_new') {
                        successMsg = _t("New lead created successfully");
                    } else {
                        successMsg = _t("Lead updated successfully");
                    }
                    
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
            } finally {
                action.state.loading = false;
            }
        })();
    },
    sequence: 15,
});

console.log("LiveChat CRM Enhanced: Thread action registered");
console.log("Available thread actions:", threadActionsRegistry.content);