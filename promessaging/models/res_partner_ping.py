from odoo import api, models
from odoo.osv import expression


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _promessaging_no_ping_domain(self):
        """Leaves out partners whose user asked not to be pinged."""
        return ["|", ("user_ids", "=", False), ("user_ids.no_ping", "=", False)]

    def _promessaging_unpingable(self):
        """The partners in this set that may not be pinged or messaged."""
        return self.sudo().filtered(
            lambda partner: any(user.no_ping for user in partner.user_ids)
        )

    @api.model
    def _get_mention_suggestions_domain(self, search):
        # keeps them out of the @ list in every composer
        return expression.AND([
            super()._get_mention_suggestions_domain(search),
            self._promessaging_no_ping_domain(),
        ])

    @api.model
    def search_for_channel_invite(self, search_term, channel_id=None, limit=30):
        result = super().search_for_channel_invite(search_term, channel_id=channel_id, limit=limit)
        # also keep them out of "New message" and channel invitations
        if isinstance(result, dict) and result.get("partners"):
            blocked = set(
                self.browse([p["id"] for p in result["partners"] if p.get("id")])
                ._promessaging_unpingable()
                .ids
            )
            if blocked:
                kept = [p for p in result["partners"] if p.get("id") not in blocked]
                result["count"] = max(0, result.get("count", len(kept)) - (len(result["partners"]) - len(kept)))
                result["partners"] = kept
        return result
