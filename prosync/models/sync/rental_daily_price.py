# -*- coding: utf-8 -*-

import logging
from datetime import datetime

from ..utilities import normalize_bool, normalize_char, update_with_daily_price_context

_logger = logging.getLogger(__name__)


class rental_daily_price_sync:

    def __init__(self, name, sheet, database):
        self.name = name
        self.sheet = sheet
        self.database = database
        self.updated_items = []
        self.warning_items = []
        self.error_items = []

    def sync_rental_daily_price(self):
        _logger.info("ProSync: Starting RENTAL_DAILY_PRICE sync process.")
        sync_start_time = datetime.now()

        report_id = self.database['prosync.report'].create({
            'name': f"Rental Daily Price Sync: {self.name}",
            'status': 'success',
            'sync_type': 'rental_daily_price',
            'start_time': sync_start_time,
        })

        required_fields = ["sku", "valid", "continue"]
        sheet_columns = self.sheet[0] if self.sheet else []

        missing_columns = [h for h in required_fields if h not in [c.strip().lower() for c in sheet_columns]]
        if missing_columns:
            error_msg = f"Sheet validation failed. Missing required columns: {missing_columns}."
            _logger.error(f"ProSync: {error_msg}")
            self.error_items.append(f"ProSync: {error_msg}<br/><br/>")

        column_indices = {col.strip().lower(): idx for idx, col in enumerate(sheet_columns)}

        for row_index, row in enumerate(self.sheet[1:], start=2):
            if not any(row):
                _logger.info(f"ProSync: Skipping empty row {row_index}")
                continue

            valid_raw = row[column_indices["valid"]] if "valid" in column_indices else ''
            continue_raw = row[column_indices["continue"]] if "continue" in column_indices else ''
            is_valid = normalize_bool(valid_raw)
            should_continue = normalize_bool(continue_raw)

            if not is_valid:
                if should_continue:
                    _logger.info(f"ProSync: Skipping row {row_index} (VALID=False, CONTINUE=True)")
                    continue
                else:
                    _logger.info(f"ProSync: Ending sync at row {row_index} (VALID=False, CONTINUE=False)")
                    break

            sku_raw = row[column_indices["sku"]] if "sku" in column_indices else ''
            sku = normalize_char(sku_raw)
            if not sku:
                _logger.warning(f"ProSync: Row {row_index} is missing a valid SKU. Skipping.")
                self.warning_items.append(f"ProSync: Row {row_index} is missing a valid SKU. Skipping.<br/><br/>")
                continue

            product = self.database['product.template'].search([('sku', '=', sku)], limit=1)
            if not product:
                _logger.warning(f"ProSync: Row {row_index} — No product found with SKU '{sku}'.")
                self.warning_items.append(f"ProSync: Row {row_index} — No product found with SKU '{sku}'.<br/><br/>")
                continue

            _logger.info(f"ProSync: Row {row_index} — Found product SKU '{sku}' (ID {product.id})")

            for col_idx, column_name in enumerate(sheet_columns):
                field_name = column_name.strip().lower()
                if field_name.startswith("daily_price[pricelist="):
                    _logger.info(f"ProSync [DAILY_PRICE] Row {row_index} — dispatching column '{column_name}' value='{row[col_idx]}'")
                    update_with_daily_price_context(
                        product, column_name, row[col_idx],
                        self.database, row_index, col_idx,
                        self.updated_items, self.warning_items,
                    )

        end_time = datetime.now()

        if not self.updated_items and not self.warning_items and not self.error_items:
            _logger.info("ProSync: No changes detected. Deleting rental daily price sync report.")
            report_id.unlink()
        else:
            report_id.write({
                'end_time': end_time,
                'report_text': "\n".join(self.updated_items) or "No changes detected.",
                'warning_text': "\n".join(self.warning_items) or "No warnings to display.",
                'error_text': "\n".join(self.error_items) or "No errors to display.",
                'status': 'failure' if self.error_items else 'warning' if self.warning_items else 'success',
            })
            _logger.info(f"ProSync: Rental daily price sync report saved ({len(self.updated_items)} changes, {len(self.warning_items)} warnings).")
