/** @odoo-module **/

async function initRentalFormDropdowns() {
    const form = document.querySelector('form[action="/website_form/sale.order"]');
    if (!form) return;

    const countryInput = form.querySelector('input[name="company_country"]');
    const stateInput = form.querySelector('input[name="company_state"]');
    if (!countryInput && !stateInput) return;

    let data;
    try {
        const res = await fetch('/rental/address_data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ jsonrpc: '2.0', method: 'call', id: 1, params: {} }),
        });
        const json = await res.json();
        data = json.result;
    } catch (e) {
        return;
    }
    if (!data) return;

    // Replace country text input with <select>
    let countrySelect = null;
    if (countryInput) {
        countrySelect = document.createElement('select');
        countrySelect.name = 'company_country';
        countrySelect.className = countryInput.className || 'form-control s_website_form_input';
        const defaultOpt = document.createElement('option');
        defaultOpt.value = '';
        defaultOpt.textContent = '-- Select Country --';
        countrySelect.appendChild(defaultOpt);
        data.countries.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.name;
            countrySelect.appendChild(opt);
        });
        countryInput.replaceWith(countrySelect);
    }

    // Replace state text input with <select>
    let stateSelect = null;
    if (stateInput) {
        stateSelect = document.createElement('select');
        stateSelect.name = 'company_state';
        stateSelect.className = stateInput.className || 'form-control s_website_form_input';
        const defaultOpt = document.createElement('option');
        defaultOpt.value = '';
        defaultOpt.textContent = '-- Select State / Province --';
        stateSelect.appendChild(defaultOpt);
        data.states.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.dataset.countryId = s.country_id;
            opt.textContent = s.name;
            stateSelect.appendChild(opt);
        });
        stateInput.replaceWith(stateSelect);
    }

    if (!countrySelect || !stateSelect) return;

    function filterStates() {
        const selected = String(countrySelect.value);
        Array.from(stateSelect.options).forEach(opt => {
            if (!opt.value) return;
            opt.hidden = !!(selected && opt.dataset.countryId !== selected);
        });
        // Clear state selection if it no longer matches the chosen country
        const current = stateSelect.options[stateSelect.selectedIndex];
        if (current?.value && selected && current.dataset.countryId !== selected) {
            stateSelect.value = '';
        }
    }

    countrySelect.addEventListener('change', filterStates);

    // When a state is chosen, auto-select its country
    stateSelect.addEventListener('change', () => {
        const sel = stateSelect.options[stateSelect.selectedIndex];
        if (sel?.value && sel.dataset.countryId) {
            countrySelect.value = sel.dataset.countryId;
            filterStates();
        }
    });
}

document.addEventListener('DOMContentLoaded', initRentalFormDropdowns);
