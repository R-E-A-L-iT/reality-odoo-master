/** @odoo-module **/

import { WebsiteSale } from '@website_sale/js/website_sale';

// Empty Attribute URL Changes
WebsiteSale.include({
    /**
     * Sets the url hash from the selected product options.
     *
     * @override
     */
    _setUrlHash: function ($parent) {
        var $attributes = $parent.find('input.js_variant_change:checked, select.js_variant_change option:selected');
        if (!$attributes.length) {
            return;
        }
        var attributeIds = $attributes.toArray().map((elem) => $(elem).data("value_id"));
        // Attribute URL Only Show Variant Products Listing Page
        if (attributeIds.length > 0){
            window.location.replace('#attr=' + attributeIds.join(','));
        }
    },
});


