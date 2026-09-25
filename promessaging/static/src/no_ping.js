/** @odoo-module **/

import { SuggestionService } from "@mail/core/common/suggestion_service";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

/** Partners whose user asked not to be pinged. */
function blockedPartnerIds() {
    return new Set(session.promessaging_no_ping_partner_ids || []);
}

patch(SuggestionService.prototype, {
    /**
     * The composer suggests partners straight from the browser's own store, so
     * filtering them server-side is not enough on its own.
     */
    searchPartnerSuggestions(cleanedSearchTerm, thread, sort) {
        const result = super.searchPartnerSuggestions(cleanedSearchTerm, thread, sort);
        const blocked = blockedPartnerIds();
        if (!blocked.size) {
            return result;
        }
        const keep = (partners) => (partners || []).filter((partner) => !blocked.has(partner.id));
        return {
            ...result,
            mainSuggestions: keep(result.mainSuggestions),
            extraSuggestions: keep(result.extraSuggestions),
        };
    },
});
