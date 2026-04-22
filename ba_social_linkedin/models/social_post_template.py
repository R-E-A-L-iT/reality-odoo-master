# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError


class SocialPostTemplate(models.AbstractModel):
    _inherit = 'social.post.template'

    _ALLOWED_MEDIA_MIMETYPES = ('image', 'video')

    @api.constrains('image_ids')
    def _check_image_ids_mimetype(self):
        """Override to allow video files in addition to images."""
        for post in self:
            invalid = [
                img for img in post.image_ids
                if not any(img.mimetype.startswith(m) for m in self._ALLOWED_MEDIA_MIMETYPES)
            ]
            if invalid:
                raise UserError(_('Uploaded file must be an image or video.'))
