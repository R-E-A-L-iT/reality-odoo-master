/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

/**
 * Submenu Block Widget
 * Handles active link highlighting and smooth scrolling behavior
 */
publicWidget.registry.SubmenuBlock = publicWidget.Widget.extend({
    selector: '.s_submenu_block',
    events: {
        'click .s_submenu_link': '_onMenuLinkClick',
    },

    /**
     * @override
     */
    start() {
        this._updateActiveLink();
        this._setupScrollListener();
        this._setupNavbarVisibilityDetection();
        return this._super(...arguments);
    },

    /**
     * Handle menu link clicks for smooth scrolling
     * @private
     * @param {Event} ev
     */
    _onMenuLinkClick(ev) {
        const link = ev.currentTarget;
        const href = link.getAttribute('href');
        
        // Only handle anchor links (starting with #)
        if (href && href.startsWith('#')) {
            ev.preventDefault();
            
            const targetId = href.substring(1);
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                // Smooth scroll to target with offset for sticky submenu + dynamic header
                const submenuHeight = this.el.offsetHeight;
                const isNavbarHidden = this.el.classList.contains('o_navbar_hidden');
                const odooHeaderHeight = isNavbarHidden ? 0 : 56; // Adjust based on navbar visibility
                const targetPosition = targetElement.offsetTop - submenuHeight - odooHeaderHeight - 20;
                
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
                
                // Update active link
                this._setActiveLink(link);
                
                // Update URL hash
                window.history.pushState(null, null, href);
            }
        }
    },

    /**
     * Set active link
     * @private
     * @param {HTMLElement} activeLink
     */
    _setActiveLink(activeLink) {
        // Remove active class from all links
        this.el.querySelectorAll('.s_submenu_link').forEach(link => {
            link.classList.remove('active');
        });
        
        // Add active class to current link
        if (activeLink) {
            activeLink.classList.add('active');
        }
    },

    /**
     * Update active link based on scroll position
     * @private
     */
    _updateActiveLink() {
        const links = this.el.querySelectorAll('.s_submenu_link');
        const submenuHeight = this.el.offsetHeight;
        let activeLink = null;
        
        // Find the section that's currently in view
        links.forEach(link => {
            const href = link.getAttribute('href');
            if (href && href.startsWith('#')) {
                const targetId = href.substring(1);
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    const rect = targetElement.getBoundingClientRect();
                    const isNavbarHidden = this.el.classList.contains('o_navbar_hidden');
                    const odooHeaderHeight = isNavbarHidden ? 0 : 56; // Dynamic header height
                    const totalHeaderHeight = submenuHeight + odooHeaderHeight;
                    // Check if element is in viewport, considering dynamic headers
                    if (rect.top <= totalHeaderHeight + 50 && rect.bottom >= totalHeaderHeight + 50) {
                        activeLink = link;
                    }
                }
            }
        });
        
        this._setActiveLink(activeLink);
    },

    /**
     * Setup scroll listener for active link highlighting
     * @private
     */
    _setupScrollListener() {
        let ticking = false;
        
        const updateOnScroll = () => {
            if (!ticking) {
                requestAnimationFrame(() => {
                    this._updateActiveLink();
                    ticking = false;
                });
                ticking = true;
            }
        };
        
        // Add scroll listener
        window.addEventListener('scroll', updateOnScroll);
        
        // Store reference for cleanup
        this._scrollListener = updateOnScroll;
    },

    /**
     * Setup navbar visibility detection
     * @private
     */
    _setupNavbarVisibilityDetection() {
        let ticking = false;
        
        const checkNavbarVisibility = () => {
            if (!ticking) {
                requestAnimationFrame(() => {
                    // Look for Odoo's main navbar
                    const mainNavbar = document.querySelector('.o_main_navbar, .navbar-header, header nav');
                    
                    if (mainNavbar) {
                        const rect = mainNavbar.getBoundingClientRect();
                        // If main navbar is scrolled out of view (top < -50), hide it
                        const isNavbarHidden = rect.bottom <= 0;
                        
                        if (isNavbarHidden) {
                            this.el.classList.add('o_navbar_hidden');
                        } else {
                            this.el.classList.remove('o_navbar_hidden');
                        }
                    } else {
                        // If no main navbar found, always stick to top
                        this.el.classList.add('o_navbar_hidden');
                    }
                    
                    ticking = false;
                });
                ticking = true;
            }
        };
        
        // Initial check
        checkNavbarVisibility();
        
        // Add scroll listener for navbar visibility
        window.addEventListener('scroll', checkNavbarVisibility);
        
        // Store reference for cleanup
        this._navbarVisibilityListener = checkNavbarVisibility;
    },

    /**
     * @override
     */
    destroy() {
        // Clean up scroll listener
        if (this._scrollListener) {
            window.removeEventListener('scroll', this._scrollListener);
        }
        // Clean up navbar visibility listener
        if (this._navbarVisibilityListener) {
            window.removeEventListener('scroll', this._navbarVisibilityListener);
        }
        this._super(...arguments);
    },
});