/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import FormEditorRegistry from "@website/js/form_editor_registry";

FormEditorRegistry.add('create_rental_quote', {
    formFields: [{
        type: 'char',
        required: true,
        fillWith: 'company_name',
        name: 'company_name',
        string: _t('Company Name'),
    }, {
        type: 'char',
        required: true,
        fillWith: 'partner_name',
        name: 'partner_name',
        string: _t('Name'),
    }, {
        type: 'char',
        required: true,
        fillWith: 'rental_email',
        name: 'rental_email',
        string: _t('Email'),
    }, {
        type: 'date',
        required: true,
        name: 'rental_start_date',
        string: _t('Rental Start Date'),
    }, {
        type: 'date',
        required: true,
        name: 'rental_return_date',
        string: _t('Rental End Date'),
    }],
    fields: [{
        name: 'sale_order_template_id',
        type: 'many2one',
        relation: 'sale.order.template',
        string: _t('Quotation Template'),
    }, {
        name: 'user_id',
        type: 'many2one',
        relation: 'res.users',
        domain: [['share', '=', false]],
        string: _t('Saleperson'),
    }, {
        name: 'team_id',
        type: 'many2one',
        relation: 'crm.team',
        string: _t('Sales Team'),
}],
});