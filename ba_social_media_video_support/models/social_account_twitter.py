# -*- coding: utf-8 -*-
import time

import requests

from odoo import models, _
from odoo.exceptions import UserError

TWITTER_IMAGES_UPLOAD_ENDPOINT = "https://upload.twitter.com/1.1/media/upload.json"
# Twitter recommends chunks no larger than 5MB for the video APPEND command.
TWITTER_VIDEO_CHUNK_SIZE = 4 * 1024 * 1024
TWITTER_STATUS_MAX_ATTEMPTS = 30


class SocialAccountTwitter(models.Model):
    _inherit = 'social.account'

    def _get_twitter_media_category(self, mimetype):
        if mimetype.startswith('video'):
            return 'tweet_video'
        if mimetype == 'image/gif':
            return 'tweet_gif'
        return 'tweet_image'

    def _init_twitter_upload(self, image):
        data = {
            'command': 'INIT',
            'total_bytes': image['file_size'],
            'media_category': self._get_twitter_media_category(image['mimetype']),
            'media_type': image['mimetype'],
        }
        headers = self._get_twitter_oauth_header(
            TWITTER_IMAGES_UPLOAD_ENDPOINT,
            params=data
        )
        result = requests.post(
            TWITTER_IMAGES_UPLOAD_ENDPOINT,
            data=data,
            headers=headers,
            timeout=5
        )
        if not result.ok:
            # unfortunately Twitter does not return a proper error code so we have to rely on the error message
            # last known max file size for the API is 20MB for images, 512MB for videos
            generic_api_error = result.json().get('error', '')
            raise UserError(_("We could not upload your attachment, it may be corrupted, it may exceed size limit or API may have send improper response (error: %s).", generic_api_error))

        return result.json().get('media_id_string')

    def _process_twitter_upload(self, image, media_id):
        if not image['mimetype'].startswith('video'):
            return super()._process_twitter_upload(image, media_id)

        media_bytes = image['bytes']
        for segment_index, offset in enumerate(range(0, len(media_bytes), TWITTER_VIDEO_CHUNK_SIZE)):
            params = {
                'command': 'APPEND',
                'media_id': media_id,
                'segment_index': segment_index,
            }
            files = {
                'media': media_bytes[offset:offset + TWITTER_VIDEO_CHUNK_SIZE]
            }
            headers = self._get_twitter_oauth_header(
                TWITTER_IMAGES_UPLOAD_ENDPOINT,
                params=params
            )
            result = requests.post(
                TWITTER_IMAGES_UPLOAD_ENDPOINT,
                params=params,
                files=files,
                headers=headers,
                timeout=30
            )
            if not result.ok:
                raise UserError(_("We could not upload your video, it may be corrupted or exceed the size limit."))

    def _format_images_twitter(self, image_ids):
        """ Twitter needs a special kind of uploading to process images/videos.
        It's done in 3 steps: initialize upload transaction, send bytes, finalize upload transaction.
        Videos (and gifs) are processed asynchronously by Twitter after FINALIZE, so their media_id
        is only usable once a STATUS poll reports the processing as succeeded.

        More information: https://developer.twitter.com/en/docs/media/upload-media/api-reference/post-media-upload.html """

        self.ensure_one()

        if not image_ids:
            return False

        media_ids = []
        for image in image_ids:
            media_id = self._init_twitter_upload(image)
            self._process_twitter_upload(image, media_id)
            self._finish_twitter_upload(media_id)
            if image['mimetype'].startswith('video') or image['mimetype'] == 'image/gif':
                self._wait_twitter_media_processing(media_id)
            media_ids.append(media_id)

        return media_ids

    def _wait_twitter_media_processing(self, media_id):
        status_params = {
            'command': 'STATUS',
            'media_id': media_id,
        }
        for _attempt in range(TWITTER_STATUS_MAX_ATTEMPTS):
            headers = self._get_twitter_oauth_header(
                TWITTER_IMAGES_UPLOAD_ENDPOINT,
                params=status_params,
                method='GET',
            )
            result = requests.get(
                TWITTER_IMAGES_UPLOAD_ENDPOINT,
                params=status_params,
                headers=headers,
                timeout=10
            )
            if not result.ok:
                raise UserError(_("We could not check the processing status of your video attachment."))

            processing_info = result.json().get('processing_info')
            if not processing_info:
                # No processing_info means Twitter already considers the media ready.
                return

            state = processing_info.get('state')
            if state == 'succeeded':
                return
            if state == 'failed':
                error = processing_info.get('error', {}).get('message', '')
                raise UserError(_("Twitter could not process your video attachment (error: %s).", error))

            time.sleep(min(processing_info.get('check_after_secs', 1), 5))

        raise UserError(_("Timed out waiting for Twitter to finish processing your video attachment."))
