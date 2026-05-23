# -*- coding: utf-8 -*-

from odoo import api, models
from odoo import models, api


class MailWizardInvite(models.TransientModel):
    _inherit = 'mail.wizard.invite'

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        res['notify'] = False  # always default to false
        return res

    def add_followers(self):
        self.ensure_one()
        self.notify = False  # force disable before executing
        return super().add_followers()
