# -*- coding: utf-8 -*-
from odoo import api, models


class SocialPostTemplatePreview(models.Model):
    """Twitter/LinkedIn previews render every attachment as an <img>. That breaks (shows the
    browser's broken-image icon) for video attachments, since a video byte stream can't render
    through an <img> tag. Split attachments into image_urls / video_urls so the preview templates
    can render a <video> tag for the video ones instead."""
    _inherit = 'social.post.template'

    def _split_preview_attachments(self):
        self.ensure_one()
        sorted_attachments = self.image_ids.sorted(lambda image: image._origin.id or image.id, reverse=True)
        videos = sorted_attachments.filtered(lambda a: (a.mimetype or '').startswith('video'))
        images = sorted_attachments - videos
        return (
            [f'/web/image/{image._origin.id or image.id}' for image in images],
            [f'/web/content/{video._origin.id or video.id}' for video in videos],
        )

    @api.depends(lambda self: ['message', 'image_ids', 'is_twitter_post_limit_exceed', 'has_twitter_accounts'] + self._get_post_message_modifying_fields())
    def _compute_twitter_preview(self):
        self.twitter_preview = False
        for post in self.filtered('has_twitter_accounts'):
            twitter_account = post.account_ids._filter_by_media_types(['twitter'])
            image_urls, video_urls = post._split_preview_attachments()
            post.twitter_preview = self.env['ir.qweb']._render('social_twitter.twitter_preview', {
                **post._prepare_preview_values("twitter"),
                'message': post._prepare_post_content(
                    post.message,
                    'twitter',
                    **{field: post[field] for field in post._get_post_message_modifying_fields()}),
                'image_urls': image_urls,
                'video_urls': video_urls,
                'limit': twitter_account.media_id.max_post_length,
                'is_twitter_post_limit_exceed': post.is_twitter_post_limit_exceed,
            })

    @api.depends(lambda self: ['message', 'image_ids', 'display_linkedin_preview'] + self._get_post_message_modifying_fields())
    def _compute_linkedin_preview(self):
        for post in self:
            if not post.display_linkedin_preview:
                post.linkedin_preview = False
                continue
            image_urls, video_urls = post._split_preview_attachments()
            post.linkedin_preview = self.env['ir.qweb']._render('social_linkedin.linkedin_preview', {
                **post._prepare_preview_values("instagram"),
                'message': post._prepare_post_content(
                    post.message,
                    'linkedin',
                    **{field: post[field] for field in post._get_post_message_modifying_fields()}),
                'image_urls': image_urls,
                'video_urls': video_urls,
            })
