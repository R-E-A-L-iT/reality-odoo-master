
# -*- coding: utf-8 -*-

import re
import logging

from ..utilities import (
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
    update_with_lang_context,
    update_with_related_context,
)

_logger = logging.getLogger(__name__)


class stock_lot_sync:

    def __init__(self, name, sheet, database):
        self.name = name
        self.sheet = sheet
        self.database = database

    def sync_stock_lot(self):
        _logger.info("ProSync: Starting STOCK_LOT sync process.")

        required_fields = [
            "name",
            "product_id",
            "valid",
            "continue",
        ]

        sheet_columns = self.sheet[0] if len(self.sheet) > 0 else []
        column_indices = {col.strip().lower(): idx for idx, col in enumerate(sheet_columns)}

        missing_columns = [header for header in required_fields if header not in sheet_columns]
        if missing_columns:
            _logger.error(f"ProSync: Sheet validation failed. Missing columns for fields: {missing_columns}.")
            return

        stock_lot_model = self.database['stock.lot']
        all_fields = stock_lot_model.fields_get().keys()
        allowed_special_fields = {"valid", "continue"}

        for column in sheet_columns:
            column_cleaned = column.strip().lower()
            if column_cleaned in allowed_special_fields:
                _logger.info(f"ProSync: Special field '{column}' is accepted.")
                continue
            base_field = column_cleaned.split("[")[0]
            if base_field in all_fields:
                _logger.info(f"ProSync: Field '{column}' (base: '{base_field}') exists on stock.lot.")
            else:
                _logger.warning(f"ProSync: Field '{column}' (base: '{base_field}') does NOT exist on stock.lot.")

        for row_index, row in enumerate(self.sheet[1:], start=2):
            if not any(row):
                _logger.info(f"ProSync: Skipping empty row {row_index}")
                continue

            valid_raw = row[column_indices.get("valid", -1)]
            continue_raw = row[column_indices.get("continue", -1)]
            is_valid = normalize_bool(valid_raw)
            should_continue = normalize_bool(continue_raw)

            if not is_valid:
                if should_continue:
                    _logger.info(f"ProSync: Skipping row {row_index} (VALID is False, CONTINUE is True)")
                    continue
                else:
                    _logger.info(f"ProSync: Ending sheet sync at row {row_index} (VALID is False, CONTINUE is False)")
                    break

            name = normalize_char(row[column_indices.get("name", -1)])
            product_sku = normalize_char(row[column_indices.get("product_id", -1)])
            if not name or not product_sku:
                _logger.warning(f"ProSync: Row {row_index} is missing a valid Name or Product SKU. Skipping.")
                continue

            product = self.database['product.product'].search([('sku', '=', product_sku)], limit=1)
            if not product:
                _logger.warning(f"ProSync: Row {row_index} — No product found with SKU: {product_sku}. Skipping.")
                continue

            lot = self.database['stock.lot'].search([
                ('name', '=', name),
                ('product_id', '=', product.id)
            ], limit=1)

            if lot:
                _logger.info(f"ProSync: Row {row_index} — Found stock.lot with Name: {name} and Product SKU: {product_sku} (ID: {lot.id})")
                self.update_stock_lot(lot, row_index, row, column_indices)
            else:
                _logger.info(f"ProSync: Row {row_index} — No stock.lot found with Name: {name} and Product SKU: {product_sku}")
                self.create_stock_lot(row_index, row, product)

    def create_stock_lot(self, row_index, row, product):
        column_indices = {col.strip().lower(): idx for idx, col in enumerate(self.sheet[0])}
        name = normalize_char(row[column_indices.get("name", -1)])

        if not name:
            _logger.warning(f"ProSync: Row {row_index} — Cannot create stock.lot without valid Name. Skipping.")
            return

        stock_lot = self.database['stock.lot'].create({
            "name": name,
            "product_id": product.id,
        })

        if not stock_lot or not stock_lot.id:
            _logger.warning(f"ProSync: Row {row_index} — Failed to create stock.lot for Name: {name}")
            return

        _logger.info(f"ProSync: Row {row_index} — Created new stock.lot with Name: {name}, ID: {stock_lot.id}")
        self.update_stock_lot(stock_lot, row_index, row, column_indices)

    def update_stock_lot(self, lot, row_index, row, column_indices):
        stock_lot_model = self.database['stock.lot']
        all_fields = stock_lot_model.fields_get()

        for col_idx, column_name in enumerate(self.sheet[0]):
            field_name = column_name.strip().lower()

            # Never update name or product_id since they are part of the unique identifier
            if field_name in {'name', 'product_id', 'valid', 'continue'}:
                continue

            raw_value = row[col_idx]
            if "[language=" in column_name:
                update_with_lang_context(product, column_name, raw_value, all_fields, self.database, row_index, col_idx)
                continue
            elif "[related=" in column_name:
                update_with_related_context(record, column_name, raw_value, all_fields, self.database, row_index, col_idx)
                continue
            elif '[' in field_name:
                continue

            base_field = field_name.split('[')[0]
            if base_field not in all_fields:
                continue

            field_type = all_fields[base_field]['type']
            try:
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
                # elif field_type == 'many2one':
                #     value = normalize_many2one(raw_value, base_field, all_fields, self.database)
                #     if value == 'not_found':
                #         continue
                # elif field_type == 'many2many':
                #     value = normalize_many2many(raw_value, base_field, all_fields, self.database)
                else:
                    _logger.warning(f"ProSync: Row {row_index} — Field '{base_field}' has unsupported type '{field_type}'. Skipping.")
                    continue

                lot.write({base_field: value})

            except Exception as e:
                col_letter = chr(65 + col_idx)
                cell_id = f"{row_index}{col_letter}"
                _logger.error(f"ProSync: Error updating field '{base_field}' at cell {cell_id}: {str(e)}")
