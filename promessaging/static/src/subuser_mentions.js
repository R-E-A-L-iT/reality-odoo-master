/** @odoo-module **/

import { Composer } from "@mail/core/common/composer";
import { SuggestionService } from "@mail/core/common/suggestion_service";
import { patch } from "@web/core/utils/patch";

const SUBUSER_DELIMITER = "~";
const SUBUSER_TYPE = "PromessagingSubuser";

patch(SuggestionService.prototype, {
    /** ~ pings an AI sub-user, alongside the standard @ and #. */
    getSupportedDelimiters(thread, env) {
        return [...super.getSupportedDelimiters(thread, env), [SUBUSER_DELIMITER]];
    },

    async fetchSuggestions({ delimiter, term }, { thread, abortSignal } = {}) {
        if (delimiter !== SUBUSER_DELIMITER) {
            return super.fetchSuggestions({ delimiter, term }, { thread, abortSignal });
        }
        const subusers = await this.orm.silent.call(
            "promessaging.subuser",
            "get_mention_suggestions",
            [],
            { search: term || "" }
        );
        this.promessagingSubusers = subusers || [];
    },

    searchSuggestions({ delimiter, term }, { thread } = {}) {
        if (delimiter !== SUBUSER_DELIMITER) {
            return super.searchSuggestions({ delimiter, term }, { thread });
        }
        const cleaned = (term || "").toLowerCase();
        const matches = (this.promessagingSubusers || []).filter(
            (subuser) =>
                subuser.handle.toLowerCase().includes(cleaned) ||
                subuser.name.toLowerCase().includes(cleaned)
        );
        return {
            type: SUBUSER_TYPE,
            suggestions: matches,
        };
    },
});

patch(Composer.prototype, {
    get navigableListProps() {
        const props = super.navigableListProps;
        const items = this.suggestion?.state.items;
        if (!this.hasSuggestions || items?.type !== SUBUSER_TYPE) {
            return props;
        }
        const suggestions = items.suggestions || [];
        // HTML composer replaces the typed "~term" with option.label.
        // Text composer keeps the "~" and inserts the bare handle.
        const htmlEnabled = Boolean(this.composerService?.htmlEnabled);
        return {
            ...props,
            optionTemplate: "promessaging.Composer.suggestionSubuser",
            options: suggestions.map((subuser) => ({
                label: subuser.handle,
                insertLabel: htmlEnabled ? `${SUBUSER_DELIMITER}${subuser.handle}` : subuser.handle,
                subuserName: subuser.name,
                subuserDescription: subuser.description || "",
                subuserAvatar: subuser.has_avatar ? subuser.avatar : false,
                subuserInitial: subuser.initial || "?",
                classList: "o-mail-Composer-suggestion",
            })),
            onSelect: (ev, option) => {
                props.onSelect(ev, { ...option, label: option.insertLabel || option.label });
            },
        };
    },
});
