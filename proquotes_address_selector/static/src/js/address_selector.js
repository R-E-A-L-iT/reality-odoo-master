/** @odoo-module **/
// 2026-06-11 - Brainecrew Apps

import { jsonrpc } from "@web/core/network/rpc_service";
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.addressSelector = publicWidget.Widget.extend({
    selector: ".o_portal_sale_sidebar",
    events: {
        "click #invoice-address-cards .addr_card[data-partner-id]": "_onSelectInvoiceCard",
        "click #delivery-address-cards .addr_card[data-partner-id]": "_onSelectDeliveryCard",
        "click #new-invoice-trigger":  "_onNewInvoiceTrigger",
        "click #new-delivery-trigger": "_onNewDeliveryTrigger",
        "click #save-new-invoice-address":  "_onSaveNewInvoice",
        "click #save-new-delivery-address": "_onSaveNewDelivery",
        "click #cancel-new-invoice-address":  "_onCancelNewInvoice",
        "click #cancel-new-delivery-address": "_onCancelNewDelivery",
        "change #new-invoice-country": "_onInvoiceCountryChange",
        "change #new-delivery-country": "_onDeliveryCountryChange",
    },

    async start() {
        await this._super(...arguments);
        this.orderDetail = this.$el.find("table#sales_order_table").data();
        this._filterStatesByCountry("new-invoice-country", "new-invoice-state");
        this._filterStatesByCountry("new-delivery-country", "new-delivery-state");
    },

    _filterStatesByCountry(countryId, stateId) {
        const countryEl = document.getElementById(countryId);
        const stateEl   = document.getElementById(stateId);
        if (!countryEl || !stateEl) return;
        const selected = countryEl.value;
        Array.from(stateEl.options).forEach(opt => {
            if (!opt.value) return;
            opt.hidden = !!(selected && opt.dataset.countryId != selected);
        });
    },

    _onInvoiceCountryChange() {
        this._filterStatesByCountry("new-invoice-country", "new-invoice-state");
        const stateEl = document.getElementById("new-invoice-state");
        const countryEl = document.getElementById("new-invoice-country");
        const sel = stateEl?.options[stateEl.selectedIndex];
        if (sel?.value && countryEl?.value && sel.dataset.countryId != countryEl.value) {
            stateEl.value = "";
        }
    },

    _onDeliveryCountryChange() {
        this._filterStatesByCountry("new-delivery-country", "new-delivery-state");
        const stateEl = document.getElementById("new-delivery-state");
        const countryEl = document.getElementById("new-delivery-country");
        const sel = stateEl?.options[stateEl.selectedIndex];
        if (sel?.value && countryEl?.value && sel.dataset.countryId != countryEl.value) {
            stateEl.value = "";
        }
    },

    _setActiveCard(containerId, partnerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.querySelectorAll(".addr_card[data-partner-id]").forEach(card => {
            card.classList.toggle("current", card.dataset.partnerId == String(partnerId));
        });
    },

    async _onSelectInvoiceCard(ev) {
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

    _onNewInvoiceTrigger() {
        const form = document.getElementById("new-invoice-address-form");
        if (form) form.style.display = form.style.display === "none" ? "" : "none";
    },

    _onNewDeliveryTrigger() {
        const form = document.getElementById("new-delivery-address-form");
        if (form) form.style.display = form.style.display === "none" ? "" : "none";
    },

    _onCancelNewInvoice() {
        const form = document.getElementById("new-invoice-address-form");
        if (form) form.style.display = "none";
    },

    _onCancelNewDelivery() {
        const form = document.getElementById("new-delivery-address-form");
        if (form) form.style.display = "none";
    },

    _buildAddressCard(data, addressType) {
        const lines = [
            data.street,
            [data.city, data.state, data.zip].filter(Boolean).join(", "),
            data.country,
        ].filter(Boolean).join("\n");

        const card = document.createElement("div");
        card.className = "addr_card current";
        card.dataset.partnerId = String(data.partner_id);
        card.dataset.addressType = addressType;
        card.style.cursor = "pointer";

        const nameEl = document.createElement("div");
        nameEl.className = "name";
        nameEl.textContent = data.name || "";

        const linesEl = document.createElement("div");
        linesEl.className = "lines";
        linesEl.textContent = lines;

        card.appendChild(nameEl);
        card.appendChild(linesEl);
        return card;
    },

    _clearNewAddressForm(prefix) {
        ["name", "street", "city", "zip"].forEach(field => {
            const el = document.getElementById(`new-${prefix}-${field}`);
            if (el) el.value = "";
        });
        const country = document.getElementById(`new-${prefix}-country`);
        const state   = document.getElementById(`new-${prefix}-state`);
        if (country) country.value = "";
        if (state)   state.value   = "";
    },

    async _onSaveNewInvoice() {
        const result = await jsonrpc(
            "/my/orders/" + this.orderDetail.orderId + "/create_invoice_address",
            {
                access_token: this.orderDetail.token,
                name:    document.getElementById("new-invoice-name")?.value    || "",
                street:  document.getElementById("new-invoice-street")?.value  || "",
                city:    document.getElementById("new-invoice-city")?.value    || "",
                state:   document.getElementById("new-invoice-state")?.value   || "",
                zip:     document.getElementById("new-invoice-zip")?.value     || "",
                country: document.getElementById("new-invoice-country")?.value || "",
            }
        );
        if (result && result.success) {
            const container = document.getElementById("invoice-address-cards");
            const trigger   = document.getElementById("new-invoice-trigger");
            // Remove current highlight from all cards
            container.querySelectorAll(".addr_card").forEach(c => c.classList.remove("current"));
            // Insert new card before the "+ New Address" trigger
            const card = this._buildAddressCard(result, "invoice");
            container.insertBefore(card, trigger);
            // Re-attach click handler by re-delegating (widget events cover the container)
            document.getElementById("new-invoice-address-form").style.display = "none";
            this._clearNewAddressForm("invoice");
        }
    },

    async _onSaveNewDelivery() {
        const result = await jsonrpc(
            "/my/orders/" + this.orderDetail.orderId + "/create_delivery_address",
            {
                access_token: this.orderDetail.token,
                name:    document.getElementById("new-delivery-name")?.value    || "",
                street:  document.getElementById("new-delivery-street")?.value  || "",
                city:    document.getElementById("new-delivery-city")?.value    || "",
                state:   document.getElementById("new-delivery-state")?.value   || "",
                zip:     document.getElementById("new-delivery-zip")?.value     || "",
                country: document.getElementById("new-delivery-country")?.value || "",
            }
        );
        if (result && result.success) {
            const container = document.getElementById("delivery-address-cards");
            const trigger   = document.getElementById("new-delivery-trigger");
            container.querySelectorAll(".addr_card").forEach(c => c.classList.remove("current"));
            const card = this._buildAddressCard(result, "delivery");
            container.insertBefore(card, trigger);
            document.getElementById("new-delivery-address-form").style.display = "none";
            this._clearNewAddressForm("delivery");
        }
    },
});
