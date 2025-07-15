# -*- coding: utf-8 -*-
import re
import base64
import requests
from datetime import datetime
import dateutil.parser

import logging
_logger = logging.getLogger(__name__)

# 1. Add to report function

# 2. Throw error function

# 3. Normalization functions

def normalize_char(value):
    if value is None:
        return ''
    return str(value).strip()

def normalize_text(value):
    if value is None:
        return ''
    return str(value).strip()

def normalize_float(value):
    if value is None or str(value).strip() == '':
        return 0.0
    try:
        return float(re.sub(r'[^\d\.-]', '', str(value)))
    except ValueError:
        return 0.0

def normalize_integer(value):
    if value is None or str(value).strip() == '':
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0

def normalize_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False

    str_val = str(value).strip().lower()
    truthy = {'true', '1', 'yes', 'y', '✓', 'on'}
    falsy = {'false', '0', 'no', 'n', '✗', 'off'}

    if str_val in truthy:
        return True
    if str_val in falsy:
        return False
    return False

def normalize_date(value):
    if not value or not str(value).strip():
        return None
    try:
        # assuming canadian dating convention
        return dateutil.parser.parse(str(value), dayfirst=True, fuzzy=True)
    except (ValueError, TypeError):
        return None

def normalize_binary(value):
    if not value or not str(value).strip():
        return None

    url = str(value).strip()
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return base64.b64encode(response.content)
        else:
            _logger.warning(f"ProSync: Failed to fetch image from {url} — Status {response.status_code}")
    except Exception as e:
        _logger.warning(f"ProSync: Exception fetching image from {url}: {str(e)}")
    
    return None

def normalize_selection(value, field_name, model_fields):
    if not value or not str(value).strip():
        return None

    value_clean = str(value).strip().lower()
    field_info = model_fields.get(field_name)

    if not field_info or field_info['type'] != 'selection':
        return None

    # Extract selection options as (technical_value, label) pairs
    options = field_info.get('selection', [])

    # Try to match directly to technical value
    for tech_value, _ in options:
        if value_clean == str(tech_value).strip().lower():
            return tech_value

    # Try to match by label (case-insensitive)
    for tech_value, label in options:
        if value_clean == str(label).strip().lower():
            return tech_value

    return None

def normalize_many2one(value, field_name, model_fields, env):
    if value is None or str(value).strip() == "":
        return None

    value_clean = str(value).strip()
    field_info = model_fields.get(field_name)

    if not field_info or field_info['type'] != 'many2one':
        return None

    related_model = field_info.get('relation')
    if not related_model:
        return None

    match = env[related_model].search([('name', '=', value_clean)], limit=1)
    if match:
        return match.id

    _logger.warning(f"ProSync: Many2one match not found for '{value_clean}' in field '{field_name}'")
    return 'not_found'

def normalize_many2many(value, field_name, model_fields, env):
    if not value or not str(value).strip():
        return []

    field_info = model_fields.get(field_name)
    if not field_info or field_info['type'] != 'many2many':
        return []

    related_model = field_info.get('relation')
    if not related_model:
        return []

    # Split values by comma and space
    values = [v.strip() for v in value.split(',')]
    ids = []
    for val in values:
        if val:
            match = env[related_model].search([('name', '=', val)], limit=1)
            if match:
                ids.append(match.id)
            else:
                _logger.warning(f"ProSync: Many2many match not found for '{val}' in field '{field_name}'")

    return [(6, 0, ids)] if ids else []

def update_with_lang_context(product, column_name, value, all_fields, env, row_index, col_index):

    cell_ref = f"{row_index + 1}{chr(col_index + 65)}"
    _logger = logging.getLogger(__name__)

    lang_match = re.match(r"^(.+?)\[language=(.+?)\]$", column_name)
    if not lang_match:
        _logger.warning(f"ProSync: Invalid translation format at cell {cell_ref}")
        return

    base_field = lang_match.group(1)
    lang_code = lang_match.group(2)

    if base_field not in all_fields:
        _logger.warning(f"ProSync: Unknown field '{base_field}' at cell {cell_ref}")
        return

    if not all_fields[base_field].get('translate', False):
        _logger.warning(f"ProSync: Field '{base_field}' does not support translation (cell {cell_ref})")
        return

    lang_exists = env['res.lang'].sudo().search([('code', '=', lang_code)], limit=1)
    if not lang_exists:
        _logger.warning(f"ProSync: Language '{lang_code}' not installed. Skipping cell {cell_ref}")
        return

    field_type = all_fields[base_field]['type']
    normalized_value = normalize_field_by_type(field_type, value, base_field, all_fields, env)

    if normalized_value is None or normalized_value == MANY2ONE_NOT_FOUND:
        _logger.warning(f"ProSync: Could not normalize value at cell {cell_ref}")
        return

    try:
        product.with_context(lang=lang_code).sudo().write({base_field: normalized_value})
        _logger.info(f"ProSync: Updated translation of '{base_field}' for lang '{lang_code}' at cell {cell_ref}")
    except Exception as e:
        _logger.error(f"ProSync: Error updating translated field '{base_field}' at cell {cell_ref}: {e}")
