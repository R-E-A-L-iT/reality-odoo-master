/** @odoo-module **/

import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { redirect } from "@web/core/utils/urls";
import { NameAndSignature } from "@web/core/signature/name_and_signature";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

/**
 * Signature Form Component for portal quote signing.
 */
class SignatureForm extends Component {
    static template = "portal.SignatureForm";
    static components = { NameAndSignature };

    setup() {
        this.rootRef = useRef("root");
        this.rpc = useService("rpc");

        this.csrfToken = odoo.csrf_token;
        this.state = useState({
            error: false,
            success: false,
            submitting: false,
        });

        this.signature = useState({ name: this.props.defaultName });

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

        // Reset signature if inside modal
        onMounted(() => {
            const modal = this.rootRef.el.closest(".modal");
            if (modal) {
                modal.addEventListener("shown.bs.modal", () => {
                    this.signature.resetSignature();
                });
            }
        });
    }

    get sendLabel() {
        return this.props.sendLabel || _t("Accept & Sign");
    }

    async onClickSubmit() {
        const name = this.signature.name;

        if (
            (name === "Public User" || name.toLowerCase().includes("public user")) &&
            this.signature.signMode === "auto"
        ) {
            alert("You must input your own name to automatically sign the document.");
            return;
        }

        this.state.submitting = true;
        const signature = this.signature.getSignatureImage()[1];

        console.time("signature_rpc");
        try {
            const data = await this.rpc(this.props.callUrl, { name, signature });
            console.timeEnd("signature_rpc");

            if (data.force_refresh) {
                if (data.redirect_url) {
                    window.location.href = data.redirect_url;
                } else {
                    window.location.reload();
                }
                return;
            }

            this.state.error = data.error || false;
            this.state.success =
                !data.error && {
                    message: data.message,
                    redirectUrl: data.redirect_url,
                    redirectMessage: data.redirect_message,
                };
        } catch (error) {
            console.error("Signature submission failed:", error);
            alert("An error occurred while submitting your signature.");
            this.state.error = true;
        } finally {
            this.state.submitting = false;
        }
    }
}

// Patch to track signature mode (auto/manual)
patch(NameAndSignature.prototype, {
    async setMode(mode, reset) {
        await super.setMode(mode, reset);
        this.props.signature.signMode = this.state.signMode;
    },
});

registry.category("public_components").add("portal.signature_form", SignatureForm);
