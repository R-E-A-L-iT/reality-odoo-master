# -*- coding: utf-8 -*-

import logging
from datetime import datetime

from ..utilities import (
    normalize_char,
    normalize_float,
    normalize_integer,
    normalize_bool,
)

_logger = logging.getLogger(__name__)

class mrp_bom_line_sync:

    def __init__(self, name, sheet, database):
        self.name = name
        self.sheet = sheet
        self.database = database
        self.updated_items = []
        self.warning_items = []
        self.error_items = []
        self.report_id = None

    def sync_mrp_bom_line(self):
        _logger.info("ProSync: Starting MRP_BOM_LINE sync process.")

        self.report_id = self.database['prosync.report'].create({
            'name': f"MRP BOM Line Sync: {self.name}",
            'status': 'success',
            'sync_type': 'mrp_bom_line',
            'start_time': datetime.now(),
        })


        # --------------------
        # PROCESS COLUMNS
        # --------------------


        required_fields = [
            "bom_id",
            "product_id",
            "product_qty",
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

        _logger.info("ProSync: Sheet format has been validated.")

        column_indices = {
            str(col).strip().lower(): idx
            for idx, col in enumerate(sheet_columns)
            if col is not None
        }


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

            # VALID is true — get and normalize bom_id (parent product barcode)
            bom_id_raw = row[column_indices.get("bom_id", -1)] if "bom_id" in column_indices else ''
            bom_barcode = normalize_char(bom_id_raw)

            if not bom_barcode:
                _logger.warning(f"ProSync: Row {row_index} is missing a valid bom_id (parent product barcode). Skipping.")
                self.warning_items.append(
                    f"ProSync: Row {row_index} is missing a valid bom_id (parent product barcode). Skipping.<br/><br/>"
                )
                continue

            # Get product_id (BOM line product barcode)
            product_id_raw = row[column_indices.get("product_id", -1)] if "product_id" in column_indices else ''
            line_product_barcode = normalize_char(product_id_raw)

            if not line_product_barcode:
                _logger.warning(f"ProSync: Row {row_index} is missing a valid product_id (BOM line product barcode). Skipping.")
                self.warning_items.append(
                    f"ProSync: Row {row_index} is missing a valid product_id (BOM line product barcode). Skipping.<br/><br/>"
                )
                continue

            # Get product_qty
            product_qty_raw = row[column_indices.get("product_qty", -1)] if "product_qty" in column_indices else ''
            product_qty = normalize_float(product_qty_raw)

            if product_qty <= 0:
                _logger.warning(f"ProSync: Row {row_index} has invalid product_qty: {product_qty}. Skipping.")
                self.warning_items.append(
                    f"ProSync: Row {row_index} has invalid product_qty: {product_qty}. Skipping.<br/><br/>"
                )
                continue

            # Process the BOM and BOM line
            self.process_bom_line(row_index, bom_barcode, line_product_barcode, product_qty)

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


    def process_bom_line(self, row_index, bom_barcode, line_product_barcode, product_qty):
        """
        Process a single BOM line:
        1. Find or create the parent mrp.bom by product barcode
        2. Find or create the mrp.bom.line
        3. Update the quantity if changed
        """

        # --------------------
        # FIND/CREATE PARENT BOM
        # --------------------

        # Search for product.template by barcode
        product_template_model = self.database['product.template']
        parent_product = product_template_model.search([('barcode', '=', bom_barcode)], limit=1)

        if not parent_product:
            _logger.warning(f"ProSync: Row {row_index} — Parent product with barcode '{bom_barcode}' not found. Skipping.")
            self.warning_items.append(
                f"ProSync: Row {row_index} — Parent product with barcode '{bom_barcode}' not found. Please create the product first.<br/><br/>"
            )
            return

        # Search for existing mrp.bom for this product
        mrp_bom_model = self.database['mrp.bom']
        bom = mrp_bom_model.search([('product_tmpl_id', '=', parent_product.id)], limit=1)

        if not bom:
            # Create new BOM with type='phantom' (Kit)
            try:
                bom = mrp_bom_model.create({
                    'product_tmpl_id': parent_product.id,
                    'type': 'phantom',
                })
                _logger.info(f"ProSync: Row {row_index} — Created new mrp.bom (ID: {bom.id}) for product '{parent_product.name}' (barcode: {bom_barcode})")
                self.updated_items.append(
                    f'<b>Row {row_index}</b><br/>'
                    f'Created new BOM for product <u>{parent_product.name}</u> (barcode: {bom_barcode})<br/>'
                    f'BOM ID: {bom.id}, Type: phantom<br/><br/>'
                )
            except Exception as e:
                _logger.error(f"ProSync: Row {row_index} — Error creating mrp.bom for product '{parent_product.name}': {str(e)}")
                self.error_items.append(
                    f'<b>Row {row_index}</b><br/>'
                    f'Error creating BOM for product <u>{parent_product.name}</u>: {str(e)}<br/><br/>'
                )
                return
        else:
            _logger.info(f"ProSync: Row {row_index} — Found existing mrp.bom (ID: {bom.id}) for product '{parent_product.name}' (barcode: {bom_barcode})")


        # --------------------
        # FIND/CREATE BOM LINE
        # --------------------

        # Search for the line product by barcode (could be product.product or product.template)
        product_product_model = self.database['product.product']
        line_product = product_product_model.search([('barcode', '=', line_product_barcode)], limit=1)

        if not line_product:
            _logger.warning(f"ProSync: Row {row_index} — BOM line product with barcode '{line_product_barcode}' not found. Skipping.")
            self.warning_items.append(
                f"ProSync: Row {row_index} — BOM line product with barcode '{line_product_barcode}' not found. Please create the product first.<br/><br/>"
            )
            return

        # Search for existing BOM line
        mrp_bom_line_model = self.database['mrp.bom.line']
        bom_line = mrp_bom_line_model.search([
            ('bom_id', '=', bom.id),
            ('product_id', '=', line_product.id)
        ], limit=1)

        if not bom_line:
            # Create new BOM line
            try:
                bom_line = mrp_bom_line_model.create({
                    'bom_id': bom.id,
                    'product_id': line_product.id,
                    'product_qty': product_qty,
                })
                _logger.info(f"ProSync: Row {row_index} — Created new BOM line (ID: {bom_line.id}) for product '{line_product.display_name}' (barcode: {line_product_barcode})")
                self.updated_items.append(
                    f'<b>Row {row_index}</b><br/>'
                    f'Created new BOM line for product <u>{line_product.display_name}</u> (barcode: {line_product_barcode})<br/>'
                    f'Parent BOM: {parent_product.name}, Quantity: {product_qty}<br/><br/>'
                )
            except Exception as e:
                _logger.error(f"ProSync: Row {row_index} — Error creating BOM line for product '{line_product.display_name}': {str(e)}")
                self.error_items.append(
                    f'<b>Row {row_index}</b><br/>'
                    f'Error creating BOM line for product <u>{line_product.display_name}</u>: {str(e)}<br/><br/>'
                )
                return
        else:
            # Update existing BOM line if quantity changed
            existing_qty = bom_line.product_qty
            if existing_qty != product_qty:
                try:
                    bom_line.write({'product_qty': product_qty})
                    _logger.info(f"ProSync: Row {row_index} — Updated BOM line (ID: {bom_line.id}) quantity: {existing_qty} → {product_qty}")
                    self.updated_items.append(
                        f'<b>Row {row_index}</b><br/>'
                        f'Updated BOM line for product <u>{line_product.display_name}</u> (barcode: {line_product_barcode})<br/>'
                        f'Quantity updated: {existing_qty} <b>→</b> {product_qty}<br/><br/>'
                    )
                except Exception as e:
                    _logger.error(f"ProSync: Row {row_index} — Error updating BOM line quantity: {str(e)}")
                    self.error_items.append(
                        f'<b>Row {row_index}</b><br/>'
                        f'Error updating BOM line quantity: {str(e)}<br/><br/>'
                    )
            else:
                _logger.info(f"ProSync: Row {row_index} — BOM line (ID: {bom_line.id}) quantity unchanged: {product_qty}")
