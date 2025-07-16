from odoo import models, fields

class ProsyncReport(models.Model):
    _name = 'prosync.report'
    _description = 'ProSync Sync Report'

    name = fields.Char(string='Name', required=True)
    sync_type = fields.Selection([
        ('product_template', 'Product Template'),
        ('stock_lot', 'Stock/Lot'),
        ('res_partner', 'Contact'),
    ], string='Type', required=True)
    start_time = fields.Datetime(string='Start Time')
    end_time = fields.Datetime(string='End Time')