# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import models, _
from odoo.exceptions import UserError, ValidationError


class SocialPost(models.Model):
    _inherit = 'social.post'

    def _check_post_access(self):
        """Twitter no longer enforces a character-limit gate: X supports post lengths well
        beyond the legacy 280 cap depending on account type, so the app should let the
        Twitter API validate length instead of blocking here."""
        if any(not post.account_ids for post in self):
            raise UserError(_(
                'Please specify at least one account to post into (for post ID(s) %s).',
                ', '.join([str(post.id) for post in self if not post.account_ids])
            ))
        errors = defaultdict(list)
        for post in self:
            for media in post.media_ids.filtered(
                lambda media: media.media_type != 'twitter'
                and media.max_post_length
                and post.message_length > media.max_post_length
            ):
                errors[post].append(_("%s (max %s chars)", media.name, media.max_post_length))
        if bool(errors):
            raise ValidationError(_(
                "Due to length restrictions, the following posts cannot be posted:\n %s",
                "\n".join(["%s : %s" % (post.display_name, ",".join(err)) for post, err in errors.items()])
            ))
