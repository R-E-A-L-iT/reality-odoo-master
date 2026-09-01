/** @odoo-module **/

import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { addLoadingEffect } from "@web/core/utils/ui";
import { registry } from "@web/core/registry";
import { redirect } from "@web/core/utils/urls";
import { NameAndSignature } from "@web/core/signature/name_and_signature";
// Odoo 19: the "rpc" service isn't available on the public/website frontend;
// import the rpc function directly instead of useService("rpc").
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

/**
 * Portal signature request form — a full replacement of portal.SignatureForm.
 *
 * Kept in sync with Odoo 19 core (addons/portal/.../signature_form.js). The ONLY
 * intentional deviations are:
 *   1. the "Public User" guard in onClickSubmit(), which blocks auto-signing a
 *      document with the generic public-user name;
 *   2. the NameAndSignature patch at the bottom, which exposes the active
 *      signMode so that guard can tell "auto" from "draw"/"load".
 * Everything else must track core — see the getSignatureImage note below for why
 * drifting from it silently breaks signing.
 */
class SignatureForm extends Component {
    static template = "portal.SignatureForm";
    static components = { NameAndSignature };
    static props = ["*"];

    setup() {
        this.rootRef = useRef("root");

        this.csrfToken = odoo.csrf_token;
        this.state = useState({
            error: false,
            success: false,
        });
        // The stub getSignatureImage/resetSignature matter: NameAndSignature
        // replaces them once it mounts, but onMounted below (and a fast click)
        // can run first, and calling an undefined member would throw.
        this.signature = useState({
            // Deliberately NOT props.defaultName. Core pre-fills the signer box with
            // the customer/company name, which meant people just hit "Accept & Sign"
            // and the quote came back signed "R-E-A-L.iT Test Company" rather than by
            // an actual person. Starting empty forces them to type their own name.
            // The company is still shown in the "on behalf of ..." line above, so no
            // information is lost.
            name: "",
            getSignatureImage: () => "",
            resetSignature: () => {},
        });
        this.nameAndSignatureProps = {
            signature: this.signature,
            fontColor: this.props.fontColor || "black",
        };
        if (this.props.signatureRatio) {
            this.nameAndSignatureProps.displaySignatureRatio = this.props.signatureRatio;
        }
        if (this.props.signatureType) {
            this.nameAndSignatureProps.signatureType = this.props.signatureType;
        }
        if (this.props.mode) {
            this.nameAndSignatureProps.mode = this.props.mode;
        }

        // Correctly set up the signature area if it is inside a modal.
        onMounted(() => {
            const modalEl = this.rootRef.el.closest(".modal");
            if (modalEl !== null) {
                modalEl.addEventListener("shown.bs.modal", () => {
                    this.signature.resetSignature();
                    this.toggleSignatureFormVisibility();
                });
            }
        });
    }

    toggleSignatureFormVisibility() {
        this.rootRef.el.classList.toggle("d-none", document.querySelector(".editor_enable"));
    }

    get sendLabel() {
        return this.props.sendLabel || _t("Accept & Sign");
    }

    /**
     * Handles click on the submit button: validates the name + signature and
     * posts them to callUrl.
     *
     * @returns {Promise}
     */
    async onClickSubmit() {
        const name = this.signature.name;
        if (
            (name === "Public User" || name.toLowerCase().includes("public user")) &&
            this.signature.signMode === "auto"
        ) {
            alert("You must input your own name to automatically sign the document.");
            return;
        }

        const button = document.querySelector(".o_portal_sign_submit");
        const icon = button.removeChild(button.firstChild);
        const restoreBtnLoading = addLoadingEffect(button);

        // Odoo 19 changed getSignatureImage() to return the full data URL as a
        // STRING ("data:image/png;base64,iVBOR..."); in 17 it returned an
        // [mimetype, base64] ARRAY. The old `[1]` indexing therefore yielded the
        // second CHARACTER of that string ("a"), which the server rejected with
        // "Invalid Operation. Image is not encoded in base64."
        const signature = this.signature.getSignatureImage().split(",")[1];

        const data = await rpc(this.props.callUrl, { name, signature });
        if (data.force_refresh) {
            restoreBtnLoading();
            button.prepend(icon);
            if (data.redirect_url) {
                redirect(data.redirect_url);
            } else {
                window.location.reload();
            }
            // do not resolve if we reload the page
            return new Promise(() => {});
        }
        this.state.error = data.error || false;
        this.state.success = !data.error && {
            message: data.message,
            redirectUrl: data.redirect_url,
            redirectMessage: data.redirect_message,
        };
    }
}

// Expose the active signature mode ("auto" / "draw" / "load") on the shared
// signature state so onClickSubmit's Public-User guard can tell them apart.
patch(NameAndSignature.prototype, {
    async setMode(mode, reset) {
        await super.setMode(mode, reset);
        this.props.signature.signMode = this.state.signMode;
    },
});

registry.category("public_components").add("portal.signature_form", SignatureForm);
