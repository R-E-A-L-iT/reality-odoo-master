/** @odoo-module **/
// 2026-06-11 - Brainecrew Apps

import { jsonrpc } from "@web/core/network/rpc_service";
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.addressSelector = publicWidget.Widget.extend({
    selector: ".o_portal_sale_sidebar",
    events: {
        // Card selection
        "click #rental-address-section": "_onSectionClick",
        // Edit / Delete action buttons
        "click .addr_edit_btn":   "_onEditAddress",
        "click .addr_delete_btn": "_onDeleteAddress",
        // Add new address triggers
        "click #new-address-trigger-invoice":  "_onNewAddressTrigger",
        "click #new-address-trigger-delivery": "_onNewAddressTrigger",
        // Add new modal
        "click #save-new-modal":          "_onSaveNewModal",
        "click #cancel-new-modal":        "_onCloseNewModal",
        "click #addr-new-modal-backdrop": "_onCloseNewModal",
        "change #new-modal-country":      "_onNewModalCountryChange",
        // Inline edit form
        "click #save-inline-edit":    "_onSaveInlineEdit",
        "click #cancel-inline-edit":  "_onCloseInlineEdit",
        "change #inline-edit-country": "_onInlineEditCountryChange",
    },

    async start() {
        await this._super(...arguments);
        this.orderDetail = this.$el.find("table#sales_order_table").data();

        // Move the add-new popup to <body> so position:fixed is viewport-relative.
        const newModal = document.getElementById("addr-new-modal");
        if (newModal) document.body.appendChild(newModal);

        // Enable mouse click-drag scroll on both card containers.
        ["invoice-address-cards", "delivery-address-cards"].forEach(id => {
            const el = document.getElementById(id);
            if (el) this._initDragScroll(el);
        });
    },

    // ── Unified section click → card selection ────────────────────────────────

    async _onSectionClick(ev) {
        if (ev.target.closest(".addr_action_btn"))  return;
        if (ev.target.closest(".addr_card.add_card")) return;
        if (ev.target.closest(".addresses"))         return;
        if (ev.target.closest("#addr-inline-editor")) return;
        if (ev.target.closest("#addr-new-modal"))    return;

        const card = ev.target.closest(".addr_card[data-partner-id]");
        if (!card) return;

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
            const containerId = addressType === "invoice"
                ? "invoice-address-cards"
                : "delivery-address-cards";
            this._setActiveCard(containerId, partnerId);
        }
    },

    _setActiveCard(containerId, partnerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.querySelectorAll(".addr_card[data-partner-id]").forEach(card => {
            card.classList.toggle("current", card.dataset.partnerId == String(partnerId));
        });
    },

    // ── Add new address ───────────────────────────────────────────────────────

    _onNewAddressTrigger(ev) {
        ev.stopImmediatePropagation();
        const type = ev.currentTarget.id === "new-address-trigger-invoice" ? "invoice" : "delivery";
        this._setVal("new-modal-type", type);

        // Update modal legend to reflect which section
        const legend = document.getElementById("new-modal-legend");
        if (legend) {
            legend.textContent = type === "invoice" ? "New Invoice Address" : "New Delivery Address";
        }

        // Clear all fields
        ["name", "street", "city", "zip"].forEach(f => this._setVal(`new-modal-${f}`, ""));
        this._setVal("new-modal-country", "");
        this._setVal("new-modal-state",   "");
        this._filterStatesByCountry("new-modal-country", "new-modal-state");

        const modal = document.getElementById("addr-new-modal");
        if (modal) modal.style.display = "flex";
    },

    _onCloseNewModal() {
        const modal = document.getElementById("addr-new-modal");
        if (modal) modal.style.display = "none";
    },

    async _onSaveNewModal() {
        const type = document.getElementById("new-modal-type")?.value;
        if (!type) return;

        const result = await jsonrpc(
            "/my/orders/" + this.orderDetail.orderId + "/create_typed_address",
            {
                access_token: this.orderDetail.token,
                address_type: type,
                name:    document.getElementById("new-modal-name")?.value    || "",
                street:  document.getElementById("new-modal-street")?.value  || "",
                city:    document.getElementById("new-modal-city")?.value    || "",
                state:   document.getElementById("new-modal-state")?.value   || "",
                zip:     document.getElementById("new-modal-zip")?.value     || "",
                country: document.getElementById("new-modal-country")?.value || "",
            }
        );

        if (result && result.success) {
            const containerId = type === "invoice" ? "invoice-address-cards" : "delivery-address-cards";
            const triggerId   = type === "invoice" ? "new-address-trigger-invoice" : "new-address-trigger-delivery";
            const container   = document.getElementById(containerId);
            const trigger     = document.getElementById(triggerId);

            if (container) {
                // Remove default card if it's showing
                const defaultId = container.dataset.defaultPartnerId;
                container.querySelectorAll(".addr_card[data-partner-id]").forEach(c => {
                    if (c.dataset.partnerId == defaultId) c.remove();
                });
                // Clear current highlight from existing cards
                container.querySelectorAll(".addr_card").forEach(c => c.classList.remove("current"));
            }

            const newCard = this._buildAddressCard(result, type);
            if (container && trigger) container.insertBefore(newCard, trigger);
            else if (container) container.appendChild(newCard);

            this._onCloseNewModal();
        }
    },

    _onNewModalCountryChange() {
        this._filterStatesByCountry("new-modal-country", "new-modal-state");
    },

    // ── Edit address → inline form in section ────────────────────────────────

    _onEditAddress(ev) {
        ev.stopImmediatePropagation();
        const btn  = ev.currentTarget;
        const type = btn.dataset.addressType;

        // Move inline editor into the correct section (after its addr_cards row)
        const containerId = type === "invoice" ? "invoice-address-cards" : "delivery-address-cards";
        const container   = document.getElementById(containerId);
        const editor      = document.getElementById("addr-inline-editor");
        if (container && editor) {
            container.parentNode.insertBefore(editor, container.nextSibling);
        }

        // Populate hidden meta fields
        this._setVal("inline-edit-partner-id",   btn.dataset.partnerId);
        this._setVal("inline-edit-address-type", type);

        // Populate text fields
        this._setVal("inline-edit-name",   btn.dataset.name   || "");
        this._setVal("inline-edit-street", btn.dataset.street || "");
        this._setVal("inline-edit-city",   btn.dataset.city   || "");
        this._setVal("inline-edit-zip",    btn.dataset.zip    || "");

        const countryEl = document.getElementById("inline-edit-country");
        if (countryEl) countryEl.value = btn.dataset.countryId || "";
        this._filterStatesByCountry("inline-edit-country", "inline-edit-state");
        const stateEl = document.getElementById("inline-edit-state");
        if (stateEl) stateEl.value = btn.dataset.stateId || "";

        if (editor) editor.style.display = "";
        editor?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    },

    _onCloseInlineEdit() {
        const editor = document.getElementById("addr-inline-editor");
        if (editor) editor.style.display = "none";
    },

    async _onSaveInlineEdit() {
        const partnerId   = document.getElementById("inline-edit-partner-id")?.value;
        const addressType = document.getElementById("inline-edit-address-type")?.value;
        if (!partnerId) return;

        const result = await jsonrpc(
            "/my/orders/" + this.orderDetail.orderId + "/update_address",
            {
                access_token: this.orderDetail.token,
                partner_id: parseInt(partnerId),
                name:    document.getElementById("inline-edit-name")?.value    || "",
                street:  document.getElementById("inline-edit-street")?.value  || "",
                city:    document.getElementById("inline-edit-city")?.value    || "",
                state:   document.getElementById("inline-edit-state")?.value   || "",
                zip:     document.getElementById("inline-edit-zip")?.value     || "",
                country: document.getElementById("inline-edit-country")?.value || "",
            }
        );

        if (result && result.success) {
            const containerId = addressType === "invoice"
                ? "invoice-address-cards"
                : "delivery-address-cards";
            const card = document.querySelector(
                `#${containerId} .addr_card[data-partner-id="${partnerId}"]`
            );
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

                const editBtn = card.querySelector(".addr_edit_btn");
                if (editBtn) {
                    editBtn.dataset.name   = result.name;
                    editBtn.dataset.street = result.street;
                    editBtn.dataset.city   = result.city;
                    editBtn.dataset.zip    = result.zip;
                }
            }
            this._onCloseInlineEdit();
        }
    },

    // ── Delete address ────────────────────────────────────────────────────────

    async _onDeleteAddress(ev) {
        ev.stopImmediatePropagation();
        const btn         = ev.currentTarget;
        const partnerId   = btn.dataset.partnerId;
        const type        = btn.dataset.addressType;
        const containerId = `${type}-address-cards`;
        const container   = document.getElementById(containerId);

        // Default company card — don't archive
        if (container && container.dataset.defaultPartnerId == partnerId) return;

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
            const card = document.querySelector(
                `#${containerId} .addr_card[data-partner-id="${partnerId}"]`
            );
            if (card) card.remove();

            this._onCloseEditModal();

            const remaining = container?.querySelectorAll(".addr_card[data-partner-id]").length || 0;

            if (result.was_selected && remaining > 0) {
                const firstCard = container.querySelector(".addr_card[data-partner-id]");
                firstCard?.classList.add("current");
                const newId = parseInt(firstCard.dataset.partnerId);
                const route = type === "invoice"
                    ? "/my/orders/" + this.orderDetail.orderId + "/select_invoice_address"
                    : "/my/orders/" + this.orderDetail.orderId + "/select_delivery_address";
                jsonrpc(route, { partner_id: newId, access_token: this.orderDetail.token });
            }

            if (remaining === 0) {
                const defaultCard = this._buildDefaultCard(container, type);
                if (defaultCard) container.appendChild(defaultCard);
            }
        }
    },

    // ── Build card DOM helpers ────────────────────────────────────────────────

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
        card.style.cursor     = "pointer";
        card.style.paddingTop = "36px";

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

    _buildDefaultCard(container, addressType) {
        const d = container?.dataset;
        if (!d || !d.defaultPartnerId) return null;

        const lines = [
            d.defaultStreet,
            [d.defaultCity, d.defaultState, d.defaultZip].filter(Boolean).join(", "),
            d.defaultCountry,
        ].filter(Boolean).join("\n");

        const card = document.createElement("div");
        card.className = "addr_card current";
        card.dataset.partnerId   = d.defaultPartnerId;
        card.dataset.addressType = addressType;
        card.style.cursor     = "pointer";
        card.style.paddingTop = "36px";

        const actions = document.createElement("div");
        actions.className = "addr_card_actions";
        actions.innerHTML = `
            <button class="addr_action_btn addr_edit_btn"
                    data-partner-id="${d.defaultPartnerId}"
                    data-address-type="${addressType}"
                    data-name="${d.defaultName || ""}"
                    data-street="${d.defaultStreet || ""}"
                    data-city="${d.defaultCity || ""}"
                    data-zip="${d.defaultZip || ""}"
                    data-state-id="0"
                    data-country-id="0"
                    title="Edit">
                <svg viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M8.5 1.5L10.5 3.5L4 10H2V8L8.5 1.5Z" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </button>
            <button class="addr_action_btn addr_delete_btn"
                    data-partner-id="${d.defaultPartnerId}"
                    data-address-type="${addressType}"
                    title="Delete">
                <svg viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M2 3h8M5 3V2h2v1M4 3v6h4V3H4z" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </button>`;

        const badge = document.createElement("span");
        badge.className = "addr_badge mb-1";
        badge.textContent = "Default";

        const nameEl = document.createElement("div");
        nameEl.className = "name";
        nameEl.textContent = d.defaultName || "";

        const linesEl = document.createElement("div");
        linesEl.className = "lines";
        linesEl.textContent = lines;

        card.appendChild(actions);
        card.appendChild(badge);
        card.appendChild(nameEl);
        card.appendChild(linesEl);
        return card;
    },

    // ── Country/state filtering ───────────────────────────────────────────────

    _initDragScroll(el) {
        let active = false;
        let startX = 0;
        let startScrollLeft = 0;

        el.addEventListener("mousedown", e => {
            active = true;
            startX = e.pageX - el.getBoundingClientRect().left;
            startScrollLeft = el.scrollLeft;
            el.classList.add("is-dragging");
        });
        el.addEventListener("mouseleave", () => {
            active = false;
            el.classList.remove("is-dragging");
        });
        el.addEventListener("mouseup", () => {
            active = false;
            el.classList.remove("is-dragging");
        });
        el.addEventListener("mousemove", e => {
            if (!active) return;
            e.preventDefault();
            const x = e.pageX - el.getBoundingClientRect().left;
            el.scrollLeft = startScrollLeft - (x - startX);
        });
    },

    _filterStatesByCountry(countryId, stateId) {
        const countryEl = document.getElementById(countryId);
        const stateEl   = document.getElementById(stateId);
        if (!countryEl || !stateEl) return;
        const selected = countryEl.value;
        const active   = selected && selected !== "0";
        Array.from(stateEl.options).forEach(opt => {
            if (!opt.value) return;
            opt.hidden = !!(active && opt.dataset.countryId != selected);
        });
        const sel = stateEl.options[stateEl.selectedIndex];
        if (sel?.value && active && sel.dataset.countryId != selected) {
            stateEl.value = "";
        }
    },

    _onInlineEditCountryChange() { this._filterStatesByCountry("inline-edit-country", "inline-edit-state"); },
    _onNewModalCountryChange() { this._filterStatesByCountry("new-modal-country",   "new-modal-state");  },

    // ── DOM helpers ───────────────────────────────────────────────────────────

    _setVal(id, val) {
        const el = document.getElementById(id);
        if (el) el.value = val;
    },
});
