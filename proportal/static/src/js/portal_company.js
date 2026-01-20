/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.ProportalCompanySettings = publicWidget.Widget.extend({
    selector: '.address-form',
    events: {
        'submit': '_onSubmitForm',
    },

    /**
     * Handle form submission via AJAX
     */
    _onSubmitForm: function (ev) {
        ev.preventDefault();

        const form = ev.currentTarget;
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;

        // Disable button and show loading state
        submitBtn.disabled = true;
        submitBtn.textContent = 'Saving...';

        const formData = new FormData(form);
        const url = form.getAttribute('action');

        console.log('PROPORTAL: Submitting to:', url);

        // Submit via fetch API
        fetch(url, {
            method: 'POST',
            body: formData,
            credentials: 'same-origin',
            headers: {
                'Accept': 'application/json'
            }
        })
        .then(response => {
            console.log('PROPORTAL: Response status:', response.status);
            if (!response.ok) {
                throw new Error('Request failed with status: ' + response.status);
            }
            return response.json();
        })
        .then(data => {
            console.log('PROPORTAL: Response data:', data);
            if (data.success) {
                console.log('PROPORTAL: Success! Reloading page...');

                // Show success message
                const successMsg = document.createElement('div');
                successMsg.className = 'alert alert-success alert-dismissible fade show mt-3';
                successMsg.innerHTML = `<strong>Success!</strong> ${data.message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
                form.parentElement.insertBefore(successMsg, form);

                // Reset button
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;

                // Reload the page to show updated data after a short delay
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                throw new Error(data.error || 'Unknown error');
            }
        })
        .catch(error => {
            console.error('PROPORTAL: Error:', error);

            // Show error message
            const errorMsg = document.createElement('div');
            errorMsg.className = 'alert alert-danger alert-dismissible fade show mt-3';
            errorMsg.innerHTML = `<strong>Error!</strong> ${error.message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;

            // Remove any existing alerts
            const existingAlerts = form.parentElement.querySelectorAll('.alert');
            existingAlerts.forEach(alert => alert.remove());

            // Add new error message
            form.parentElement.insertBefore(errorMsg, form);

            // Reset button
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        });

        return false;
    },
});

export default publicWidget.registry.ProportalCompanySettings;
