# -*- coding: utf-8 -*-
from odoo import api, models, _
from odoo.exceptions import UserError

ALLOWED_VIDEO_MIMETYPES = (
    'video/mp4',
    'video/quicktime',
    'video/mpeg',
    'video/webm',
    'video/x-msvideo',
)


class SocialPostTemplate(models.Model):
    _inherit = 'social.post.template'

    @api.constrains('image_ids')
    def _check_image_ids_mimetype(self):
        for post in self:
            for attachment in post.image_ids:
                mimetype = attachment.mimetype or ''
                if not mimetype.startswith('image') and mimetype not in ALLOWED_VIDEO_MIMETYPES:
                    raise UserError(_('Uploaded file does not seem to be a valid image or video.'))
