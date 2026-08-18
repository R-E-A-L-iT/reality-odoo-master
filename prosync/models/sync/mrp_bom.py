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
    update_with_related_context,
    update_with_special_context,
)

_logger = logging.getLogger(__name__)

class mrp_bom_sync:

    def __init__(self, name, sheet, database):
        self.name = name
        self.sheet = sheet
        self.database = database
        self.updated_items = []
        self.warning_items = []
        self.error_items = []
        self.report_id = None

    def sync_mrp_bom(self):
        _logger.info("ProSync: Starting PRODUCT_TEMPLATE sync process.")

        self.report_id = self.database['prosync.report'].create({
            'name': f"MRP BOM Sync: {self.name}",
            'status': 'success',
            'sync_type': 'mrp_bom',
            'start_time': datetime.now(),
        })


        # --------------------
        # PROCESS COLUMNS
        # --------------------


        required_fields = [
            "product_tmpl_id[related=sku]",
            "code",
            "valid",
            "continue",
        ]

        sheet_columns = self.sheet[0] if len(self.sheet) > 0 else []
        sheet_width = len(sheet_columns)

        # variables that will contain a list of any missing columns in the sheet
        sheet_columns_lower = [c.strip().lower() for c in sheet_columns]
        missing_columns = [header for header in required_fields if header not in sheet_columns_lower]

        # verify that sheet format is as expected
        if missing_columns:
            error_msg = f"Sheet validation failed. Missing columns for fields: {missing_columns}."
            _logger.error(f"ProSync: {error_msg}")
            self.error_items.append(
                f'ProSync: {error_msg}<br/><br/>'
            )

        # Check if each column maps to a real field on mrp.bom
        mrp_bom_model = self.database['mrp.bom']
        all_fields = mrp_bom_model.fields_get().keys()

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

            if "[special=products]" in column_cleaned:
                _logger.info(f"ProSync: Field '{column}' is a special field for products.")
                continue

            # Strip any [bracketed] metadata (like [language=fr_CA])
            base_field = column_cleaned.split("[")[0]

            # Validate against actual fields
            if base_field in all_fields:
                _logger.info(f"ProSync: Field '{column}' (base: '{base_field}') exists on mrp.bom.")
            else:
                _logger.warning(f"ProSync: Field '{column}' (base: '{base_field}') does NOT exist on mrp.bom.")
                self.warning_items.append(
                    f"ProSync: Field '{column}' (base: '{base_field}') does NOT exist on mrp.bom.<br/><br/>"
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

            # VALID is true — get and normalize CODE
            code_raw = row[column_indices.get("code", -1)] if "code" in column_indices else ''
            code = normalize_char(code_raw)

            if not code:
                _logger.warning(f"ProSync: Row {row_index} is missing a valid CODE. Skipping.")
                self.warning_items.append(
                    f"ProSync: Row {row_index} is missing a valid CODE. Skipping.<br/><br/>"
                )
                continue

            # Search for matching mrp.bom
            bom = self.database['mrp.bom'].search([('code', '=', code)], limit=1)
            if bom:
                _logger.info(f"ProSync: Row {row_index} — Found bom with CODE: {code} (ID: {bom.id})")
                self.update_mrp_bom(bom, row_index, row, column_indices)
            else:
                _logger.info(f"ProSync: Row {row_index} — No bom found with CODE: {code}")
                self.create_mrp_bom(row_index, row)

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
        


    def create_mrp_bom(self, row_index, row):
        column_indices = {col.strip().lower(): idx for idx, col in enumerate(self.sheet[0])}

        code_raw = row[column_indices.get("code", -1)] if "code" in column_indices else ''
        # Parent product is keyed by SKU (via the required "product_tmpl_id[related=sku]"
        # column), matching how every other syncer resolves product.template records.
        sku_raw = row[column_indices.get("product_tmpl_id[related=sku]", -1)] if "product_tmpl_id[related=sku]" in column_indices else ''

        code = normalize_char(code_raw)
        product_tmpl_id = self.database['product.template'].sudo().search([('sku', '=', normalize_char(sku_raw))], limit=1)

        if not code or not product_tmpl_id:
            _logger.warning(f"ProSync: Row {row_index} — Cannot create bom without valid Code and Product Template ID. Skipping.")
            self.warning_items.append(
                f"ProSync: Row {row_index} — Cannot create bom without valid Code and Product Template ID. Skipping.<br/><br/>"
            )
            return

        bom_model = self.database['mrp.bom']

        bom = bom_model.create({
            "code": code,
            "product_tmpl_id": product_tmpl_id.id,
        })

        _logger.info(f"ProSync: Row {row_index} — Created new mrp.bom with CODE: {code}, ID: {bom.id}")

        # Call update logic to populate remaining fields
        self.update_mrp_bom(bom, row_index, row, column_indices)


    def update_mrp_bom(self, bom, row_index, row, column_indices):
        bom_model = self.database['mrp.bom']
        all_fields = bom_model.fields_get()

        for col_idx, column_name in enumerate(self.sheet[0]):
            field_name = column_name.strip().lower()

            # skip columns already processed
            if field_name in {'code', 'valid', 'continue'}:
                continue

            raw_value = row[col_idx]
            # deal with columns using parametres
            if "[language=" in column_name:
                update_with_lang_context(bom, column_name, raw_value, all_fields, self.database, row_index, col_idx)
                continue
            elif "[related=" in column_name:
                try:
                    update_with_related_context(bom, column_name, raw_value, all_fields, self.database, row_index, col_idx)
                except Exception as e:
                    _logger.error(f"ProSync: Row {row_index} — Error updating related field '{field_name}' with value '{raw_value}': {str(e)}")
                    self.error_items.append(
                        f"ProSync: Row {row_index} — Error updating related field '{field_name}' with value '{raw_value}': {str(e)}<br/><br/>"
                    )
                continue
            elif "[special=" in column_name:
                update_with_special_context(bom, column_name, raw_value, self.database, row_index, col_idx, self.updated_items)
                continue
            elif '[' in field_name:
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
                
                existing_value = bom[base_field]
                if value == existing_value:
                    continue

                # Write value to bom
                bom.write({base_field: value})

                col_letter = chr(65 + col_idx)
                cell_id = f"{row_index}{col_letter}"
                change_summary = (
                    f'<b>{cell_id}</b>, {bom.product_tmpl_id.name}<br/>'
                    f'Field <u>{base_field}</u> updated: "{existing_value}" <b>→</b> "{value}"<br/><br/>'
                )
                self.updated_items.append(change_summary)

            except Exception as e:
                col_letter = chr(65 + col_idx)  # A = 65
                cell_id = f"{row_index}{col_letter}"
                _logger.error(f"ProSync: Error updating field '{base_field}' at cell {cell_id}: {str(e)}")
                self.error_items.append(
                    f'<b>{cell_id}</b>, {bom.product_tmpl_id.name}<br/>'
                    f'Error updating <u>{base_field}</u>: {str(e)}<br/><br/>'
                )


