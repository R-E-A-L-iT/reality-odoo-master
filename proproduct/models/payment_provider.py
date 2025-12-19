import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    @api.model
    def _get_compatible_providers(
        self, company_id, partner_id, amount, currency_id=None, force_tokenization=False,
        is_express_checkout=False, is_validation=False, **kwargs
    ):
        """
        Ensure provider selection works in website/public-user context in multi-company setups.

        Key fixes:
        - Run the parent compatibility search under sudo() (public user often can't read providers on prod)
        - Force allowed_company_ids + with_company(company) so record rules and company-dependent fields behave
        - Provide a fallback search so checkout doesn't brick if parent returns 0 due to access rules/join domains
        """

        # Use the same env as selection to avoid mismatched context in logs
        base_company = self.env['res.company'].browse(company_id).exists()
        base_currency = self.env['res.currency'].browse(currency_id).exists() if currency_id else None
        base_partner = self.env['res.partner'].browse(partner_id).exists()
        website_id = kwargs.get('website_id')  # website_sale usually passes this

        # Force the correct multi-company context (and sudo to survive public user ACLs)
        self_scoped = self.sudo().with_context(
            allowed_company_ids=[company_id],
            force_company=company_id,  # helps some company-dependent computes
        )
        if base_company:
            self_scoped = self_scoped.with_company(base_company)

        # ---- Call parent method in the correct context
        compatible_providers = super(PaymentProvider, self_scoped)._get_compatible_providers(
            company_id, partner_id, amount, currency_id=currency_id,
            force_tokenization=force_tokenization,
            is_express_checkout=is_express_checkout,
            is_validation=is_validation,
            **kwargs
        )

        # ---- Logging: initial state
        _logger.info(
            "=" * 80 + "\n"
            "PAYMENT PROVIDER SELECTION\n"
            "Company: %s (ID: %s)\n"
            "Currency: %s (ID: %s)\n"
            "Partner: %s (ID: %s, Country: %s)\n"
            "Website ID (kwarg): %s\n"
            "allowed_company_ids (scoped): %s\n"
            "Amount: %s\n"
            "Providers found by parent method: %s\n"
            "Provider details: %s",
            base_company.name if base_company else 'None',
            company_id,
            base_currency.name if base_currency else 'None',
            currency_id,
            base_partner.name if base_partner else 'None',
            partner_id,
            base_partner.country_id.name if base_partner and base_partner.country_id else 'None',
            website_id,
            self_scoped.env.context.get('allowed_company_ids'),
            amount,
            len(compatible_providers),
            [(p.name, p.company_id.name if p.company_id else 'SHARED', p.code, p.state) for p in compatible_providers]
        )

        # ---- Apply your company filtering (shared OR exact match)
        company_filtered_providers = compatible_providers.filtered(
            lambda p: not p.company_id or p.company_id.id == company_id
        )

        # If parent returned nothing (common on prod due to ACLs/joins), do a safe fallback search.
        if not company_filtered_providers:
            _logger.warning(
                "Parent compatibility returned 0 providers. Running fallback provider search under sudo()."
            )

            # Build a conservative fallback domain:
            # - enabled providers only
            # - provider is either shared or assigned to this company
            # - if website_id is provided, provider website is either empty or matches
            domain = [
                ('state', 'in', ['enabled', 'test']),
                '|', ('company_id', '=', False), ('company_id', '=', company_id),
            ]
            if website_id:
                domain += ['|', ('website_id', '=', False), ('website_id', '=', website_id)]

            fallback_providers = self_scoped.search(domain)

            # Keep your final company filtering (redundant but explicit)
            company_filtered_providers = fallback_providers.filtered(
                lambda p: not p.company_id or p.company_id.id == company_id
            )

            _logger.warning(
                "Fallback providers found: %s | Details: %s",
                len(company_filtered_providers),
                [(p.name, p.code, p.company_id.name if p.company_id else 'SHARED', p.state,
                  p.website_id.name if p.website_id else 'NO WEBSITE') for p in company_filtered_providers]
            )

        # ---- Final logging
        if not company_filtered_providers:
            _logger.error(
                "NO PAYMENT PROVIDERS AVAILABLE!\n"
                "Company: %s (ID: %s)\n"
                "Currency: %s\n"
                "Website ID: %s\n"
                "This likely means:\n"
                "1. Provider records are not visible to the public user due to ACL/record rules\n"
                "2. Provider is not enabled/published or not linked to the website\n"
                "3. Multi-company context is still wrong\n"
                "Check: Settings → Payment Providers + access rules on payment.provider / payment.method / payment.icon",
                base_company.name if base_company else 'None',
                company_id,
                base_currency.name if base_currency else 'None',
                website_id,
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