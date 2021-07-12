/*odoo.define('proquotes.section_and_note_backend', function (require) {
// The goal of this file is to contain JS hacks related to allowing
// section and note on sale order and invoice.

// [UPDATED] now also allows configuring products on sale order.

"use strict";
var FieldChar = require('web.basic_fields').FieldChar;
var FieldOne2Many = require('web.relational_fields').FieldOne2Many;
var fieldRegistry = require('web.field_registry');
var ListFieldText = require('web.basic_fields').ListFieldText;
var ListRenderer = require('web.ListRenderer');

var SectionAndNoteListRenderer = ListRenderer.extend({

    _renderBodyCell: function (record, node, index, options) {
        var $cell = this._super.apply(this, arguments);

        var is_section = record.data.display_type === 'line_section';
        var is_note = record.data.display_type === 'line_note';
        var is_multiple_section = record.data.display_type === 'line_multiple_section';
        var is_option_section = record.data.display_type === 'line_option_section';

        if (is_multiple_section || is_option_section || is_section || is_note) {
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

    _renderRow: function (record, index) {
        var $row = this._super.apply(this, arguments);

        if (record.data.display_type) {
            $row.addClass('o_is_' + record.data.display_type);
        }

        return $row;
    },
    _renderView: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.$('.o_list_table').addClass('o_section_and_note_list_view');
        });
    }
});

// We create a custom widget because this is the cleanest way to do it:
// to be sure this custom code will only impact selected fields having the widget
// and not applied to any other existing ListRenderer.
var SectionAndNoteFieldOne2Many = FieldOne2Many.extend({
    _getRenderer: function () {
        if (this.view.arch.tag === 'tree') {
            return SectionAndNoteListRenderer;
        }
        return this._super.apply(this, arguments);
    },
});

// This is a merge between a FieldText and a FieldChar.
// We want a FieldChar for section,
// and a FieldText for the rest (product and note).
var SectionAndNoteFieldText = function (parent, name, record, options) {
    var isSection = record.data.display_type === 'line_section';
    var Constructor = isSection ? FieldChar : ListFieldText;
    return new Constructor(parent, name, record, options);
};

fieldRegistry.add('section_and_note_one2many', SectionAndNoteFieldOne2Many);
fieldRegistry.add('section_and_note_text', SectionAndNoteFieldText);

return SectionAndNoteListRenderer;
});*/
