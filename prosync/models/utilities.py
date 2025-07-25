# -*- coding: utf-8 -*-
import re
import json
import base64
import requests
from datetime import datetime
import dateutil.parser
import unicodedata

from odoo import fields

import logging
_logger = logging.getLogger(__name__)

# 
# Normalize char data
#
def normalize_char(value):
    if isinstance(value, str):
        value = unicodedata.normalize('NFKC', value)  # Normalize form
        value = ''.join(c for c in value if unicodedata.category(c)[0] != 'C')  # Remove control characters
        value = value.strip()
    if value is None:
        return ''
    return str(value).strip()

# 
# Normalize text data
#
def normalize_text(value):
    if value is None:
        return ''
    return str(value).strip()

# 
# Normalize float data
#
def normalize_float(value):
    if value is None or str(value).strip() == '':
        return 0.0
    try:
        return float(re.sub(r'[^\d\.-]', '', str(value)))
    except ValueError:
        return 0.0

# 
# Normalize integer data
#
def normalize_integer(value):
    if value is None or str(value).strip() == '':
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0

# 
# Normalize boolean data
#
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

# 
# Normalize date data
#
def normalize_date(value, field_type='date'):
    s = str(value).strip()
    if not s or s.lower() == 'false':
        return None
    try:
        dt = dateutil.parser.parse(s, dayfirst=True, fuzzy=True)
        return dt if field_type == 'datetime' else dt.date()
    except (ValueError, TypeError):
        return None


# 
# Normalize binary data
#
def normalize_binary(value):
    if not value or not str(value).strip():
        return False
        
    if value in [None, False, 'False', '', 'none', 'None']:
        return False

    url = str(value).strip()
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return base64.b64encode(response.content)
        else:
            _logger.warning(f"ProSync: Failed to fetch image from {url} — Status {response.status_code}")
    except Exception as e:
        _logger.warning(f"ProSync: Exception fetching image from {url}: {str(e)}")
    
    return False

# 
# Normalize selection data
#
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

# 
# Update a product field with language context
#
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

    field_info = all_fields[base_field]
    if not field_info.get('translate', False):
        _logger.warning(f"ProSync: Field '{base_field}' does not support translation (cell {cell_ref})")
        return

    lang_exists = env['res.lang'].sudo().search([('code', '=', lang_code)], limit=1)
    if not lang_exists:
        _logger.warning(f"ProSync: Language '{lang_code}' not installed. Skipping cell {cell_ref}")
        return

    field_type = field_info['type']
    normalized_value = None

    try:
        if field_type == 'char':
            normalized_value = normalize_char(value)
        elif field_type == 'text':
            normalized_value = normalize_text(value)
        elif field_type in ('float', 'monetary'):
            normalized_value = normalize_float(value)
        elif field_type == 'integer':
            normalized_value = normalize_integer(value)
        elif field_type == 'boolean':
            normalized_value = normalize_bool(value)
        elif field_type in ('date', 'datetime'):
            normalized_value = normalize_date(value)
        elif field_type == 'binary':
            normalized_value = normalize_binary(value)
        elif field_type == 'selection':
            normalized_value = normalize_selection(value, base_field, all_fields)
        elif field_type == 'many2one':
            normalized_value = normalize_many2one(value, base_field, all_fields, env)
            if normalized_value == 'not_found':
                _logger.warning(f"ProSync: Could not find many2one value for '{base_field}' at cell {cell_ref}")
                return
        elif field_type == 'many2many':
            normalized_value = normalize_many2many(value, base_field, all_fields, env)
        else:
            _logger.warning(f"ProSync: Unsupported field type '{field_type}' for '{base_field}' at cell {cell_ref}")
            return
    except Exception as e:
        _logger.error(f"ProSync: Normalization error at cell {cell_ref} ({base_field}): {e}")
        return

    try:
        product.with_context(lang=lang_code).sudo().write({base_field: normalized_value})
        _logger.info(f"ProSync: Updated translation of '{base_field}' for lang '{lang_code}' at cell {cell_ref}")
    except Exception as e:
        _logger.error(f"ProSync: Error updating translated field '{base_field}' at cell {cell_ref}: {e}")

