/** @odoo-module **/

import { ListController }  from "@web/views/list/list_controller";
import { ListView } from "@web/views/list/list_view";
import { registry } from '@web/core/registry';

console.log('ListView:', ListView);
console.log('Type of ListView:', typeof ListView);
export class TreeButtons extends ListController {
    setup() {
        super.setup();
        this.onClickPeopleSearchWizard = this._openWizard.bind(this, 'apl.people.search.wizard', 'Search People');
        this.onClickCompaniesSearchWizard = this._openWizard.bind(this, 'apl.companies.search.wizard', 'Companies Search');
    }

    _openWizard(resModel, name) {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: resModel,
            name: name,
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            res_id: false,
        });
    }
}

TreeButtons.template = 'de_apollo_connector.search_buttons';

//Remain to migrate this part

//class AplSearchResultsListView extends ListView.Controller {}
//AplSearchResultsListView.components = {
//    Controller: TreeButtons,
//};
//
//// Register using Component (without spreading listView)
//if (ListView) {
//    registry.category('views').add('apl_search_button_in_tree', {
//        Component: AplSearchResultsListView,
//    });
//} else {
//    console.error('ListView is undefined');
//}



// old code odoo 16
//registry.category('views').add('apl_search_button_in_tree', AplSearchResultsListView);


//odoo.define('de_apollo_connector.tree_search_buttons', function (require) {
//    "use strict";
//
//    var ListController = require('web.ListController');
//    var ListView = require('web.ListView');
//    var viewRegistry = require('web.view_registry');
//
//    var TreeButtons = ListController.extend({
//        buttons_template: 'de_apollo_connector.search_buttons',
//        events: _.extend({}, ListController.prototype.events, {
//            'click .open_wizard_action_apl_people_search_results': '_OpenPeopleSearchWizard',
//            'click .open_wizard_action_companies_search': '_OpenCompaniesSearchWizard',
//        }),
//        _OpenPeopleSearchWizard: function () {
//            this._openWizard('apl.people.search.wizard', 'Search People');
//        },
//        _OpenCompaniesSearchWizard: function () {
//            this._openWizard('apl.companies.search.wizard', 'Companies Search'); // Update with your actual model name
//        },
//        _openWizard: function (resModel, name) {
//            this.do_action({
//                type: 'ir.actions.act_window',
//                res_model: resModel,
//                name: name,
//                view_mode: 'form',
//                view_type: 'form',
//                views: [[false, 'form']],
//                target: 'new',
//                res_id: false,
//            });
//        },
//    });
//
//    var AplSearchResultsListView = ListView.extend({
//        config: _.extend({}, ListView.prototype.config, {
//            Controller: TreeButtons,
//        }),
//    });
//
//    viewRegistry.add('apl_search_button_in_tree', AplSearchResultsListView);
//});