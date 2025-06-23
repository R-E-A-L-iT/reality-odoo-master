# -*- coding: utf-8 -*-

import base64
import requests

from .utilities import utilities
from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo.tools.translate import _
from odoo import models

from .product_common import product_sync_common

_logger = logging.getLogger(__name__)

class sync_pricelist:

    def __init__(self, name, sheet, database):
        self.name = name
        self.sheet = sheet
        self.database = database
        self.sync_report = []



    # utility function
    # in odoo, booleans are "True" or "False"
    # in sheets, booleans are "TRUE" or "FALSE"
    # this function normalizes those values
    def normalize_bools(self, value):
        if value.strip().upper() in ["TRUE", "1"]:
            return True
        elif value.strip().upper() in ["FALSE", "0", ""]:
            return False

        return value.strip()



    # add error to sync report function
    # sync report sent on sync end
    def add_to_report(self, level, message):
        entry = f"{level.upper()}: {message}"
        self.sync_report.append(entry)



    # this function will be called to start the synchronization process for pricelists.
    # it delegates the function of actually updating or creating the product item to the other two functions
    def syncPricelist(self):
        _logger.info("syncPricelist: Starting synchronization process for pricelist")

        # variables for sync report
        items_updated = []
        overall_status = "success"

        # variables to verify format
        # if you need to add more columns for new sync data, add them here
        expected_columns = {
            "SKU": "sku",
            "EN-Name": "name_en",
            "EN-Description": "desc_en",
            "FR-Name": "name_fr",
            "FR-Description": "desc_fr",
            "PriceCAD": "price_cad",
            "PriceUSD": "price_usd",
            "Can Rental": "rental_can",
            "US Rental": "rental_usd",
            "Store Image": "store_image",
            "Store Title": "store_title",
            "Store Description": "store_desc",
            "Publish_CA": "publish_can",
            "Publish_USA": "publish_usa",
            "Can_Be_Sold": "can_be_sold",
            "Can_Be_Rented": "can_be_rented",
            "isSoftware": "is_software",
            "Type": "type",
            "ProductCategory": "category",
            "Product Type": "product_type",
            "ECOM-FOLDER": "folder",
            "ECOM-MEDIA": "media",
            "Valid": "valid",
            "Continue": "continue",
        }
        expected_width = len(expected_columns)

        # columns that will not trigger sync validation failure regardless of whether they are present or not
        ignored_columns = [
            "DEALER DISCOUNT",
            "Barcode",
            "Purchase Price CAD",
            "Purchase Price USD",
        ]

        sheet_columns = self.sheet[0] if len(self.sheet) > 0 else []
        sheet_width = len(sheet_columns)
        
        # variables that will contain a list of any missing or extra columns in the sheet
        missing_columns = [header for header in expected_columns.keys() if header not in sheet_columns]
        extra_columns = [header for header in sheet_columns if header not in expected_columns and header not in ignored_columns]
        
        # initialize list of warnings/errors for report
        sync_report = []
        
        # verify that sheet format is as expected
        if sheet_width < expected_width or missing_columns or extra_columns:
            error_msg = f"Sheet validation failed. Missing: {missing_columns}, Extra: {extra_columns}."
            _logger.error(f"syncPricelist: {error_msg}")
            self.add_to_report("ERROR", error_msg)
            return {"status": "error", "sync_report": self.sync_report, "items_updated": items_updated}

        _logger.info("syncPricelist: Sheet validated. Proceeding with Pricelist synchronization.")

        # start processing rows beginning at second row
        for row_index, row in enumerate(self.sheet[1:], start=2):
            try:
                
                # only proceed if the value for continue is marked as true
                continue_column = sheet_columns.index("Continue")
                should_continue = str(row[continue_column]).strip().lower() == "true"

                if not should_continue:
                    _logger.info("syncPricelist: Row %d: Continue is set to false. Stopping the sync here.", row_index)
                    break
                
                
                # only proceed if the row is marked as valid
                valid_column = sheet_columns.index("Valid")
                valid = str(row[valid_column]).strip().lower() == "true"

                if not valid:
                    # _logger.info("syncPricelist: Row %d: Marked as invalid. Skipping.", row_index)
                    continue
    
                
                # get eid/sn and check if it exists in odoo
                sku_column = sheet_columns.index("SKU")
                sku = str(row[sku_column]).strip()

                if not sku:
                    self.add_to_report("WARNING", f"Row {row_index}: Missing SKU. Skipping.")
                    continue
                
                existing_product = self.database.env["product.template"].search([("sku", "=", sku)], limit=1)
                
                if existing_product:
                    # _logger.info("syncPricelist: Row %d: SKU '%s' found in Odoo. Calling updateProduct.", row_index, sku)
                    update_report = self.updateProduct(existing_product.id, row, sheet_columns, row_index)
                    items_updated.append(
                        f"Updated Product: {sku}, Fields Updated: {', '.join(update_report or [])}"
                    )
                else:
                    # _logger.info("syncPricelist: Row %d: SKU '%s' not found in Odoo. Calling createProduct.", row_index, sku)
                    self.createProduct(sku, row, sheet_columns, row_index)
                    items_updated.append(f"Created Product: {sku}")
            
            except Exception as e:
                error_msg = f"Row {row_index}: Error occurred while processing: {str(e)}"
                _logger.error(f"syncPricelist: {error_msg}", exc_info=True)
                self.add_to_report("ERROR", f"{error_msg}")
                overall_status = "error"
                
        # if self.sync_report:
        #     utilities.send_report(self.sync_report, "Pricelist", self.database)

        # check for any errors
        if any("ERROR" in report for report in self.sync_report):
            overall_status = "error"
        elif any("WARNING" in report for report in self.sync_report):
            overall_status = "warning"
        
        return {
            "status": overall_status,
            "sync_report": self.sync_report,
            "items_updated": items_updated,
        }


    # this function is called to update a product that already exists
    # it will attempt to update the product cell by cell, and skip updating any info that generates errors
    # fields that are not updated will be added to a report at the end
    def updateProduct(self, product_id, row, sheet_columns, row_index):
        # _logger.info("updateProduct: Searching for any changes for product: %s.", product_id)
        updated_fields = []

        try:
            
            # Check for glitched external identifier
            ext_id = self.database.env["ir.model.data"].search(
                [("model", "=", "product.template"), ("res_id", "=", product_id)], limit=1
            )
            if ext_id and ext_id.res_id == 0:
                _logger.warning(
                    "updateProduct: External ID '%s' is glitched (Record ID: %s). Deleting and fixing.",
                    ext_id.name, ext_id.res_id
                )
                ext_id.unlink()

            product = self.database.env["product.template"].browse(product_id)

            if not product.exists():
                raise ValueError(f"Product with ID {product_id} does not exist.")
            
            # map the google sheets cells to odoo fields
            field_mapping = {
                "SKU": "sku",
                "EN-Name": "name",
                "FR-Name": "name",
                "EN-Description": "description_sale",
                "FR-Description": "description_sale",
                "Store Image": "image_1920",
                "PriceCAD": "list_price",
                "PriceUSD": "list_price",
                "Can Rental": "",
                "US Rental": "",
                "Publish_CA": "publish_can",
                "Publish_USA": "publish_usa",
                "Can_Be_Sold": "can_be_sold",
                "Can_Be_Rented": "can_be_rented",
            }

            for column_name, odoo_field in field_mapping.items():
                try:
                    if column_name in sheet_columns:
                        
                        # get new sheets value
                        column_index = sheet_columns.index(column_name)
                        sheet_value = str(row[column_index]).strip()
                        sheet_value_normalized = self.normalize_bools(sheet_value.strip())

                        # update name fields for both languages
                        if column_name in ["EN-Name", "FR-Name"]:
                            
                            name = sheet_value
                            
                            # get lang and normalize odoo name
                            # this is necessary for comparison because odoo adds SKU to beginning of product name
                            lang = "en_US" if column_name == "EN-Name" else "fr_CA"
                            odoo_name = product.with_context(lang=lang).name

                            # compare normalized names and update if necessary
                            if odoo_name != name:
                                _logger.info(
                                    "updateProduct: Field 'name' (%s) changed for Product ID %s. Old Value: '%s', New Value: '%s'.",
                                    "English" if lang == "en_US" else "French", product_id, odoo_name, name
                                )
                                product.with_context(lang=lang).sudo().write({"name": name})
                                updated_fields.append(f"name ({'English' if lang == 'en_US' else 'French'})")

                            # double check translation worked
                            updated_name = product.with_context(lang=lang).name
                            if updated_name != name:
                                _logger.error(
                                    "updateProduct: Post-update mismatch for 'name' (%s) on Product ID %s. Expected: '%s', Actual: '%s'.",
                                    "English" if lang == "en_US" else "French", product_id, name, updated_name
                                )
                                self.add_to_report(
                                    "ERROR",
                                    f"Post-update mismatch for 'name' ({'English' if lang == 'en_US' else 'French'}) "
                                    f"on Product ID {product_id}. Expected: '{name}', Actual: '{updated_name}'."
                                )

                        # update description fields for both languages
                        elif column_name in ["EN-Description", "FR-Description"]:
                            
                            # extract description and update
                            lang = "en_US" if column_name == "EN-Description" else "fr_CA"
                            description = sheet_value
                            current_description = product.with_context(lang=lang).description_sale or ""
                            if current_description != description:
                                _logger.info(
                                    "updateProduct: Field 'description_sale' (%s) changed for Product ID %s. Old Value: '%s', New Value: '%s'.",
                                    "English" if lang == "en_US" else "French", product_id, current_description, description
                                )
                                product.with_context(lang=lang).sudo().write({"description_sale": description})
                                updated_fields.append(f"description_sale ({'English' if lang == 'en_US' else 'French'})")

                            # double check translation worked
                            updated_description = product.with_context(lang=lang).description_sale or ""
                            if updated_description != description:
                                _logger.error(
                                    "updateProduct: Post-update mismatch for 'description_sale' (%s) on Product ID %s. Expected: '%s', Actual: '%s'.",
                                    "English" if lang == "en_US" else "French", product_id, description, updated_description
                                )
                                self.add_to_report(
                                    "ERROR",
                                    f"Post-update mismatch for 'description_sale' ({'English' if lang == 'en_US' else 'French'}) "
                                    f"on Product ID {product_id}. Expected: '{description}', Actual: '{updated_description}'."
                                )

                        # update price fields for both pricelists
                        elif column_name in ["PriceCAD", "PriceUSD"]:
                            pricelist_name = "🇨🇦" if column_name == "PriceCAD" else "🇺🇸"
                            price = float(sheet_value) if sheet_value else 0.0

                            # default product price is set to cad
                            if pricelist_name == "🇨🇦":
                                product.list_price = price

                            # search for the pricelist
                            pricelist = self.database.env["product.pricelist"].search([("name", "=", pricelist_name)], limit=1)
                            if not pricelist:
                                _logger.error(
                                    "updateProduct: Pricelist '%s' not found for Product ID %s. Skipping price update.",
                                    pricelist_name, product_id
                                )
                                self.add_to_report(
                                    "ERROR",
                                    f"Pricelist '{pricelist_name}' not found for Product ID {product_id}. Skipping price update."
                                )
                                continue

                            # search for existing price within pricelist
                            price_rule = self.database.env["product.pricelist.item"].search([
                                ("pricelist_id", "=", pricelist.id),
                                ("product_tmpl_id", "=", product.id)
                            ], limit=1)

                            if price_rule:

                                # compare and update if necessary
                                if price_rule.fixed_price != price:
                                    _logger.info(
                                        "updateProduct: Updating price for Product ID %s on Pricelist '%s'. Old Value: '%s', New Value: '%s'.",
                                        product_id, pricelist_name, price_rule.fixed_price, price
                                    )
                                    price_rule.write({"fixed_price": price})
                                    updated_fields.append(f"price ({pricelist_name})")
                            else:

                                # add price if not already existing
                                _logger.info(
                                    "updateProduct: Creating new price rule for Product ID %s on Pricelist '%s'. Value: '%s'.",
                                    product_id, pricelist_name, price
                                )

                                applied_on = "1_product"
                                product_variant_id = None

                                self.database.env["product.pricelist.item"].sudo().create({
                                    "pricelist_id": pricelist.id,
                                    "applied_on": applied_on,
                                    "product_tmpl_id": product.id,
                                    "product_id": product_variant_id,
                                    "fixed_price": price,
                                })
                                updated_fields.append(f"new price rule ({pricelist_name})")

                        # update rental prices for both pricelists
                        elif column_name in ["Can Rental", "US Rental"]:
                            pricelist_name = "CAD RENTAL" if column_name == "Can Rental" else "USD RENTAL"
                            rental_price = float(sheet_value) if sheet_value else 0.0

                            # search for the pricelist
                            rental_pricelist = self.database.env["product.pricelist"].search([("name", "=", pricelist_name)], limit=1)
                            if not rental_pricelist:
                                _logger.error(
                                    "updateProduct: Rental pricelist '%s' not found for Product ID %s. Skipping rental price update.",
                                    pricelist_name, product_id
                                )
                                self.add_to_report(
                                    "ERROR",
                                    f"Rental pricelist '{pricelist_name}' not found for Product ID {product_id}. Skipping rental price update."
                                )
                                continue

                            # search for existing price within pricelist
                            rental_price_rule = self.database.env["product.pricelist.item"].search([
                                ("pricelist_id", "=", rental_pricelist.id),
                                ("product_tmpl_id", "=", product_id)
                            ], limit=1)

                            if rental_price_rule:

                                # compare and update if necessary
                                if rental_price_rule.fixed_price != rental_price:
                                    _logger.info(
                                        "updateProduct: Updating rental price for Product ID %s on Rental Pricelist '%s'. Old Value: '%s', New Value: '%s'.",
                                        product_id, pricelist_name, rental_price_rule.fixed_price, rental_price
                                    )
                                    rental_price_rule.write({"fixed_price": rental_price})
                                    updated_fields.append(f"rental price ({pricelist_name})")
                            else:

                                # add price if not already existing
                                _logger.info(
                                    "updateProduct: Creating new rental price rule for Product ID %s on Rental Pricelist '%s'. Value: '%s'.",
                                    product_id, pricelist_name, rental_price
                                )
                                self.database.env["product.pricelist.item"].sudo().create({
                                    "pricelist_id": rental_pricelist.id,
                                    "product_tmpl_id": product_id,
                                    "fixed_price": rental_price,
                                    "applied_on": "0_product_variant",
                                })
                                updated_fields.append(f"new rental price rule ({pricelist_name})")

                        # update published status
                        elif column_name in ["Publish_CA", "Publish_USA"]:

                            publish = self.normalize_bools(sheet_value.strip())
                            
                            if column_name == "Publish_CA":
                                product.is_ca = publish
                                product.is_published = publish

                                if product.is_ca == publish:
                                    updated_fields.append("is_ca")
                                if product.is_published == publish:
                                    updated_fields.append("is_published")

                            elif column_name == "Publish_USA":
                                product.is_us = publish

                                if product.is_us == publish:
                                    updated_fields.append("is_us")

                        # update sale and rental status
                        elif column_name in ["Can_Be_Sold", "Can_Be_Rented"]:
                            can_be_value = self.normalize_bools(sheet_value.strip())

                            if column_name == "Can_Be_Sold":
                                product.sale_ok = can_be_value
                                if product.sale_ok == can_be_value:
                                    updated_fields.append("sale_ok")

                            elif column_name == "Can_Be_Rented":
                                product.rent_ok = can_be_value
                                if product.rent_ok == can_be_value:
                                    updated_fields.append("rent_ok")
                        
                        elif column_name == "Purchase Price CAD":

                            purchase_price_cad = str(row[sheet_columns.index("Purchase Price CAD")]).strip()
                            cad_currency = self.database.env['res.currency'].search([('name', '=', 'CAD')], limit=1)
                            cad_partner = self.database.env['res.partner'].search(
                                [('name', '=', 'Leica Geosystems Ltd.'), ('is_company', '=', True)],
                                limit=1
                            )

                            if purchase_price_cad and cad_currency and cad_partner:

                                supplier_info = self.database.env['product.supplierinfo'].search([
                                    ('product_tmpl_id', '=', product.id),
                                    ('partner_id', '=', cad_partner.id),
                                    ('currency_id', '=', cad_currency.id),
                                ], limit=1)

                                if supplier_info:
                                    if supplier_info.price != purchase_price_cad:
                                        supplier_info.sudo().write({'price': purchase_price_cad})
                                        updated_fields.append(f'supplier_price_{cad_partner.name}')
                                        _logger.info("Updated %s price for Product %s to %.2f %s", cad_partner.name, product.id, purchase_price_cad, cad_currency.name)
                                    else:
                                        _logger.info("No change to %s price for Product %s (still %.2f)", cad_partner.name, product.id, purchase_price_cad)
                                else:
                                    vals = {
                                        'partner_id': cad_partner.id,
                                        'currency_id': cad_currency.id,
                                        'price': purchase_price_cad,
                                        'product_tmpl_id': product.id,
                                        # optionally set minimum_qty, sequence, delay, etc
                                    }
                                    self.database.env['product.supplierinfo'].sudo().create(vals)
                                    updated_fields.append(f'supplier_price_{cad_partner.name}')
                                    _logger.info("Created vendor price for %s on Product %s: %.2f %s", cad_partner.name, product.id, purchase_price_cad, cad_currency.name)

                        elif column_name == "Purhcase Price USD":

                            purchase_price_usd = str(row[sheet_columns.index("Purchase Price USD")]).strip()
                            usd_currency = self.database.env['res.currency'].search([('name', '=', 'USD')], limit=1)
                            usd_partner = self.database.env['res.partner'].search(
                                [('name', '=', 'Leica Geosystems Inc'), ('is_company', '=', True)],
                                limit=1
                            )

                            if purchase_price_usd and usd_currency and usd_partner:

                                supplier_info = self.database.env['product.supplierinfo'].search([
                                    ('product_tmpl_id', '=', product.id),
                                    ('partner_id', '=', usd_partner.id),
                                    ('currency_id', '=', usd_currency.id),
                                ], limit=1)

                                if supplier_info:
                                    if supplier_info.price != purchase_price_usd:
                                        supplier_info.sudo().write({'price': purchase_price_usd})
                                        updated_fields.append(f'supplier_price_{usd_partner.name}')
                                        _logger.info("Updated %s price for Product %s to %.2f %s", usd_partner.name, product.id, purchase_price_usd, usd_currency.name)
                                    else:
                                        _logger.info("No change to %s price for Product %s (still %.2f)", usd_partner.name, product.id, purchase_price_usd)
                                else:
                                    vals = {
                                        'partner_id': usd_partner.id,
                                        'currency_id': usd_currency.id,
                                        'price': purchase_price_usd,
                                        'product_tmpl_id': product.id,
                                        # optionally set minimum_qty, sequence, delay, etc
                                    }
                                    self.database.env['product.supplierinfo'].sudo().create(vals)
                                    updated_fields.append(f'supplier_price_{usd_partner.name}')
                                    _logger.info("Created vendor price for %s on Product %s: %.2f %s", usd_partner.name, product.id, purchase_price_usd, usd_currency.name)

                        elif column_name == "Barcode":

                            barcode = str(row[sheet_columns.index("Barcode")]).strip()

                            if barcode:

                                # check if barcode already exists
                                existing_barcode = self.database.env["product.template"].search([("barcode", "=", barcode)], limit=1)

                                if existing_barcode.barcode == barcode:
                                    _logger.info(
                                        "updateProduct: Barcode already set and unchanged. No update needed for Product ID %s.",
                                        barcode, product_id
                                    )
                                    # self.add_to_report("ERROR", f"Barcode '{barcode}' already exists for another product. Skipping update for Product ID {product_id}.")
                                else:
                                    product.sudo().write({"barcode": barcode})
                                    updated_fields.append("barcode")
                                    _logger.info("updateProduct: Updated barcode for Product ID %s to '%s'.", product_id, barcode)
                            
                except Exception as e:
                    _logger.error(
                        "updateProduct: Error while updating field '%s' for Product ID %s: %s",
                        odoo_field, product_id, str(e), exc_info=True
                    )
                    self.add_to_report("ERROR", f"updateProduct: Error while updating field {odoo_field} for Product ID {product_id}: {str(e)}")

        except Exception as e:
            _logger.error(
                "updateProduct: Error while updating product ID %s: %s",
                product_id, str(e), exc_info=True
            )
            self.add_to_report("ERROR", f"Error while updating product ID {product_id}: {str(e)}")



    # this function is called to create a new product if the sku is not recognized
    # it will attempt to create the product cell by cell, and skip creating any info that generates errors
    # fields that are not updated will be added to a report at the end
    def createProduct(self, product_id, row, sheet_columns, row_index):
        _logger.info("createProduct: Creating new product with SKU: %s.", product_id)


        # todo: add price rules creation for this function instead of having to run sync twice

        try:
            # Set company and default responsible user
            company_id = 1 # R-E-A-L.iT in the system
            user_id = 2 # Ezekiel deBlois in the system
            responsible_user = self.database.env["res.users"].search([("id", "=", user_id)], limit=1)
            if not responsible_user:
                raise ValueError("No valid responsible user found for company ID %s." % company_id)

            # Check for existing external ID in ir.model.data
            existing_ext_id = self.database.env["ir.model.data"].search(
                [("model", "=", "product.template"), ("name", "=", product_id)], limit=1
            )

            if existing_ext_id:
                # Check if the external ID is valid
                product = self.database.env["product.template"].browse(existing_ext_id.res_id)

                if not product.exists() or existing_ext_id.res_id == 0:
                    # External ID is glitched; clean it up
                    _logger.warning(
                        "createProduct: External ID '%s' is glitched (Record ID: %s). Deleting and fixing.",
                        product_id, existing_ext_id.res_id
                    )
                    existing_ext_id.unlink()
                else:
                    _logger.info(
                        "createProduct: External ID '%s' is valid and linked to Product ID %s. Skipping creation.",
                        product_id, existing_ext_id.res_id
                    )
                    return  # Skip creation if the external ID is valid and linked to an existing product

            # Check if the product already exists by name or SKU
            product = self.database.env["product.template"].search([("sku", "=", product_id)], limit=1)
            if product:
                _logger.info(
                    "createProduct: Product with SKU '%s' already exists as Product ID %s. Creating external ID.",
                    product_id, product.id
                )
                # Create a new external ID for the existing product
                self.database.env["ir.model.data"].sudo().create({
                    "name": product_id,
                    "model": "product.template",
                    "res_id": product.id,
                })
                return product

            # Prepare initial values for product creation
            product_values = {
                "sku": product_id,
                "sale_ok": True,
                "rent_ok": False,
                "company_id": company_id,
                "responsible_id": responsible_user.id,
                "name": "Unnamed Product %s" % product_id,  # Fallback name
                "detailed_type": 'product',
            }
            # _logger.error("[product_id] SKU: " + product_id)

            translations = {}
            field_mapping = {
                "EN-Name": ("name", "en_US"),
                "FR-Name": ("name", "fr_CA"),
                "EN-Description": ("description_sale", "en_US"),
                "FR-Description": ("description_sale", "fr_CA"),
                "PriceCAD": "list_price",
                "Store Image": "image_1920",
                "Publish_CA": "is_ca",
                "Publish_USA": "is_us",
                "Can_Be_Sold": "sale_ok",
                "Can_Be_Rented": "rent_ok",
            }

            # Loop through the columns to set product values
            for column_name, field_info in field_mapping.items():
                try:
                    if column_name in sheet_columns:
                        column_index = sheet_columns.index(column_name)
                        sheet_value = str(row[column_index]).strip()

                        # Handle translations separately
                        if isinstance(field_info, tuple):
                            field, lang = field_info
                            translations.setdefault(lang, {})[field] = sheet_value
                            if field == "name" and lang == "en_US" and sheet_value:
                                product_values["name"] = sheet_value
                        # elif column_name == "SKU":
                            # _logger.error("[sheet_value] SKU: " + sheet_value)
                        elif column_name in ["Publish_CA", "Publish_USA", "Can_Be_Sold", "Can_Be_Rented"]:
                            product_values[field_info] = self.normalize_bools(sheet_value.strip())
                        elif column_name == "PriceCAD":
                            product_values[field_info] = float(sheet_value) if sheet_value else 0.0
                        elif column_name == "Store Image" and sheet_value:
                            try:
                                response = requests.get(sheet_value, timeout=10)
                                if response.status_code == 200:
                                    product_values["image_1920"] = base64.b64encode(response.content)
                                else:
                                    _logger.warning(
                                        "createProduct: Failed to fetch image from URL '%s' for Product ID %s. Status Code: %s.",
                                        sheet_value, product_id, response.status_code
                                    )
                            except requests.exceptions.RequestException as e:
                                _logger.error(
                                    "createProduct: Error fetching image for Product ID %s from URL '%s': %s",
                                    product_id, sheet_value, str(e), exc_info=True
                                )
                except Exception as e:
                    _logger.error(
                        "createProduct: Error while processing field '%s' for Product ID %s: %s",
                        column_name, product_id, str(e), exc_info=True
                    )

            # Use savepoints to handle errors during creation
            try:
                self.database.env.cr.execute("SAVEPOINT create_product_savepoint")

                product = self.database.env["product.template"].sudo().create(product_values)
                self.database.env.cr.execute("RELEASE SAVEPOINT create_product_savepoint")
                _logger.info("createProduct: Successfully created Product ID %s with values: %s.", product.id, product_values)

                # Set translations for the product
                for lang, fields in translations.items():
                    try:
                        product.with_context(lang=lang).sudo().write(fields)
                        _logger.info(
                            "createProduct: Successfully set translations for Product ID %s in language %s: %s.",
                            product.id, lang, fields
                        )
                    except Exception as e:
                        _logger.error(
                            "createProduct: Error setting translations for Product ID %s in language %s: %s",
                            product.id, lang, str(e), exc_info=True
                        )

                # check sku creation
                if product.sku != product_id:

                    product.sku = product_id

                    _logger.error(
                        "createProduct: SKU mismatch for just created Product ID %s. Expected: %s, Actual: %s.",
                        product.id, product_id, product.sku
                    )
                    self.add_to_report(
                        "ERROR",
                        f"SKU mismatch for Product ID {product.id}. Expected: {product_id}, Actual: {product.sku}.")

            except Exception as e:
                self.database.env.cr.execute("ROLLBACK TO SAVEPOINT create_product_savepoint")
                _logger.error(
                    "createProduct: Error during product creation for Product ID %s: %s",
                    product_id, str(e), exc_info=True
                )

        except Exception as e:
            error_msg = f"Row {row_index}: Error creating Product with SKU {product_id}: {str(e)}"
            _logger.error(f"createProduct: {error_msg}", exc_info=True)