# 
# Update a product's pricing rules and handle storage of past pricing rules
# 
def update_with_price_context(product, column_name, value, env, row_index, col_index):
    cell_ref = f"{row_index + 1}{chr(col_index + 65)}"

    match = re.match(r'^price\[pricelist=(.+?)\]$', column_name.strip().lower())
    if not match:
        _logger.warning(f"ProSync: Invalid pricelist field format at cell {cell_ref}: {column_name}")
        return

    currency_code = match.group(1).upper()

    currency_flag_map = {
        "USD": "🇺🇸",
        "CAD": "🇨🇦"
    }

    company_map = {
        "USD": "R-E-A-L.iT U.S. Inc.",
        "CAD": "R-E-A-L.iT Solutions"
    }

    company_name = company_map.get(currency_code)
    if not company_name:
        _logger.warning(f"ProSync: No company mapping defined for currency '{currency_code}'")
        return

    company = env["res.company"].search([("name", "=", company_name)], limit=1)
    if not company:
        _logger.warning(f"ProSync: Company '{company_name}' not found in system for currency '{currency_code}'")
        return

    pricelist_name = currency_flag_map.get(currency_code)
    if not pricelist_name:
        _logger.warning(f"ProSync: Unsupported or unmapped currency '{currency_code}' at cell {cell_ref}")
        return

    pricelist_model = env["product.pricelist"]
    priceitem_model = env["product.pricelist.item"]
    currency_model = env["res.currency"]

    currency = currency_model.search([("name", "=", currency_code)], limit=1)
    if not currency:
        _logger.warning(f"ProSync: Currency '{currency_code}' not found in system (cell {cell_ref})")
        return

    main_pricelist = pricelist_model.search([
        ("name", "=", pricelist_name),
        ("currency_id", "=", currency.id),
        ("active", "=", True),
    ], limit=1)

    if not main_pricelist:
        _logger.warning(f"ProSync: Main pricelist for '{currency_code}' not found (cell {cell_ref})")
        return

    try:
        new_price = float(value)
    except (ValueError, TypeError):
        _logger.warning(f"ProSync: Invalid price value '{value}' at cell {cell_ref}")
        return

    existing_main_item = priceitem_model.search([
        ("pricelist_id", "=", main_pricelist.id),
        ("applied_on", "=", "1_product"),
        ("product_tmpl_id", "=", product.id)
    ], limit=1)

    today_str = fields.Date.today().strftime("%Y-%m-%d")
    today_pricelist = pricelist_model.search([
        ("name", "=", today_str),
        ("currency_id", "=", currency.id),
        ("active", "=", True),
    ], limit=1)

    if not today_pricelist:
        today_pricelist = pricelist_model.create({
            "name": today_str,
            "currency_id": currency.id,
            "active": True,
            "company_id": company.id,
        })
        _logger.info(f"ProSync: Created new dated pricelist '{today_str}' (cell {cell_ref})")

    if existing_main_item:
        existing_main_item.write({"fixed_price": new_price})
        _logger.info(f"ProSync: Updated main pricelist '{main_pricelist.name}' for product {product.name} with new price {new_price} (cell {cell_ref})")

        existing_today_item = priceitem_model.search([
            ("pricelist_id", "=", today_pricelist.id),
            ("applied_on", "=", "1_product"),
            ("product_tmpl_id", "=", product.id)
        ], limit=1)

        if existing_today_item:
            existing_today_item.write({"fixed_price": new_price})
            _logger.info(f"ProSync: Updated today's pricelist '{today_str}' for product {product.name} (cell {cell_ref})")
        else:
            priceitem_model.create({
                "pricelist_id": today_pricelist.id,
                "applied_on": "1_product",
                "product_tmpl_id": product.id,
                "fixed_price": new_price,
                "company_id": company.id,
            })
            _logger.info(f"ProSync: Created new price rule in today's pricelist for product {product.name} (cell {cell_ref})")
    else:
        priceitem_model.create({
            "pricelist_id": main_pricelist.id,
            "applied_on": "1_product",
            "product_tmpl_id": product.id,
            "fixed_price": new_price,
            "company_id": company.id,
        })
        _logger.info(f"ProSync: Created new main pricelist rule for product {product.name} (cell {cell_ref})")

        priceitem_model.create({
            "pricelist_id": today_pricelist.id,
            "applied_on": "1_product",
            "product_tmpl_id": product.id,
            "fixed_price": new_price,
            "company_id": company.id,
        })
        _logger.info(f"ProSync: Created new price rule in today's pricelist for product {product.name} (cell {cell_ref})")

