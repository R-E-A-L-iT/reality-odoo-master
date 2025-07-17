# -*- coding: utf-8 -*-
import logging

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
    update_with_related_context,
)

_logger = logging.getLogger(__name__)

class res_partner_sync:

    def __init__(self, name, sheet, database):
        self.name = name
        self.sheet = sheet
        self.database = database
        self.updated_items = []
        self.warning_items = []
        self.error_items = []
        self.report_id = None

    def sync_res_partner(self):
        _logger.info("ProSync: Starting RES_PARTNER sync process.")

        self.report_id = self.database['prosync.report'].create({
            'name': f"Contact Sync: {self.name}",
            'status': 'success',
            'sync_type': 'res_partner',
            'start_time': datetime.now(),
        })

        required_fields = ["name", "valid", "continue"]
        sheet_columns = self.sheet[0] if self.sheet else []
        column_indices = {col.strip().lower(): idx for idx, col in enumerate(sheet_columns)}

        missing_columns = [header for header in required_fields if header not in sheet_columns]
        if missing_columns:
            _logger.error(f"ProSync: Sheet validation failed. Missing columns for fields: {missing_columns}")
            self.error_items.append(f"ProSync: Sheet validation failed. Missing columns for fields: {missing_columns}<br/><br/>")
            return

        partner_model = self.database['res.partner']
        all_fields = partner_model.fields_get().keys()
        allowed_special_fields = {"valid", "continue"}

        for column in sheet_columns:
            base_field = column.strip().split('[')[0]
            if base_field in allowed_special_fields:
                _logger.info(f"ProSync: Special field '{column}' is accepted.")
                continue
            if base_field in all_fields:
                _logger.info(f"ProSync: Field '{column}' (base: '{base_field}') exists on res.partner.")
            else:
                _logger.warning(f"ProSync: Field '{column}' (base: '{base_field}') does NOT exist on res.partner.")
                self.warning_items.append(
                    f"ProSync: Field '{column}' (base: '{base_field}') does NOT exist on res.partner.<br/><br/>"
                )

        for row_index, row in enumerate(self.sheet[1:], start=2):
            if not any(row):
                _logger.info(f"ProSync: Skipping empty row {row_index}")
                continue

            is_valid = normalize_bool(row[column_indices.get("valid", -1)])
            should_continue = normalize_bool(row[column_indices.get("continue", -1)])

            if not is_valid:
                if should_continue:
                    _logger.info(f"ProSync: Skipping row {row_index} (VALID is False, CONTINUE is True)")
                    continue
                else:
                    _logger.info(f"ProSync: Ending sync at row {row_index} (VALID is False, CONTINUE is False)")
                    break

            name = normalize_char(row[column_indices.get("name", -1)])
            if not name:
                _logger.warning(f"ProSync: Row {row_index} missing Name. Skipping.")
                self.warning_items.append(
                    f"ProSync: Row {row_index} missing Name. Skipping.<br/><br/>"
                )
                continue

            partner = partner_model.search([('name', '=', name)], limit=1)
            if partner:
                _logger.info(f"ProSync: Row {row_index} — Found partner '{name}' (ID: {partner.id})")
                self.update_res_partner(partner, row_index, row, column_indices)
            else:
                _logger.info(f"ProSync: Row {row_index} — No partner found. Creating new partner '{name}'")
                self.create_res_partner(row_index, row)

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


    def create_res_partner(self, row_index, row):
        name = normalize_char(row[self.sheet[0].index("name")])
        partner = self.database['res.partner'].create({"name": name})
        
        _logger.info(f"ProSync: Row {row_index} — Created new res.partner '{name}' (ID: {partner.id})")
        self.update_res_partner(partner, row_index, row, {col.strip().lower(): i for i, col in enumerate(self.sheet[0])})

    def update_res_partner(self, partner, row_index, row, column_indices):
        all_fields = self.database['res.partner'].fields_get()

        for col_idx, column_name in enumerate(self.sheet[0]):
            field = column_name.strip().lower()
            if field in {"name", "valid", "continue"}:
                continue

            raw_value = row[col_idx]
            if "[language=" in column_name:
                update_with_lang_context(partner, column_name, raw_value, all_fields, self.database, row_index, col_idx)
                continue
            if "[related=" in column_name:
                update_with_related_context(partner, column_name, raw_value, all_fields, self.database, row_index, col_idx)
                continue
            if "[" in column_name:
                continue

            base_field = field.split('[')[0]
            if base_field not in all_fields:
                continue

            field_type = all_fields[base_field]['type']
            try:
                if field_type == 'char':
                    value = normalize_char(raw_value)
                elif field_type == 'text':
                    value = normalize_text(raw_value)
                elif field_type in {'float', 'monetary'}:
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
                    _logger.warning(f"ProSync: Row {row_index} — Unsupported field type '{field_type}' for '{base_field}'")
                    self.warning_items.append(
                        f"ProSync: Row {row_index} — Unsupported field type '{field_type}' for '{base_field}'<br/><br/>"
                    )
                    continue

                partner.write({base_field: value})

                col_letter = chr(65 + col_idx)
                cell_id = f"{row_index}{col_letter}"
                self.updated_items.append(
                    f"<b>{cell_id}</b>, {partner.name}<br/>"
                    f"Field <u>{base_field}</u> updated to: \"{value}\"<br/><br/>"
                )

            except Exception as e:
                col_letter = chr(65 + col_idx)
                _logger.error(f"ProSync: Error at cell {row_index}{col_letter} updating field '{base_field}': {str(e)}")
                self.error_items.append(
                    f"Error at cell {row_index}{col_letter} updating field '{base_field}': {str(e)}<br/>"
                )
