# -*- coding: utf-8 -*-


from odoo import fields, models
import pprint

from urllib.parse import urlparse

class APLSendDataWizard(models.TransientModel):
    _name = "apl.send.data.wizard"
    _description = 'Search People Wizard'

    apl_instance_id = fields.Many2one(
        'apl.instance',
        string='APL Instance',
        default=lambda self: self._compute_default_apl_instance(),
        domain = "[('state','=','active')]"
    )

    def _compute_default_apl_instance(self):
        # Find an APL instance record in the current company and return its ID
        apl_instance = self.env['apl.instance'].search([
            ('company_id', '=', self.env.company.id),('state', '=', 'active')
        ], limit=1)  # Limit to one record (if available)

        return apl_instance.id if apl_instance else False

    def action_process(self):
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids', [])

        record_ids = self.env[active_model].search([('id','in',active_ids)])
        for record in record_ids:
            record._send_to_apollo(self.apl_instance_id)
            

    def _send_res_partner_to_apollo(self, record_ids):
        self.ensure_one()
        partner_ids = self.env['res.partner'].search([('id','in',record_ids)])
        
        person_data = {}
        account_data = {}

        data_acc = data_per = []

        person_apl_id = account_apl_id = ''
        
        for partner in partner_ids:

            # check is this contact or company
            if partner.company_type == 'company':
                company_partner = partner
            elif partner.parent_id.company_type == 'company':
                company_partner = partner.parent_id
            else:
                company_partner = partner.parent_id

            if company_partner:
                # parse website domain of parent 
                parsed_url = urlparse(partner.parent_id.website)
                domain = parsed_url.hostname

                # Account Date
                account_data = {
                    "name": company_partner.name,
                    "website_url": company_partner.website,
                    "blog_url": company_partner.blog_url,
                    "angellist_url": company_partner.blog_url,
                    "linkedin_url": company_partner.blog_url,
                    "twitter_url": company_partner.blog_url,
                    "facebook_url": company_partner.blog_url,
                    "phone": "+918602017706",
                    "founded_year": 2007,
                    "primary_domain": domain,
                    "sanitized_phone": "+918602017706",
                    "domain": domain,
                    "source": "deployment",
                    "original_source": "deployment",
                }

                if not company_partner.apl_id:
                    data_acc = self.apl_instance_id._post_apollo_data('accounts', account_data)
                    account_apl_id = data_acc["account"]["id"]        
                    company_partner.write({
                        'apl_id': account_apl_id,
                    })
                else:
                    api_str = 'accounts' + '/' + company_partner.apl_id
                    data_acc = self.apl_instance_id._put_apollo_data(api_str, account_data)

            # Create Contact in Apollo
            if partner.company_type == 'person':
                # Fist name and Second name
                split_names = partner.name.split(" ", 1)  # Split at the first space
                if len(split_names) == 2:
                    first_name, last_name = split_names

                
                label_names = [str(label_id.name) for label_id in partner.category_id]
                
                person_data = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "name": partner.name,
                    "title": partner.function if partner.function else '',
                    "headline": partner.function,
                    "email": partner.email if partner.email else '',
                    "website_url": partner.website if partner.website else '',
                    "city": partner.city if partner.city else '',
                    "state": partner.state_id.name if partner.state_id else '',
                    "country": partner.country_id.name if partner.country_id else '',
                    "present_raw_address": partner.city if partner.city else '' + ", " + partner.state_id.name if partner.state_id else '' + ", " + partner.country_id.name if partner.country_id else '',
                    "label_names": label_names,
                    "phone_numbers": [
                        {
                          "raw_number": "+923001616395",
                          "sanitized_number": "+923001616395",
                          "type": "work_hq",
                          "position": 0,
                          "status": "no_status",
                          "dnc_status": '',
                          "dnc_other_info": ''
                        },
                        {
                          "raw_number": "+923001616396",
                          "sanitized_number": "+923001616396",
                          "type": "mobile",
                          "position": 1,
                          "status": "valid_number",
                          "dnc_status": '',
                          "dnc_other_info": ''
                        }
                      ],
                }
                if company_partner:
                    person_data['account'] = account_data



                if not partner.apl_id:
                    data_per = self.apl_instance_id._post_apollo_data('contacts', person_data)
                    if 'contact' in data_per:
                        person_apl_id = data_per['contact']['id']
                    partner.write({
                        'apl_id': person_apl_id,
                    })
                    api_str = 'contacts' + '/' + partner.apl_id
                    person_data = {
                        "account_id": company_partner.apl_id,
                    }
                    data_per = self.apl_instance_id._put_apollo_data(api_str, person_data)
                else:
                    api_str = 'contacts' + '/' + partner.apl_id
                    data_per = self.apl_instance_id._put_apollo_data(api_str, person_data)
                    

    def _send_lead_to_apollo(self, record_ids):
        self.ensure_one()
        lead_ids = self.env['crm.lead'].search([('id','in',record_ids)])
        
        lead_data = {}
        apl_id = ''
        lead_json = []
        
        for lead in lead_ids:
            lead_data = {
                "name": lead.name,
                "amount": lead.expected_revenue,
                "account_id": lead.partner_id.apl_id if lead.partner_id.apl_id else '',
                "description":lead.description,
                "source": lead.source_id.name,
                "stage_name": lead.stage_id.name,
                "is_won": True if lead.won_status == 'won' else False,
                "is_closed": True if lead.won_status == 'won' else False,
                "closed_lost_reason": lead.lost_reason_id.name,
            }
            if not lead.apl_id:
                lead_json = self.apl_instance_id._post_apollo_data('opportunities', lead_data)
                apl_id = lead_json["opportunity"]["id"]        
                lead.write({
                    'apl_id': apl_id,
                })
            else:
                api_str = 'opportunities' + '/' + lead.apl_id
                lead_json = self.apl_instance_id._put_apollo_data(api_str, lead_data)