# 
# Update a many2one, many2many, or one2many field using a specified search
# 
def update_with_related_context(record, column_name, raw_value, all_fields, database, row_index, col_idx):
    try:
        # Step 1: Parse field name and parameter
        field_name, param_part = column_name.strip().split('[', 1)
        field_name = field_name.strip().lower()
        param_content = param_part.strip(']')

        if not param_content.startswith("related="):
            raise ValueError("Missing or malformed [related=...] parameter")

        related_field = param_content.split('=', 1)[1].strip()

        # Step 2: Validate base field
        if field_name not in all_fields:
            _logger.warning(f"ProSync: Row {row_index} — Field '{field_name}' not found on model. Skipping.")
            return

        field_info = all_fields[field_name]
        field_type = field_info['type']

        if field_type not in {'many2one', 'many2many'}:
            _logger.warning(f"ProSync: Row {row_index} — Field '{field_name}' is not a relation field. Skipping.")
            return

        related_model_name = field_info.get('relation')
        if not related_model_name:
            _logger.warning(f"ProSync: Row {row_index} — No relation model found for field '{field_name}'. Skipping.")
            return

        # Step 3: Search in related model
        related_model = database[related_model_name]
        search_domain = [(related_field, '=', raw_value.strip())]

        if field_type == 'many2one':
            match = related_model.search(search_domain, limit=1)
            if match:
                try:
                    record.write({field_name: match.id})
                except Exception as e:
                    _logger.error(f"ProSync: Row {row_index} — Error updating many2one field '{field_name}' with value '{raw_value}: {str(e)}'")
            else:
                _logger.warning(f"ProSync: Row {row_index} — No match found in {related_model_name} for {related_field} = '{raw_value}'")

        elif field_type == 'many2many':
            values = [v.strip() for v in raw_value.split(',') if v.strip()]
            ids = []
            for val in values:
                match = related_model.search([(related_field, '=', val)], limit=1)
                if match:
                    ids.append(match.id)
                else:
                    _logger.warning(f"ProSync: Row {row_index} — No match found in {related_model_name} for many2many value '{val}'")
            if ids:
                record.write({field_name: [(6, 0, ids)]})

    except Exception as e:
        col_letter = chr(65 + col_idx)
        cell_id = f"{row_index}{col_letter}"
        _logger.error(f"ProSync: Error updating field '{column_name}' at cell {cell_id}: {str(e)}")

