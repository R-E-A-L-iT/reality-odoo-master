from odoo import _, api, models
from odoo.exceptions import UserError


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    def _promessaging_blocked_chats(self):
        """Direct conversations with someone who cannot be reached."""
        me = self.env.user.partner_id
        blocked = self.env["discuss.channel"]
        for channel in self.sudo():
            if channel.channel_type != "chat":
                continue
            others = channel.channel_member_ids.partner_id - me
            if others._promessaging_unpingable():
                blocked |= channel
        return blocked

    def message_post(self, **kwargs):
        """Nothing gets written into a chat with someone who is out of reach."""
        if self._promessaging_blocked_chats():
            raise UserError(_("This person cannot be reached by Direct Message."))
        return super().message_post(**kwargs)

    @api.model
    def channel_get(self, partners_to, pin=True):
        """Refuse a Direct Message to someone who cannot be pinged."""
        blocked = self.env["res.partner"].browse(
            [pid for pid in partners_to if pid != self.env.user.partner_id.id]
        )._promessaging_unpingable()
        if blocked:
            raise UserError(_(
                "%s cannot be reached by Direct Message.",
                ", ".join(blocked.mapped("display_name")),
            ))
        return super().channel_get(partners_to, pin=pin)

    def add_members(self, partner_ids=None, guest_ids=None, invite_to_rtc_call=False,
                    open_chat_window=False, post_joined_message=True):
        """Same for pulling them into a conversation after the fact."""
        if partner_ids:
            blocked = self.env["res.partner"].browse(partner_ids)._promessaging_unpingable()
            # they may still join a channel themselves, they just cannot be added
            blocked -= self.env.user.partner_id
            if blocked:
                raise UserError(_(
                    "%s cannot be added to a conversation.",
                    ", ".join(blocked.mapped("display_name")),
                ))
        return super().add_members(
            partner_ids=partner_ids, guest_ids=guest_ids,
            invite_to_rtc_call=invite_to_rtc_call, open_chat_window=open_chat_window,
            post_joined_message=post_joined_message,
        )
