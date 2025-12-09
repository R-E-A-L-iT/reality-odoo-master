# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    @api.model
    def _get_compatible_providers(
        self, company_id, partner_id, amount, currency_id=None, force_tokenization=False,
        is_express_checkout=False, is_validation=False, **kwargs
    ):
        """
        Override to enforce company-aware payment provider selection.

        This ensures payment providers are filtered based on company assignment:
        - Shared providers (company_id = False) are available to ALL companies
        - Company-specific providers are only available to their assigned company

        This allows:
        1. Global payment providers (e.g., shared Stripe account) to work across all companies
        2. Company-specific providers (e.g., separate USD/CAD Stripe accounts) to be restricted

        Critical for multi-company setups with currency-specific payment accounts.
        """
        # Call parent method to get initial compatible providers
        compatible_providers = super()._get_compatible_providers(
            company_id, partner_id, amount, currency_id=currency_id,
            force_tokenization=force_tokenization,
            is_express_checkout=is_express_checkout,
            is_validation=is_validation,
            **kwargs
        )

        # Get context for logging
        company = self.env['res.company'].browse(company_id)
        currency = self.env['res.currency'].browse(currency_id) if currency_id else None
        partner = self.env['res.partner'].browse(partner_id)

        # Log initial state
        _logger.info(
            "=" * 80 + "\n"
            "PAYMENT PROVIDER SELECTION\n"
            "Company: %s (ID: %s)\n"
            "Currency: %s (ID: %s)\n"
            "Partner: %s (ID: %s, Country: %s)\n"
            "Amount: %s\n"
            "Providers found by parent method: %s\n"
            "Provider details: %s",
            company.name if company else 'None',
            company_id,
            currency.name if currency else 'None',
            currency_id,
            partner.name if partner else 'None',
            partner_id,
            partner.country_id.name if partner and partner.country_id else 'None',
            amount,
            len(compatible_providers),
            [(p.name, p.company_id.name if p.company_id else 'SHARED', p.code) for p in compatible_providers]
        )

        # Apply company filtering that respects shared providers
        # Show providers that either:
        # 1. Have no company assigned (company_id = False) - shared across all companies
        # 2. Are assigned to the exact company making the order
        company_filtered_providers = compatible_providers.filtered(
            lambda p: not p.company_id or p.company_id.id == company_id
        )

        # Log filtering results
        if len(company_filtered_providers) != len(compatible_providers):
            removed_providers = compatible_providers - company_filtered_providers
            _logger.warning(
                "COMPANY FILTER APPLIED\n"
                "Removed %s provider(s) due to company mismatch:\n"
                "%s\n"
                "Keeping %s provider(s):\n"
                "%s",
                len(removed_providers),
                [(p.name, p.company_id.name if p.company_id else 'SHARED', 'Expected: ' + company.name + ' or SHARED') for p in removed_providers],
                len(company_filtered_providers),
                [(p.name, p.company_id.name if p.company_id else 'SHARED', p.code) for p in company_filtered_providers]
            )

        # Additional validation: log if no providers found
        if not company_filtered_providers:
            _logger.error(
                "NO PAYMENT PROVIDERS AVAILABLE!\n"
                "Company: %s (ID: %s)\n"
                "Currency: %s\n"
                "This likely means:\n"
                "1. No payment providers are configured (shared or for this company)\n"
                "2. Payment providers are disabled\n"
                "3. Payment providers don't support this currency\n"
                "4. Payment providers don't support the customer's country\n"
                "Please check Settings → Payment Providers configuration.",
                company.name if company else 'None',
                company_id,
                currency.name if currency else 'None'
            )
        else:
            _logger.info(
                "FINAL PROVIDER SELECTION: %s provider(s) available\n"
                "Details: %s\n"
                "=" * 80,
                len(company_filtered_providers),
                [(p.name, p.code, p.company_id.name if p.company_id else 'SHARED', p.state) for p in company_filtered_providers]
            )

        return company_filtered_providers