# 
# Handle special exceptions usually for one2many fields which can't be directly supported by the sync
# Currently only used for updating vendor prices
# 
def update_with_special_context(product, column_name, raw_value, database, row_index, col_idx, updated_items):
    column_name_clean = column_name.lower().strip()
    value_str = str(raw_value).strip()
    if not value_str or value_str.lower() == "false":
        return  # Treat empty/false as no update needed

    col_letter = chr(65 + col_idx)
    cell_id = f"{row_index}{col_letter}"

    # MRP BOM products special handling
    if "[special=products]" in column_name_clean:
        try:
            # Parse JSON-style string
            parsed_products = json.loads(value_str)
            if not isinstance(parsed_products, list):
                raise ValueError("Parsed value is not a list of products")

            # Delete existing BOM lines
            product.bom_line_ids.unlink()

            created_lines = []
            for entry in parsed_products:
                sku = entry.get("product_id", "").strip()
                qty = entry.get("product_qty", "").strip()
                uom_name = entry.get("product_uom_id", "").strip()

                if not sku or not qty or not uom_name:
                    continue  # skip incomplete entries

                product_id = database['product.product'].search([('sku', '=', sku)], limit=1)
                if not product_id:
                    _logger.warning(f"ProSync: Row {row_index} — Could not find product with SKU '{sku}'")
                    continue

                uom = database['uom.uom'].search([('name', '=', uom_name)], limit=1)
                if not uom:
                    _logger.warning(f"ProSync: Row {row_index} — Could not find UOM '{uom_name}'")
                    continue

                line_vals = {
                    'product_id': product_id.id,
                    'product_qty': float(qty),
                    'product_uom_id': uom.id,
                    'bom_id': product.id,
                }
                created_lines.append(line_vals)

            if created_lines:
                database['mrp.bom.line'].create(created_lines)
                updated_items.append(
                    f"<b>{cell_id}</b>, {product.product_tmpl_id.name}<br/>"
                    f"Updated <u>{len(created_lines)}</u> BOM lines.<br/><br/>"
                )
                _logger.info(f"ProSync: Row {row_index} — Updated {len(created_lines)} BOM lines.")

        except Exception as e:
            _logger.warning(f"ProSync: Row {row_index} — Error parsing [special=products]: {str(e)}")
        return

    # Purchase vendor pricing logic (default)
    if "[special=purchase_cad]" in column_name_clean:
        currency_code = "CAD"
        vendor_name = "Leica Geosystems Ltd."
        company_name = "R-E-A-L.iT"
    elif "[special=purchase_usd]" in column_name_clean:
        currency_code = "USD"
        vendor_name = "Leica Geosystems Inc"
        company_name = "R-E-A-L.iT"
    else:
        _logger.warning(f"ProSync: Row {row_index} — Unrecognized special column '{column_name_clean}'. Skipping.")
        return

    # Parse price
    try:
        price = float(value_str)
    except ValueError:
        _logger.warning(f"ProSync: Row {row_index} — Invalid price '{value_str}' in {column_name_clean}. Skipping.")
        return

    # Look up related records
    currency = database['res.currency'].search([('name', '=', currency_code)], limit=1)
    partner = database['res.partner'].search([('name', '=', vendor_name), ('is_company', '=', True)], limit=1)
    company = database['res.company'].search([('name', '=', company_name)], limit=1)

    if not (currency and partner and company):
        _logger.warning(f"ProSync: Row {row_index} — Missing currency, partner, or company for {column_name_clean}.")
        return

    supplier_info = database['product.supplierinfo'].sudo().search([
        ('product_tmpl_id', '=', product.id),
        ('partner_id', '=', partner.id),
        ('currency_id', '=', currency.id),
    ], limit=1)

    if supplier_info:
        if supplier_info.price != price:
            supplier_info.sudo().write({'price': price})
            _logger.info("Updated %s price for Product %s to %.2f %s", partner.name, product.id, price, currency.name)
            updated_items.append(
                f"<b>{cell_id}</b>, {product.sku}<br/>"
                f"Updated vendor <u>{partner.name}</u> price: {price:.2f} {currency.name}<br/><br/>"
            )
        else:
            _logger.info("No change to %s price for Product %s (still %.2f)", partner.name, product.id, price)
    else:
        database['product.supplierinfo'].with_company(company.id).sudo().create({
            'partner_id': partner.id,
            'currency_id': currency.id,
            'price': price,
            'product_tmpl_id': product.id,
            'company_id': company.id,
        })
        _logger.info("Created vendor price for %s on Product %s: %.2f %s", partner.name, product.id, price, currency.name)
        updated_items.append(
            f"<b>{cell_id}</b>, {product.sku}<br/>"
            f"Created vendor <u>{partner.name}</u> price: {price:.2f} {currency.name}<br/><br/>"
        )