# -*- coding: utf-8 -*-

from odoo import models, fields, api

class quote_generator(models.Model):

    _inherit = "sale.order"
    _name = 'sale.order'
    _description = 'quote_generator.quote_generator'
    


    name = fields.Char()
    description = fields.Text()


    @api.depends('value')
    def _value_pc(self):
        for record in self:
            record.value2 = float(record.value) / 100
    #_inherit = "sale.order"
    #def action_quotation_sent(self):
     #   if self.filtered(lambda so: so.state != 'draft'):
      #      raise UserError(_('Custom Error Message to Prove Sucsess'))
       # for order in self:
        #    order.message_subscribe(partner_ids=order.partner_id.ids)
        #self.write({'state': 'sent'})
            
            