# -*- coding: utf-8 -*-

from odoo import models, fields, api

class quote_generator(models.Model):
    _name = 'quote_generator.quote_generator'
    _inherit = "sale.order"
    _description = 'quote_generator.quote_generator'
    
    transaction_ids = fields.Many2many('payment.transactionQ', 'sale_order_transaction_rel', 'sale_order_id', 'transaction_id', string='Transactions', copy=False, readonly=True)
    tag_ids = fields.Many2many('crm.tagQ', 'sale_order_tag_rel', 'order_id', 'tag_id', string='Tags')

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
            