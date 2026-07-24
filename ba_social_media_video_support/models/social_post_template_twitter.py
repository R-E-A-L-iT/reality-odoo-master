# -*- coding: utf-8 -*-
from odoo import api, models


class SocialPostTemplate(models.Model):
    _inherit = 'social.post.template'

    @api.depends('message', 'has_twitter_accounts')
    def _compute_twitter_post_limit_message(self):
        for post in self:
            post.twitter_post_limit_message = False
            post.is_twitter_post_limit_exceed = False
