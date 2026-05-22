/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { registry } from "@web/core/registry";

console.log("Registry:", registry);

// Fetch ListView from the registry instead of direct import
const ListView = registry.category("views").get("list");
console.log("ListView from registry:", ListView);

if (!ListView) {
    console.error("ListView is undefined. Ensure that the module is properly loaded.");
} else {
    export class TreeButtons extends ListController {
        setup() {
            super.setup();
            this.onClickPeopleSearchWizard = this._openWizard.bind(this, "apl.people.search.wizard", "Search People");
            this.onClickCompaniesSearchWizard = this._openWizard.bind(this, "apl.companies.search.wizard", "Companies Search");
        }

        _openWizard(resModel, name) {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: resModel,
                name: name,
                view_mode: "form",
                views: [[false, "form"]],
                target: "new",
                res_id: false,
            });
        }
    }

    TreeButtons.template = "de_apollo_connector.search_buttons";

    class AplSearchResultsListView extends ListView.Controller {}
    AplSearchResultsListView.components = {
        Controller: TreeButtons,
    };

    registry.category("views").add("apl_search_button_in_tree", {
        ...ListView,
        Controller: TreeButtons,
    });
}
