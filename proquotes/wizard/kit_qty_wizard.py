# -*- coding: utf-8 -*-

import re
from odoo import api, fields, models


class KitQtyWizardLine(models.TransientModel):
    _name = 'proquotes.kit.qty.wizard.line'
    _description = 'Kit Quantity Wizard Line'
    _order = 'id asc'

    wizard_id    = fields.Many2one('proquotes.kit.qty.wizard', ondelete='cascade')
    bom_line_id  = fields.Many2one('mrp.bom.line')
    product_id   = fields.Many2one('product.product', string='Component')
    sku          = fields.Char(string='SKU')
    product_name = fields.Char(string='Component Name')
    original_qty = fields.Float(string='BOM Default', readonly=True)
    qty          = fields.Float(string='Quote Qty', digits='Product Unit of Measure')


class KitQtyWizard(models.TransientModel):
    _name = 'proquotes.kit.qty.wizard'
    _description = 'Edit Kit Component Quantities'

    sale_line_id     = fields.Many2one('sale.order.line', required=True)
    kit_product_name = fields.Char(related='sale_line_id.product_id.name', readonly=True, string='Kit Product')
    line_ids         = fields.One2many('proquotes.kit.qty.wizard.line', 'wizard_id', string='Components')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        sale_line_id = self.env.context.get('default_sale_line_id')
        if not sale_line_id:
            return res

        sale_line = self.env['sale.order.line'].browse(sale_line_id)
        bom = self.env['mrp.bom'].search([
            ('product_tmpl_id', '=', sale_line.product_id.product_tmpl_id.id),
            ('type', '=', 'phantom'),
        ], limit=1)

        if not bom or not bom.bom_line_ids:
            return res

        # Parse existing ba_kit_description to pre-fill current quantities
        current_qtys = {}
        if sale_line.ba_kit_description:
            for text_line in sale_line.ba_kit_description.split('\n'):
                text_line = text_line.strip()
                m = re.match(r'^(\d+(?:\.\d+)?)\s*x\s+(.+)$', text_line)
                if m:
                    qty = float(m.group(1))
                    rest = m.group(2).strip()
                    if ' - ' in rest:
                        sku_part, name_part = rest.split(' - ', 1)
                        current_qtys[sku_part.strip()] = qty
                        current_qtys[name_part.strip()] = qty
                    else:
                        current_qtys[rest] = qty

        wizard_lines = []
        for bom_line in bom.bom_line_ids:
            product = bom_line.product_id
            sku = product.product_tmpl_id.sku or ''
            qty = current_qtys.get(sku) or current_qtys.get(product.name) or bom_line.product_qty
            wizard_lines.append((0, 0, {
                'bom_line_id': bom_line.id,
                'product_id': product.id,
                'sku': sku,
                'product_name': product.name,
                'original_qty': bom_line.product_qty,
                'qty': qty,
            }))

        res.update({
            'sale_line_id': sale_line_id,
            'line_ids': wizard_lines,
        })
        return res

    def action_save(self):
        line = self.sale_line_id

        # Rebuild ba_kit_description
        parts = []
        for wl in self.line_ids:
            qty = int(wl.qty) if wl.qty == int(wl.qty) else wl.qty
            sku = wl.sku
            name = wl.product_name or (wl.product_id.name if wl.product_id else '')
            part = f"{qty}x {sku} - {name}" if sku else f"{qty}x {name}"
            parts.append(part)
        line.write({'ba_kit_description': '\n'.join(parts)})

        # Sync quantities to pending (non-done) stock moves on linked delivery
        moves = self.env['stock.move'].search([
            ('sale_line_id', '=', line.id),
            ('state', 'not in', ['done', 'cancel']),
        ])
        for wl in self.line_ids:
            matching = moves.filtered(lambda m: m.product_id == wl.product_id)
            if matching:
                matching.write({'product_uom_qty': wl.qty})

        return {'type': 'ir.actions.act_window_close'}
