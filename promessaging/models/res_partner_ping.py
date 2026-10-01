from odoo import api, models
from odoo.fields import Domain


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
        return Domain(super()._get_mention_suggestions_domain(search)) & Domain(
            self._promessaging_no_ping_domain()
        )

    @api.model
    def search_for_channel_invite(self, search_term, channel_id=None, limit=30):
        """Discuss invites list partner_ids; drop anyone who cannot be pinged."""
        result = super().search_for_channel_invite(
            search_term, channel_id=channel_id, limit=limit
        )
        partner_ids = result.get("partner_ids") or []
        if not partner_ids:
            return result
        blocked = set(self.browse(partner_ids)._promessaging_unpingable().ids)
        if not blocked:
            return result
        kept = [pid for pid in partner_ids if pid not in blocked]
        result["count"] = max(0, result.get("count", len(partner_ids)) - (len(partner_ids) - len(kept)))
        result["partner_ids"] = kept
        return result
