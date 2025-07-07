from odoo.http import request
import logging
_logger = logging.getLogger(__name__)


class reverse_sync_email():

    @staticmethod
    def sendReport(type, msg):
        _logger.warning("Reverse Sync Report")
        values = {'subject': str(type) + ': Reverse Sync Report'}
        recipients = ["sync@store.r-e-a-l.it"]
        for email_address in recipients:
            message = request.env['mail.message'].create(values)[0]
            values = {'mail_message_id': message.id}

            email = request.env['mail.mail'].create(values)[0]
            email.body_html = msg
            email.email_to = email_address
            email_id = {email.id}
            email.process_email_queue(email_id)
        return
