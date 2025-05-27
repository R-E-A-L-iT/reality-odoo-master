from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)
_logger.info("✅ Loaded custom sale_order.py module")

class StockLot(models.Model):
    _inherit = 'stock.lot'

    bundle_instance_id = fields.Many2one(
        'product.bundle.instance',
        string="Bundle Instance",
        help="Optional link to a product bundle instance"
    )
