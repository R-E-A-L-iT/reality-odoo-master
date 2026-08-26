/** @odoo-module **/

// ─────────────────────────────────────────────────────────────────────────────
// Pre-launch "notify me" signup form
//
// Extracted from three_product.js (disabled in the manifest for the Odoo 19
// migration). This is a mailing-list signup, not a store feature — it posts to
// /prowebsite/notify_signup (see controllers/main.py) and never touches the
// cart or pricelists.
//
// Feature-detected, not product-gated: this only runs if a page actually
// contains .o_omnigo_notify_form, so it's a no-op everywhere else.
//
// Styling lives in three_product.css (.o_omnigo_notify_*), which stays enabled.
// ─────────────────────────────────────────────────────────────────────────────

import { whenReady } from "@odoo/owl";

whenReady(() => {
    const form = document.querySelector(".o_omnigo_notify_form");
    if (!form) return;

    // ── i18n ─────────────────────────────────────────────────────────────────
    // Only the keys this form uses. Mirrors the _t() contract in
    // three_product.js: function-valued entries receive the extra args.
    const pageLang = (document.documentElement.lang || 'en_US').replace('-', '_');

    const _i18n = {
        fr_CA: {
            notifyMissingName: 'Veuillez entrer votre prénom et votre nom.',
            notifyInvalidEmail:'Veuillez entrer une adresse courriel valide.',
            notifyGenericError:'Une erreur est survenue — veuillez réessayer.',
        },
        es_ES: {
            notifyMissingName: 'Por favor ingrese su nombre y apellido.',
            notifyInvalidEmail:'Por favor ingrese un correo electrónico válido.',
            notifyGenericError:'Algo salió mal — por favor intente de nuevo.',
        },
    };

    function _t(key, fallback, ...args) {
        const dict = _i18n[pageLang];
        const val = dict ? dict[key] : undefined;
        if (val === undefined) {
            return typeof fallback === 'function' ? fallback(...args) : fallback;
        }
        return typeof val === 'function' ? val(...args) : val;
    }

    const listKey   = form.dataset.listKey || '';
    const fieldsEl  = form.querySelector(".o_omnigo_notify_fields");
    const successEl = form.querySelector(".o_omnigo_notify_success");
    const errorEl   = form.querySelector(".o_omnigo_notify_error");
    const firstIn   = form.querySelector(".o_omnigo_notify_first");
    const lastIn    = form.querySelector(".o_omnigo_notify_last");
    const emailIn   = form.querySelector(".o_omnigo_notify_email");
    const submitBtn = form.querySelector(".o_omnigo_notify_submit");

    const jq = window.$ || window.jQuery;
    const emailRe = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

    function showError(msg) {
        if (!errorEl) return;
        errorEl.textContent = msg;
        errorEl.classList.add("is-visible");
    }

    function clearError() {
        errorEl?.classList.remove("is-visible");
    }

    form.addEventListener("submit", (e) => {
        e.preventDefault();
        clearError();

        const first_name = (firstIn?.value || '').trim();
        const last_name  = (lastIn?.value || '').trim();
        const email      = (emailIn?.value || '').trim();

        if (!first_name || !last_name) {
            showError(_t('notifyMissingName', 'Please enter your first and last name.'));
            return;
        }
        if (!emailRe.test(email)) {
            showError(_t('notifyInvalidEmail', 'Please enter a valid email address.'));
            return;
        }

        submitBtn.disabled = true;
        submitBtn.classList.add("is-loading");

        jq.ajax({
            url: "/prowebsite/notify_signup",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                id: 1,
                params: { first_name, last_name, email, list_key: listKey },
            }),
            success(resp) {
                submitBtn.disabled = false;
                submitBtn.classList.remove("is-loading");
                const result = resp?.result;
                if (result?.success) {
                    fieldsEl?.classList.add("is-hidden");
                    successEl?.classList.add("is-visible");
                } else {
                    const err = result?.error;
                    const msg = err === 'invalid_email'
                        ? _t('notifyInvalidEmail', 'Please enter a valid email address.')
                        : _t('notifyGenericError', 'Something went wrong — please try again.');
                    showError(msg);
                }
            },
            error(xhr) {
                console.error("[notify_signup] HTTP error:", xhr.status);
                submitBtn.disabled = false;
                submitBtn.classList.remove("is-loading");
                showError(_t('notifyGenericError', 'Something went wrong — please try again.'));
            },
        });
    });
});
