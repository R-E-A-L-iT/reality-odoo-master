from odoo import models, fields, api

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

    @api.model
    def manual_trigger_prosync_schedule(self):
        cron = self.env.ref('prosync.ir_cron_prosync_schedule', raise_if_not_found=False)
        if cron:
            cron.method_direct_trigger()
        return True

    def dummy_button(self):
        _logger.info("Dummy button clicked.")
        return True
