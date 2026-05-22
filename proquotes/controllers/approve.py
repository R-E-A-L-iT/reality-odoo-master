from odoo import http
from odoo.http import request

import logging
_logger = logging.getLogger(__name__)

class ApproveController(http.Controller):

    @http.route('/approve/application_submitted/<int:order_id>', type='json', auth='public', website=True, csrf=False)
    def approve_application_submitted(self, order_id, **kwargs):
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order or not order.exists():
            return {'error': 'Order not found'}

        # Safely get the incoming JSON payload
        try:
            data = request.get_json_data() or {}
        except Exception:
            data = {}

        submission_id = data.get('submission_uuid')

        # Compose the message
        message = "Customer submitted an APPROVE financing application."
        if submission_id:
            message += f"<br/><i>Submission ID:</i> {submission_id}"

        order.message_post(
            body=message,
            message_type='notification',
            subtype_xmlid='mail.mt_note'
        )

        return {'success': True}

