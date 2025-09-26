# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools import html2plaintext
from odoo.exceptions import AccessError


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    # Field to track if a lead has been created from this channel
    livechat_lead_id = fields.Many2one(
        'crm.lead', 
        string='Related CRM Lead',
        help="Lead created from this livechat conversation"
    )

    def execute_command_create_lead_enhanced(self):
        """
        Enhanced lead creation method for UI button action
        """
        self.ensure_one()
        partner = self.env.user.partner_id
        
        # Check if user has CRM access
        has_crm_access = (
            self.env.user.has_group('crm.group_use_lead') or
            self.env.user.has_group('sales_team.group_sale_salesman') or
            self.env.user.has_group('sales_team.group_sale_salesman_all_leads') or
            self.env.user.has_group('base.group_user')
        )
        
        if not has_crm_access:
            self._send_transient_message(partner, _('You do not have permission to create leads.'))
            return {'success': False, 'message': 'No permission'}

        # Check if this is a livechat channel
        if self.channel_type != 'livechat':
            self._send_transient_message(partner, _('Lead creation is only available for livechat channels.'))
            return {'success': False, 'message': 'Not livechat channel'}

        # Check if lead already exists
        if self.livechat_lead_id:
            self._send_transient_message(
                partner, 
                _('Lead already exists: %s', self.livechat_lead_id._get_html_link())
            )
            return {'success': False, 'message': 'Lead already exists'}

        try:
            # Create the lead
            lead = self._create_lead_from_livechat(partner)
            
            # Link the lead to this channel
            self.livechat_lead_id = lead.id
            
            # Send success message
            msg = _('Lead created successfully: %s', lead._get_html_link())
            self._send_transient_message(partner, msg)
            
            # Post chat history in lead's internal notes  
            chat_history = self._get_channel_history()
            lead.message_post(
                body=_('Lead created from LiveChat conversation: %s<br/><br/><strong>Chat History:</strong><br/>%s', 
                       self.name, chat_history),
                message_type='notification',
                subtype_xmlid='mail.mt_note'  # Internal note instead of comment
            )
            
            return {'success': True, 'message': 'Lead created successfully'}
            
        except Exception as e:
            self._send_transient_message(partner, _('Error creating lead: %s', str(e)))
            return {'success': False, 'message': str(e)}

    def execute_command_update_lead_enhanced(self):
        """
        Update existing lead with new conversation messages
        """
        self.ensure_one()
        partner = self.env.user.partner_id
        
        # Check if user has CRM access
        has_crm_access = (
            self.env.user.has_group('crm.group_use_lead') or
            self.env.user.has_group('sales_team.group_sale_salesman') or
            self.env.user.has_group('sales_team.group_sale_salesman_all_leads') or
            self.env.user.has_group('base.group_user')
        )
        
        if not has_crm_access:
            self._send_transient_message(partner, _('You do not have permission to update leads.'))
            return {'success': False, 'message': 'No permission'}

        # Check if lead exists
        if not self.livechat_lead_id:
            self._send_transient_message(partner, _('No lead associated with this chat. Create a lead first.'))
            return {'success': False, 'message': 'No lead exists'}

        try:
            # Get new messages since last update
            new_history = self._get_new_channel_history()
            
            if new_history:
                # Update lead description with new messages
                current_description = self.livechat_lead_id.description or ""
                updated_description = current_description + "\n\n--- New Messages ---\n" + new_history
                
                self.livechat_lead_id.write({
                    'description': updated_description
                })
                
                # Post new messages in lead's internal notes
                self.livechat_lead_id.message_post(
                    body=_('LiveChat conversation updated:<br/><br/><strong>New Messages:</strong><br/>%s', new_history),
                    message_type='notification',
                    subtype_xmlid='mail.mt_note'  # Internal note
                )
                
                msg = _('Lead updated with new conversation: %s', self.livechat_lead_id._get_html_link())
            else:
                msg = _('No new messages to update in lead: %s', self.livechat_lead_id._get_html_link())
                
            self._send_transient_message(partner, msg)
            return {'success': True, 'message': 'Lead updated successfully'}
            
        except Exception as e:
            self._send_transient_message(partner, _('Error updating lead: %s', str(e)))
            return {'success': False, 'message': str(e)}

    def _create_lead_from_livechat(self, partner):
        """
        Create a lead from livechat conversation
        Enhanced version of the base CRM livechat functionality
        """
        # Get customer partners (exclude the operator)
        customers = self.env['res.partner']
        for customer in self.with_context(active_test=False).channel_partner_ids.filtered(
            lambda p: p != partner and p.partner_share
        ):
            if customer.is_public:
                customers = self.env['res.partner']
                break
            else:
                customers |= customer

        # Get UTM source
        utm_source = self.env.ref('livechat_crm_enhanced.utm_source_livechat_enhanced', raise_if_not_found=False)
        if not utm_source:
            utm_source = self.env.ref('crm_livechat.utm_source_livechat', raise_if_not_found=False)

        # Prepare lead values
        lead_name = self.name or _('LiveChat Conversation')
        if len(lead_name) > 50:
            lead_name = lead_name[:50] + '...'

        lead_vals = {
            'name': lead_name,
            'partner_id': customers[0].id if customers else False,
            'user_id': partner.user_ids[0].id if partner.user_ids else False,
            'team_id': False,
            'description': _('Lead created from LiveChat conversation: %s', self.name),  # Brief description only
            'referred': partner.name,
            'source_id': utm_source.id if utm_source else False,
            'tag_ids': [(6, 0, [self.env.ref('livechat_crm_enhanced.crm_tag_livechat').id])] if self.env.ref('livechat_crm_enhanced.crm_tag_livechat', raise_if_not_found=False) else False,
        }

        # Create and return the lead
        return self.env['crm.lead'].create(lead_vals)

    def _get_new_channel_history(self):
        """
        Get channel history from messages that haven't been included in the lead yet
        This is a simplified version - in production, you might want to track timestamps
        """
        if not self.livechat_lead_id:
            return ""
            
        # For now, return all messages (could be enhanced to track last sync timestamp)
        return self._get_channel_history()

    def get_livechat_lead_status(self):
        """
        Return status information about lead creation for this channel
        Used by JavaScript to determine button state
        """
        self.ensure_one()
        
        if self.channel_type != 'livechat':
            return {'status': 'not_livechat'}
            
        # Check for CRM access - try multiple groups
        has_crm_access = (
            self.env.user.has_group('crm.group_use_lead') or
            self.env.user.has_group('sales_team.group_sale_salesman') or
            self.env.user.has_group('sales_team.group_sale_salesman_all_leads') or
            self.env.user.has_group('base.group_user')  # Any internal user can create leads
        )
        
        if not has_crm_access:
            return {'status': 'no_permission'}
            
        if self.livechat_lead_id:
            return {
                'status': 'lead_exists',
                'lead_id': self.livechat_lead_id.id,
                'lead_name': self.livechat_lead_id.name,
                'lead_url': '/web#id=%d&model=crm.lead&view_type=form' % self.livechat_lead_id.id
            }
        else:
            return {'status': 'can_create_lead'}