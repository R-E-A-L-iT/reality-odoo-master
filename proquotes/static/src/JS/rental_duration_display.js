/** @odoo-module **/

function initRentalDuration() {
    const form = document.querySelector('form[action="/website_form/sale.order"]');
    if (!form) return;

    const startInput = form.querySelector('input[name="rental_start_date"]');
    const endInput = form.querySelector('input[name="rental_return_date"]');
    if (!startInput || !endInput) return;

    const durationEl = document.createElement('small');
    durationEl.className = 'text-muted rental-duration-display d-block mt-1';

    const endFieldWrapper = endInput.closest('.s_website_form_field') || endInput.parentElement;
    endFieldWrapper.after(durationEl);

    function updateDuration() {
        const start = new Date(startInput.value);
        const end = new Date(endInput.value);
        if (startInput.value && endInput.value && end >= start) {
            const days = Math.max(1, Math.round((end - start) / 86400000));
            durationEl.textContent = `Duration: ${days} day${days !== 1 ? 's' : ''}`;
        } else {
            durationEl.textContent = '';
        }
    }

    startInput.addEventListener('change', updateDuration);
    endInput.addEventListener('change', updateDuration);
}

document.addEventListener('DOMContentLoaded', initRentalDuration);
