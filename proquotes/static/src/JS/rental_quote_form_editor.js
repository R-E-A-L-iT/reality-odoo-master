/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import FormEditorRegistry from "@website/js/form_editor_registry";

FormEditorRegistry.add('create_rental_quote', {
    formFields: [{
        type: 'date',
        modelRequired: true,
        name: 'rental_start_date',
        fillWith: 'rental_start_date',
        string: _t('Start of Rental period'),
    }, {
        type: 'date',
        required: true,
        fillWith: 'rental_return_date',
        name: 'rental_return_date',
        string: _t('End of Rental period'),
    }, {
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
    },],
    fields: [{
        name: 'sale_order_template_id',
        type: 'many2one',
        relation: 'sale.order.template',
        string: _t('Quotation Template'),
    }, {
        name: 'user_id',
        type: 'many2one',
        relation: 'res.users',
        string: _t('Saleperson'),
    }, {
        name: 'team_id',
        type: 'many2one',
        relation: 'crm.team',
        string: _t('Sales Team'),
}],
    // successPage: '/job-thank-you',
});