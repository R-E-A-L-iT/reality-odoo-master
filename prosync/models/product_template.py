# -*- coding: utf-8 -*-

import base64
import requests

from .utilities import (
    normalize_char,
    normalize_text,
    normalize_date,
    normalize_float,
    normalize_integer,
    normalize_bool,
    normalize_binary,
    normalize_selection,
    normalize_many2one,
    normalize_many2many,
)

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


        # --------------------
        # PROCESS COLUMNS
        # --------------------


        required_fields = [
            "sku",
            "name",
            "valid",
            "continue",
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
        all_fields = product_template_model.fields_get().keys()

        # Define always-allowed column names (not actual model fields)
        allowed_special_fields = {"valid", "continue"}

        for column in sheet_columns:
            column_cleaned = column.strip().lower()

            # Skip always-allowed special fields
            if column_cleaned in allowed_special_fields:
                _logger.info(f"ProSync: Special field '{column}' is accepted (not in model).")
                continue

            # Skip price fields like "price[pricelist=CAD]"
            if column_cleaned.startswith("price[pricelist="):
                _logger.info(f"ProSync: Field '{column}' is a recognized pricelist field.")
                continue

            # Strip any [bracketed] metadata (like [language=fr_CA])
            base_field = column_cleaned.split("[")[0]

            # Validate against actual fields
            if base_field in all_fields:
                _logger.info(f"ProSync: Field '{column}' (base: '{base_field}') exists on product.template.")
            else:
                _logger.warning(f"ProSync: Field '{column}' (base: '{base_field}') does NOT exist on product.template.")

        _logger.info("ProSync: Sheet format has been validated.")

        column_indices = {col.strip().lower(): idx for idx, col in enumerate(sheet_columns)}


        # --------------------
        # PROCESS ROWS
        # --------------------


        for row_index, row in enumerate(self.sheet[1:], start=2):  # start=2 for logging row number
            # Defensive: skip completely empty rows
            if not any(row):
                _logger.info(f"ProSync: Skipping empty row {row_index}")
                continue

            # Normalize 'valid' and 'continue' values
            valid_raw = row[column_indices.get("valid", -1)] if "valid" in column_indices else ''
            continue_raw = row[column_indices.get("continue", -1)] if "continue" in column_indices else ''

            is_valid = normalize_bool(valid_raw)
            should_continue = normalize_bool(continue_raw)

            if not is_valid:
                if should_continue:
                    _logger.info(f"ProSync: Skipping row {row_index} (VALID is False, CONTINUE is True)")
                    continue
                else:
                    _logger.info(f"ProSync: Ending sheet sync at row {row_index} (VALID is False, CONTINUE is False)")
                    break

            # VALID is true — get and normalize SKU
            sku_raw = row[column_indices.get("sku", -1)] if "sku" in column_indices else ''
            sku = normalize_char(sku_raw)

            if not sku:
                _logger.warning(f"ProSync: Row {row_index} is missing a valid SKU. Skipping.")
                continue

            # Search for matching product.template
            product = self.database['product.template'].search([('sku', '=', sku)], limit=1)
            if product:
                _logger.info(f"ProSync: Row {row_index} — Found product with SKU: {sku} (ID: {product.id})")
                self.update_product_template(product, row_index, row, column_indices)
            else:
                _logger.info(f"ProSync: Row {row_index} — No product found with SKU: {sku}")
                self.create_product_template(row_index, row)

    def create_product_template(self, row_index, row):
        _logger.info(f"ProSync: Row {row_index} — Creating new product.template (not yet implemented)")

    def update_product_template(self, product, row_index, row, column_indices):
        product_model = self.database['product.template']
        all_fields = product_model.fields_get()

        for col_idx, column_name in enumerate(self.sheet[0]):
            field_name = column_name.strip().lower()

            # Skip special control columns
            if field_name in {'sku', 'valid', 'continue'}:
                continue

            # Skip bracketed fields for now (e.g., language/pricelist variants)
            if '[' in field_name and not field_name.startswith("price[pricelist="):
                continue

            # Strip [bracket] metadata
            base_field = field_name.split('[')[0]

            # Skip if not a valid field
            if base_field not in all_fields:
                continue

            field_type = all_fields[base_field]['type']
            raw_value = row[col_idx]

            try:
                # Normalize value by field type
                if field_type == 'char':
                    value = normalize_char(raw_value)
                elif field_type == 'text':
                    value = normalize_text(raw_value)
                elif field_type == 'float' or field_type == 'monetary':
                    value = normalize_float(raw_value)
                elif field_type == 'integer':
                    value = normalize_integer(raw_value)
                elif field_type == 'boolean':
                    value = normalize_bool(raw_value)
                elif field_type in {'date', 'datetime'}:
                    value = normalize_date(raw_value)
                elif field_type == 'binary':
                    value = normalize_binary(raw_value)
                elif field_type == 'selection':
                    value = normalize_selection(raw_value, base_field, all_fields)
                elif field_type == 'many2one':
                    value = normalize_many2one(raw_value, base_field, all_fields, self.database)
                    if value == '__not_found__':
                        continue
                elif field_type == 'many2many':
                    value = normalize_many2many(raw_value, base_field, all_fields, self.database)
                else:
                    _logger.warning(f"ProSync: Row {row_index} — Field '{base_field}' has unsupported type '{field_type}'. Skipping.")
                    continue

                # Write value to product
                product.write({base_field: value})

            except Exception as e:
                col_letter = chr(65 + col_idx)  # A = 65
                cell_id = f"{row_index}{col_letter}"
                _logger.error(f"ProSync: Error updating field '{base_field}' at cell {cell_id}: {str(e)}")


