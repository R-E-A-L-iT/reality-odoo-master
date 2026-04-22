# -*- coding: utf-8 -*-
from odoo import models


class SocialAccountLinkedin(models.Model):
    _inherit = 'social.account'

    def _linkedin_bearer_headers(self, linkedin_access_token=None):
        """Override to use a supported LinkedIn API version.
        The base module uses '202211' (November 2022) which is deprecated.
        """
        headers = super()._linkedin_bearer_headers(linkedin_access_token)
        headers['LinkedIn-Version'] = '202501'
        return headers
