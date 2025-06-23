import logging
from odoo import api, fields, models
from odoo.http import request

_logger = logging.getLogger(__name__)

class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    ip_address = fields.Char(string="IP Address", readonly=True, index=True)

    @api.model
    def _get_visitor_from_request(self, force_create=False, force_track_values=None):
        visitor = super(WebsiteVisitor, self)._get_visitor_from_request(
            force_create=force_create,
            force_track_values=force_track_values,
        )
        try:
            ip = request.httprequest.remote_addr
        except Exception:
            # Not in a request (e.g. shell, cron); nothing to do
            return visitor
        
        if ip and visitor.ip_address != ip:
            try:
                # sudo in case public user can’t write to visitor
                visitor.sudo().write({'ip_address': ip})
            except Exception:
                _logger.exception(
                    "Error writing IP %r to website.visitor %s",
                    ip, visitor.id
                )

        return visitor