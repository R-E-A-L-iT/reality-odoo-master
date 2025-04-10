/** @odoo-module **/
import { patch } from "@web/core/utils/patch";

const WebsitePreviewLoader = odoo.loader.modules.get("@website/client_actions/website_preview/website_preview");

if (WebsitePreviewLoader) {
    patch(WebsitePreviewLoader.WebsitePreview.prototype, {
        setup() {
            super.setup();
        },
        _onPageUnload() {
            this.iframe.el.setAttribute('is-ready', 'false');
           if (!this.websiteContext.edition && this.iframe.el.contentDocument.body && this.iframefallback.el) {
                this.iframefallback.el.contentDocument.body.replaceWith(this.iframe.el.contentDocument.body.cloneNode(true));
                this.iframefallback.el.classList.remove('d-none');
                // $().getScrollingElement(this.iframefallback.el.contentDocument)[0].scrollTop = $().getScrollingElement(this.iframe.el.contentDocument)[0].scrollTop;
                this._cleanIframeFallback();
            }
        }
    });
}
