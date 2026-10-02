/** @odoo-module **/

import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { redirect } from "@web/core/utils/urls";
import { NameAndSignature } from "@web/core/signature/name_and_signature";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { flushPortalRentalDates, portalRentalSignBlock } from "./rental";
import { autoSignNameBlocked } from "./signer_name";

function signRequestFailedMessage() {
    const french = (document.documentElement.lang || "").toLowerCase().startsWith("fr");
    return french
        ? "La soumission ne peut pas être signée. Veuillez réessayer."
        : "The quote could not be signed. Please try again.";
}

/**
 * This Component is a signature request form. It uses
 * @see NameAndSignature for the input fields, adds a submit
 * button, and handles the RPC to save the result.
 */
class SignatureForm extends Component {
    static template = "portal.SignatureForm"
    static components = { NameAndSignature }

    setup() {
        this.rootRef = useRef("root");
        this.rpc = useService("rpc");

        this.csrfToken = odoo.csrf_token;
        this.state = useState({
            error: false,
            success: false,
        });
        this.signature = useState({ name: this.props.defaultName });
        this.nameAndSignatureProps = {
            signature: this.signature,
            fontColor: this.props.fontColor || "black",
        };
        console.log('setup')
        if (this.props.signatureRatio) {
            this.nameAndSignatureProps.displaySignatureRatio = this.props.signatureRatio;
        }
        if (this.props.signatureType) {
            this.nameAndSignatureProps.signatureType = this.props.signatureType;
        }
        if (this.props.mode) {
            this.nameAndSignatureProps.mode = this.props.mode;
        }


        // Correctly set up the signature area if it is inside a modal
        onMounted(() => {
            this.rootRef.el.closest('.modal').addEventListener('shown.bs.modal', () => {
                this.signature.resetSignature();
            });
        });
    }

    get sendLabel() {
        return this.props.sendLabel || _t("Accept & Sign");
    }

     /**
     * Handles click on the submit button.
     *
     * This will get the current name and signature and validate them.
     * If they are valid, they are sent to the server, and the reponse is
     * handled. If they are invalid, it will display the errors to the user.
     *
     * @returns {Promise}
     */
    _hideSignModal() {
        const modal = this.rootRef.el && this.rootRef.el.closest(".modal");
        const ModalApi = window.bootstrap && window.bootstrap.Modal;
        if (!modal || !ModalApi) {
            return;
        }
        ModalApi.getOrCreateInstance(modal).hide();
    }

    async onClickSubmit() {
        // The page button normally stops the dialog from opening. This is
        // the backstop when the dialog is already open: same inline message,
        // and close the dialog so that message is not hidden behind it.
        const blocked = portalRentalSignBlock();
        if (blocked) {
            this.state.error = blocked;
            this.state.success = false;
            this._hideSignModal();
            return;
        }
        const start = document.getElementById("rental-start");
        const end = document.getElementById("rental-end");
        if (start && end && !start.disabled && !end.disabled) {
            // Save the period first. Accept writes the signature before
            // confirm, so a missing or invalid period has to be rejected
            // here and on the server before that write.
            const saved = await flushPortalRentalDates();
            if (saved && saved.error) {
                this.state.error = saved.error;
                this.state.success = false;
                this._hideSignModal();
                return;
            }
        }
        const name = this.signature.name;
        if (autoSignNameBlocked(name, this.signature.signMode)) {
            alert("You must input your own name to automatically sign the document.");
            return;
        }
        const signature = this.signature.getSignatureImage()[1];
        const payload = { name, signature };
        if (start && end && !start.disabled && !end.disabled) {
            payload.rental_start = start.value || "";
            payload.rental_end = end.value || "";
        }
        let data;
        try {
            data = await this.rpc(this.props.callUrl, payload);
        } catch (error) {
            this.state.success = false;
            this.state.error = signRequestFailedMessage();
            return;
        }
        if (!data || data.error) {
            // A readable {error: ...} from the accept route is shown in the
            // dialog. It must not be treated as success.
            this.state.success = false;
            this.state.error = (data && data.error) || signRequestFailedMessage();
            return;
        }
        if (data.force_refresh) {
            if (data.redirect_url) {
                redirect(data.redirect_url);
            } else {
                window.location.reload();
            }
            // do not resolve if we reload the page
            return new Promise(() => {});
        }
        this.state.error = false;
        this.state.success = {
            message: data.message,
            redirectUrl: data.redirect_url,
            redirectMessage: data.redirect_message,
        };
    }
}
patch(NameAndSignature.prototype, {
    async setMode(mode, reset) {
        await super.setMode(mode, reset);
        this.props.signature.signMode = this.state.signMode;
    }
})
registry.category("public_components").add("portal.signature_form", SignatureForm);
