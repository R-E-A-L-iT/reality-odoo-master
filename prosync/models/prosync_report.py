from odoo import models, fields, api

class ProsyncReport(models.Model):
    _name = 'prosync.report'
    _description = 'ProSync Sync Report'

    name = fields.Char(string='Name', required=True)
    status = fields.Selection([
        ('success', "Success"),
        ('warning', "Warning"),
        ('failure', "Errors"),
    ], string="Status", required=True)
    sync_type = fields.Selection([
        ('product_template', 'Product Template'),
        ('stock_lot', 'Stock/Lot'),
        ('res_partner', 'Contact'),
        ('mrp_bom', 'Bill of Materials'),
        ('product_product', 'Product Variant'),
    ], string='Type', required=True)
    start_time = fields.Datetime(string='Start Time')
    end_time = fields.Datetime(string='End Time')
    duration = fields.Float(string="Sync Duration (minutes)", compute="_compute_sync_duration", store=True)
    sync_date = fields.Date(string="Sync Date", compute="_compute_sync_date", store=True)

    report_text = fields.Html(string="Sync Report", readonly=True)
    warning_text = fields.Html(string="Warnings", readonly=True)
    error_text = fields.Html(string="Errors", readonly=True)

    @api.depends('start_time', 'end_time')
    def _compute_sync_duration(self):
        for record in self:
            if record.start_time and record.end_time:
                delta = record.end_time - record.start_time
                record.duration = delta.total_seconds() / 60.0
            else:
                record.duration = 0.0

    @api.depends('start_time')
    def _compute_sync_date(self):
        for record in self:
            record.sync_date = record.start_time.date() if record.start_time else None

    @api.model
    def manual_trigger_prosync_schedule(self):
        cron = self.env.ref('prosync.prosync_schedule', raise_if_not_found=False)
        if not cron:
            raise UserError("Cron 'prosync.prosync_schedule' not found.")
        cron.method_direct_trigger()
        return True

    def dummy_button(self):
        _logger.info("Dummy button clicked.")
        return True
