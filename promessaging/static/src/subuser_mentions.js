/** @odoo-module **/

import { Composer } from "@mail/core/common/composer";
import { SuggestionService } from "@mail/core/common/suggestion_service";
import { patch } from "@web/core/utils/patch";

const SUBUSER_DELIMITER = "~";
const SUBUSER_TYPE = "PromessagingSubuser";

patch(SuggestionService.prototype, {
    /** ~ pings an AI sub-user, alongside the standard @ and #. */
    getSupportedDelimiters(thread) {
        return [...super.getSupportedDelimiters(thread), [SUBUSER_DELIMITER]];
    },

    async fetchSuggestions({ delimiter, term }, { thread } = {}) {
        if (delimiter !== SUBUSER_DELIMITER) {
            return super.fetchSuggestions({ delimiter, term }, { thread });
        }
        const subusers = await this.orm.silent.call(
            "promessaging.subuser",
            "get_mention_suggestions",
            [],
            { search: term || "" }
        );
        this.promessagingSubusers = subusers || [];
    },

    searchSuggestions({ delimiter, term }, { thread, sort = false } = {}) {
        if (delimiter !== SUBUSER_DELIMITER) {
            return super.searchSuggestions({ delimiter, term }, { thread, sort });
        }
        const cleaned = (term || "").toLowerCase();
        const matches = (this.promessagingSubusers || []).filter(
            (subuser) =>
                subuser.handle.toLowerCase().includes(cleaned) ||
                subuser.name.toLowerCase().includes(cleaned)
        );
        return {
            type: SUBUSER_TYPE,
            mainSuggestions: matches,
            extraSuggestions: [],
        };
    },
});

patch(Composer.prototype, {
    get navigableListProps() {
        const props = super.navigableListProps;
        if (!this.hasSuggestions || this.suggestion.state.items.type !== SUBUSER_TYPE) {
            return props;
        }
        const suggestions = [
            ...this.suggestion.state.items.mainSuggestions,
            ...this.suggestion.state.items.extraSuggestions,
        ];
        return {
            ...props,
            optionTemplate: "promessaging.Composer.suggestionSubuser",
            options: suggestions.map((subuser) => ({
                // the delimiter is already in the text, so the label is the bare handle
                label: subuser.handle,
                subuserName: subuser.name,
                subuserDescription: subuser.description || "",
                classList: "o-mail-Composer-suggestion",
            })),
        };
    },
});
