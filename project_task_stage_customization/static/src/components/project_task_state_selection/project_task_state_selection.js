import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import {
    ProjectTaskStateSelection,
    projectTaskStateSelection,
} from "@project/components/project_task_state_selection/project_task_state_selection";
import { TaskStageWithStateSelection } from "@project/components/project_task_state_selection/project_task_stage_state_selection/project_task_stage_with_state_selection";

export class CustomProjectTaskStateSelection extends ProjectTaskStateSelection {
    setup() {
        super.setup();
        Object.assign(this.icons, {
            "011_not_started": "o_status",
            "01_in_progress": "o_status bg-info",
        });
        Object.assign(this.colorIcons, {
            "011_not_started": "",
            "01_in_progress": "text-info",
        });
        Object.assign(this.colorButton, {
            "011_not_started": "btn-outline-secondary",
            "01_in_progress": "btn-outline-info",
        });
    }

    get options() {
        const parentOptions = super.options;
        const currentState = this.props.record.data[this.props.name];
        if (currentState === "04_waiting_normal") {
            return parentOptions;
        }
        const fieldSelection = this.props.record.fields[this.props.name].selection;
        const notStartedLabel =
            fieldSelection.find(([state]) => state === "011_not_started")?.[1] || _t("Not started");
        return [["011_not_started", notStartedLabel], ...parentOptions];
    }
}

export const customProjectTaskStateSelection = {
    ...projectTaskStateSelection,
    component: CustomProjectTaskStateSelection,
};

registry
    .category("fields")
    .add("project_task_state_selection", customProjectTaskStateSelection, { force: true });

patch(TaskStageWithStateSelection, {
    components: {
        ...TaskStageWithStateSelection.components,
        ProjectTaskStateSelection: CustomProjectTaskStateSelection,
    },
});
