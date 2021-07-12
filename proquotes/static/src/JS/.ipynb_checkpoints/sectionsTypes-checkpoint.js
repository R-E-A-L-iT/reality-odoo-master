odoo.define('proquotes.section_types_backend', function (require) {
    
    "use strict";
    var FieldChar = require('web.basic_fields').FieldChar;
    var FieldOne2Many = require('web.relational_fields').FieldOne2Many;
    var fieldRegistry = require('web.field_registry');
    var ListFieldText = require('web.basic_fields').ListFieldText;
    var ListRenderer = require('web.ListRenderer');
    var CustomSectionRenderer = ListRenderer.extend({
        _renderBodyCell: function (record, node, index, options) {
            var $cell = this._super.apply(this, arguments);

            var isOptionalSection = record.data.display_type === 'line_option_section';
            var isMultipleSection = record.data.display_type === 'line_multiple_section';

            if (isOptionalSection || isMultipleSection) {
                if (node.attrs.widget === "handle") {
                    return $cell;
                } else if (node.attrs.name === "name") {
                    var nbrColumns = this._getNumberOfCols();
                    if (this.handleField) {
                        nbrColumns--;
                    }
                    if (this.addTrashIcon) {
                        nbrColumns--;
                    }
                    $cell.attr('colspan', nbrColumns);
                } else {
                    $cell.removeClass('o_invisible_modifier');
                    return $cell.addClass('o_hidden');
                }
            }

            return $cell;
        },
    
    });
});