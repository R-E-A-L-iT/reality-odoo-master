# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PickingSignWizard(models.TransientModel):
    _name = 'proquotes.picking.sign.wizard'
    _description = 'Rental Transfer Sign Wizard'

    picking_id = fields.Many2one('stock.picking', required=True)
    signed_by = fields.Char(string='Signed By')
    signature = fields.Binary(string='Signature', required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        picking_id = self.env.context.get('default_picking_id')
        if picking_id:
            picking = self.env['stock.picking'].browse(picking_id)
            res['picking_id'] = picking_id
            res['signed_by'] = picking.partner_id.name or ''
        return res

    def action_confirm(self):
        self.ensure_one()
        picking = self.picking_id
        picking.write({
            'signature': self.signature,
            'signed_by': self.signed_by,
            'signed_on': fields.Datetime.now(),
        })
        report = self.env['ir.actions.report']._render_qweb_pdf(
            'stock.action_report_delivery', picking.id
        )
        filename = '%s_signed_delivery_slip' % picking.name
        message = _('Transfer signed by %s', self.signed_by) if self.signed_by else _('Transfer signed')
        picking.message_post(
            body=message,
            attachments=[('%s.pdf' % filename, report[0])],
        )
        return {'type': 'ir.actions.act_window_close'}
