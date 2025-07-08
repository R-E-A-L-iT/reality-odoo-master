import logging
from odoo import api, fields, models
from odoo.http import request

_logger = logging.getLogger(__name__)

class CrmRevealView(models.Model):
    _inherit = 'crm.reveal.view'

    visitor_id = fields.Many2one(
        'website.visitor',
        string="Website Visitor",
        readonly=True,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        visitor = None
        # Before we write the crm.reveal.view, pull the current visitor out of the session
        for vals in vals_list:
            try:
                visitor = request.env['website.visitor']._get_visitor_from_request()
            except Exception as e:
                # Exception if called outside HTTP
                _logger.debug("Skipping adding visitor ID on crm.reveal.view create: %s", e)

            if visitor:
                try:
                    vals['visitor_id'] = visitor.id
                except Exception:
                    _logger.exception(
                        "Failed to assign visitor_id=%s to crm.reveal.view vals=%s",
                        visitor.id, vals
                    )

        return super().create(vals_list)

    def _create_reveal_view(self, website_id, url, ip_address, country_code, state_code, rules_excluded):
        rules = self.env['crm.reveal.rule']._match_url(website_id, url, country_code, state_code, rules_excluded)

        if rules:
            visitor_id = None
            try:
                visitor = request.env['website.visitor']._get_visitor_from_request()
                visitor_id = visitor.id if visitor else None
            except Exception as e:
                _logger.debug("Unable to get visitor in _create_reveal_view: %s", e)

            for rule in rules:
                if str(rule['id']) in rules_excluded:
                    continue

                query = """
                    INSERT INTO crm_reveal_view (reveal_ip, reveal_rule_id, reveal_state, create_date, visitor_id)
                    VALUES (%s, %s, 'to_process', now() at time zone 'UTC', %s)
                    ON CONFLICT DO NOTHING;
                """
                params = (ip_address, rule['id'], visitor_id)
                self.env.cr.execute(query, params)

                rules_excluded.append(str(rule['id']))

            return rules_excluded

        return False
