/** @odoo-module **/
// 2026-06-11 - Brainecrew Apps

import { jsonrpc } from "@web/core/network/rpc_service";
import publicWidget from "@web/legacy/js/public/public_widget";

// Static icon markup only — never interpolate user-controlled text (address
// name/street/etc.) into innerHTML. User data is always applied afterwards
// via .textContent/.value/.dataset, which cannot be interpreted as markup.
const ICON_EDIT = '<svg viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M8.5 1.5L10.5 3.5L4 10H2V8L8.5 1.5Z" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const ICON_DELETE = '<svg viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M2 3h8M5 3V2h2v1M4 3v6h4V3H4z" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const ICON_SAVE = '<svg viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg"><polyline points="1.5 6.5 4.5 9.5 10.5 2.5" stroke="currentColor" stroke-width="1.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const ICON_CANCEL = '<svg viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M2.5 2.5l7 7M9.5 2.5l-7 7" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>';

publicWidget.registry.addressSelector = publicWidget.Widget.extend({
    selector: ".o_portal_sale_sidebar",
    events: {
        // Card selection
        "click #rental-address-section": "_onSectionClick",
        // Per-card view/edit toggle
        "click .addr_edit_btn":   "_onEditClick",
        "click .addr_cancel_btn": "_onCancelClick",
        "click .addr_save_btn":   "_onSaveClick",
        "click .addr_delete_btn": "_onDeleteClick",
        // Add new address triggers
        "click #new-address-trigger-invoice":  "_onAddTrigger",
        "click #new-address-trigger-delivery": "_onAddTrigger",
        // Per-card country/state filtering + keyboard shortcuts while editing
        "change .edit-country":     "_onEditCountryChange",
        "keydown .addr_card_edit":  "_onEditKeydown",
    },

    async start() {
        await this._super(...arguments);
        this.orderDetail = this.$el.find("table#sales_order_table").data();
        this._labels = this._readLabels();
        document.querySelectorAll("#rental-address-section .addr_card").forEach(card => {
            this._filterCardStates(card);
        });
    },

    // ── Card selection ──────────────────────────────────────────────────────

    async _onSectionClick(ev) {
        if (ev.target.closest(".addr_action_btn"))    return;
        if (ev.target.closest(".addr_card.add_card")) return;
        if (ev.target.closest(".addr_card_edit"))     return;

        const card = ev.target.closest(".addr_card[data-partner-id]");
        if (!card || card.classList.contains("editing")) return;

        const partnerId   = card.dataset.partnerId;
        const addressType = card.dataset.addressType;
        if (!partnerId || !addressType) return;

        const route = addressType === "invoice"
            ? "/my/orders/" + this.orderDetail.orderId + "/select_invoice_address"
            : "/my/orders/" + this.orderDetail.orderId + "/select_delivery_address";

        const result = await jsonrpc(route, {
            partner_id:   parseInt(partnerId),
            access_token: this.orderDetail.token,
        });

        if (result && result.success) {
            this._setActiveCard(this._containerId(addressType), partnerId);
        }
    },

    _setActiveCard(containerId, partnerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.querySelectorAll(".addr_card[data-partner-id]").forEach(card => {
            card.classList.toggle("current", card.dataset.partnerId == String(partnerId));
        });
    },

    // ── Add a brand-new address: a blank card appears in edit mode ─────────

    _onAddTrigger(ev) {
        ev.stopImmediatePropagation();
        const addressType = ev.currentTarget.id === "new-address-trigger-invoice" ? "invoice" : "delivery";
        const container = document.getElementById(this._containerId(addressType));
        if (!container) return;

        // Only one unsaved blank card at a time — focus it instead of stacking more.
        // (The add-tile itself also lacks data-partner-id, so it must be excluded here.)
        const pending = container.querySelector(".addr_card:not(.add_card):not([data-partner-id])");
        if (pending) {
            pending.querySelector(".edit-name")?.focus();
            return;
        }

        this._closeAllEdits(null);
        const card = this._buildBlankCard(addressType);
        this._insertCard(container, card);
        card.querySelector(".edit-name")?.focus();
        card.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
    },

    // ── Edit / Cancel / Save (in place, no popup) ───────────────────────────

    _onEditClick(ev) {
        ev.stopImmediatePropagation();
        const card = ev.currentTarget.closest(".addr_card");
        this._closeAllEdits(card);
        this._setCardMode(card, "edit");
        card.querySelector(".edit-name")?.focus();
    },

    _onCancelClick(ev) {
        ev.stopImmediatePropagation();
        this._discardCardEdit(ev.currentTarget.closest(".addr_card"));
    },

    _discardCardEdit(card) {
        if (!card) return;
        if (!card.dataset.partnerId) {
            // Never saved — just remove the blank card.
            card.remove();
            return;
        }
        this._resetEditInputs(card);
        this._setCardMode(card, "view");
    },

    _closeAllEdits(exceptCard) {
        document.querySelectorAll("#rental-address-section .addr_card.editing").forEach(card => {
            if (card !== exceptCard) this._discardCardEdit(card);
        });
    },

    async _onSaveClick(ev) {
        ev.stopImmediatePropagation();
        const card = ev.currentTarget.closest(".addr_card");
        if (card.dataset.saving === "1") return; // already persisting this card
        const editDiv = card.querySelector(".addr_card_edit");
        const viewDiv = card.querySelector(".addr_card_view");
        const addressType = card.dataset.addressType;
        // Only a blank new card (from "Add Address") needs creating. The
        // "Default" card always has a partner-id (the order's own contact)
        // and is edited in place — that's the point of it representing the
        // company's main address.
        const isCreate = !card.dataset.partnerId;

        const countryEl = editDiv.querySelector(".edit-country");
        const stateEl   = editDiv.querySelector(".edit-state");
        const vals = {
            name:    editDiv.querySelector(".edit-name")?.value.trim()   || "",
            street:  editDiv.querySelector(".edit-street")?.value.trim() || "",
            city:    editDiv.querySelector(".edit-city")?.value.trim()   || "",
            state:   stateEl?.value   || "",
            zip:     editDiv.querySelector(".edit-zip")?.value.trim()    || "",
            country: countryEl?.value || "",
        };

        // Optimistic UI: the user already sees exactly what they typed, so
        // reflect it immediately instead of making them wait on the network
        // round trip — the actual save happens in the background below.
        const optimistic = {
            name: vals.name,
            street: vals.street,
            city: vals.city,
            zip: vals.zip,
            state: stateEl?.options[stateEl.selectedIndex]?.text || "",
            country: countryEl?.options[countryEl.selectedIndex]?.text || "",
        };
        card.dataset.name      = optimistic.name;
        card.dataset.street    = optimistic.street;
        card.dataset.city      = optimistic.city;
        card.dataset.zip       = optimistic.zip;
        card.dataset.countryId = vals.country;
        card.dataset.stateId   = vals.state;
        viewDiv.querySelector(".name").textContent = optimistic.name;
        viewDiv.querySelector(".lines").innerHTML = this._formatLines(optimistic);
        this._setCardMode(card, "view");
        if (card.dataset.fallback === "1") {
            this._syncTwinDefaultCard(card, addressType, optimistic);
        }

        card.dataset.saving = "1";
        const params = { access_token: this.orderDetail.token, ...vals };
        let route;
        if (isCreate) {
            route = "create_typed_address";
            params.address_type = addressType;
        } else {
            route = "update_address";
            params.partner_id = parseInt(card.dataset.partnerId);
        }

        const result = await jsonrpc("/my/orders/" + this.orderDetail.orderId + "/" + route, params);
        delete card.dataset.saving;

        if (!result || !result.success) {
            // Something went wrong server-side — don't leave the user
            // thinking an unsaved change was saved. Reopen it for editing.
            window.alert("Could not save this address. Please try again.");
            this._setCardMode(card, "edit");
            return;
        }

        if (isCreate) {
            const container = document.getElementById(this._containerId(addressType));
            container?.querySelectorAll(".addr_card[data-partner-id]").forEach(c => c.classList.remove("current"));
            card.classList.add("current");
            card.dataset.partnerId = result.partner_id;
        }
    },

    // Updates the Default card in the OTHER section so both stay in sync,
    // since editing either one writes to the same underlying partner record.
    _syncTwinDefaultCard(card, addressType, result) {
        const otherContainerId = addressType === "invoice" ? "delivery-address-cards" : "invoice-address-cards";
        const twin = document.querySelector(`#${otherContainerId} .addr_card[data-fallback="1"]`);
        if (!twin || twin === card) return;

        twin.dataset.name      = card.dataset.name;
        twin.dataset.street    = card.dataset.street;
        twin.dataset.city      = card.dataset.city;
        twin.dataset.zip       = card.dataset.zip;
        twin.dataset.countryId = card.dataset.countryId;
        twin.dataset.stateId   = card.dataset.stateId;

        const twinView = twin.querySelector(".addr_card_view");
        twinView.querySelector(".name").textContent = result.name || "";
        twinView.querySelector(".lines").innerHTML = this._formatLines(result);

        // Refresh its edit inputs too, so opening Edit on the twin later
        // shows the values that were just saved rather than stale ones.
        if (!twin.classList.contains("editing")) {
            this._resetEditInputs(twin);
        }
    },

    _resetEditInputs(card) {
        const editDiv = card.querySelector(".addr_card_edit");
        if (!editDiv) return;
        const d = card.dataset;
        editDiv.querySelector(".edit-name").value   = d.name   || "";
        editDiv.querySelector(".edit-street").value = d.street || "";
        editDiv.querySelector(".edit-city").value   = d.city   || "";
        editDiv.querySelector(".edit-zip").value    = d.zip    || "";
        editDiv.querySelector(".edit-country").value = d.countryId || "";
        this._filterCardStates(card);
        editDiv.querySelector(".edit-state").value  = d.stateId || "";
    },

    _setCardMode(card, mode) {
        const view = card.querySelector(".addr_card_view");
        const edit = card.querySelector(".addr_card_edit");
        if (mode === "edit") {
            if (view) view.style.display = "none";
            if (edit) edit.style.display = "";
            card.classList.add("editing");
        } else {
            if (edit) edit.style.display = "none";
            if (view) view.style.display = "";
            card.classList.remove("editing");
        }
    },

    // ── Delete ───────────────────────────────────────────────────────────────

    async _onDeleteClick(ev) {
        ev.stopImmediatePropagation();
        const card = ev.currentTarget.closest(".addr_card");
        const partnerId = card.dataset.partnerId;
        const addressType = card.dataset.addressType;
        // Defense in depth — the "Default" card never renders a delete
        // button, but never act on it even if one somehow exists.
        if (!partnerId || card.dataset.fallback === "1") return;

        const confirmed = window.confirm(
            addressType === "invoice"
                ? "Delete this invoice address?"
                : "Delete this delivery address?"
        );
        if (!confirmed) return;

        // Optimistic UI: remove it immediately so the deletion feels instant,
        // then persist in the background. Keep enough to undo the removal
        // if the server call turns out to have failed.
        const container = document.getElementById(this._containerId(addressType));
        const nextSibling = card.nextSibling;
        card.remove();

        const result = await jsonrpc(
            "/my/orders/" + this.orderDetail.orderId + "/delete_address",
            {
                access_token: this.orderDetail.token,
                partner_id:   parseInt(partnerId),
                address_type: addressType,
            }
        );

        if (!result || !result.success) {
            // Roll back: the delete didn't actually happen, so put it back.
            if (container) {
                if (nextSibling) container.insertBefore(card, nextSibling);
                else container.appendChild(card);
            }
            window.alert("Could not delete this address. Please try again.");
            return;
        }

        // The server always falls back to the order's main contact when the
        // deleted address was selected — that's the permanent "Default" card.
        if (result.was_selected) {
            container?.querySelectorAll(".addr_card[data-partner-id]").forEach(c => c.classList.remove("current"));
            container?.querySelector('.addr_card[data-fallback="1"]')?.classList.add("current");
        }
    },

    // ── Blank "Add Address" card builder ────────────────────────────────────

    _buildBlankCard(addressType) {
        const card = document.createElement("div");
        card.className = "addr_card";
        card.dataset.addressType = addressType;

        const view = document.createElement("div");
        view.className = "addr_card_view";
        view.innerHTML =
            '<div class="addr_card_actions">' +
                '<button class="addr_action_btn addr_edit_btn" title="' + this._labels.editTitle + '">' + ICON_EDIT + '</button>' +
                '<button class="addr_action_btn addr_delete_btn" title="' + this._labels.deleteTitle + '">' + ICON_DELETE + '</button>' +
            '</div>' +
            '<div class="name"></div>' +
            '<div class="lines"></div>';

        const edit = document.createElement("div");
        edit.className = "addr_card_edit";
        edit.style.display = "none";
        edit.innerHTML =
            '<div class="addr_card_actions">' +
                '<button class="addr_action_btn addr_save_btn" title="' + this._labels.saveTitle + '">' + ICON_SAVE + '</button>' +
                '<button class="addr_action_btn addr_cancel_btn" title="' + this._labels.cancelTitle + '">' + ICON_CANCEL + '</button>' +
            '</div>' +
            '<div class="edit_row"><input type="text" class="edit-name" placeholder="' + this._labels.name + '"/></div>' +
            '<div class="edit_row"><input type="text" class="edit-street" placeholder="' + this._labels.street + '"/></div>' +
            '<div class="edit_row"><input type="text" class="edit-city" placeholder="' + this._labels.city + '"/></div>' +
            '<div class="edit_row edit_row--split">' +
                '<select class="edit-country"></select>' +
                '<select class="edit-state"></select>' +
            '</div>' +
            '<div class="edit_row"><input type="text" class="edit-zip" placeholder="' + this._labels.zip + '"/></div>';

        this._cloneOptionsInto(edit.querySelector(".edit-country"), "addr-country-options-template");
        this._cloneOptionsInto(edit.querySelector(".edit-state"),   "addr-state-options-template");

        card.appendChild(view);
        card.appendChild(edit);
        this._filterCardStates(card);
        this._setCardMode(card, "edit");
        return card;
    },

    _cloneOptionsInto(select, templateId) {
        const tpl = document.getElementById(templateId);
        if (tpl && select) select.innerHTML = tpl.innerHTML;
    },

    _insertCard(container, card) {
        if (!container) return;
        // The "Add Address" tile must always stay last in the row.
        const addTile = container.querySelector(".add_card");
        if (addTile) {
            container.insertBefore(card, addTile);
        } else {
            container.appendChild(card);
        }
    },

    _formatLines(data) {
        const parts = [
            data.street,
            [data.city, data.state, data.zip].filter(Boolean).join(", "),
            data.country,
        ].filter(Boolean);
        // Build each line through textContent so any user-entered text is
        // escaped, then join with a literal <br> — the only real markup.
        return parts.map(p => {
            const d = document.createElement("div");
            d.textContent = p;
            return d.innerHTML;
        }).join("<br>");
    },

    _containerId(addressType) {
        return addressType === "invoice" ? "invoice-address-cards" : "delivery-address-cards";
    },

    // ── Country/state filtering, scoped to whichever card is being edited ──

    _onEditCountryChange(ev) {
        const card = ev.target.closest(".addr_card");
        if (card) this._filterCardStates(card);
    },

    _filterCardStates(card) {
        const countryEl = card.querySelector(".edit-country");
        const stateEl   = card.querySelector(".edit-state");
        if (!countryEl || !stateEl) return;
        const selected = countryEl.value;
        Array.from(stateEl.options).forEach(opt => {
            if (!opt.value) return;
            opt.hidden = !!(selected && opt.dataset.countryId !== selected);
        });
        const cur = stateEl.options[stateEl.selectedIndex];
        if (cur?.value && selected && cur.dataset.countryId !== selected) {
            stateEl.value = "";
        }
    },

    // ── Keyboard shortcuts while editing a card ─────────────────────────────

    _onEditKeydown(ev) {
        if (ev.key === "Enter" && ev.target.tagName !== "SELECT") {
            ev.preventDefault();
            ev.currentTarget.querySelector(".addr_save_btn")?.click();
        } else if (ev.key === "Escape") {
            ev.currentTarget.querySelector(".addr_cancel_btn")?.click();
        }
    },

    // ── Localized strings, read once from the server-rendered markup so
    //    JS-built cards (blank "Add Address" cards) match the portal's
    //    language without duplicating the translation logic here ───────────

    _readLabels() {
        const anyCard = document.querySelector("#rental-address-section .addr_card:not(.add_card)");
        const editDiv  = anyCard?.querySelector(".addr_card_edit");
        const editBtn  = anyCard?.querySelector(".addr_edit_btn");
        const deleteBtn = document.querySelector("#rental-address-section .addr_delete_btn");
        return {
            name:   editDiv?.querySelector(".edit-name")?.placeholder   || "Name",
            street: editDiv?.querySelector(".edit-street")?.placeholder || "Street",
            city:   editDiv?.querySelector(".edit-city")?.placeholder   || "City",
            zip:    editDiv?.querySelector(".edit-zip")?.placeholder    || "Zip/Postal Code",
            editTitle:    editBtn?.title    || "Edit",
            saveTitle:    editDiv?.querySelector(".addr_save_btn")?.title   || "Save",
            cancelTitle:  editDiv?.querySelector(".addr_cancel_btn")?.title || "Cancel",
            deleteTitle:  deleteBtn?.title || "Delete",
        };
    },
});
