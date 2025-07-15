# -*- coding: utf-8 -*-

import base64
import requests

import logging

_logger = logging.getLogger(__name__)

class product_template_sync:

    def __init__(self, name, sheet, database):
        self.name = name
        self.sheet = sheet
        self.database = database
        # self.sync_report = []

    def sync_product_template(self):
        _logger.info("ProSync: Starting PRODUCT_TEMPLATE sync process.")

        required_fields = [
            "sku",
            "name",
        ]

        sheet_columns = self.sheet[0] if len(self.sheet) > 0 else []
        sheet_width = len(sheet_columns)
        
        # variables that will contain a list of any missing columns in the sheet
        missing_columns = [header for header in required_fields if header not in sheet_columns]
        
        # verify that sheet format is as expected
        if missing_columns:
            error_msg = f"Sheet validation failed. Missing columns for fields: {missing_columns}."
            _logger.error(f"ProSync: {error_msg}")

        # Check if each column maps to a real field on product.template
        product_template_model = self.database['product.template']
        all_fields = product_template_model.fields_get().keys()  # includes inherited/custom fields

        for column in sheet_columns:
            column_cleaned = column.strip().lower()
            if column_cleaned in all_fields:
                _logger.info(f"ProSync: Field '{column}' exists on product.template")
            else:
                _logger.error(f"ProSync: Field '{column}' does NOT exist on product.template")

        _logger.info("ProSync: Sheet format has been validated.")
