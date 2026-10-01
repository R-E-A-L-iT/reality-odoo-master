/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { registry } from "@web/core/registry";

export class TreeButtons extends ListController {
    setup() {
        super.setup();
        this.onClickPeopleSearchWizard = this._openWizard.bind(
            this,
            "apl.people.search.wizard",
            "Search People"
        );
        this.onClickCompaniesSearchWizard = this._openWizard.bind(
            this,
            "apl.companies.search.wizard",
            "Companies Search"
        );
    }

    _openWizard(resModel, name) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: resModel,
            name: name,
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
        });
    }
}

TreeButtons.template = "de_apollo_connector.ListView.Buttons";

const viewRegistry = registry.category("views");
if (viewRegistry.contains("list")) {
    const listView = viewRegistry.get("list");
    viewRegistry.add("apl_search_button_in_tree", {
        ...listView,
        Controller: TreeButtons,
        buttonTemplate: "de_apollo_connector.ListView.Buttons",
    });
}
