/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";
import options from "@web_editor/js/editor/snippets.options";

/**
 * Submenu Block Options
 * Provides customization options for the submenu block in the website editor
 */
options.registry.SubmenuBlock = options.Class.extend({
    
    /**
     * @override
     */
    start() {
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Add and manage links functionality
     * Opens the full link management dialog
     */
    async addLink(previewMode, widgetValue, params) {
        // Get existing links
        const $links = this.$target.find('.s_submenu_link');

        const linkData = [];
        $links.each((index, link) => {
            const $link = $(link);
            const $parent = $link.closest('.nav-item');
            if (!$parent.hasClass('d-none') || $link.text().trim()) {
                linkData.push({
                    text: $link.text().trim(),
                    href: $link.attr('href') || '#',
                    visible: !$parent.hasClass('d-none')
                });
            }
        });

        // Open the link management dialog
        const newLinkData = await this._showLinkEditDialog(linkData);
        if (newLinkData) {
            this._updateLinks(newLinkData);
        }
    },

    /**
     * Set hover color (text or background)
     */
    setHoverColor(previewMode, widgetValue, params) {
        const type = params.defaultValue || 'text'; // 'text' or 'bg'
        let colorValue = params.activeValue;

        // If no activeValue, try to extract from class
        if (!colorValue) {
            const colorClass = params.colorPrefix + widgetValue;
            const isBackground = type === 'bg' || colorClass.startsWith('bg-');
            colorValue = this._extractColorFromClass(colorClass, isBackground);
        }

        if (colorValue) {
            const varName = type === 'bg' ? '--submenu-link-hover-bg' : '--submenu-link-hover-color';
            this.$target[0].style.setProperty(varName, colorValue);

            // Store the selected color name as a data attribute for state tracking
            const attrName = type === 'bg' ? 'data-hover-bg-color' : 'data-hover-text-color';
            this.$target[0].setAttribute(attrName, widgetValue);
        }
    },

    /**
     * Set active color (text or background)
     */
    setActiveColor(previewMode, widgetValue, params) {
        const type = params.defaultValue || 'text'; // 'text' or 'bg'
        let colorValue = params.activeValue;

        // If no activeValue, try to extract from class
        if (!colorValue) {
            const colorClass = params.colorPrefix + widgetValue;
            const isBackground = type === 'bg' || colorClass.startsWith('bg-');
            colorValue = this._extractColorFromClass(colorClass, isBackground);
        }

        if (colorValue) {
            const varName = type === 'bg' ? '--submenu-link-active-bg' : '--submenu-link-active-color';
            this.$target[0].style.setProperty(varName, colorValue);

            // Store the selected color name as a data attribute for state tracking
            const attrName = type === 'bg' ? 'data-active-bg-color' : 'data-active-text-color';
            this.$target[0].setAttribute(attrName, widgetValue);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'setHoverColor': {
                const type = params.defaultValue || 'text';
                const attrName = type === 'bg' ? 'data-hover-bg-color' : 'data-hover-text-color';
                return this.$target[0].getAttribute(attrName) || '';
            }
            case 'setActiveColor': {
                const type = params.defaultValue || 'text';
                const attrName = type === 'bg' ? 'data-active-bg-color' : 'data-active-text-color';
                return this.$target[0].getAttribute(attrName) || '';
            }
        }
        return this._super(methodName, params);
    },

    /**
     * Extract color value from a Bootstrap/Odoo color class
     * @private
     */
    _extractColorFromClass(className, isBackground) {
        const testEl = document.createElement('div');
        testEl.style.cssText = 'position: absolute; left: -9999px; top: -9999px; visibility: hidden;';
        testEl.className = className;
        document.body.appendChild(testEl);

        const computedStyle = window.getComputedStyle(testEl);
        const colorValue = isBackground ? computedStyle.backgroundColor : computedStyle.color;

        document.body.removeChild(testEl);

        // Return the color if it's valid
        if (colorValue && colorValue !== 'rgba(0, 0, 0, 0)' && colorValue !== 'transparent') {
            return colorValue;
        }
        return null;
    },

    /**
     * Show dialog for editing links using a simpler approach
     * @private
     */
    async _showLinkEditDialog(linkData) {
        // Create a simple overlay dialog without Bootstrap dependency
        const overlay = document.createElement('div');
        overlay.className = 'submenu-link-editor-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
        `;

        const dialog = document.createElement('div');
        dialog.className = 'submenu-link-editor-dialog';
        dialog.style.cssText = `
            background: white;
            border-radius: 8px;
            max-width: 800px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        `;

        dialog.innerHTML = `
            <div class="p-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h5 class="mb-0">${_t('Manage Submenu Links')}</h5>
                    <button type="button" class="btn btn-sm btn-light close-dialog">
                        <i class="fa fa-times"></i>
                    </button>
                </div>
                
                <div class="alert alert-info">
                    <i class="fa fa-info-circle"></i> 
                    ${_t('Use #section-id for anchor links (e.g., #about, #contact). You can add unlimited links!')}
                </div>
                
                <div id="link-editor">
                    ${linkData.map((link, index) => `
                        <div class="row mb-3 link-row" data-index="${index}">
                            <div class="col-5">
                                <label class="form-label">${_t('Link Text')}</label>
                                <input type="text" class="form-control link-text" value="${link.text}" placeholder="Enter link text...">
                            </div>
                            <div class="col-5">
                                <label class="form-label">${_t('URL or Anchor')}</label>
                                <input type="text" class="form-control link-href" value="${link.href}" placeholder="#section-id or https://...">
                            </div>
                            <div class="col-2 d-flex align-items-end">
                                <button type="button" class="btn btn-sm btn-outline-danger remove-link me-1" title="${_t('Remove this link')}">
                                    <i class="fa fa-trash"></i>
                                </button>
                                <button type="button" class="btn btn-sm btn-outline-secondary move-up" title="${_t('Move up')}">
                                    <i class="fa fa-arrow-up"></i>
                                </button>
                            </div>
                        </div>
                    `).join('')}
                </div>
                
                <div class="d-flex gap-2 mt-3">
                    <button type="button" class="btn btn-success" id="add-link">
                        <i class="fa fa-plus"></i> ${_t('Add New Link')}
                    </button>
                </div>
                
                <div class="d-flex gap-2 mt-4 pt-3 border-top">
                    <button type="button" class="btn btn-secondary close-dialog">${_t('Cancel')}</button>
                    <button type="button" class="btn btn-primary" id="save-links">${_t('Save Changes')}</button>
                </div>
            </div>
        `;

        overlay.appendChild(dialog);
        document.body.appendChild(overlay);

        return new Promise((resolve) => {
            let saveInProgress = false; // Prevent double-click saves

            // Add link functionality
            dialog.querySelector('#add-link').addEventListener('click', () => {
                this._addNewLinkRow(dialog);
            });

            // Remove link and move functionality
            dialog.addEventListener('click', (e) => {
                if (e.target.classList.contains('remove-link') || e.target.closest('.remove-link')) {
                    e.target.closest('.link-row').remove();
                } else if (e.target.classList.contains('move-up') || e.target.closest('.move-up')) {
                    const row = e.target.closest('.link-row');
                    const prevRow = row.previousElementSibling;
                    if (prevRow) {
                        row.parentNode.insertBefore(row, prevRow);
                    }
                }
            });

            // Save functionality - prevent double clicks
            dialog.querySelector('#save-links').addEventListener('click', () => {
                if (saveInProgress) return; // Prevent double-click
                saveInProgress = true;
                
                const rows = dialog.querySelectorAll('#link-editor .link-row');
                const newLinkData = [];
                rows.forEach(row => {
                    const text = row.querySelector('.link-text').value.trim();
                    const href = row.querySelector('.link-href').value.trim();
                    if (text) { // Only save non-empty links
                        newLinkData.push({
                            text: text,
                            href: href || '#',
                        });
                    }
                });
                overlay.remove();
                resolve(newLinkData);
            });

            // Close functionality
            const closeButtons = dialog.querySelectorAll('.close-dialog');
            closeButtons.forEach(btn => {
                btn.addEventListener('click', () => {
                    overlay.remove();
                    resolve(null);
                });
            });

            // Close on overlay click
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    overlay.remove();
                    resolve(null);
                }
            });
        });
    },

    /**
     * Update links in the submenu
     * @private
     */
    _updateLinks(newLinkData) {
        const $nav = this.$target.find('.s_submenu_list');
        $nav.empty();
        
        newLinkData.forEach(link => {
            if (link.text.trim()) {
                const $li = $(`
                    <li class="nav-item">
                        <a class="nav-link s_submenu_link" href="${link.href}">${link.text}</a>
                    </li>
                `);
                $nav.append($li);
            }
        });
    },

    /**
     * Add a new link row to the dialog
     * @private
     */
    _addNewLinkRow(dialog) {
        const linkEditor = dialog.querySelector('#link-editor');
        const newIndex = linkEditor.children.length;
        const newRow = document.createElement('div');
        newRow.className = 'row mb-3 link-row';
        newRow.setAttribute('data-index', newIndex);
        newRow.innerHTML = `
            <div class="col-5">
                <label class="form-label">${_t('Link Text')}</label>
                <input type="text" class="form-control link-text" value="" placeholder="Enter link text...">
            </div>
            <div class="col-5">
                <label class="form-label">${_t('URL or Anchor')}</label>
                <input type="text" class="form-control link-href" value="#" placeholder="#section-id or https://...">
            </div>
            <div class="col-2 d-flex align-items-end">
                <button type="button" class="btn btn-sm btn-outline-danger remove-link me-1" title="${_t('Remove this link')}">
                    <i class="fa fa-trash"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary move-up" title="${_t('Move up')}">
                    <i class="fa fa-arrow-up"></i>
                </button>
            </div>
        `;
        linkEditor.appendChild(newRow);
        // Focus on the new text input
        newRow.querySelector('.link-text').focus();
    },


    /**
     * @override
     */
    cleanForSave() {
        this._super(...arguments);
        // Remove any temporary classes or attributes
        this.$target.find('.s_submenu_link').removeClass('active');
        // Keep the data attributes for color state tracking:
        // data-hover-bg-color, data-hover-text-color,
        // data-active-bg-color, data-active-text-color
    },
});