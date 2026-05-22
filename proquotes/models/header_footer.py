# -*- coding: utf-8 -*-


import logging

from odoo import fields, models
from odoo.exceptions import UserError
from odoo import models, fields

_logger = logging.getLogger(__name__)


class footer_header(models.Model):
    _name = "header.footer"
    _description = "Hold info for Headers and Footer"
    _rec_name = "name"
    name = fields.Char(string="Name", required=True)
    record_type = fields.Selection(
        [("Footer", "Footer"), ("Header", "Header")], required=True, default="Footer"
    )
    url = fields.Char(string="Resource URL", required=True)
    company_ids = fields.Many2many("res.company")
    active = fields.Boolean(string="Active", default=True)
    header_id = fields.Many2one('res.users')
    # Get Footer based on URL
    def _get_footer(self, url):
        complete_url = "https://cdn.r-e-a-l.it/images/footer/" + url + ".png"
        footers = self.env["header.footer"].search(
            [("url", "=", complete_url), ("record_type", "=", "Footer")]
        )
        if len(footers) == 1:
            return footers[0].id
        elif len(footers) == 0:
            return self.env["header.footer"].create({"name": url, "url": complete_url})
        raise UserError("Invalid Match Count for URL: " + str(complete_url))

    # Get Header based on URL
    def _get_header(self, url):
        complete_url = "https://cdn.r-e-a-l.it/images/header/" + url
        headers = self.env["header.footer"].search(
            [("url", "=", complete_url), ("record_type", "=", "Header")]
        )
        if len(headers) == 1:
            return headers[0].id
        elif len(headers) == 0:
            return self.env["header.footer"].create(
                {"name": url, "url": complete_url, "record_type": "Header"}
            )
        raise UserError("Invalid Match Count for URL: " + str(complete_url))

    # Init footer for based on old footer field
    def _init_footers(self, model):
        records = self.env[model].search([("footer", "!=", False)])
        for record in records:
            record.footer_id = self._get_footer(record.footer)

    # Init header for based on old footer field
    def _init_headers(self, model):
        records = self.env[model].search([("header", "!=", False)])
        for record in records:
            record.header_id = self._get_header(record.header)

    def init_records(self, model):
        # Init header and footer of all records
        records = self.env[model]

        # Confirm Old Footer Field
        if "footer_id" in dir(records) and "footer" in dir(records):
            self._init_footers(model)
        # Confirm Old Header Field
        if "header_id" in dir(records) and "header" in dir(records):
            self._init_headers(model)
