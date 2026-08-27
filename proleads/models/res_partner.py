# -*- coding: utf-8 -*-

from odoo import fields, models


class ResPartner(models.Model):
    """Contact-level LinkedIn link.

    Moved here from the retired `procontact` module, which was deleted — this
    was the only field of it still wanted. The column name is unchanged
    (res_partner.linkedin_link) so existing data carries over untouched.

    Note this is the CONTACT-level link; `crm.lead.linkedin_link` (see
    crm_lead.py) is a separate field on the lead itself.
    """
    _inherit = 'res.partner'

    linkedin_link = fields.Char(
        string="LinkedIn link"
    )
