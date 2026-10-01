# -*- coding: utf-8 -*-

import ast
import base64
import requests
import re

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
from urllib import request
from dateutil.relativedelta import relativedelta
from datetime import date, datetime
from odoo.tools import format_date
import logging

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"
    skuhidden = fields.One2many("ir.model.data", "res_id", readonly=True)
    sku = fields.Char(related="skuhidden.name", string="SKU")
    description_sale_clean = fields.Text(
        compute='_compute_description_sale_clean',
        store=False
    )

    def _compute_description_sale_clean(self):
        for product in self:
            product.description_sale_clean = html2plaintext(
                product.description_sale or ''
            )

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

    def _prosync_extract_ccp_key(self):
        self.ensure_one()
        sku = (self.sku or "").strip()
        if not sku.upper().startswith("CCP-"):
            return False
        return sku[4:].strip()  # everything after CCP-

    def import_images_from_ccp_lots(self, timeout=5):
        StockLot = self.env["stock.lot"].sudo()

        for product in self:
            ccp_key = product._prosync_extract_ccp_key()
            if not ccp_key:
                continue

            lot = StockLot.search([("name", "ilike", ccp_key)], limit=1)
            if not lot:
                _logger.info("ProSync Images: No stock.lot found for CCP key '%s' (product %s)", ccp_key, product.id)
                continue

            lot_sku = (getattr(lot, "sku", False) or "").strip()
            if not lot_sku:
                _logger.info("ProSync Images: stock.lot %s matched '%s' but has no lot.sku", lot.id, ccp_key)
                continue

            image_url = f"https://cdn.r-e-a-l.it/images/ecommerce/Leica/{lot_sku}/{lot_sku}-01.png"

            # Keep going even if a single product fails
            with self.env.cr.savepoint():
                try:
                    resp = requests.get(image_url, timeout=timeout)
                    if resp.status_code == 200 and resp.content:
                        product.image_1920 = base64.b64encode(resp.content)
                        _logger.info("ProSync Images: Uploaded image for product %s from %s", product.id, image_url)
                    else:
                        _logger.warning(
                            "ProSync Images: Image not found for lot_sku '%s' (status %s) url=%s",
                            lot_sku, resp.status_code, image_url
                        )
                except Exception as e:
                    _logger.exception("ProSync Images: Error processing product %s url=%s: %s", product.id, image_url, e)

    # Odoo 19: create is @api.model_create_multi (receives a list of vals dicts).
    @api.model_create_multi
    def create(self, vals_list):
        records = super(ProductTemplate, self).create(vals_list)
        for record, vals in zip(records, vals_list):
            if "sku" in vals:
                self._update_skuhidden(record.id, vals["sku"], record.name)
        return records

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

    @api.model
    def _search_get_detail(self, website, order, options):
        res = super()._search_get_detail(website, order, options)

        mapping = res.get('mapping', {})
        fetch_fields = res.get('fetch_fields', [])

        if 'description' in mapping:
            mapping['description']['name'] = 'description_sale_clean'
            mapping['description']['type'] = 'text'
            mapping['description']['match'] = True

            if 'description_sale_clean' not in fetch_fields:
                fetch_fields.append('description_sale_clean')

        return res
