/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import {
    Component,
    onWillDestroy,
    onWillStart,
    useRef,
    useState,
} from "@odoo/owl";

const POLL_INTERVAL = 8000;
// stop polling a conversation that has been quiet this long (resumes on send)
const POLL_IDLE_TIMEOUT = 3 * 60 * 1000;

export class AiChatBubble extends Component {
    static template = "promessaging.AiChatBubble";
    static props = {};

    setup() {
        this.orm = useService("orm");
        // Odoo's own breakpoint: below it the bubble would sit on top of the UI
        this.ui = useState(useService("ui"));
        this.threadRef = useRef("thread");
        this.state = useState({
            available: false,
            open: false,
            directory: [],
            chat: null,
            messages: [],
            draft: "",
            sending: false,
            error: false,
        });

        onWillStart(async () => {
            if (!session.uid || session.is_public) {
                return;
            }
            await this.loadDirectory();
        });

        onWillDestroy(() => this.stopPolling());
    }

    async loadDirectory() {
        try {
            const directory = await this.orm.call("promessaging.ai.chat", "get_directory", []);
            this.state.directory = directory || [];
            this.state.available = this.state.directory.length > 0;
        } catch (error) {
            // never let the bubble break the web client
            console.warn("ProMessaging: could not load the AI directory", error);
            this.state.available = false;
        }
    }

    /** Hidden on a narrow screen: there it covers what you are trying to tap. */
    get visible() {
        return this.state.available && !this.ui.isSmall;
    }

    get onlyAssistant() {
        return this.state.directory.length === 1 ? this.state.directory[0] : null;
    }

    togglePanel() {
        if (this.state.open || this.state.chat) {
            this.state.open = false;
            this.closeChat();
            return;
        }
        // with a single assistant there is nothing to choose from
        if (this.onlyAssistant) {
            this.state.open = true;
            this.openChat(this.onlyAssistant);
            return;
        }
        this.state.open = true;
    }

    async openChat(subuser) {
        this.state.error = false;
        try {
            const chat = await this.orm.call("promessaging.ai.chat", "open_chat", [subuser.id]);
            this.state.chat = chat;
            this.state.messages = chat.messages || [];
            this.startPolling();
            this.scrollToEnd();
        } catch (error) {
            this.state.error = this.errorMessage(error);
        }
    }

    closeChat() {
        if (this.onlyAssistant) {
            this.state.open = false;
        }
        this.stopPolling();
        this.state.chat = null;
        this.state.messages = [];
        this.state.draft = "";
        this.state.error = false;
    }

    get lastMessageId() {
        return this.state.messages.length
            ? this.state.messages[this.state.messages.length - 1].id
            : 0;
    }

    async send() {
        const body = this.state.draft.trim();
        if (!body || !this.state.chat || this.state.sending) {
            return;
        }
        this.state.sending = true;
        this.state.error = false;
        this.state.draft = "";
        try {
            const result = await this.orm.call("promessaging.ai.chat", "post_message", [
                [this.state.chat.id],
                body,
            ]);
            this.appendMessages(result.messages || []);
            this.startPolling();
        } catch (error) {
            this.state.error = this.errorMessage(error);
        } finally {
            this.state.sending = false;
            this.scrollToEnd();
        }
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.send();
        }
    }

    appendMessages(messages) {
        const known = new Set(this.state.messages.map((message) => message.id));
        for (const message of messages) {
            if (!known.has(message.id)) {
                this.state.messages.push(message);
            }
        }
    }

    startPolling() {
        this.stopPolling();
        this._pollSince = Date.now();
        this._poll = setInterval(async () => {
            if (!this.state.chat || this.state.sending || this.ui.isSmall) {
                return;
            }
            // don't poll a background tab, and give up on a quiet conversation
            if (document.hidden) {
                return;
            }
            if (Date.now() - this._pollSince > POLL_IDLE_TIMEOUT) {
                this.stopPolling();
                return;
            }
            try {
                const result = await this.orm.silent.call(
                    "promessaging.ai.chat",
                    "fetch_messages",
                    [[this.state.chat.id], this.lastMessageId]
                );
                const messages = result.messages || [];
                if (messages.length) {
                    this._pollSince = Date.now();
                    this.appendMessages(messages);
                    this.scrollToEnd();
                }
            } catch (_error) {
                // a failed poll is not worth reporting; the next one may work
            }
        }, POLL_INTERVAL);
    }

    stopPolling() {
        if (this._poll) {
            clearInterval(this._poll);
            this._poll = null;
        }
    }

    scrollToEnd() {
        // the thread is not in the DOM yet on open, so wait for the paint after render
        const scroll = () => {
            const el = this.threadRef.el;
            if (el) {
                el.scrollTop = el.scrollHeight;
            }
        };
        requestAnimationFrame(() => requestAnimationFrame(scroll));
    }

    errorMessage(error) {
        return (
            (error && error.data && error.data.message) ||
            (error && error.message) ||
            String(error)
        );
    }
}

registry.category("main_components").add("promessaging.AiChatBubble", {
    Component: AiChatBubble,
});
