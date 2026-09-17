/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";
import { Component, reactive, useState } from "@odoo/owl";

/**
 * Keeps track of which AI sub-user this browser session is acting as.
 * The choice lives in the Odoo session server-side, so it holds for every
 * request made from this device until logout.
 */
export const subuserSessionService = {
    dependencies: ["rpc"],
    start(env, { rpc }) {
        const state = reactive({
            loaded: false,
            isAiUser: false,
            required: false,
            current: false,
            options: [],
            prompting: false,
            error: false,
        });

        function apply(payload) {
            state.isAiUser = payload.is_ai_user;
            state.required = payload.required;
            state.current = payload.current;
            state.options = payload.options || [];
            state.loaded = true;
            // a required choice always shows the prompt
            state.prompting = state.prompting || payload.required;
        }

        async function load() {
            if (!session.uid || session.is_public) {
                state.loaded = true;
                return;
            }
            try {
                apply(await rpc("/promessaging/subuser/state"));
            } catch (error) {
                console.warn("ProMessaging: could not read the sub-user session", error);
                state.loaded = true;
            }
        }

        async function select(subuserId, pin) {
            state.error = false;
            const result = await rpc("/promessaging/subuser/select", {
                subuser_id: subuserId,
                pin: pin,
            });
            if (!result.ok) {
                state.error = _t("That PIN does not match this sub-user.");
                return false;
            }
            apply(result.state);
            state.prompting = false;
            return true;
        }

        async function clear() {
            apply(await rpc("/promessaging/subuser/clear"));
            state.prompting = state.required;
        }

        function prompt() {
            state.error = false;
            state.prompting = true;
        }

        load();
        return { state, load, select, clear, prompt };
    },
};

registry.category("services").add("promessaging_subuser", subuserSessionService);

/** Full-screen gate: nothing else can be touched until a PIN is entered. */
export class SubuserGate extends Component {
    static template = "promessaging.SubuserGate";
    static props = {};

    setup() {
        this.subuserService = useService("promessaging_subuser");
        this.state = useState(this.subuserService.state);
        this.form = useState({ subuserId: false, pin: "", busy: false });
    }

    get options() {
        return this.state.options || [];
    }

    get selectedId() {
        return this.form.subuserId || (this.options.length ? this.options[0].id : false);
    }

    onSelectChange(ev) {
        this.form.subuserId = parseInt(ev.target.value, 10);
    }

    onKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.confirm();
        }
    }

    async confirm() {
        if (this.form.busy || !this.selectedId || !this.form.pin) {
            return;
        }
        this.form.busy = true;
        try {
            const ok = await this.subuserService.select(this.selectedId, this.form.pin);
            if (ok) {
                this.form.pin = "";
            }
        } finally {
            this.form.busy = false;
        }
    }

    /** Only dismissable when the choice was optional (switching identity). */
    get canCancel() {
        return !this.state.required;
    }

    cancel() {
        this.state.prompting = false;
    }
}

registry.category("main_components").add("promessaging.SubuserGate", {
    Component: SubuserGate,
});

/** Systray badge naming the sub-user in charge, with a way to switch. */
export class SubuserSystray extends Component {
    static template = "promessaging.SubuserSystray";
    static props = {};

    setup() {
        this.subuserService = useService("promessaging_subuser");
        this.state = useState(this.subuserService.state);
    }

    onClick() {
        this.subuserService.prompt();
    }
}

registry.category("systray").add(
    "promessaging.SubuserSystray",
    { Component: SubuserSystray },
    { sequence: 25 }
);
