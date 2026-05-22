# -*- coding: utf-8 -*-

from odoo import models, fields, _


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

        # Check for existing lead (smart detection)
        existing_lead = self._find_existing_customer_lead()
        if existing_lead:
            # Link this chat to the existing lead
            self.livechat_lead_id = existing_lead.id
            
            # Post chat history to existing lead
            chat_history = self._get_channel_history()
            existing_lead.message_post(
                body=_('New LiveChat conversation linked: %s<br/><br/><strong>Chat History:</strong><br/>%s', 
                       self.name, chat_history),
                message_type='notification',
                subtype_xmlid='mail.mt_note'
            )
            
            return {
                'success': True, 
                'message': 'Linked to existing lead',
                'lead_id': existing_lead.id,
                'lead_url': f'/web#id={existing_lead.id}&model=crm.lead&view_type=form'
            }

        # Check if lead already exists for this specific channel
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
                'message': 'Lead created successfully',
                'lead_id': lead.id,
                'lead_url': f'/web#id={lead.id}&model=crm.lead&view_type=form'
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
                    author_id=self.env['res.partner'].sudo().browse(2).id,
                    subtype_xmlid='mail.mt_note'  # Internal note
                )
                
            return {
                'success': True, 
                'message': 'Lead updated successfully',
                'lead_id': self.livechat_lead_id.id,
                'lead_url': f'/web#id={self.livechat_lead_id.id}&model=crm.lead&view_type=form'
            }
            
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

    def _find_existing_customer_lead(self):
        """
        Smart detection of existing leads for the customer in this chat
        Priority: Partner ID > Email > Phone > Name matching
        """
        self.ensure_one()
        
        # Get customer information from channel
        visitor = None
        partner = None
        
        # Try to get customer partner (exclude operators)
        for channel_partner in self.channel_partner_ids.filtered(lambda p: p.partner_share):
            if not channel_partner.is_public:
                partner = channel_partner
                break
        
        # Get visitor info if available
        if hasattr(self, 'livechat_visitor_id') and self.livechat_visitor_id:
            visitor = self.livechat_visitor_id
        
        # Search criteria for existing leads
        Lead = self.env['crm.lead']
        domain_options = []
        
        # 1. Search by partner (highest priority)
        if partner:
            domain_options.append([('partner_id', '=', partner.id)])
        
        # 2. Search by email
        email_addresses = []
        if partner and partner.email:
            email_addresses.append(partner.email)
        if visitor and visitor.email:
            email_addresses.append(visitor.email)
        
        for email in email_addresses:
            if email:
                domain_options.extend([
                    [('email_from', 'ilike', email)],
                    [('partner_id.email', 'ilike', email)]
                ])
        
        # 3. Search by phone
        phone_numbers = []
        if partner and partner.phone:
            phone_numbers.append(partner.phone)
        if partner and partner.mobile:
            phone_numbers.append(partner.mobile)
        if visitor and visitor.mobile:
            phone_numbers.append(visitor.mobile)
            
        for phone in phone_numbers:
            if phone:
                # Clean phone number for better matching
                clean_phone = ''.join(filter(str.isdigit, phone))[-10:]  # Last 10 digits
                if len(clean_phone) >= 7:  # Minimum meaningful phone length
                    domain_options.extend([
                        [('phone', 'ilike', f'%{clean_phone}%')],
                        [('mobile', 'ilike', f'%{clean_phone}%')],
                        [('partner_id.phone', 'ilike', f'%{clean_phone}%')],
                        [('partner_id.mobile', 'ilike', f'%{clean_phone}%')]
                    ])
        
        # 4. Search by name (lowest priority)
        names = []
        if partner and partner.name:
            names.append(partner.name)
        if visitor and visitor.display_name:
            names.append(visitor.display_name)
            
        for name in names:
            if name and len(name.strip()) > 2:  # Avoid very short names
                domain_options.extend([
                    [('contact_name', 'ilike', name)],
                    [('partner_id.name', 'ilike', name)]
                ])
        
        # Try each search criteria in priority order
        for domain in domain_options:
            # Only search active leads
            full_domain = domain + [
                ('active', '=', True),
                ('probability', '<', 100)  # Not won leads
            ]
            
            existing_leads = Lead.search(full_domain, limit=1, order='create_date desc')
            if existing_leads:
                return existing_leads[0]
        
        return Lead  # Empty recordset

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
            
        # Check for existing lead linked to this channel
        if self.livechat_lead_id:
            return {
                'status': 'lead_exists',
                'lead_id': self.livechat_lead_id.id,
                'lead_name': self.livechat_lead_id.name,
                'lead_url': '/web#id=%d&model=crm.lead&view_type=form' % self.livechat_lead_id.id
            }
        
        # Smart detection: check for existing lead for this customer
        existing_lead = self._find_existing_customer_lead()
        if existing_lead:
            # Auto-link the existing lead to this channel
            self.livechat_lead_id = existing_lead.id
            return {
                'status': 'lead_exists',
                'lead_id': existing_lead.id,
                'lead_name': existing_lead.name,
                'lead_url': '/web#id=%d&model=crm.lead&view_type=form' % existing_lead.id,
                'auto_linked': True
            }
        else:
            return {'status': 'can_create_lead'}