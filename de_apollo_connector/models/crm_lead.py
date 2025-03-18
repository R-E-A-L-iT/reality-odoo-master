# -*- coding: utf-8 -*-

import requests
import json

from odoo import api, exceptions, fields, models, _
from odoo.exceptions import UserError, ValidationError
import pprint

from urllib.parse import urlparse

class CRMTag(models.Model):
    _inherit = 'crm.tag'

    apl_id = fields.Char(
        string='Apollo ID',
        help="The Apollo ID is used for tracking purposes."
    )
    apl_date_update = fields.Date('Last Update Date', help="he date of the most recent update of tags with Apollo.")


class CRMStage(models.Model):
    _inherit = 'crm.stage'

    apl_id = fields.Char(
        string='Apollo ID',
        help="The Apollo ID is used for tracking purposes."
    )
    apl_date_update = fields.Date('Last Update Date', help="he date of the most recent update of stages with Apollo.")

    
class CRMLead(models.Model):
    _inherit = 'crm.lead'

    apl_id = fields.Char(
        string='Apollo ID',
        help="The Apollo ID is used for tracking purposes."
    )
    apl_date_sync = fields.Datetime('Synronization Date', help="he date of the most recent synchronization of contacts with Apollo.")

    update_required_for_apollo = fields.Boolean(
        string='Update Required for Apollo',
        store=True,
        default=True,
        help="Set to 'True' when this record requires an update in Apollo."
    )

    def action_send_to_apollo_data(self):
        ''' Open the account.payment.register wizard to pay the selected journal entries.
        :return: An action opening the account.payment.register wizard.
        '''
        return {
            'name': _('Apollo'),
            'res_model': 'apl.send.data.wizard',
            'view_mode': 'form',
            'context': {
                'active_model': 'crm.lead',
                'active_ids': self.ids,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def _cron_send_to_apollo(self):
        assign_cron = self.env["ir.config_parameter"].sudo().get_param("apl.contacts.auto")
        record_ids = self.env['crm.lead'].search([('update_required_for_apollo','=',True)])
        #apl_instance = self.env['apl.instance'].search([
        #    ('company_id', '=', self.env.company.id),
        #], limit=1)  # Limit to one record (if available)
        if assign_cron:
            for record in record_ids:
                record._send_to_apollo(record.company_id.apl_instance_id)
            
    def _send_to_apollo(self, apl_instance_id):
        self.ensure_one()
        
        lead_data = {}
        apl_id = ''
        lead_json = []
        
        for lead in self:
            lead_data = {
                "name": lead.name,
                "amount": lead.expected_revenue,
                #"opportunity_stage_id":"5c14XXXXXXXXXXXXXXXXXXXX",
                #"closed_date":"2020-12-18",
                "account_id": lead.partner_id.apl_id if lead.partner_id.apl_id else '',
                "description":lead.description,
                "source": lead.source_id.name,
                "stage_name": lead.stage_id.name,
                "is_won": True if lead.won_status == 'won' else False,
                "is_closed": True if lead.won_status == 'won' else False,
                "closed_lost_reason": lead.lost_reason_id.name,
            }
            if not lead.apl_id:
                lead_json = apl_instance_id._post_apollo_data('opportunities', lead_data)
                apl_id = lead_json["opportunity"]["id"]        
                lead_id = lead.write({
                    'apl_id': apl_id,
                })
            else:
                if lead.update_required_for_apollo == True:
                    api_str = 'opportunities' + '/' + lead.apl_id
                    lead_json = apl_instance_id._put_apollo_data(api_str, lead_data)
            lead.write({
                'apl_date_sync': self.env.cr.now(),
                'update_required_for_apollo': False,
            })

    @api.onchange('name', 'expected_revenue', 'partner_id', 'description','stage_id','won_status',
                  'function','phone','mobile'
                 )
    def _onchange_lead_for_apollo(self):
        for lead in self:
            # Check if any field in the lead record has changed
            any_field_changed = any(getattr(lead, field) != lead._origin[field] for field in lead._fields.keys())
            lead.update_required_for_apollo = any_field_changed


    

