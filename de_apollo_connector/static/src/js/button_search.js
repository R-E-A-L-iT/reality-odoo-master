odoo.define('de_apollo_connector.tree_search_buttons', function (require) {
    "use strict";
    
    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');
    
    var TreeButtons = ListController.extend({
        buttons_template: 'de_apollo_connector.search_buttons',
        events: _.extend({}, ListController.prototype.events, {
            'click .open_wizard_action_apl_people_search_results': '_OpenPeopleSearchWizard',
            'click .open_wizard_action_companies_search': '_OpenCompaniesSearchWizard',
        }),
        _OpenPeopleSearchWizard: function () {
            this._openWizard('apl.people.search.wizard', 'Search People');
        },
        _OpenCompaniesSearchWizard: function () {
            this._openWizard('apl.companies.search.wizard', 'Companies Search'); // Update with your actual model name
        },
        _openWizard: function (resModel, name) {
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: resModel,
                name: name,
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                target: 'new',
                res_id: false,
            });
        },
    });

    var AplSearchResultsListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: TreeButtons,
        }),
    });

    viewRegistry.add('apl_search_button_in_tree', AplSearchResultsListView);
});
