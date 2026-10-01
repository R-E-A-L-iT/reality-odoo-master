from odoo import http
from odoo.http import request

from odoo.addons.mail.controllers.thread import ThreadController


class PromessagingThreadController(ThreadController):

    @http.route()
    def mail_message_post(self, thread_model, thread_id, post_data, context=None, **kwargs):
        # discuss channels are internal chat, only document chatters are restricted
        if thread_model != "discuss.channel":
            Users = request.env["res.users"]
            # message_post falls back to a note when no subtype is given
            if (post_data.get("subtype_xmlid") or "mail.mt_note") != "mail.mt_note":
                Users._promessaging_check_send_message()
            else:
                Users._promessaging_check_note_recipients(
                    request.env["res.partner"].browse(post_data.get("partner_ids") or []),
                    post_data.get("partner_emails") or [],
                )
        return super().mail_message_post(thread_model, thread_id, post_data, context=context, **kwargs)
