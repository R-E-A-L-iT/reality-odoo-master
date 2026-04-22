# -*- coding: utf-8 -*-
import logging
import requests
from werkzeug.urls import url_join

from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SocialLivePostLinkedin(models.Model):
    _inherit = 'social.live.post'

    # -------------------------------------------------------------------------
    # Fix 1: Image upload — better error handling + increased timeouts
    # -------------------------------------------------------------------------

    def _linkedin_upload_image(self, account_id, image_id):
        """Override to fix silent error masking and increase upload timeouts.

        Base module bug: when initializeUpload returns a non-OK response,
        it logs the error but continues executing, then raises a misleading
        "try reducing your image size" UserError instead of the real API error.
        """
        # Step 1 — Register image upload
        data = {
            "initializeUploadRequest": {
                "owner": account_id.linkedin_account_urn,
            },
        }
        response = requests.post(
            url_join(self.env['social.media']._LINKEDIN_ENDPOINT, 'images?action=initializeUpload'),
            headers=account_id._linkedin_bearer_headers(),
            json=data,
            timeout=30,  # increased from 10s
        )

        if not response.ok:
            try:
                error_detail = response.json().get('message', response.text)
            except Exception:
                error_detail = response.text
            _logger.error(
                'LinkedIn image upload init failed (HTTP %s): %r',
                response.status_code, error_detail,
            )
            raise UserError(_(
                "Could not register the image upload with LinkedIn (HTTP %s: %s). "
                "Please check your LinkedIn connection or try again later.",
                response.status_code, error_detail,
            ))

        try:
            response_json = response.json()
        except Exception:
            raise UserError(_("LinkedIn returned an unexpected response. Please try again."))

        if 'value' not in response_json or 'uploadUrl' not in response_json['value']:
            raise UserError(_(
                "We could not upload your image, try reducing its size and posting it again "
                "(error: Failed during upload registering)."
            ))

        upload_url = response_json['value']['uploadUrl']
        image_urn = response_json['value']['image']

        # Step 2 — Upload binary data
        binary_data = image_id.with_context(bin_size=False).raw
        headers = account_id._linkedin_bearer_headers()
        headers['Content-Type'] = 'application/octet-stream'

        response = requests.request(
            'POST', upload_url, data=binary_data, headers=headers,
            timeout=60,  # increased from 15s
        )

        if not response.ok:
            _logger.error(
                'LinkedIn image binary upload failed (HTTP %s): %r',
                response.status_code, response.text,
            )
            raise UserError(_(
                "We could not upload your image to LinkedIn (HTTP %s). "
                "Supported formats: JPEG, PNG, GIF, WEBP.",
                response.status_code,
            ))

        return image_urn

    # -------------------------------------------------------------------------
    # Fix 2: Video upload support
    # -------------------------------------------------------------------------

    def _linkedin_upload_video(self, account_id, video_id):
        """Upload a video to LinkedIn using the 3-step chunked upload process.

        LinkedIn API: POST /rest/videos?action=initializeUpload
        Returns the video URN to use in the post content payload.
        """
        video_data = video_id.with_context(bin_size=False).raw
        file_size = len(video_data)

        # Step 1 — Initialize video upload
        init_data = {
            "initializeUploadRequest": {
                "owner": account_id.linkedin_account_urn,
                "fileSizeBytes": file_size,
                "uploadCaptions": False,
                "uploadThumbnail": False,
            }
        }
        response = requests.post(
            url_join(self.env['social.media']._LINKEDIN_ENDPOINT, 'videos?action=initializeUpload'),
            headers=account_id._linkedin_bearer_headers(),
            json=init_data,
            timeout=30,
        )

        if not response.ok:
            try:
                error_detail = response.json().get('message', response.text)
            except Exception:
                error_detail = response.text
            _logger.error(
                'LinkedIn video upload init failed (HTTP %s): %r',
                response.status_code, error_detail,
            )
            raise UserError(_(
                "Could not initialize LinkedIn video upload (HTTP %s: %s).",
                response.status_code, error_detail,
            ))

        try:
            response_json = response.json()
        except Exception:
            raise UserError(_("LinkedIn returned an unexpected response during video upload initialization."))

        value = response_json.get('value', {})
        video_urn = value.get('video')
        upload_token = value.get('uploadToken', '')
        upload_instructions = value.get('uploadInstructions', [])

        if not video_urn or not upload_instructions:
            raise UserError(_("Could not initialize LinkedIn video upload. Please try again."))

        # Step 2 — Upload video chunks
        uploaded_part_ids = []
        for instruction in upload_instructions:
            chunk_start = instruction.get('firstByte', 0)
            chunk_end = instruction.get('lastByte', file_size - 1)
            upload_url = instruction.get('uploadUrl')
            chunk_data = video_data[chunk_start:chunk_end + 1]

            chunk_response = requests.put(
                upload_url,
                data=chunk_data,
                headers={'Content-Type': 'application/octet-stream'},
                timeout=120,
            )

            if not chunk_response.ok:
                raise UserError(_(
                    "Could not upload video chunk to LinkedIn (HTTP %s). Please try again.",
                    chunk_response.status_code,
                ))

            uploaded_part_ids.append(chunk_response.headers.get('etag', ''))

        # Step 3 — Finalize upload
        finalize_data = {
            "finalizeUploadRequest": {
                "video": video_urn,
                "uploadToken": upload_token,
                "uploadedPartIds": uploaded_part_ids,
            }
        }
        finalize_response = requests.post(
            url_join(self.env['social.media']._LINKEDIN_ENDPOINT, 'videos?action=finalizeUpload'),
            headers=account_id._linkedin_bearer_headers(),
            json=finalize_data,
            timeout=30,
        )

        if not finalize_response.ok:
            _logger.error(
                'LinkedIn video finalize failed (HTTP %s): %r',
                finalize_response.status_code, finalize_response.text,
            )
            raise UserError(_(
                "Could not finalize LinkedIn video upload (HTTP %s). Please try again.",
                finalize_response.status_code,
            ))

        return video_urn

    def _post_linkedin(self):
        """Override to route video attachments to _linkedin_upload_video.

        When image_ids contains only images, delegates to super() unchanged.
        When a video is present, handles the full post with video content.
        LinkedIn does not support mixed image+video — video takes priority.
        """
        for live_post in self:
            if not live_post.post_id.image_ids:
                # No media — let base handle it (URL article preview, text only)
                super(SocialLivePostLinkedin, live_post)._post_linkedin()
                continue

            video_ids = live_post.post_id.image_ids.filtered(
                lambda a: a.mimetype.startswith('video'))

            if not video_ids:
                # Images only — delegate entirely to base method (unchanged)
                super(SocialLivePostLinkedin, live_post)._post_linkedin()
                continue

            # Video present — build the post payload with video content
            data = {
                "author": live_post.account_id.linkedin_account_urn,
                "commentary": self._format_to_linkedin_little_text(live_post.message),
                "distribution": {"feedDistribution": "MAIN_FEED"},
                "lifecycleState": "PUBLISHED",
                "visibility": "PUBLIC",
            }

            try:
                # LinkedIn supports 1 video per post; take the first video
                video_urn = self._linkedin_upload_video(live_post.account_id, video_ids[0])
                data["content"] = {"media": {"id": video_urn}}
            except UserError as e:
                live_post.write({'state': 'failed', 'failure_reason': str(e)})
                continue

            response = requests.post(
                url_join(self.env['social.media']._LINKEDIN_ENDPOINT, 'posts'),
                headers=live_post.account_id._linkedin_bearer_headers(),
                json=data,
                timeout=10,
            )

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
            live_post.write(values)
