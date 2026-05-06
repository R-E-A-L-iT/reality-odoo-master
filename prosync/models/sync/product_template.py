# -*- coding: utf-8 -*-

import re
import base64
import logging
import requests

from datetime import datetime

from ..utilities import (
    normalize_char,
    normalize_text,
    normalize_date,
    normalize_float,
    normalize_integer,
    normalize_bool,
    normalize_binary,
    normalize_selection,
    update_with_lang_context,
    update_with_price_context,
    update_with_rental_price_context,
    update_with_related_context,
    update_with_special_context,
)

_logger = logging.getLogger(__name__)

class product_template_sync:

    def __init__(self, name, sheet, database):
        self.name = name
        self.sheet = sheet
        self.database = database
        self.updated_items = []
        self.warning_items = []
        self.error_items = []
        self.rental_updated_items = []
        self.rental_warning_items = []
        self.report_id = None

    def sync_product_template(self):
        _logger.info("ProSync: Starting PRODUCT_TEMPLATE sync process.")

        sync_start_time = datetime.now()
        self.report_id = self.database['prosync.report'].create({
            'name': f"Product Template Sync: {self.name}",
            'status': 'success',
            'sync_type': 'product_template',
            'start_time': sync_start_time,
        })


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
            self.error_items.append(
                f'ProSync: {error_msg}<br/><br/>'
            )

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

            # Skip rental price fields like "rental_price[pricelist=CAD]"
            if column_cleaned.startswith("rental_price[pricelist="):
                _logger.info(f"ProSync: Field '{column}' is a recognized rental pricing field.")
                continue

            # Strip any [bracketed] metadata (like [language=fr_CA])
            base_field = column_cleaned.split("[")[0]

            # Validate against actual fields
            if base_field in all_fields:
                _logger.info(f"ProSync: Field '{column}' (base: '{base_field}') exists on product.template.")
            else:
                _logger.warning(f"ProSync: Field '{column}' (base: '{base_field}') does NOT exist on product.template.")
                self.warning_items.append(
                    f"ProSync: Field '{column}' (base: '{base_field}') does NOT exist on product.template.<br/><br/>"
                )

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
                self.warning_items.append(
                    f"ProSync: Row {row_index} is missing a valid SKU. Skipping.<br/><br/>"
                )
                continue

            # Search for matching product.template
            product = self.database['product.template'].search([('sku', '=', sku)], limit=1)
            if product:
                _logger.info(f"ProSync: Row {row_index} — Found product with SKU: {sku} (ID: {product.id})")
                self.update_product_template(product, row_index, row, column_indices)
            else:
                _logger.info(f"ProSync: Row {row_index} — No product found with SKU: {sku}")
                self.create_product_template(row_index, row)

        end_time = datetime.now()

        if not self.updated_items and not self.warning_items and not self.error_items:
            _logger.info("ProSync: No changes detected. Deleting sync report.")
            self.report_id.unlink()
        else:
            self.report_id.write({
                'end_time': end_time,
                'report_text': "\n".join(self.updated_items) or "No changes detected.",
                'warning_text': "\n".join(self.warning_items) or "No warnings to display",
                'error_text': "\n".join(self.error_items) or "No errors to display",
                'status': 'failure' if self.error_items else 'warning' if self.warning_items else 'success',
            })

        # Create a separate Rental Price report if rental changes occurred
        _logger.info(f"ProSync [RENTAL] End of sync — rental_updated={len(self.rental_updated_items)} rental_warnings={len(self.rental_warning_items)}")
        if self.rental_updated_items or self.rental_warning_items:
            rental_report = self.database['prosync.report'].create({
                'name': f"Rental Price Sync: {self.name}",
                'status': 'success',
                'sync_type': 'rental_price',
                'start_time': sync_start_time,
            })
            rental_report.write({
                'end_time': end_time,
                'report_text': "\n".join(self.rental_updated_items) or "No changes detected.",
                'warning_text': "\n".join(self.rental_warning_items) or "No warnings to display",
                'error_text': "No errors to display",
                'status': 'warning' if self.rental_warning_items else 'success',
            })
            _logger.info(f"ProSync: Created rental price sync report with {len(self.rental_updated_items)} changes.")
        


    def create_product_template(self, row_index, row):
        column_indices = {col.strip().lower(): idx for idx, col in enumerate(self.sheet[0])}

        sku_raw = row[column_indices.get("sku", -1)] if "sku" in column_indices else ''
        name_raw = row[column_indices.get("name", -1)] if "name" in column_indices else ''

        sku = normalize_char(sku_raw)
        name = normalize_char(name_raw)

        if not sku or not name:
            _logger.warning(f"ProSync: Row {row_index} — Cannot create product without valid SKU and Name. Skipping.")
            self.warning_items.append(
                f"ProSync: Row {row_index} — Cannot create product without valid SKU and Name. Skipping.<br/><br/>"
            )
            return

        product_model = self.database['product.template']

        product = product_model.create({
            "sku": sku,
            "name": name,
            "company_id": False,
            "responsible_id": False,
        })

        _logger.info(f"ProSync: Row {row_index} — Created new product.template with SKU: {sku}, ID: {product.id}")

        # Call update logic to populate remaining fields
        self.update_product_template(product, row_index, row, column_indices)


    def update_product_template(self, product, row_index, row, column_indices):
        product_model = self.database['product.template']
        all_fields = product_model.fields_get()

        header = self.sheet[0]
        _logger.info(f"ProSync [DEBUG] Row {row_index} — header cols={len(header)} | row cols={len(row)} | SKU={getattr(product, 'sku', product.id)}")

        for col_idx, column_name in enumerate(header):
            field_name = column_name.strip().lower()

            # skip columns already processed
            if field_name in {'sku', 'valid', 'continue'}:
                continue

            # Guard: row may be shorter than header (trailing empty cells stripped by gspread)
            if col_idx >= len(row):
                _logger.info(f"ProSync [DEBUG] Row {row_index} col {col_idx} ('{column_name}') — no cell value (row shorter than header), treating as empty")
                raw_value = ''
            else:
                raw_value = row[col_idx]

            # deal with columns using parametres
            if "[language=" in column_name:
                update_with_lang_context(product, column_name, raw_value, all_fields, self.database, row_index, col_idx)
                continue
            elif "[related=" in column_name:
                try:
                    update_with_related_context(product, column_name, raw_value, all_fields, self.database, row_index, col_idx)
                except Exception as e:
                    _logger.error(f"ProSync: Row {row_index} — Error updating related field '{field_name}' with value '{raw_value}': {str(e)}")
                    self.error_items.append(
                        f"ProSync: Row {row_index} — Error updating related field '{field_name}' with value '{raw_value}': {str(e)}<br/><br/>"
                    )
                continue
            elif field_name.startswith("price[pricelist="):
                update_with_price_context(product, column_name, raw_value, self.database, row_index, col_idx)
                continue
            elif field_name.startswith("rental_price[pricelist="):
                _logger.info(f"ProSync [RENTAL] Row {row_index} col {col_idx} — detected rental price column '{column_name}' | raw value='{raw_value}'")
                try:
                    update_with_rental_price_context(product, column_name, raw_value, self.database, row_index, col_idx, self.rental_updated_items, self.rental_warning_items)
                except Exception as e:
                    _logger.error(f"ProSync [RENTAL] Row {row_index} — UNHANDLED ERROR in update_with_rental_price_context for column '{column_name}': {str(e)}", exc_info=True)
                    self.rental_warning_items.append(f"Row {row_index} col '{column_name}': Unexpected error: {str(e)}<br/><br/>")
                continue
            elif "[special=" in column_name:
                update_with_special_context(product, column_name, raw_value, self.database, row_index, col_idx, self.updated_items)
                continue
            elif '[' in field_name:
                continue

            # Strip [bracket] metadata
            base_field = field_name.split('[')[0]

            # Skip if not a valid field
            if base_field not in all_fields:
                continue

            field_type = all_fields[base_field]['type']

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
                    value = normalize_date(raw_value, field_type=field_type)
                elif field_type == 'binary':
                    value = normalize_binary(raw_value)
                elif field_type == 'selection':
                    value = normalize_selection(raw_value, base_field, all_fields)
                elif field_type == 'many2one':
                    _logger.warning(f"ProSync: Row {row_index} Field '{base_field}' not updated because it is a many2one field and missing the [related=] tag. See documentation for more information.")
                    self.warning_items.append(
                        f"ProSync: Row {row_index} Field '{base_field}' not updated because it is a many2one field and missing the [related=] tag. See documentation for more information.<br/><br/>"
                    )
                elif field_type == 'many2many':
                    _logger.warning(f"ProSync: Row {row_index} Field '{base_field}' not updated because it is a many2many field and missing the [related=] tag. See documentation for more information.")
                    self.warning_items.append(
                        f"ProSync: Row {row_index} Field '{base_field}' not updated because it is a many2many field and missing the [related=] tag. See documentation for more information.<br/><br/>"
                    )
                else:
                    _logger.warning(f"ProSync: Row {row_index} — Field '{base_field}' has unsupported type '{field_type}'. Skipping.")
                    self.warning_items.append(
                        f"ProSync: Row {row_index} — Field '{base_field}' has unsupported type '{field_type}'. Skipping.<br/><br/>"
                    )
                    continue
                
                existing_value = product[base_field]
                if value == existing_value:
                    continue

                # Write value to product
                product.write({base_field: value})

                col_letter = chr(65 + col_idx)
                cell_id = f"{row_index}{col_letter}"
                change_summary = (
                    f'<b>{cell_id}</b>, {product.sku}<br/>'
                    f'Field <u>{base_field}</u> updated: "{existing_value}" <b>→</b> "{value}"<br/><br/>'
                )
                self.updated_items.append(change_summary)


            except Exception as e:
                col_letter = chr(65 + col_idx)  # A = 65
                cell_id = f"{row_index}{col_letter}"
                _logger.error(f"ProSync: Error updating field '{base_field}' at cell {cell_id}: {str(e)}")
                self.error_items.append(
                    f'<b>{cell_id}</b>, {product.sku}<br/>'
                    f'Error updating <u>{base_field}</u>: {str(e)}<br/><br/>'
                )


