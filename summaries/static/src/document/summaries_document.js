/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";
import { Component, markup, onWillStart, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { SummariesStats } from "@summaries/stats/summaries_stats";

const TEXT_CLASS = {
    default: "",
    primary: "text-primary",
    success: "text-success",
    warning: "text-warning",
    danger: "text-danger",
    info: "text-info",
    muted: "text-muted",
};

const ALERT_CLASS = {
    default: "alert-secondary",
    primary: "alert-primary",
    success: "alert-success",
    warning: "alert-warning",
    danger: "alert-danger",
    info: "alert-info",
    muted: "alert-light",
};

const BAR_CLASS = {
    default: "bg-secondary",
    primary: "bg-primary",
    success: "bg-success",
    warning: "bg-warning",
    danger: "bg-danger",
    info: "bg-info",
    muted: "bg-secondary",
};

const INLINE_RE = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;

/** Split a string into inline tokens: bold, italic, code, link, doc, text. */
export function parseInline(value) {
    const text = value === 0 ? "0" : value || "";
    const tokens = [];
    let lastIndex = 0;
    for (const match of String(text).matchAll(INLINE_RE)) {
        if (match.index > lastIndex) {
            tokens.push({ type: "text", text: String(text).slice(lastIndex, match.index) });
        }
        const piece = match[0];
        if (piece.startsWith("**")) {
            tokens.push({ type: "bold", text: piece.slice(2, -2) });
        } else if (piece.startsWith("`")) {
            tokens.push({ type: "code", text: piece.slice(1, -1) });
        } else if (piece.startsWith("[")) {
            const label = piece.slice(1, piece.indexOf("]"));
            const target = piece.slice(piece.indexOf("](") + 2, -1);
            if (target.startsWith("odoo:")) {
                const [, model, resId] = target.split(":");
                tokens.push({ type: "doc", text: label, model, id: parseInt(resId, 10) });
            } else {
                tokens.push({ type: "link", text: label, url: target });
            }
        } else {
            tokens.push({ type: "italic", text: piece.slice(1, -1) });
        }
        lastIndex = match.index + piece.length;
    }
    if (lastIndex < String(text).length) {
        tokens.push({ type: "text", text: String(text).slice(lastIndex) });
    }
    return tokens;
}

export class InlineText extends Component {
    static template = "summaries.InlineText";
    static props = {
        text: { type: [String, Number], optional: true },
        openRef: { type: Function, optional: true },
    };

    get tokens() {
        return parseInline(this.props.text);
    }

    onDocClick(token) {
        if (this.props.openRef) {
            this.props.openRef({ model: token.model, id: token.id });
        }
    }
}

export class SummariesBlocks extends Component {
    static template = "summaries.SummariesBlocks";
    static props = {
        blocks: { type: Array },
        openRef: { type: Function, optional: true },
        resId: { type: [Number, Boolean], optional: true },
        onTriggerRoutine: { type: Function, optional: true },
    };

    textClass(block) {
        return TEXT_CLASS[block.style] || "";
    }

    alertClass(block) {
        return ALERT_CLASS[block.style] || ALERT_CLASS.default;
    }

    barClass(block) {
        return BAR_CLASS[block.style] || BAR_CLASS.primary;
    }

    barWidth(block) {
        const value = Math.max(0, Math.min(Number(block.value) || 0, 100));
        return `width: ${value}%;`;
    }

    imageStyle(block) {
        return `max-width: 100%; width: ${block.width || "auto"};`;
    }

    /** A routine's accent: a style name maps to its colour, a hex is used as is. */
    routineColor(routine) {
        const named = {
            default: "#6c757d",
            primary: "#a855f7",
            success: "#5cb85c",
            warning: "#f0ad4e",
            danger: "#d9534f",
            info: "#5b8def",
            muted: "#9aa0ab",
        };
        return named[routine.color] || routine.color || "#6c757d";
    }

    routineStatusColor(routine) {
        return { ok: "#5cb85c", warning: "#f0ad4e", error: "#d9534f" }[routine.status] || "#5cb85c";
    }

    routineStatusLabel(routine) {
        const label = { ok: "Running fine", warning: "Needs attention", error: "Failing" }[
            routine.status
        ];
        return routine.status_note || label || "";
    }

    async triggerRoutine(routine) {
        if (this.props.onTriggerRoutine) {
            await this.props.onTriggerRoutine(routine);
        }
    }

    markupHtml(html) {
        // sanitized server-side in _clean_blocks
        return markup(html || "");
    }

    onLinkClick(item) {
        if (item.model && item.id && this.props.openRef) {
            this.props.openRef({ model: item.model, id: item.id });
        }
    }
}
SummariesBlocks.components = { SummariesBlocks, InlineText, SummariesStats };

export class SummariesPlanDialog extends Component {
    static template = "summaries.SummariesPlanDialog";
    static components = { Dialog };
    static props = {
        plan: { type: Object },
        readonly: { type: Boolean, optional: true },
        onSave: { type: Function },
        onExecute: { type: Function },
        onToggleStep: { type: Function },
        close: { type: Function },
    };

    setup() {
        this.state = useState({
            steps: this.props.plan.steps.map((step) => ({ ...step })),
            summary: this.props.plan.summary || "",
            taskDone: this.props.plan.task_done,
            executedOn: this.props.plan.executed_on || false,
            sentTo: false,
            busy: false,
            error: false,
        });
    }

    get aiCount() {
        return this.state.steps.filter((step) => step.actor === "ai").length;
    }

    get humanCount() {
        return this.state.steps.filter((step) => step.actor !== "ai").length;
    }

    setActor(step, actor) {
        step.actor = actor;
    }

    async toggleStep(index) {
        const step = this.state.steps[index];
        step.done = !step.done;
        try {
            const plan = await this.props.onToggleStep(index, step.done);
            if (plan) {
                this.state.steps = plan.steps.map((one) => ({ ...one }));
                this.state.taskDone = plan.task_done;
            }
        } catch (error) {
            step.done = !step.done; // put it back
            this.state.error = this.constructor.errorOf(error);
        }
    }

    get remainingForAi() {
        return this.state.steps.filter((step) => step.actor === "ai" && !step.done).length;
    }

    get remainingForHuman() {
        return this.state.steps.filter((step) => step.actor !== "ai" && !step.done).length;
    }

    updateText(step, ev) {
        step.text = ev.target.value;
    }

    addStep() {
        this.state.steps.push({ text: "", actor: "human", note: "", done: false });
    }

    removeStep(index) {
        this.state.steps.splice(index, 1);
    }

    get cleanedSteps() {
        return this.state.steps
            .filter((step) => (step.text || "").trim())
            .map((step) => ({ ...step, text: step.text.trim() }));
    }

    async save() {
        this.state.busy = true;
        try {
            await this.props.onSave({ summary: this.state.summary, steps: this.cleanedSteps });
            this.props.close();
        } catch (error) {
            this.state.error = this.constructor.errorOf(error);
        } finally {
            this.state.busy = false;
        }
    }

    async execute() {
        this.state.busy = true;
        try {
            // save first: executing an edited plan should use what is on screen
            await this.props.onSave({ summary: this.state.summary, steps: this.cleanedSteps });
            const result = await this.props.onExecute();
            if (result && !result.ok) {
                this.state.error = result.error || _t("The assistant could not be reached.");
                return;
            }
            // stay open: the button turning green is how you know it went
            this.state.executedOn = _t("just now");
            this.state.sentTo = (result && result.subuser) || false;
        } catch (error) {
            this.state.error = this.constructor.errorOf(error);
        } finally {
            this.state.busy = false;
        }
    }

    static errorOf(error) {
        return (
            (error && error.data && error.data.message) ||
            (error && error.message) ||
            String(error)
        );
    }
}

export class SummariesDocument extends Component {
    static template = "summaries.SummariesDocument";
    static components = { SummariesBlocks, InlineText, SummariesPlanDialog };
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.triggerRoutine = this.triggerRoutine.bind(this);
        this.state = useState({
            loading: true,
            doc: null,
            newTask: "",
            editing: false,
            draft: "",
            draftIntro: "",
            error: false,
        });
        this.openRef = this.openRef.bind(this);
        onWillStart(() => this.loadDocument());
    }

    get resId() {
        return this.props.record.resId;
    }

    get readonly() {
        return Boolean(this.props.readonly);
    }

    /** The raw JSON editor is a maintenance tool, not everyday UI. */
    get isDebugMode() {
        return Boolean(this.env.debug);
    }

    /** How many tasks sit in each state, for the line above the list. */
    get taskTally() {
        const tasks = (this.state.doc && this.state.doc.tasks) || [];
        const count = (state) => tasks.filter((task) => task.plan_state === state).length;
        return {
            aiReady: count("ai_ready"),
            humanNext: count("human_next"),
            humanOnly: count("human_only"),
        };
    }

    async loadDocument() {
        this.state.loading = true;
        try {
            if (!this.resId) {
                this.state.doc = null;
                return;
            }
            this.state.doc = await this.orm.call("summaries.summary", "get_document", [[this.resId]]);
        } finally {
            this.state.loading = false;
        }
    }

    async reload() {
        await this.loadDocument();
        await this.props.record.load();
    }

    // ----- tasks

    async toggleTask(task) {
        await this.orm.write("summaries.objective", [task.id], { done: !task.done });
        await this.reload();
    }

    async addTask() {
        const name = this.state.newTask.trim();
        if (!name) {
            return;
        }
        await this.orm.create("summaries.objective", [{ summary_id: this.resId, name }]);
        this.state.newTask = "";
        await this.reload();
    }

    onNewTaskKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.addTask();
        }
    }

    async renameTask(task, ev) {
        const name = ev.target.value.trim();
        if (!name || name === task.name) {
            ev.target.value = task.name;
            return;
        }
        await this.orm.write("summaries.objective", [task.id], { name });
        await this.reload();
    }

    async deleteTask(task) {
        await this.orm.unlink("summaries.objective", [task.id]);
        await this.reload();
    }

    async executeTask(task, notify = false) {
        this.state.executing[task.id] = true;
        let result;
        try {
            result = await this.orm.call("summaries.objective", "action_execute", [[task.id]]);
            await this.reload();
        } finally {
            delete this.state.executing[task.id];
        }
        // the plan dialog reports errors inline, so it asks for no notification
        if (notify && result) {
            this.notification.add(
                result.ok
                    ? _t("%s is working on it.", result.subuser)
                    : _t("Could not reach %s (%s).", result.subuser, result.error || _t("unknown error")),
                { type: result.ok ? "info" : "warning" }
            );
        }
        return result;
    }

    isExecuting(task) {
        return Boolean(this.state.executing[task.id]);
    }

    async openPlan(task) {
        const plan = await this.orm.call("summaries.objective", "get_plan", [[task.id]]);
        this.dialog.add(SummariesPlanDialog, {
            plan,
            readonly: this.readonly,
            onSave: async (edited) => {
                await this.orm.call("summaries.objective", "set_plan", [[task.id], edited]);
                await this.reload();
            },
            onExecute: () => this.executeTask(task),
            onToggleStep: async (index, done) => {
                const updated = await this.orm.call("summaries.objective", "mark_step", [
                    [task.id],
                    index,
                    done,
                ]);
                await this.reload();
                return updated;
            },
        });
    }

    openRef(ref) {
        if (!ref || !ref.model || !ref.id) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: ref.model,
            res_id: ref.id,
            view_mode: "form",
            views: [[false, "form"]],
        });
    }

    async triggerRoutine(routine) {
        const result = await this.orm.call("summaries.summary", "trigger_routine", [
            [this.resId],
            routine.key || routine.name,
        ]);
        await this.loadDocument();
        this.notification.add(
            result.ok
                ? _t("%s is running %s.", result.subuser, result.routine)
                : _t("Could not reach %s (%s).", result.subuser, result.error || _t("unknown error")),
            { type: result.ok ? "info" : "warning" }
        );
    }

    // ----- content

    toggleSource() {
        this.state.error = false;
        if (!this.state.editing) {
            this.state.draft = this.state.doc ? this.state.doc.content : "[]";
            this.state.draftIntro = this.state.doc ? this.state.doc.intro : "[]";
        }
        this.state.editing = !this.state.editing;
    }

    async saveContent() {
        this.state.error = false;
        try {
            await this.orm.call("summaries.summary", "set_intro", [[this.resId], this.state.draftIntro]);
            await this.orm.call("summaries.summary", "set_content", [[this.resId], this.state.draft]);
        } catch (error) {
            this.state.error =
                (error && error.data && error.data.message) || (error && error.message) || String(error);
            return;
        }
        this.state.editing = false;
        await this.reload();
    }
}

export const summariesDocument = { component: SummariesDocument };

registry.category("view_widgets").add("summaries_document", summariesDocument);
