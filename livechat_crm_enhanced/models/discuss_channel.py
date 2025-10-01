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
        Enhanced lead creation method with smart duplicate prevention
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

        # SMART DUPLICATE PREVENTION: Check for existing leads before creating
        existing_lead = self._find_existing_customer_lead()
        if existing_lead:
            # Link this chat to the existing lead instead of creating new one
            self.livechat_lead_id = existing_lead.id
            
            # Update the existing lead with current chat messages
            chat_history = self._get_channel_history()
            existing_lead.message_post(
                body=_('New LiveChat conversation linked: %s<br/><br/><strong>Chat History:</strong><br/>%s', 
                       self.name, chat_history),
                message_type='notification',
                subtype_xmlid='mail.mt_note'
            )
            
            # Send message to operator
            msg = _('Linked to existing lead: %s (Customer: %s)', 
                   existing_lead._get_html_link(), 
                   self._get_visitor_name())
            self._send_transient_message(partner, msg)
            
            return {
                'success': True, 
                'message': 'Linked to existing lead',
                'action': 'linked_existing',
                'lead_id': existing_lead.id
            }

        # Check if THIS channel already has a linked lead (safety check)
        if self.livechat_lead_id:
            self._send_transient_message(
                partner, 
                _('Lead already exists: %s', self.livechat_lead_id._get_html_link())
            )
            return {'success': False, 'message': 'Lead already exists'}

        try:
            # Create NEW lead only if no existing lead found
            lead = self._create_lead_from_livechat(partner)
            
            # Link the lead to this channel
            self.livechat_lead_id = lead.id
            
            # Send success message
            msg = _('New lead created successfully: %s (Customer: %s)', 
                   lead._get_html_link(), 
                   self._get_visitor_name())
            self._send_transient_message(partner, msg)
            
            # Post chat history in lead's internal notes  
            chat_history = self._get_channel_history()
            lead.message_post(
                body=_('Lead created from LiveChat conversation: %s<br/><br/><strong>Chat History:</strong><br/>%s', 
                       self.name, chat_history),
                message_type='notification',
                subtype_xmlid='mail.mt_note'  # Internal note instead of comment
            )
            
            return {
                'success': True, 
                'message': 'New lead created successfully',
                'action': 'created_new',
                'lead_id': lead.id
            }
            
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
        Uses smart detection to find existing customer leads
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
        
        # Step 1: Check if THIS channel already has a linked lead
        if self.livechat_lead_id:
            return {
                'status': 'lead_exists',
                'lead_id': self.livechat_lead_id.id,
                'lead_name': self.livechat_lead_id.name,
                'lead_url': '/web#id=%d&model=crm.lead&view_type=form' % self.livechat_lead_id.id,
                'source': 'channel_linked'
            }
        
        # Step 2: Check if visitor/customer already has ANY lead in system
        existing_lead = self._find_existing_customer_lead()
        if existing_lead:
            # Automatically link this chat to the existing lead
            self.livechat_lead_id = existing_lead.id
            return {
                'status': 'lead_exists',
                'lead_id': existing_lead.id,
                'lead_name': existing_lead.name,
                'lead_url': '/web#id=%d&model=crm.lead&view_type=form' % existing_lead.id,
                'source': 'auto_detected',
                'visitor_info': {
                    'name': self._get_visitor_name(),
                    'email': self._get_visitor_email(),
                    'phone': self._get_visitor_phone()
                }
            }
        
        # Step 3: No existing lead found - can create new one
        return {
            'status': 'can_create_lead',
            'visitor_info': {
                'name': self._get_visitor_name(),
                'email': self._get_visitor_email(),
                'phone': self._get_visitor_phone()
            }
        }

    def _get_visitor_partner(self):
        """
        Get partner if visitor is logged in or identified
        Returns the visitor partner (not the operator)
        """
        self.ensure_one()
        operator_partner = self.env.user.partner_id
        
        # Find non-operator partners in the channel
        for partner in self.channel_partner_ids:
            if partner != operator_partner and partner.partner_share:
                return partner
        return False

    def _get_visitor_email(self):
        """
        Extract visitor email from channel/visitor information
        """
        self.ensure_one()
        
        # Method 1: Check if visitor partner has email
        visitor_partner = self._get_visitor_partner()
        if visitor_partner and visitor_partner.email:
            return visitor_partner.email
        
        # Method 2: Check channel members for email
        for member in self.channel_member_ids:
            if member.partner_id.email and member.partner_id != self.env.user.partner_id:
                return member.partner_id.email
        
        # Method 3: Extract from livechat visitor info if available
        if hasattr(self, 'livechat_visitor_id') and self.livechat_visitor_id:
            return getattr(self.livechat_visitor_id, 'email', False)
        
        return False

    def _get_visitor_phone(self):
        """
        Extract visitor phone from channel/visitor information
        """
        self.ensure_one()
        
        # Method 1: Check if visitor partner has phone
        visitor_partner = self._get_visitor_partner()
        if visitor_partner and visitor_partner.phone:
            return visitor_partner.phone
        
        # Method 2: Check channel members for phone
        for member in self.channel_member_ids:
            if member.partner_id.phone and member.partner_id != self.env.user.partner_id:
                return member.partner_id.phone
        
        # Method 3: Extract from livechat visitor info if available
        if hasattr(self, 'livechat_visitor_id') and self.livechat_visitor_id:
            return getattr(self.livechat_visitor_id, 'phone', False)
        
        return False

    def _get_visitor_name(self):
        """
        Extract visitor name from channel/visitor information
        """
        self.ensure_one()
        
        # Method 1: Check if visitor partner has name
        visitor_partner = self._get_visitor_partner()
        if visitor_partner and visitor_partner.name:
            return visitor_partner.name
        
        # Method 2: Check channel members for name
        for member in self.channel_member_ids:
            if member.partner_id.name and member.partner_id != self.env.user.partner_id:
                return member.partner_id.name
        
        # Method 3: Use anonymous name from channel
        if hasattr(self, 'anonymous_name') and self.anonymous_name:
            return self.anonymous_name
        
        # Method 4: Extract from livechat visitor info if available
        if hasattr(self, 'livechat_visitor_id') and self.livechat_visitor_id:
            return getattr(self.livechat_visitor_id, 'name', False)
        
        return 'Anonymous Visitor'

    def _find_existing_customer_lead(self):
        """
        Find existing lead for the current livechat visitor
        Returns the most recent active lead for the customer, or False if none found
        """
        self.ensure_one()
        Lead = self.env['crm.lead']
        
        # Get visitor information
        visitor_partner = self._get_visitor_partner()
        visitor_email = self._get_visitor_email()
        visitor_phone = self._get_visitor_phone()
        visitor_name = self._get_visitor_name()
        
        # Priority 1: Direct partner match (if visitor is logged in)
        if visitor_partner:
            lead = Lead.search([
                ('partner_id', '=', visitor_partner.id),
                ('active', '=', True)
            ], limit=1, order='create_date desc')
            if lead:
                return lead
        
        # Priority 2: Email match (most reliable for anonymous visitors)
        if visitor_email:
            lead = Lead.search([
                ('email_from', 'ilike', visitor_email),
                ('active', '=', True)
            ], limit=1, order='create_date desc')
            if lead:
                return lead
            
            # Also check partner email in leads
            lead = Lead.search([
                ('partner_id.email', 'ilike', visitor_email),
                ('active', '=', True)
            ], limit=1, order='create_date desc')
            if lead:
                return lead
        
        # Priority 3: Phone match
        if visitor_phone:
            # Clean phone number for comparison
            clean_phone = visitor_phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            if len(clean_phone) > 5:  # Only search if phone has meaningful length
                lead = Lead.search([
                    ('phone', 'ilike', clean_phone[-7:]),  # Match last 7 digits
                    ('active', '=', True)
                ], limit=1, order='create_date desc')
                if lead:
                    return lead
                
                # Also check mobile field
                lead = Lead.search([
                    ('mobile', 'ilike', clean_phone[-7:]),
                    ('active', '=', True)
                ], limit=1, order='create_date desc')
                if lead:
                    return lead
        
        # Priority 4: Name match (as fallback, only for non-anonymous visitors)
        if visitor_name and visitor_name != 'Anonymous Visitor' and len(visitor_name) > 3:
            # Split name and try to match
            name_parts = visitor_name.split()
            if len(name_parts) >= 2:  # First and last name
                lead = Lead.search([
                    ('name', 'ilike', visitor_name),
                    ('active', '=', True)
                ], limit=1, order='create_date desc')
                if lead:
                    return lead
                
                # Try matching with partner name
                lead = Lead.search([
                    ('partner_id.name', 'ilike', visitor_name),
                    ('active', '=', True)
                ], limit=1, order='create_date desc')
                if lead:
                    return lead
        
        # No existing lead found
        return False