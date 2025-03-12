# -*- coding: utf-8 -*-

from odoo import api, fields, Command, models, _
from odoo.exceptions import UserError, AccessError

class AplOpsWizard(models.TransientModel):
    _name = 'apl.ops.wizard'
    _description = 'APL Ops Wizard'

    page_start = fields.Integer('From Page', default=1, required=True)
    page_last = fields.Integer('Last Page', default=1, required=True)
    
    duplicate_records = fields.Boolean('Ignore Duplicate Records')
    op_name = fields.Char(string='Operation')
    
    type = fields.Selection([
        ('lead', 'Lead'), ('opportunity', 'Opportunity')], required=True, tracking=15, index=True,
        default=lambda self: 'lead' if self.env['res.users'].has_group('crm.group_use_lead') else 'opportunity')

    @api.constrains('page_start', 'page_last')
    def _check_page_constraints(self):
        for record in self:
            if record.page_start < 0:
                raise ValidationError("From Page cannot be less than 0.")
            if record.page_last < 0:
                raise ValidationError("Last Page cannot be less than 0.")
            if record.page_start > record.page_last:
                raise ValidationError("From Page cannot be greater than Last Page.")
                
    @api.model
    def default_get(self, fields):
        res = super(AplOpsWizard, self).default_get(fields)
        if 'op_name' in self._context:
            res['op_name'] = self._context.get('op_name')
        return res

        
    def run_process(self):
        # You can access the 'op_name' context variable here
        # It will contain the value passed from the button's context
        op_name = self._context.get('op_name')
        #raise UserError(op_name)

        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id', [])

        apl_instance_id = self.env['apl.instance'].browse(active_id)

        start_page = self.page_start
        last_page = self.page_last
        for i in range(start_page, last_page + 1):
            data = {
                "page" : i,
            }
            if op_name == 'contacts':
                json_data = apl_instance_id._post_apollo_data('contacts/search', data)
                if isinstance(json_data, list):
                    json_data_list = json_data
                elif isinstance(json_data, dict):
                    json_data_list = json_data.get('contacts', [])
    
                for obj in json_data_list:
                    partner_id = self.env['res.partner'].search([('apl_id','=',obj.get('id'))],limit=1)
                    state_id = self.env['res.country.state'].search([('name','=',obj.get('state'))],limit=1)
                    country_id = self.env['res.country'].search([('name','=',obj.get('country'))],limit=1)
                    
                    vals = {
                        'company_type': 'person',
                        'apl_id': obj.get('id'),
                        'apl_account_id': obj.get('account_id'),
                        'name': obj.get('name'),
                        'linkedin_url': obj.get('linkedin_url'),
                        'function': obj.get('title'),
                        'photo_url': obj.get('photo_url'),
                        'email': obj.get('email'),
                        'city': obj.get('state'),
                        'state_id': state_id.id,
                        'country_id': country_id.id,
                        'phone': obj.get('sanitized_phone'),
                    }
                    if partner_id: #Update Records
                        if self.duplicate_records:
                            partner_id = self.env['res.partner'].create(vals)
                        else:
                            partner_id.write(vals)
                    else:
                        partner_id = self.env['res.partner'].create(vals)
                    
                    partner_id._compute_image()
                    partner_id.write({
                        'update_required_for_apollo': False,
                    })
                apl_instance_id.write({
                    'apl_date_import_contacts': self.env.cr.now(),
                })
            # -------------------------------------------------
            # apollo accounts are the companies contact in odoo
            # -------------------------------------------------
            elif op_name == 'accounts':
                json_data = apl_instance_id._post_apollo_data('accounts/search', data)
                if isinstance(json_data, list):
                    json_data_list = json_data
                elif isinstance(json_data, dict):
                    json_data_list = json_data.get('accounts', [])

                #raise UserError(len(json_data_list))
                for obj in json_data_list:
                    account_id = self.env['res.partner'].search([('apl_id','=',obj.get('id'))],limit=1)
                    contact_ids = self.env['res.partner'].search([('apl_account_id','=',obj.get('id'))])
                    vals = {
                        'company_type': 'company',
                        'apl_id': obj.get('id'),
                        'name': obj.get('name'),
                        'website': obj.get('website_url'),
                        'blog_url': obj.get('blog_url'),
                        'angellist_url': obj.get('angellist_url'),
                        'linkedin_url': obj.get('linkedin_url'),
                        'twitter_url': obj.get('twitter_url'),
                        'facebook_url': obj.get('facebook_url'),
                        'phone': (obj.get('phone') or '') + (', ' + obj.get('sanitized_phone') if obj.get('sanitized_phone') else ''),
                        'photo_url': obj.get('logo_url'),
                        'founded_year': obj.get('founded_year'),                        
                    }
                    if account_id: #Update Records
                        if self.duplicate_records:
                            account_id = self.env['res.partner'].create(vals)
                        else:
                            account_id.write(vals)
                    else:
                        account_id = self.env['res.partner'].create(vals)
                    
                    if len(contact_ids):
                        contact_ids.write({
                            'parent_id': account_id.id,
                        })
                    account_id._compute_image()
                    account_id.write({
                        'update_required_for_apollo': False,
                    })
                    
                apl_instance_id.write({
                    'apl_date_import_accounts': self.env.cr.now(),
                })
            # -------------------------------------------------
            # apollo opportunities are the companies contact in odoo
            # -------------------------------------------------
            elif op_name == 'leads':
                json_data = apl_instance_id._post_apollo_data('opportunities/search', data)
                
                if isinstance(json_data, list):
                    json_data_list = json_data
                elif isinstance(json_data, dict):
                    json_data_list = json_data.get('opportunities', [])
                    json_account_list = json_data.get('account', [])

                for obj in json_data_list:
                    lead_id = self.env['crm.lead'].search([('apl_id','=',obj.get('id'))],limit=1)
                    partner_id = self.env['res.partner'].search([('apl_id','=',obj.get('account_id'))],limit=1)
                    stage_id = self.env['res.partner'].search([('apl_id','=',obj.get('opportunity_stage_id'))],limit=1)

                    #create account data
                    if not partner_id:
                        for obj1 in json_account_list:
                            vals = {
                                'company_type': 'company',
                                'apl_id': obj1.get('id'),
                                'name': obj1.get('name'),
                                'website_url': obj1.get('website_url'),
                                'blog_url': obj1.get('blog_url'),
                                'angellist_url': obj1.get('angellist_url'),
                                'linkedin_url': obj1.get('linkedin_url'),
                                'twitter_url': obj1.get('twitter_url'),
                                'facebook_url': obj1.get('facebook_url'),
                                'phone': (obj1.get('phone') or '') + (', ' + obj1.get('sanitized_phone') if obj.get('sanitized_phone') else ''),
                                'photo_url': obj1.get('logo_url'),
                                'founded_year': obj1.get('founded_year'),                        
                            }
                            partner_id = self.env['res.partner'].create(vals)
                            partner_id._compute_image()
                            partner_id.write({
                                'update_required_for_apollo': False,
                            })
                        
                    vals = {
                        'apl_id': obj.get('id'),
                        'name': obj.get('name'),
                        'description': obj.get('description'),
                        'expected_revenue': obj.get('amount'),
                        'partner_id': partner_id.id,
                        #'stage_id': stage_id.id,
                        'date_closed': obj.get('closed_date'),
                        'type': self.type,
                    }
                    if lead_id: #Update Records
                        if self.duplicate_records:
                            lead_id = self.env['crm.lead'].create(vals)
                        else:
                            lead_id.write(vals)
                    else:
                        lead_id = self.env['crm.lead'].create(vals)

                    lead_id.write({
                        'update_required_for_apollo': False,
                    })
                    
                apl_instance_id.write({
                    'apl_date_import_leads': self.env.cr.now(),
                })

        #raise UserError(active_id)
        # You can now use the 'op_name' variable as needed
        # For example, print it or save it in the database.
        #self.env['your.model'].create({'name': op_name})

        return {'type': 'ir.actions.act_window_close'}
        
