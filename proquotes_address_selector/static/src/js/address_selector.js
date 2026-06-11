/** @odoo-module **/
// 2026-06-11 - Brainecrew Apps

import { jsonrpc } from "@web/core/network/rpc_service";
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.addressSelector = publicWidget.Widget.extend({
    selector: ".o_portal_sale_sidebar",
    events: {
        // Card selection
        "click #invoice-address-cards .addr_card[data-partner-id]": "_onSelectInvoiceCard",
        "click #delivery-address-cards .addr_card[data-partner-id]": "_onSelectDeliveryCard",
        // Edit buttons
        "click .addr_edit_btn": "_onEditAddress",
        // Delete buttons
        "click .addr_delete_btn": "_onDeleteAddress",
        // New address trigger
        "click #new-invoice-trigger":  "_onNewInvoiceTrigger",
        "click #new-delivery-trigger": "_onNewDeliveryTrigger",
        // Save / cancel new address
        "click #save-new-invoice-address":    "_onSaveNewInvoice",
        "click #save-new-delivery-address":   "_onSaveNewDelivery",
        "click #cancel-new-invoice-address":  "_onCancelNewInvoice",
        "click #cancel-new-delivery-address": "_onCancelNewDelivery",
        // Save / cancel edit address
        "click #save-edit-invoice-address":    "_onSaveEditInvoice",
        "click #save-edit-delivery-address":   "_onSaveEditDelivery",
        "click #cancel-edit-invoice-address":  "_onCancelEditInvoice",
        "click #cancel-edit-delivery-address": "_onCancelEditDelivery",
        // Country dropdowns
        "change #new-invoice-country":  "_onNewInvoiceCountryChange",
        "change #new-delivery-country": "_onNewDeliveryCountryChange",
        "change #edit-invoice-country": "_onEditInvoiceCountryChange",
        "change #edit-delivery-country":"_onEditDeliveryCountryChange",
    },

    async start() {
        await this._super(...arguments);
        this.orderDetail = this.$el.find("table#sales_order_table").data();
    },

    // ── Country/state filtering ───────────────────────────────────────────────

    _filterStatesByCountry(countryId, stateId) {
        const countryEl = document.getElementById(countryId);
        const stateEl   = document.getElementById(stateId);
        if (!countryEl || !stateEl) return;
        const selected = countryEl.value;
        Array.from(stateEl.options).forEach(opt => {
            if (!opt.value) return;
            opt.hidden = !!(selected && opt.dataset.countryId != selected);
        });
        // Clear state if it no longer matches country
        const sel = stateEl.options[stateEl.selectedIndex];
        if (sel?.value && selected && sel.dataset.countryId != selected) {
            stateEl.value = "";
        }
    },

    _onNewInvoiceCountryChange()  { this._filterStatesByCountry("new-invoice-country",  "new-invoice-state");  },
    _onNewDeliveryCountryChange() { this._filterStatesByCountry("new-delivery-country", "new-delivery-state"); },
    _onEditInvoiceCountryChange() { this._filterStatesByCountry("edit-invoice-country", "edit-invoice-state"); },
    _onEditDeliveryCountryChange(){ this._filterStatesByCountry("edit-delivery-country","edit-delivery-state");},

    // ── Card selection ────────────────────────────────────────────────────────

    _setActiveCard(containerId, partnerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.querySelectorAll(".addr_card[data-partner-id]").forEach(card => {
            card.classList.toggle("current", card.dataset.partnerId == String(partnerId));
        });
    },

    async _onSelectInvoiceCard(ev) {
        if (ev.target.closest(".addr_action_btn")) return;
        const card = ev.currentTarget;
        const partnerId = card.dataset.partnerId;
        if (!partnerId) return;
        const result = await jsonrpc(
            "/my/orders/" + this.orderDetail.orderId + "/select_invoice_address",
            { partner_id: parseInt(partnerId), access_token: this.orderDetail.token }
        );
        if (result && result.success) {
            this._setActiveCard("invoice-address-cards", partnerId);
        }
    },

    async _onSelectDeliveryCard(ev) {
        if (ev.target.closest(".addr_action_btn")) return;
        const card = ev.currentTarget;
        const partnerId = card.dataset.partnerId;
        if (!partnerId) return;
        const result = await jsonrpc(
            "/my/orders/" + this.orderDetail.orderId + "/select_delivery_address",
            { partner_id: parseInt(partnerId), access_token: this.orderDetail.token }
        );
        if (result && result.success) {
            this._setActiveCard("delivery-address-cards", partnerId);
        }
    },

    // ── Edit address ──────────────────────────────────────────────────────────

    _onEditAddress(ev) {
        ev.stopPropagation();
        const btn = ev.currentTarget;
        const type      = btn.dataset.addressType;
        const partnerId = btn.dataset.partnerId;
        const prefix    = type === "invoice" ? "edit-invoice" : "edit-delivery";

        // Hide new-address form if open
        const newForm = document.getElementById(`new-${type}-address-form`);
        if (newForm) newForm.style.display = "none";

        // Populate hidden partner id
        const hiddenId = document.getElementById(`${prefix}-partner-id`);
        if (hiddenId) hiddenId.value = partnerId;

        // Populate fields from data attributes on the button
        this._setVal(`${prefix}-name`,   btn.dataset.name   || "");
        this._setVal(`${prefix}-street`, btn.dataset.street || "");
        this._setVal(`${prefix}-city`,   btn.dataset.city   || "");
        this._setVal(`${prefix}-zip`,    btn.dataset.zip    || "");

        const countryEl = document.getElementById(`${prefix}-country`);
        const stateEl   = document.getElementById(`${prefix}-state`);
        if (countryEl) countryEl.value = btn.dataset.countryId || "";
        this._filterStatesByCountry(`${prefix}-country`, `${prefix}-state`);
        if (stateEl)   stateEl.value   = btn.dataset.stateId   || "";

        // Show the form
        const editForm = document.getElementById(`${prefix}-address-form`);
        if (editForm) editForm.style.display = "";
        editForm?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    },

    async _onSaveEditInvoice() {
        await this._saveEdit("invoice");
    },

    async _onSaveEditDelivery() {
        await this._saveEdit("delivery");
    },

    async _saveEdit(type) {
        const prefix    = `edit-${type}`;
        const partnerId = document.getElementById(`${prefix}-partner-id`)?.value;
        if (!partnerId) return;

        const result = await jsonrpc(
            "/my/orders/" + this.orderDetail.orderId + "/update_address",
            {
                access_token: this.orderDetail.token,
                partner_id: parseInt(partnerId),
                name:    document.getElementById(`${prefix}-name`)?.value    || "",
                street:  document.getElementById(`${prefix}-street`)?.value  || "",
                city:    document.getElementById(`${prefix}-city`)?.value    || "",
                state:   document.getElementById(`${prefix}-state`)?.value   || "",
                zip:     document.getElementById(`${prefix}-zip`)?.value     || "",
                country: document.getElementById(`${prefix}-country`)?.value || "",
            }
        );
        if (result && result.success) {
            // Update the card in place
            const containerId = `${type}-address-cards`;
            const card = document.querySelector(`#${containerId} .addr_card[data-partner-id="${partnerId}"]`);
            if (card) {
                const nameEl = card.querySelector(".name");
                if (nameEl) nameEl.textContent = result.name;

                const linesEl = card.querySelector(".lines");
                if (linesEl) {
                    const parts = [
                        result.street,
                        [result.city, result.state, result.zip].filter(Boolean).join(", "),
                        result.country,
                    ].filter(Boolean);
                    linesEl.textContent = parts.join("\n");
                }

                // Update data attributes on edit button so re-editing is accurate
                const editBtn = card.querySelector(".addr_edit_btn");
                if (editBtn) {
                    editBtn.dataset.name      = result.name;
                    editBtn.dataset.street    = result.street;
                    editBtn.dataset.city      = result.city;
                    editBtn.dataset.zip       = result.zip;
                }
            }
            // Hide edit form
            const form = document.getElementById(`${prefix}-address-form`);
            if (form) form.style.display = "none";
        }
    },

    _onCancelEditInvoice()  { this._hideForm("edit-invoice-address-form");  },
    _onCancelEditDelivery() { this._hideForm("edit-delivery-address-form"); },

    // ── Delete address ────────────────────────────────────────────────────────

    async _onDeleteAddress(ev) {
        ev.stopPropagation();
        const btn       = ev.currentTarget;
        const partnerId = btn.dataset.partnerId;
        const type      = btn.dataset.addressType;

        const confirmed = window.confirm(
            type === "invoice"
                ? "Delete this invoice address?"
                : "Delete this delivery address?"
        );
        if (!confirmed) return;

        const result = await jsonrpc(
            "/my/orders/" + this.orderDetail.orderId + "/delete_address",
            {
                access_token: this.orderDetail.token,
                partner_id:   parseInt(partnerId),
                address_type: type,
            }
        );

        if (result && result.success) {
            const containerId = `${type}-address-cards`;
            const card = document.querySelector(`#${containerId} .addr_card[data-partner-id="${partnerId}"]`);
            if (card) card.remove();

            // Hide any open edit/new forms for this type
            this._hideForm(`edit-${type}-address-form`);

            // If the deleted address was selected, select the first remaining card
            if (result.was_selected) {
                const container  = document.getElementById(containerId);
                const firstCard  = container?.querySelector(".addr_card[data-partner-id]");
                if (firstCard) {
                    firstCard.classList.add("current");
                    // Persist selection to backend
                    const newPartnerId = parseInt(firstCard.dataset.partnerId);
                    const route = type === "invoice"
                        ? "/my/orders/" + this.orderDetail.orderId + "/select_invoice_address"
                        : "/my/orders/" + this.orderDetail.orderId + "/select_delivery_address";
                    jsonrpc(route, { partner_id: newPartnerId, access_token: this.orderDetail.token });
                }
            }

            // Show empty state if no cards remain
            const container = document.getElementById(containerId);
            const remaining = container?.querySelectorAll(".addr_card[data-partner-id]").length || 0;
            if (remaining === 0) {
                const emptyState = document.createElement("div");
                emptyState.className = "addr_empty_state";
                emptyState.innerHTML = '<i class="fa fa-inbox"></i><div>No saved addresses on file</div>';
                const trigger = document.getElementById(`new-${type}-trigger`);
                container.insertBefore(emptyState, trigger);
            }
        }
    },

    // ── New address trigger ───────────────────────────────────────────────────

    _onNewInvoiceTrigger() {
        this._hideForm("edit-invoice-address-form");
        this._toggleForm("new-invoice-address-form");
    },

    _onNewDeliveryTrigger() {
        this._hideForm("edit-delivery-address-form");
        this._toggleForm("new-delivery-address-form");
    },

    _onCancelNewInvoice()  { this._hideForm("new-invoice-address-form");  },
    _onCancelNewDelivery() { this._hideForm("new-delivery-address-form"); },

    async _onSaveNewInvoice() {
        await this._saveNew("invoice");
    },

    async _onSaveNewDelivery() {
        await this._saveNew("delivery");
    },

    async _saveNew(type) {
        const prefix = `new-${type}`;
        const result = await jsonrpc(
            "/my/orders/" + this.orderDetail.orderId + `/create_${type}_address`,
            {
                access_token: this.orderDetail.token,
                name:    document.getElementById(`${prefix}-name`)?.value    || "",
                street:  document.getElementById(`${prefix}-street`)?.value  || "",
                city:    document.getElementById(`${prefix}-city`)?.value    || "",
                state:   document.getElementById(`${prefix}-state`)?.value   || "",
                zip:     document.getElementById(`${prefix}-zip`)?.value     || "",
                country: document.getElementById(`${prefix}-country`)?.value || "",
            }
        );
        if (result && result.success) {
            const container = document.getElementById(`${type}-address-cards`);
            const trigger   = document.getElementById(`new-${type}-trigger`);

            // Remove any empty-state placeholder
            container.querySelectorAll(".addr_empty_state").forEach(el => el.remove());

            // Remove current highlight from all cards
            container.querySelectorAll(".addr_card").forEach(c => c.classList.remove("current"));

            // Build and insert new card before the trigger
            const card = this._buildAddressCard(result, type);
            container.insertBefore(card, trigger);

            this._hideForm(`${prefix}-address-form`);
            this._clearForm(prefix);
        }
    },

    // ── DOM helpers ───────────────────────────────────────────────────────────

    _setVal(id, val) {
        const el = document.getElementById(id);
        if (el) el.value = val;
    },

    _hideForm(id) {
        const el = document.getElementById(id);
        if (el) el.style.display = "none";
    },

    _toggleForm(id) {
        const el = document.getElementById(id);
        if (el) el.style.display = el.style.display === "none" ? "" : "none";
    },

    _clearForm(prefix) {
        ["name", "street", "city", "zip"].forEach(f => this._setVal(`${prefix}-${f}`, ""));
        this._setVal(`${prefix}-country`, "");
        this._setVal(`${prefix}-state`,   "");
    },

    _buildAddressCard(data, addressType) {
        const lines = [
            data.street,
            [data.city, data.state, data.zip].filter(Boolean).join(", "),
            data.country,
        ].filter(Boolean).join("\n");

        const card = document.createElement("div");
        card.className = "addr_card current";
        card.dataset.partnerId   = String(data.partner_id);
        card.dataset.addressType = addressType;
        card.style.cursor   = "pointer";
        card.style.paddingTop = "36px";

        // Action buttons
        const actions = document.createElement("div");
        actions.className = "addr_card_actions";
        actions.innerHTML = `
            <button class="addr_action_btn addr_edit_btn"
                    data-partner-id="${data.partner_id}"
                    data-address-type="${addressType}"
                    data-name="${data.name || ""}"
                    data-street="${data.street || ""}"
                    data-city="${data.city || ""}"
                    data-zip="${data.zip || ""}"
                    data-state-id="0"
                    data-country-id="0"
                    title="Edit">
                <svg viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M8.5 1.5L10.5 3.5L4 10H2V8L8.5 1.5Z" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </button>
            <button class="addr_action_btn addr_delete_btn"
                    data-partner-id="${data.partner_id}"
                    data-address-type="${addressType}"
                    title="Delete">
                <svg viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M2 3h8M5 3V2h2v1M4 3v6h4V3H4z" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </button>`;

        const nameEl = document.createElement("div");
        nameEl.className = "name";
        nameEl.textContent = data.name || "";

        const linesEl = document.createElement("div");
        linesEl.className = "lines";
        linesEl.textContent = lines;

        card.appendChild(actions);
        card.appendChild(nameEl);
        card.appendChild(linesEl);
        return card;
    },
});
