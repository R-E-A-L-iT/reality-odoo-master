odoo.define('section_and_note_backend', function (require) {
    var CustomSectionRenderer = SectionAndNoteListRenderer.extend({
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
    
}