/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.rentalFormDropdowns = publicWidget.Widget.extend({
    selector: '.s_website_form form, form.s_website_form',

    async start() {
        await this._super(...arguments);
        const form = this.el;
        const countryInput = form.querySelector('input[name="company_country"]');
        const stateInput   = form.querySelector('input[name="company_state"]');
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
        } catch (e) { return; }
        if (!data) return;

        // Replace country text input with <select>
        let countrySelect = null;
        if (countryInput) {
            countrySelect = document.createElement('select');
            countrySelect.name = 'company_country';
            countrySelect.className = countryInput.className;
            const defOpt = document.createElement('option');
            defOpt.value = '';
            defOpt.textContent = '-- Select Country --';
            countrySelect.appendChild(defOpt);
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
            stateSelect.className = stateInput.className;
            const defOpt = document.createElement('option');
            defOpt.value = '';
            defOpt.textContent = '-- Select State / Province --';
            stateSelect.appendChild(defOpt);
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

        const filterStates = () => {
            const selected = String(countrySelect.value);
            Array.from(stateSelect.options).forEach(opt => {
                if (!opt.value) return;
                opt.hidden = !!(selected && opt.dataset.countryId !== selected);
            });
            const cur = stateSelect.options[stateSelect.selectedIndex];
            if (cur?.value && selected && cur.dataset.countryId !== selected) {
                stateSelect.value = '';
            }
        };

        countrySelect.addEventListener('change', filterStates);

        stateSelect.addEventListener('change', () => {
            const sel = stateSelect.options[stateSelect.selectedIndex];
            if (sel?.value && sel.dataset.countryId) {
                countrySelect.value = sel.dataset.countryId;
                filterStates();
            }
        });
    },
});
