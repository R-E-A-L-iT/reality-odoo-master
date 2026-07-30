import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { rpc } from '@web/core/network/rpc';

export class PerProductDelivery extends Interaction {
    static selector = '.o_per_product_delivery';

    dynamicContent = {
        'input[type="radio"]': { 't-on-change': this.onCarrierChange },
    };

    async willStart() {
        await this.waitFor(this.fetchRates());
    }

    async fetchRates() {
        const lineId = this.el.dataset.lineId;
        for (const radio of this.el.querySelectorAll('input[type="radio"]')) {
            const carrierId = radio.dataset.carrierId;
            const badge = this.el.querySelector(
                `.o_wsale_delivery_badge_price_line[data-carrier-id="${carrierId}"]`
            );
            if (!badge) continue;
            try {
                const result = await rpc('/shop/rate_carrier_for_line', {
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
    }

    async onCarrierChange(ev) {
        const input = ev.target;
        if (!input.dataset.carrierId) return;

        const lineId = parseInt(this.el.dataset.lineId);
        const carrierId = parseInt(input.dataset.carrierId);

        const payBtn = document.querySelector('#o_payment_submit_button');
        if (payBtn) payBtn.disabled = true;

        try {
            const result = await this.waitFor(rpc('/shop/update_carrier_for_line', {
                line_id: lineId,
                carrier_id: carrierId,
            }));
            if (result && result.success) {
                // Reload so the payment form's amount is always in sync with the
                // updated order total — prevents the "cart has been updated" error.
                window.location.reload();
            }
        } catch (e) {
            console.error('Failed to update carrier for line', e);
            if (payBtn) payBtn.disabled = false;
        }
    }
}

registry.category('public.interactions').add(
    'website_sale_product_shipping.per_product_delivery',
    PerProductDelivery,
);
