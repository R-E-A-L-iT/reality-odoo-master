/** @odoo-module **/

import { jsonrpc } from "@web/core/network/rpc_service";
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.ccpSelection = publicWidget.Widget.extend({
    selector: ".o_portal_sale_sidebar",
    events: {
        "change .ccp-radio": "_onCcpTypeChange",
        "change .ccp-period-select": "_onPeriodChange",
        "click .ccp-next-btn": "_onNextClick",
        "click .ccp-back-btn": "_onBackClick",
        "click .ccp-clear-btn": "_onClearClick",
    },

    async start() {
        this.orderDetail = this.$el.find("table#sales_order_table").data();
        await this._super(...arguments);
        this._initializeCcpSections();
    },

    /**
     * Initialize all CCP selection sections
     */
    _initializeCcpSections: function () {
        const self = this;
        const ccpContainers = document.querySelectorAll(".ccp-selection-container");

        ccpContainers.forEach((container) => {
            // Check if CCP product already added (from session storage)
            const sectionName = container.getAttribute("data-section");
            const storedLineId = sessionStorage.getItem(`ccp_line_${sectionName}`);

            if (storedLineId) {
                // Check if line still exists in the order
                const lineExists = document.querySelector(`#${storedLineId}`);
                if (lineExists) {
                    // Show confirmation step
                    self._showStep(container, 3);
                } else {
                    // Line was removed, clear storage
                    sessionStorage.removeItem(`ccp_line_${sectionName}`);
                }
            }

            // Load product images for CCP types
            self._loadCcpImages(container);
        });
    },

    /**
     * Load product images for CCP types
     */
    _loadCcpImages: function (container) {
        const scannerName = container.getAttribute("data-scanner");
        const imagePlaceholders = container.querySelectorAll(".ccp-image-placeholder");

        imagePlaceholders.forEach((placeholder) => {
            const ccpType = placeholder.getAttribute("data-ccp-type");

            // Search for a product matching this scanner and CCP type
            // We'll use a simple approach: look for any product with this pattern in the name
            const searchPattern = `${scannerName} Laser Scanner CCP ${ccpType}`;

            // Try to find the product image from existing order lines or load a placeholder
            // For now, we'll set a placeholder background
            placeholder.style.minHeight = "80px";
            placeholder.style.backgroundColor = "#f0f0f0";
            placeholder.style.display = "flex";
            placeholder.style.alignItems = "center";
            placeholder.style.justifyContent = "center";
            placeholder.innerHTML = `<span style="color: #999;">${ccpType}</span>`;
        });
    },

    /**
     * Handle CCP type radio button change
     */
    _onCcpTypeChange: function (ev) {
        const container = ev.currentTarget.closest(".ccp-selection-container");
        const step1 = container.querySelector(".ccp-step-1");
        const nextBtn = step1.querySelector(".ccp-next-btn");

        // Enable next button when a type is selected
        const selectedRadio = step1.querySelector(".ccp-radio:checked");
        if (selectedRadio) {
            nextBtn.disabled = false;
        }
    },

    /**
     * Handle period dropdown change
     */
    _onPeriodChange: function (ev) {
        const container = ev.currentTarget.closest(".ccp-selection-container");
        const step2 = container.querySelector(".ccp-step-2");
        const nextBtn = step2.querySelector(".ccp-next-btn");
        const select = ev.currentTarget;

        // Enable next button when a period is selected
        if (select.value) {
            nextBtn.disabled = false;
        } else {
            nextBtn.disabled = true;
        }
    },

    /**
     * Handle Next button click
     */
    _onNextClick: function (ev) {
        ev.preventDefault();
        const container = ev.currentTarget.closest(".ccp-selection-container");
        const currentStep = ev.currentTarget.closest(".ccp-step");

        if (currentStep.classList.contains("ccp-step-1")) {
            // Move to step 2
            this._showStep(container, 2);
        } else if (currentStep.classList.contains("ccp-step-2")) {
            // Add CCP product and move to step 3
            this._addCcpProduct(container);
        }
    },

    /**
     * Handle Back button click
     */
    _onBackClick: function (ev) {
        ev.preventDefault();
        const container = ev.currentTarget.closest(".ccp-selection-container");
        this._showStep(container, 1);
    },

    /**
     * Handle Clear button click
     */
    _onClearClick: function (ev) {
        ev.preventDefault();
        const container = ev.currentTarget.closest(".ccp-selection-container");
        this._removeCcpProduct(container);
    },

    /**
     * Show a specific step in the CCP selection flow
     */
    _showStep: function (container, stepNumber) {
        const steps = container.querySelectorAll(".ccp-step");
        steps.forEach((step, index) => {
            if (index + 1 === stepNumber) {
                step.classList.add("active");
            } else {
                step.classList.remove("active");
            }
        });
    },

    /**
     * Add CCP product to the order
     */
    _addCcpProduct: function (container) {
        const self = this;
        const scannerName = container.getAttribute("data-scanner");
        const sectionName = container.getAttribute("data-section");
        const orderId = container.getAttribute("data-order-id");

        // Get selected CCP type and period
        const selectedType = container.querySelector(".ccp-radio:checked");
        const selectedPeriod = container.querySelector(".ccp-period-select");

        if (!selectedType || !selectedPeriod.value) {
            console.error("CCP type or period not selected");
            return;
        }

        const ccpType = selectedType.value;
        const period = selectedPeriod.value;

        // Show loading
        const step2 = container.querySelector(".ccp-step-2");
        const nextBtn = step2.querySelector(".ccp-next-btn");
        nextBtn.disabled = true;
        nextBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Loading...';

        // Call backend to add product
        jsonrpc(`/my/orders/${orderId}/add_ccp_line`, {
            access_token: this.orderDetail.token,
            scanner_name: scannerName,
            ccp_type: ccpType,
            period: period,
            section_name: sectionName,
        }).then((data) => {
            if (data && data.success) {
                // Store the added line ID in session storage
                if (data.line_id) {
                    sessionStorage.setItem(`ccp_line_${sectionName}`, data.line_id);
                }

                // Update the selected type display in step 3
                const selectedTypeDisplay = container.querySelector(".ccp-selected-type");
                if (selectedTypeDisplay) {
                    selectedTypeDisplay.textContent = ccpType;
                }

                // Reload the page content to show the new product
                if (data.sale_inner_template) {
                    self.$("#portal_sale_content").html($(data.sale_inner_template));
                }

                // Move to confirmation step
                self._showStep(container, 3);
            } else {
                // Show error
                alert(data.error || "Failed to add CCP product. Please try again.");
                nextBtn.disabled = false;
                nextBtn.textContent = "Next";
            }
        }).catch((error) => {
            console.error("Error adding CCP product:", error);
            alert("An error occurred. Please try again.");
            nextBtn.disabled = false;
            nextBtn.textContent = "Next";
        });
    },

    /**
     * Remove CCP product from the order
     */
    _removeCcpProduct: function (container) {
        const self = this;
        const sectionName = container.getAttribute("data-section");
        const orderId = container.getAttribute("data-order-id");
        const lineId = sessionStorage.getItem(`ccp_line_${sectionName}`);

        if (!lineId) {
            console.error("No CCP line ID found in session storage");
            // Reset to step 1 anyway
            this._resetSelection(container);
            return;
        }

        // Show loading
        const step3 = container.querySelector(".ccp-step-3");
        const clearBtn = step3.querySelector(".ccp-clear-btn");
        clearBtn.disabled = true;
        clearBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Clearing...';

        // Remove the line by setting selected to false (using existing /select endpoint)
        jsonrpc(`/my/orders/${orderId}/remove_ccp_line`, {
            access_token: this.orderDetail.token,
            line_id: lineId,
            section_name: sectionName,
        }).then((data) => {
            if (data) {
                // Clear session storage
                sessionStorage.removeItem(`ccp_line_${sectionName}`);

                // Reload the page content
                if (data.sale_inner_template) {
                    self.$("#portal_sale_content").html($(data.sale_inner_template));
                }

                // Reset the selection
                self._resetSelection(container);
            } else {
                alert("Failed to remove CCP product. Please try again.");
                clearBtn.disabled = false;
                clearBtn.textContent = "Clear CCP Selection";
            }
        }).catch((error) => {
            console.error("Error removing CCP product:", error);
            alert("An error occurred. Please try again.");
            clearBtn.disabled = false;
            clearBtn.textContent = "Clear CCP Selection";
        });
    },

    /**
     * Reset the CCP selection to step 1
     */
    _resetSelection: function (container) {
        // Reset radio buttons
        const radios = container.querySelectorAll(".ccp-radio");
        radios.forEach((radio) => {
            radio.checked = false;
        });

        // Reset period dropdown
        const periodSelect = container.querySelector(".ccp-period-select");
        if (periodSelect) {
            periodSelect.value = "";
        }

        // Reset next buttons to disabled
        const nextBtns = container.querySelectorAll(".ccp-next-btn");
        nextBtns.forEach((btn) => {
            btn.disabled = true;
            btn.textContent = "Next";
        });

        // Show step 1
        this._showStep(container, 1);
    },
});

export default publicWidget.registry.ccpSelection;
