/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.PerProductDelivery = publicWidget.Widget.extend({
    selector: '.o_per_product_delivery',

    start() {
        this.rpc = this.bindService('rpc');
        this._fetchRates();
        return this._super(...arguments);
    },

    events: {
        'change input[type="radio"]': '_onCarrierChange',
    },

    async _fetchRates() {
        const lineId = this.el.dataset.lineId;
        for (const radio of this.el.querySelectorAll('input[type="radio"]')) {
            const carrierId = radio.dataset.carrierId;
            const badge = this.el.querySelector(
                `.o_wsale_delivery_badge_price_line[data-carrier-id="${carrierId}"]`
            );
            if (!badge) continue;
            try {
                const result = await this.rpc('/shop/rate_carrier_for_line', {
                    line_id: parseInt(lineId),
                    carrier_id: parseInt(carrierId),
                });
                if (result && result.success) {
                    badge.textContent = result.price === 0
                        ? 'Free'
                        : parseFloat(result.price).toFixed(2);
                    badge.classList.replace('text-bg-primary', 'text-bg-success');
                } else {
                    badge.textContent = 'N/A';
                    badge.classList.replace('text-bg-primary', 'text-bg-secondary');
                }
            } catch (e) {
                badge.textContent = 'N/A';
            }
        }
    },

    async _onCarrierChange(ev) {
        const input = ev.target;
        if (!input.dataset.carrierId) return;

        const lineId = parseInt(this.el.dataset.lineId);
        const carrierId = parseInt(input.dataset.carrierId);

        const payBtn = document.querySelector('#o_payment_submit_button');
        if (payBtn) payBtn.disabled = true;

        try {
            const result = await this.rpc('/shop/update_carrier_for_line', {
                line_id: lineId,
                carrier_id: carrierId,
            });
            if (result && result.success) {
                // Reload so the payment form's amount is always in sync with the
                // updated order total — prevents the "cart has been updated" error.
                window.location.reload();
            }
        } catch (e) {
            console.error('Failed to update carrier for line', e);
            if (payBtn) payBtn.disabled = false;
        }
    },
});
