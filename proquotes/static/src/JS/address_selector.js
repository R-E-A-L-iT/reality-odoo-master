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
        "change .edit-state":       "_onEditFieldInput",
        "input .edit-name":         "_onEditFieldInput",
        "input .edit-street":       "_onEditFieldInput",
        "input .edit-street2":      "_onEditFieldInput",
        "input .edit-city":         "_onEditFieldInput",
        "input .edit-zip":          "_onEditFieldInput",
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
        // The "Default" card is the company's main address and is never
        // editable here — if they need a different invoice/delivery address
        // they add a new one. (The edit button isn't rendered on it, but
        // guard anyway.)
        if (card.dataset.fallback === "1") return;
        this._closeAllEdits(card);
        this._clearFieldErrors(card);
        this._setCardMode(card, "edit");
        card.querySelector(".edit-name")?.focus();
    },

    _onCancelClick(ev) {
        ev.stopImmediatePropagation();
        this._discardCardEdit(ev.currentTarget.closest(".addr_card"));
    },

    _discardCardEdit(card) {
        if (!card) return;
        this._clearFieldErrors(card);
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
        const addressType = card.dataset.addressType;
        // Only a blank new card (from "Add Address") needs creating. The
        // "Default" card always has a partner-id (the order's own contact)
        // and is edited in place — that's the point of it representing the
        // company's main address.
        const isCreate = !card.dataset.partnerId;

        this._clearFieldErrors(card);
        const vals = this._readEditVals(editDiv);
        const missing = this._missingFields(editDiv, vals);
        if (missing.length) {
            this._showFieldErrors(card, missing);
            this._focusField(card, missing[0]);
            return;
        }

        const countryEl = editDiv.querySelector(".edit-country");
        const stateEl   = editDiv.querySelector(".edit-state");
        // Optimistic UI: the user already sees exactly what they typed, so
        // reflect it immediately instead of making them wait on the network
        // round trip — the actual save happens in the background below.
        const optimistic = {
            name: vals.name || "",
            street: vals.street || "",
            street2: vals.street2 !== undefined ? vals.street2 : (card.dataset.street2 || ""),
            city: vals.city || "",
            zip: vals.zip || "",
            state: stateEl?.value ? (stateEl.options[stateEl.selectedIndex]?.text || "") : "",
            country: countryEl?.value ? (countryEl.options[countryEl.selectedIndex]?.text || "") : "",
            countryId: vals.country !== undefined ? vals.country : (card.dataset.countryId || ""),
            stateId: vals.state !== undefined ? vals.state : (card.dataset.stateId || ""),
        };
        const snapshot = this._captureCard(card);
        let twinSnapshot = null;
        const twin = card.dataset.fallback === "1" ? this._twinDefaultCard(addressType) : null;
        if (twin) twinSnapshot = this._captureCard(twin);

        this._paintCard(card, optimistic);
        this._setCardMode(card, "view");
        if (twin) this._syncTwinDefaultCard(card, addressType, optimistic);

        card.dataset.saving = "1";
        const params = { access_token: this.orderDetail.token };
        Object.entries(vals).forEach(([key, value]) => {
            if (value !== undefined) params[key] = value;
        });
        let route;
        if (isCreate) {
            route = "create_typed_address";
            params.address_type = addressType;
        } else {
            route = "update_address";
            params.partner_id = parseInt(card.dataset.partnerId);
        }

        let result;
        try {
            result = await jsonrpc("/my/orders/" + this.orderDetail.orderId + "/" + route, params);
        } catch (_err) {
            result = null;
        }
        delete card.dataset.saving;

        if (!result || !result.success) {
            // Don't leave the card looking saved, and don't wipe what they
            // typed — the edit inputs still hold it. Dataset goes back so
            // Cancel restores the last stored address.
            this._restoreCard(card, snapshot);
            if (twinSnapshot) this._restoreCard(twin, twinSnapshot);
            this._setCardMode(card, "edit");
            if (result && result.fields && result.fields.length) {
                this._showFieldErrors(card, result.fields);
                this._focusField(card, result.fields[0]);
            } else {
                this._showFormError(card, (result && result.error) || this._labels.errSave);
            }
            return;
        }

        this._applyServerResult(card, result);
        if (isCreate) {
            const container = document.getElementById(this._containerId(addressType));
            container?.querySelectorAll(".addr_card[data-partner-id]").forEach(c => c.classList.remove("current"));
            card.classList.add("current");
            card.dataset.partnerId = result.partner_id;
        }
    },

    // Only inputs that are actually on the card are returned. A missing
    // input stays undefined so it is left out of the payload and the server
    // does not blank the stored value.
    _readEditVals(editDiv) {
        const read = (selector) => {
            const el = editDiv.querySelector(selector);
            if (!el) return undefined;
            return (el.value || "").trim();
        };
        return {
            name: read(".edit-name"),
            street: read(".edit-street"),
            street2: read(".edit-street2"),
            city: read(".edit-city"),
            state: read(".edit-state"),
            zip: read(".edit-zip"),
            country: read(".edit-country"),
        };
    },

    _missingFields(editDiv, vals) {
        const missing = [];
        if (vals.street !== undefined && !vals.street) missing.push("street");
        if (vals.city !== undefined && !vals.city) missing.push("city");
        if (vals.country !== undefined && !vals.country) missing.push("country");
        if (this._countryHasStates(editDiv) && vals.state !== undefined && !vals.state) {
            missing.push("state");
        }
        if (vals.zip !== undefined && !vals.zip) missing.push("zip");
        return missing;
    },

    _countryHasStates(editDiv) {
        const countryEl = editDiv.querySelector(".edit-country");
        const stateEl = editDiv.querySelector(".edit-state");
        if (!countryEl || !stateEl || !countryEl.value) return false;
        const selected = countryEl.value;
        return Array.from(stateEl.options).some(
            (opt) => opt.value && opt.dataset.countryId === selected
        );
    },

    _showFieldErrors(card, fields) {
        const messages = {
            street: this._labels.errStreet,
            city: this._labels.errCity,
            state: this._labels.errState,
            zip: this._labels.errZip,
            country: this._labels.errCountry,
        };
        let shown = false;
        fields.forEach((field) => {
            const input = card.querySelector(".edit-" + field);
            const err = card.querySelector('.addr_field_error[data-field="' + field + '"]');
            if (input) {
                input.classList.add("addr_invalid");
                input.setAttribute("aria-invalid", "true");
            }
            if (err && messages[field]) {
                err.textContent = messages[field];
                err.hidden = false;
                shown = true;
            }
        });
        if (!shown) this._showFormError(card, this._labels.errSave);
    },

    _showFormError(card, message) {
        const el = card.querySelector(".addr_form_error");
        if (!el) {
            window.alert(message);
            return;
        }
        el.textContent = message;
        el.hidden = false;
    },

    _clearFieldErrors(card) {
        if (!card) return;
        card.querySelectorAll(".addr_invalid").forEach((el) => {
            el.classList.remove("addr_invalid");
            el.removeAttribute("aria-invalid");
        });
        card.querySelectorAll(".addr_field_error, .addr_form_error").forEach((el) => {
            el.textContent = "";
            el.hidden = true;
        });
    },

    _clearOneField(card, field) {
        const input = card.querySelector(".edit-" + field);
        if (input) {
            input.classList.remove("addr_invalid");
            input.removeAttribute("aria-invalid");
        }
        const err = card.querySelector('.addr_field_error[data-field="' + field + '"]');
        if (err) {
            err.textContent = "";
            err.hidden = true;
        }
    },

    _onEditFieldInput(ev) {
        const input = ev.target.closest("input, select");
        const card = input?.closest(".addr_card");
        if (!input || !card) return;
        const field = ["name", "street", "street2", "city", "state", "zip", "country"].find((name) =>
            input.classList.contains("edit-" + name)
        );
        if (field) this._clearOneField(card, field);
    },

    _focusField(card, field) {
        card.querySelector(".edit-" + field)?.focus();
    },

    _captureCard(card) {
        const view = card.querySelector(".addr_card_view");
        return {
            name: card.dataset.name || "",
            street: card.dataset.street || "",
            street2: card.dataset.street2 || "",
            city: card.dataset.city || "",
            zip: card.dataset.zip || "",
            countryId: card.dataset.countryId || "",
            stateId: card.dataset.stateId || "",
            nameText: view?.querySelector(".name")?.textContent || "",
            linesHtml: view?.querySelector(".lines")?.innerHTML || "",
        };
    },

    _restoreCard(card, snap) {
        if (!card || !snap) return;
        card.dataset.name = snap.name;
        card.dataset.street = snap.street;
        card.dataset.street2 = snap.street2;
        card.dataset.city = snap.city;
        card.dataset.zip = snap.zip;
        card.dataset.countryId = snap.countryId;
        card.dataset.stateId = snap.stateId;
        const view = card.querySelector(".addr_card_view");
        const nameEl = view?.querySelector(".name");
        const linesEl = view?.querySelector(".lines");
        if (nameEl) nameEl.textContent = snap.nameText;
        if (linesEl) linesEl.innerHTML = snap.linesHtml;
    },

    _paintCard(card, data) {
        card.dataset.name = data.name || "";
        card.dataset.street = data.street || "";
        card.dataset.street2 = data.street2 || "";
        card.dataset.city = data.city || "";
        card.dataset.zip = data.zip || "";
        if (data.countryId !== undefined) card.dataset.countryId = data.countryId || "";
        if (data.stateId !== undefined) card.dataset.stateId = data.stateId || "";
        const view = card.querySelector(".addr_card_view");
        const nameEl = view?.querySelector(".name");
        const linesEl = view?.querySelector(".lines");
        if (nameEl) nameEl.textContent = data.name || "";
        if (linesEl) linesEl.innerHTML = this._formatLines(data);
    },

    _applyServerResult(card, result) {
        this._paintCard(card, {
            name: result.name || "",
            street: result.street || "",
            street2: result.street2 || "",
            city: result.city || "",
            zip: result.zip || "",
            state: result.state || "",
            country: result.country || "",
            countryId: card.dataset.countryId || "",
            stateId: card.dataset.stateId || "",
        });
        const edit = card.querySelector(".addr_card_edit");
        const assign = (selector, value) => {
            const input = edit?.querySelector(selector);
            if (input && input.tagName === "INPUT") input.value = value || "";
        };
        assign(".edit-name", result.name);
        assign(".edit-street", result.street);
        assign(".edit-street2", result.street2);
        assign(".edit-city", result.city);
        assign(".edit-zip", result.zip);
    },

    _twinDefaultCard(addressType) {
        const otherContainerId = addressType === "invoice" ? "delivery-address-cards" : "invoice-address-cards";
        return document.querySelector(`#${otherContainerId} .addr_card[data-fallback="1"]`);
    },

    // Updates the Default card in the OTHER section so both stay in sync,
    // since editing either one writes to the same underlying partner record.
    _syncTwinDefaultCard(card, addressType, result) {
        const otherContainerId = addressType === "invoice" ? "delivery-address-cards" : "invoice-address-cards";
        const twin = document.querySelector(`#${otherContainerId} .addr_card[data-fallback="1"]`);
        if (!twin || twin === card) return;

        twin.dataset.name      = card.dataset.name;
        twin.dataset.street    = card.dataset.street;
        twin.dataset.street2   = card.dataset.street2;
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
        const street2El = editDiv.querySelector(".edit-street2");
        if (street2El) street2El.value = d.street2 || "";
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
                '<button type="button" class="addr_action_btn addr_edit_btn" title="' + this._escAttr(this._labels.editTitle) + '">' + ICON_EDIT + '</button>' +
                '<button type="button" class="addr_action_btn addr_delete_btn" title="' + this._escAttr(this._labels.deleteTitle) + '">' + ICON_DELETE + '</button>' +
            '</div>' +
            '<div class="name"></div>' +
            '<div class="lines"></div>';

        const edit = document.createElement("div");
        edit.className = "addr_card_edit";
        edit.style.display = "none";
        edit.innerHTML =
            '<div class="addr_card_actions">' +
                '<button type="button" class="addr_action_btn addr_save_btn" title="' + this._escAttr(this._labels.saveTitle) + '">' + ICON_SAVE + '</button>' +
                '<button type="button" class="addr_action_btn addr_cancel_btn" title="' + this._escAttr(this._labels.cancelTitle) + '">' + ICON_CANCEL + '</button>' +
            '</div>' +
            '<div class="edit_row"><input type="text" class="edit-name" placeholder="' + this._escAttr(this._labels.name) + '"/></div>' +
            '<div class="edit_row"><input type="text" class="edit-street" placeholder="' + this._escAttr(this._labels.street) + '"/>' +
                '<div class="addr_field_error" data-field="street" hidden></div></div>' +
            '<div class="edit_row"><input type="text" class="edit-street2" placeholder="' + this._escAttr(this._labels.street2) + '"/></div>' +
            '<div class="edit_row"><input type="text" class="edit-city" placeholder="' + this._escAttr(this._labels.city) + '"/>' +
                '<div class="addr_field_error" data-field="city" hidden></div></div>' +
            '<div class="edit_row edit_row--split">' +
                '<div class="edit_field"><select class="edit-country"></select>' +
                    '<div class="addr_field_error" data-field="country" hidden></div></div>' +
                '<div class="edit_field"><select class="edit-state"></select>' +
                    '<div class="addr_field_error" data-field="state" hidden></div></div>' +
            '</div>' +
            '<div class="edit_row"><input type="text" class="edit-zip" placeholder="' + this._escAttr(this._labels.zip) + '"/>' +
                '<div class="addr_field_error" data-field="zip" hidden></div></div>' +
            '<div class="addr_form_error" hidden></div>';

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

    _escAttr(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/"/g, "&quot;")
            .replace(/</g, "&lt;");
    },

    _formatLines(data) {
        let cityLine = "";
        if (data.city) {
            cityLine += data.city;
            if (data.state || data.zip) cityLine += ", ";
        }
        if (data.state) {
            cityLine += data.state;
            if (data.zip) cityLine += " ";
        }
        if (data.zip) cityLine += data.zip;
        const parts = [
            data.street,
            data.street2,
            cityLine.trim(),
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
        if (!card) return;
        this._filterCardStates(card);
        this._clearOneField(card, "country");
        this._clearOneField(card, "state");
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
        // The Default card no longer renders an edit button, so read the edit
        // tooltip from any card that still has one (a non-default address).
        const editBtn  = document.querySelector("#rental-address-section .addr_edit_btn");
        const deleteBtn = document.querySelector("#rental-address-section .addr_delete_btn");
        const errBox = document.getElementById("addr-error-labels");
        const err = (field, fallback) => {
            const text = errBox?.querySelector('[data-field="' + field + '"]')?.textContent?.trim();
            return text || fallback;
        };
        return {
            name:   editDiv?.querySelector(".edit-name")?.placeholder   || "Name",
            street: editDiv?.querySelector(".edit-street")?.placeholder || "Street",
            street2: editDiv?.querySelector(".edit-street2")?.placeholder || "Suite / Unit",
            city:   editDiv?.querySelector(".edit-city")?.placeholder   || "City",
            zip:    editDiv?.querySelector(".edit-zip")?.placeholder    || "Zip/Postal Code",
            editTitle:    editBtn?.title    || "Edit",
            saveTitle:    editDiv?.querySelector(".addr_save_btn")?.title   || "Save",
            cancelTitle:  editDiv?.querySelector(".addr_cancel_btn")?.title || "Cancel",
            deleteTitle:  deleteBtn?.title || "Delete",
            errStreet: err("street", "Street is required."),
            errCity: err("city", "City is required."),
            errCountry: err("country", "Country is required."),
            errState: err("state", "State/Province is required."),
            errZip: err("zip", "Zip/Postal code is required."),
            errSave: err("save", "Could not save this address. Please try again."),
        };
    },
});
