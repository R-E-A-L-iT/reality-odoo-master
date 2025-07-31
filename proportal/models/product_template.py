# -*- coding: utf-8 -*-

import ast
import base64
import requests
import re

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
from urllib import request
import logging

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"
    skuhidden = fields.One2many("ir.model.data", "res_id", readonly=True)
    sku = fields.Char(related="skuhidden.name", string="SKU")

    def import_images_from_url(self):
        for product in self:
            sku = product.sku
            if not sku:
                continue

            image_url = f"https://cdn.r-e-a-l.it/images/ecommerce/Leica/{sku}/{sku}-01.png"

            try:
                response = requests.get(image_url, timeout=5)
                if response.status_code == 200:
                    product.image_1920 = base64.b64encode(response.content)
                    _logger.info(f"ProPortal: Uploaded image for {sku}")
                    self.env.cr.commit()
                else:
                    _logger.warning(f"ProPortal: Image not found for {sku} (status {response.status_code})")
            except Exception as e:
                _logger.error(f"ProPortal: Error processing {sku}: {e}")

    @api.model
    def create(self, vals):
        record = super(ProductTemplate, self).create(vals)
        if "sku" in vals:
            self._update_skuhidden(record.id, vals["sku"], record.name)
        return record

    def write(self, vals):
        result = super(ProductTemplate, self).write(vals)
        if "sku" in vals:
            for record in self:
                self._update_skuhidden(record.id, vals["sku"], record.name)
        return result

    def _update_skuhidden(self, record_id, sku_value, record_name):
        IrModelData = self.env["ir.model.data"]
        data = IrModelData.search([("res_id", "=", record_id), ("model", "=", "product.template")], limit=1)
        if data:
            data.write({"name": sku_value, "display_name": record_name})
        else:
            IrModelData.create({"name": sku_value, "module": "",
                                "model": "product.template", "res_id": record_id,
                                "display_name": record_name,
                                })
