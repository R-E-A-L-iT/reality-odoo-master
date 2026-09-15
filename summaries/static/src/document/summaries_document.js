/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";
import { Component, markup, onWillStart, useState } from "@odoo/owl";
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

export class SummariesDocument extends Component {
    static template = "summaries.SummariesDocument";
    static components = { SummariesBlocks, InlineText };
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
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

    async executeTask(task) {
        await this.orm.call("summaries.objective", "action_execute", [[task.id]]);
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
