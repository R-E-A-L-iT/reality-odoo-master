# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Reverse relation to track livechat sessions
    livechat_channel_ids = fields.One2many(
        'discuss.channel',
        'livechat_lead_id',
        string='LiveChat Sessions',
        help="LiveChat conversations that created or updated this lead"
    )

    livechat_channel_count = fields.Integer(
        string='LiveChat Sessions Count',
        compute='_compute_livechat_channel_count',
        help="Number of LiveChat sessions related to this lead"
    )

    @api.depends('livechat_channel_ids')
    def _compute_livechat_channel_count(self):
        for lead in self:
            lead.livechat_channel_count = len(lead.livechat_channel_ids)

    def action_view_livechat_sessions(self):
        """
        Open a view showing all livechat sessions related to this lead
        """
        self.ensure_one()
        
        if self.livechat_channel_count == 1:
            # Open single session directly
            return {
                'type': 'ir.actions.act_window',
                'name': 'LiveChat Session',
                'res_model': 'discuss.channel',
                'res_id': self.livechat_channel_ids[0].id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            # Open list view of multiple sessions
            return {
                'type': 'ir.actions.act_window',
                'name': 'LiveChat Sessions',
                'res_model': 'discuss.channel',
                'domain': [('id', 'in', self.livechat_channel_ids.ids)],
                'view_mode': 'tree,form',
                'target': 'current',
            }
    
    def get_livechat_history_summary(self):
        """
        Get a summary of all livechat conversations for this lead
        """
        self.ensure_one()
        
        if not self.livechat_channel_ids:
            return _("No LiveChat conversations")
            
        summary = []
        for channel in self.livechat_channel_ids:
            message_count = len(channel.message_ids)
            last_message = channel.message_ids.sorted('create_date', reverse=True)[:1]
            last_message_date = last_message.create_date if last_message else channel.create_date
            
            summary.append(
                _("Session: %s (%d messages, last: %s)") % (
                    channel.name,
                    message_count,
                    last_message_date.strftime('%Y-%m-%d %H:%M')
                )
            )
        
        return "\n".join(summary)
