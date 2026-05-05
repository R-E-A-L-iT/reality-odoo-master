/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.ProductImageZoom = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar, .o_portal_html_view',
    events: {
        'click .zoomable-product-image': '_onImageClick',
    },

    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments);
        this.zoomLevel = 1;
        this.minZoom = 1;
        this.maxZoom = 5;
        this.zoomStep = 0.5;
        this.isDragging = false;
        this.startX = 0;
        this.startY = 0;
        this.translateX = 0;
        this.translateY = 0;
        this.$currentTrigger = null;
        return this._super.apply(this, arguments);
    },

    /**
     * Handle image click to open zoom modal
     */
    _onImageClick: function (ev) {
        if (this.$modal && this.$modal.length) {
            return;
        }

        const $target = $(ev.currentTarget);
        const imgSrc = $target.data('zoom-src') || $target.attr('src');
        const altText = $target.attr('alt') || 'Product Image';

        this.$currentTrigger = $target;

        const galleryItems = [];
        $target.siblings('.product-gallery-data').find('.gallery-item').each(function () {
            const $item = $(this);
            if ($item.hasClass('gallery-video')) {
                galleryItems.push({ type: 'video', embed: $item.data('embed') || '', thumb: $item.data('thumb') || '' });
            } else {
                galleryItems.push({ type: 'image', src: $item.data('src') || '', thumb: $item.data('thumb') || '' });
            }
        });

        this._createModal(imgSrc, altText, galleryItems);
    },

    /**
     * Create and display the zoom modal
     */
    _createModal: function (imgSrc, altText, galleryItems) {
        // Reset zoom and position
        this.zoomLevel = 1;
        this.translateX = 0;
        this.translateY = 0;
        this.galleryItems = galleryItems || [];
        this.activeGalleryIndex = -1;

        const thumbnailStripHtml = this.galleryItems.length ? `
            <div class="zoom-thumbnail-strip" id="zoomThumbnailStrip">
                ${this.galleryItems.map((item, i) => `
                    <div class="zoom-thumb-item${item.type === 'video' ? ' is-video' : ''}" data-gallery-index="${i}">
                        <img src="${item.thumb}" alt="Image ${i + 1}" draggable="false">
                        ${item.type === 'video' ? '<div class="zoom-thumb-play"><i class="fa fa-play"></i></div>' : ''}
                    </div>
                `).join('')}
            </div>
        ` : '';

        // Create modal HTML
        const modalHtml = `
            <div class="image-zoom-modal${this.galleryItems.length ? ' has-gallery' : ''}" id="imageZoomModal">
                <div class="image-zoom-overlay"></div>
                <div class="image-zoom-container">
                    <button class="zoom-close-btn" aria-label="Close">
                        <i class="fa fa-times"></i>
                    </button>
                    <div class="zoom-controls">
                        <button class="zoom-in-btn" aria-label="Zoom In">
                            <i class="fa fa-plus"></i>
                        </button>
                        <button class="zoom-out-btn" aria-label="Zoom Out">
                            <i class="fa fa-minus"></i>
                        </button>
                        <button class="zoom-reset-btn" aria-label="Reset Zoom">
                            <i class="fa fa-refresh"></i>
                        </button>
                    </div>
                    <div class="zoom-image-wrapper">
                        <img src="${imgSrc}" alt="${altText}" class="zoom-image" id="zoomImage" draggable="false">
                        <div class="zoom-video-wrapper" id="zoomVideoWrapper" style="display:none;"></div>
                    </div>
                    <div class="zoom-loader">
                        <i class="fa fa-spinner fa-spin"></i>
                    </div>
                    ${thumbnailStripHtml}
                </div>
            </div>
        `;

        // Append modal to body
        $('body').append(modalHtml);

        // Get modal elements
        this.$modal = $('#imageZoomModal');
        this.$image = $('#zoomImage');
        this.$loader = this.$modal.find('.zoom-loader');

        // Ensure loader is visible
        this.$loader.show();

        // Bind events
        this._bindModalEvents();

        // Show modal with animation
        setTimeout(() => {
            this.$modal.addClass('active');
        }, 10);

        // Handle image load - check if already cached
        const imageElement = this.$image[0];
        if (imageElement.complete && imageElement.naturalHeight !== 0) {
            // Image is already cached and loaded
            this.$loader.hide();
        } else {
            // Wait for image to load
            this.$image.on('load.imageZoom', () => {
                this.$loader.hide();
            });

            // Handle image error
            this.$image.on('error.imageZoom', () => {
                this.$loader.html('<i class="fa fa-exclamation-triangle"></i> Failed to load image');
            });
        }
    },

    /**
     * Bind all modal events
     */
    _bindModalEvents: function () {
        const self = this;

        // Close button
        this.$modal.find('.zoom-close-btn').on('click', () => this._closeModal());

        // Overlay click to close
        this.$modal.find('.image-zoom-overlay').on('click', () => this._closeModal());

        // Zoom controls
        this.$modal.find('.zoom-in-btn').on('click', () => this._zoomIn());
        this.$modal.find('.zoom-out-btn').on('click', () => this._zoomOut());
        this.$modal.find('.zoom-reset-btn').on('click', () => this._resetZoom());

        // Thumbnail gallery clicks
        this.$modal.find('.zoom-thumb-item').on('click', (e) => {
            const index = parseInt($(e.currentTarget).data('gallery-index'));
            this._activateGalleryItem(index);
        });

        // Keyboard events
        $(document).on('keydown.imageZoom', (e) => {
            if (e.key === 'Escape') this._closeModal();
            if (e.key === '+' || e.key === '=') this._zoomIn();
            if (e.key === '-' || e.key === '_') this._zoomOut();
            if (e.key === '0') this._resetZoom();
        });

        // Mouse wheel zoom
        this.$modal.find('.zoom-image-wrapper').on('wheel', (e) => {
            e.preventDefault();
            if (e.originalEvent.deltaY < 0) {
                this._zoomIn();
            } else {
                this._zoomOut();
            }
        });

        // Drag functionality for panning
        this.$image.on('mousedown', (e) => {
            if (this.zoomLevel > 1) {
                e.preventDefault();
                this.isDragging = true;
                this.startX = e.clientX - this.translateX;
                this.startY = e.clientY - this.translateY;
                this.$image.css('cursor', 'grabbing');
            }
        });

        $(document).on('mousemove.imageZoom', (e) => {
            if (this.isDragging && this.zoomLevel > 1) {
                e.preventDefault();
                this.translateX = e.clientX - this.startX;
                this.translateY = e.clientY - this.startY;
                this._updateImageTransform();
            }
        });

        $(document).on('mouseup.imageZoom', () => {
            if (this.isDragging) {
                this.isDragging = false;
                this.$image.css('cursor', this.zoomLevel > 1 ? 'grab' : 'default');
            }
        });

        // Touch events for mobile
        let touchStartDistance = 0;
        let lastTouchX = 0;
        let lastTouchY = 0;

        this.$image.on('touchstart', (e) => {
            if (e.touches.length === 2) {
                // Pinch zoom
                const touch1 = e.touches[0];
                const touch2 = e.touches[1];
                touchStartDistance = Math.hypot(
                    touch2.clientX - touch1.clientX,
                    touch2.clientY - touch1.clientY
                );
            } else if (e.touches.length === 1 && this.zoomLevel > 1) {
                // Pan
                lastTouchX = e.touches[0].clientX - this.translateX;
                lastTouchY = e.touches[0].clientY - this.translateY;
            }
        });

        this.$image.on('touchmove', (e) => {
            if (e.touches.length === 2) {
                // Pinch zoom
                e.preventDefault();
                const touch1 = e.touches[0];
                const touch2 = e.touches[1];
                const touchDistance = Math.hypot(
                    touch2.clientX - touch1.clientX,
                    touch2.clientY - touch1.clientY
                );

                if (touchStartDistance > 0) {
                    const scale = touchDistance / touchStartDistance;
                    const newZoom = this.zoomLevel * scale;
                    this.zoomLevel = Math.max(this.minZoom, Math.min(this.maxZoom, newZoom));
                    touchStartDistance = touchDistance;
                    this._updateImageTransform();
                }
            } else if (e.touches.length === 1 && this.zoomLevel > 1) {
                // Pan
                e.preventDefault();
                this.translateX = e.touches[0].clientX - lastTouchX;
                this.translateY = e.touches[0].clientY - lastTouchY;
                this._updateImageTransform();
            }
        });
    },

    /**
     * Switch main view to a gallery item (image or video)
     */
    _activateGalleryItem: function (index) {
        const item = this.galleryItems[index];
        if (!item) return;

        this.activeGalleryIndex = index;

        this.$modal.find('.zoom-thumb-item').removeClass('active');
        this.$modal.find(`.zoom-thumb-item[data-gallery-index="${index}"]`).addClass('active');

        const $videoWrapper = this.$modal.find('#zoomVideoWrapper');
        const $controls = this.$modal.find('.zoom-controls');

        if (item.type === 'video') {
            this.$image.hide();
            $videoWrapper.html(item.embed).show();
            $controls.hide();
        } else {
            $videoWrapper.empty().hide();
            this.$image.attr('src', item.src).show();
            $controls.show();
            this._resetZoom();
        }
    },

    /**
     * Zoom in
     */
    _zoomIn: function () {
        if (this.zoomLevel < this.maxZoom) {
            this.zoomLevel = Math.min(this.maxZoom, this.zoomLevel + this.zoomStep);
            this._updateImageTransform();
            this._updateCursor();
        }
    },

    /**
     * Zoom out
     */
    _zoomOut: function () {
        if (this.zoomLevel > this.minZoom) {
            this.zoomLevel = Math.max(this.minZoom, this.zoomLevel - this.zoomStep);
            // Reset position if zoomed out to minimum
            if (this.zoomLevel === this.minZoom) {
                this.translateX = 0;
                this.translateY = 0;
            }
            this._updateImageTransform();
            this._updateCursor();
        }
    },

    /**
     * Reset zoom to default
     */
    _resetZoom: function () {
        this.zoomLevel = this.minZoom;
        this.translateX = 0;
        this.translateY = 0;
        this._updateImageTransform();
        this._updateCursor();
    },

    /**
     * Update image transform (scale and translate)
     */
    _updateImageTransform: function () {
        this.$image.css({
            'transform': `translate(${this.translateX}px, ${this.translateY}px) scale(${this.zoomLevel})`,
            'transition': this.isDragging ? 'none' : 'transform 0.3s ease'
        });

        // Update button states
        this.$modal.find('.zoom-in-btn').prop('disabled', this.zoomLevel >= this.maxZoom);
        this.$modal.find('.zoom-out-btn').prop('disabled', this.zoomLevel <= this.minZoom);
    },

    /**
     * Update cursor based on zoom level
     */
    _updateCursor: function () {
        this.$image.css('cursor', this.zoomLevel > 1 ? 'grab' : 'default');
    },

    /**
     * Close modal and cleanup
     */
    _closeModal: function () {
        if (!this.$modal || !this.$modal.length) {
            return;
        }

        this.$modal.removeClass('active');

        // Remove after animation
        setTimeout(() => {
            // Unbind all events
            $(document).off('keydown.imageZoom');
            $(document).off('mousemove.imageZoom');
            $(document).off('mouseup.imageZoom');

            // Unbind image-specific events
            if (this.$image && this.$image.length) {
                this.$image.off('load.imageZoom');
                this.$image.off('error.imageZoom');
                this.$image.off('mousedown');
                this.$image.off('touchstart');
                this.$image.off('touchmove');
            }

            // Remove modal from DOM
            if (this.$modal && this.$modal.length) {
                this.$modal.remove();
            }

            // Clear references
            this.$modal = null;
            this.$image = null;
            this.$loader = null;
            this.$currentTrigger = null;

            // Reset state
            this.isDragging = false;
        }, 300);
    },

    /**
     * @override
     */
    destroy: function () {
        if (this.$modal && this.$modal.length) {
            // Immediate cleanup without animation
            $(document).off('keydown.imageZoom');
            $(document).off('mousemove.imageZoom');
            $(document).off('mouseup.imageZoom');

            if (this.$image && this.$image.length) {
                this.$image.off('load.imageZoom');
                this.$image.off('error.imageZoom');
                this.$image.off('mousedown');
                this.$image.off('touchstart');
                this.$image.off('touchmove');
            }

            this.$modal.remove();
            this.$modal = null;
            this.$image = null;
            this.$loader = null;
            this.$currentTrigger = null;
        }
        this._super.apply(this, arguments);
    }
});

export default publicWidget.registry.ProductImageZoom;
