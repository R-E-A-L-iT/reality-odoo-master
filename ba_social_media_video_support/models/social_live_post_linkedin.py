# -*- coding: utf-8 -*-
import logging

import requests
from urllib.parse import urlparse
from werkzeug.urls import url_join

from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SocialLivePostLinkedin(models.Model):
    _inherit = 'social.live.post'

    def _post_linkedin(self):
        for live_post in self:
            url_in_message = self.env['social.post']._extract_url_from_message(live_post.message)

            data = {
                "author": live_post.account_id.linkedin_account_urn,
                "commentary": self._format_to_linkedin_little_text(live_post.message),
                "distribution": {"feedDistribution": "MAIN_FEED"},
                "lifecycleState": "PUBLISHED",
                "visibility": "PUBLIC",
            }

            attachments = live_post.post_id.image_ids
            video_attachments = attachments.filtered(lambda a: (a.mimetype or '').startswith('video'))
            image_attachments = attachments - video_attachments

            if video_attachments:
                try:
                    video_urn = self._linkedin_upload_video(live_post.account_id, video_attachments[0])
                except UserError as e:
                    live_post.write({
                        'state': 'failed',
                        'failure_reason': str(e)
                    })
                    continue
                data["content"] = {"media": {"id": video_urn}}
            elif image_attachments:
                try:
                    images_urn = [
                        self._linkedin_upload_image(live_post.account_id, image_id)
                        for image_id in image_attachments
                    ]
                except UserError as e:
                    live_post.write({
                        'state': 'failed',
                        'failure_reason': str(e)
                    })
                    continue

                if len(images_urn) == 1:
                    data["content"] = {"media": {"id": images_urn[0]}}
                else:
                    data["content"] = {
                        "multiImage": {
                            "images": [{"id": image_urn} for image_urn in images_urn],
                        }
                    }

            elif url_in_message:
                tracker_code = urlparse(url_in_message).path.split('/r/')[-1]
                link_tracker = self.env['link.tracker'].search([
                    ('link_code_ids.code', '=', tracker_code),
                    ('source_id', '=', live_post.post_id.source_id.id),
                ], limit=1)
                original_url = link_tracker.url or url_in_message
                data['content'] = {
                    'article': {
                        'source': url_in_message,
                        'title': link_tracker.title or original_url,
                        'description': original_url,
                    },
                }

            response = requests.post(
                url_join(self.env['social.media']._LINKEDIN_ENDPOINT, 'posts'),
                headers=live_post.account_id._linkedin_bearer_headers(),
                json=data, timeout=10)

            post_id = response.headers.get('x-restli-id')
            if response.ok and post_id:
                values = {
                    'state': 'posted',
                    'failure_reason': False,
                    'linkedin_post_id': post_id,
                }
            else:
                try:
                    response_json = response.json()
                except Exception:
                    response_json = {}
                values = {
                    'state': 'failed',
                    'failure_reason': response_json.get('message', _('unknown')),
                }

                if response_json.get('serviceErrorCode') == 65600:
                    # Invalid access token
                    live_post.account_id._action_disconnect_accounts(response)

            live_post.write(values)

    def _linkedin_upload_video(self, account_id, video_attachment):
        # LinkedIn's Video API needs a dedicated register/upload/finalize flow (unlike images
        # which only need register + a single PUT): https://learn.microsoft.com/linkedin/marketing/integrations/community-management/shares/vector-asset-api
        data = {
            "initializeUploadRequest": {
                "owner": account_id.linkedin_account_urn,
                "fileSizeBytes": video_attachment.file_size,
                "uploadCaptions": False,
                "uploadThumbnail": False,
            },
        }
        response = requests.post(
            url_join(self.env['social.media']._LINKEDIN_ENDPOINT, 'videos?action=initializeUpload'),
            headers=account_id._linkedin_bearer_headers(),
            json=data, timeout=10)

        if not response.ok:
            _logger.error('Could not upload the video: %r.', response.text)

        response = response.json()
        upload_value = response.get('value') or {}
        upload_instructions = upload_value.get('uploadInstructions')
        video_urn = upload_value.get('video')
        upload_token = upload_value.get('uploadToken', '')

        if not upload_instructions or not video_urn:
            raise UserError(_("We could not upload your video, try reducing its size and posting it again (error: Failed during upload registering)."))

        video_bytes = video_attachment.with_context(bin_size=False).raw

        headers = account_id._linkedin_bearer_headers()
        headers['Content-Type'] = 'application/octet-stream'

        uploaded_part_ids = []
        for part in upload_instructions:
            chunk = video_bytes[part['firstByte']:part['lastByte'] + 1]
            part_response = requests.put(part['uploadUrl'], data=chunk, headers=headers, timeout=60)
            if not part_response.ok:
                raise UserError(_("We could not upload your video, try reducing its size and posting it again."))
            uploaded_part_ids.append(part_response.headers.get('etag'))

        finalize_response = requests.post(
            url_join(self.env['social.media']._LINKEDIN_ENDPOINT, 'videos?action=finalizeUpload'),
            headers=account_id._linkedin_bearer_headers(),
            json={
                "finalizeUploadRequest": {
                    "video": video_urn,
                    "uploadToken": upload_token,
                    "uploadedPartIds": uploaded_part_ids,
                },
            },
            timeout=15)

        if not finalize_response.ok:
            raise UserError(_("We could not finalize your video upload, try posting it again."))

        return video_urn
