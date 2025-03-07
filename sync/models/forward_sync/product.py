# -*- coding: utf-8 -*-

from .utilities import utilities
from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo.tools.translate import _
from odoo import models

from .product_common import product_sync_common

_logger = logging.getLogger(__name__)

SKIP_NO_CHANGE = True


class sync_products:
    def __init__(self, name, sheet, database):
        self.name = name
        self.sheet = sheet
        self.database = database

    def syncProducts(self, sheet):
        _logger.debug("PRODUCT.PY: Starting product synchronization.")
        skipped_items = []  # List to store skipped rows and errors

        # Confirm GS Tab is in the correct Format
        columns = dict()
        columnsMissing = False
        msg = ""
        i = 1

        # Debugging: Validating header format
        _logger.debug("PRODUCT.PY: Validating sheet header.")
        productHeaderDict = dict()
        productHeaderDict["SKU"] = "sku"
        productHeaderDict["EN-Name"] = "english_name"
        productHeaderDict["FR-Name"] = "french_name"
        productHeaderDict["EN-Description"] = "english_description"
        productHeaderDict["FR-Description"] = "french_description"
        productHeaderDict["PriceCAD"] = "priceCAD"
        productHeaderDict["PriceUSD"] = "priceUSD"
        productHeaderDict["Product Type"] = "type"
        productHeaderDict["Tracking"] = "tracking"
        productHeaderDict["CanBeSold"] = "can_be_sold"
        productHeaderDict["Valid"] = "valid"
        productHeaderDict["Continue"] = "continue"
        sheetWidth = len(productHeaderDict)
        columns, msg, columnsMissing = utilities.checkSheetHeader(productHeaderDict, self.sheet, self.name)

        if sheetWidth != len(sheet[i]) or columnsMissing:
            msg = (
                "<h1>Product page Invalid</h1>\n<p>"
                + str(self.name)
                + " width is: "
                + str(len(self.sheet[i]))
                + " Expected "
                + str(sheetWidth)
                + "</p>\n"
                + msg
            )
            self.database.sendSyncReport(msg)
            _logger.warning(f"PRODUCT.PY: Sheet header validation failed. {msg}")
            return True, msg

        # Debugging: Starting row processing
        _logger.debug("PRODUCT.PY: Starting row processing.")
        while True:
            # Check if the process should continue
            if str(sheet[i][columns["continue"]]).upper() != "TRUE":
                _logger.debug(f"PRODUCT.PY: Stopping processing at row {i}.")
                break

            if str(sheet[i][columns["valid"]]).upper() == "FALSE":
                _logger.debug(f"PRODUCT.PY: Skipping row {i} because 'Valid' is FALSE.")
                # skipped_items.append({
                #     "row": i,
                #     "sku": sheet[i][columns["sku"]],
                #     "error": "Row marked as invalid ('Valid' = FALSE)."
                # })
                i += 1
                continue

            # Validation checks
            key = str(sheet[i][columns["sku"]])
            try:
                # Validation: Check SKU
                if not utilities.check_id(key):
                    raise ValueError(f"Invalid SKU {key} at row {i}.")

                # Validation: Check CAD Price
                if not utilities.check_price(sheet[i][columns["priceCAD"]]):
                    raise ValueError(f"Invalid CAD price at row {i}.")

                # Validation: Check USD Price
                if not utilities.check_price(sheet[i][columns["priceUSD"]]):
                    raise ValueError(f"Invalid USD price at row {i}.")

                # Processing the row
                external_id = str(sheet[i][columns["sku"]])
                product_ids = self.database.env["ir.model.data"].search(
                    [("name", "=", external_id), ("model", "=", "product.template")]
                )

                if product_ids:
                    
                    if len(product_ids) > 1:
                        _logger.warning(
                            f"PRODUCT.PY: Multiple product IDs found for SKU {key}: {product_ids.ids}. "
                            "Using the first product found."
                        )
                    
                    product = self.database.env["product.template"].browse(
                        product_ids[0].res_id
                    ).filtered(lambda p: p.active)
                    
                    if not product:
                        raise ValueError(
                            f"Product ID recognized, but no active product found for SKU {key}."
                        )

                    self.updateProducts(
                        product,
                        str(sheet[i][:]),  # product_stringRep
                        sheet[i][columns["english_name"]],
                        sheet[i][columns["french_name"]],
                        sheet[i][columns["english_description"]],
                        sheet[i][columns["french_description"]],
                        sheet[i][columns["priceCAD"]],  # product_price_cad
                        sheet[i][columns["priceUSD"]],  # product_price_usd
                        "serial",  # product_tracking
                        "product",
                        sheet[i][columns["can_be_sold"]],
                    )  # product_type

                else:
                    self.createAndUpdateProducts(
                        external_id,
                        str(sheet[i][:]),  # product_stringRep
                        sheet[i][columns["english_name"]],
                        sheet[i][columns["french_name"]],
                        sheet[i][columns["english_description"]],
                        sheet[i][columns["french_description"]],
                        sheet[i][columns["priceCAD"]],  # product_price_cad
                        sheet[i][columns["priceUSD"]],  # product_price_usd
                        "serial",  # product_tracking
                        "product",
                        sheet[i][columns["can_be_sold"]],
                    )  # product_type

            except Exception as e:
                # Log the error and skip the problematic row
                error_message = f"PRODUCT.PY: Error occurred for SKU {key} at row {i}: {str(e)}"
                _logger.error(error_message, exc_info=True)
                skipped_items.append({
                    "row": i,
                    "sku": key,
                    "error": str(e)
                })

            i += 1

        # Compile skipped items report
        if skipped_items:
            report = "\n".join(
                [f"Row {item['row']}: SKU {item['sku']} - Error: {item['error']}" for item in skipped_items]
            )
            _logger.warning(f"PRODUCT.PY: Skipped items report:\n{report}")
            self.database.sendSyncReport(f"<h1>Skipped Items Report</h1><pre>{report}</pre>")

        _logger.info("PRODUCT.PY: Product synchronization completed successfully.")
        return False, ""


    def createProducts(self, external_id, product_name):
        _logger.debug(f"PRODUCT.PY: Creating product with external ID {external_id}.")

        # Set company_id explicitly
        # self.database.env.company.id
        company_id = 1

        # Ensure the responsible user belongs to the correct company
        responsible_user = self.database.env["res.users"].search(
            [("company_id", "=", company_id)], limit=1
        )
        if not responsible_user:
            raise ValueError(f"No responsible user found for company ID {company_id}.")

        ext = self.database.env["ir.model.data"].create(
            {"name": external_id, "model": "product.template"}
        )[0]

        product = self.database.env["product.template"].create({
            "name": product_name,
            "company_id": company_id,  # Ensure the product belongs to the current company
            "responsible_id": responsible_user.id,
        })[0]

        product.tracking = "serial"
        product.type = "product"
        ext.res_id = product.id

        _logger.info(f"PRODUCT.PY: Created product {product.name} with company_id {company_id}.")
        return product


    def updateProducts(
        self,
        product,
        product_stringRep,
        product_name_english,
        product_name_french,
        product_description_sale_english,
        product_description_sale_french,
        product_price_cad,
        product_price_usd,
        product_tracking,
        product_type,
        can_be_sold,
    ):
        _logger.debug(f"PRODUCT.PY: Checking if update is needed for product {product.name}.")
        if product.stringRep == product_stringRep and SKIP_NO_CHANGE:
            # _logger.info(f"PRODUCT.PY: No changes detected for product {product.name}. Skipping update.")
            return

        _logger.info(f"PRODUCT.PY: Updating product {product.name}.")
        product.name = product_name_english

        product_sync_common.translatePricelist(
            self.database,
            product,
            product_name_english,
            product_description_sale_english,
            "en_US",
        )
        product_sync_common.translatePricelist(
            self.database,
            product,
            product_name_french,
            product_description_sale_french,
            "fr_CA",
        )

        product.description_sale = product_description_sale_english
        _logger.debug("PRODUCT.PY: Updating tracking, price, and sale settings.")
        product.type = product_type
        product.stringRep = product_stringRep

        product_sync_common.addProductToPricelist(
            self.database, product, "🇨🇦", product_price_cad
        )
        product_sync_common.addProductToPricelist(
            self.database, product, "🇺🇸", product_price_usd
        )
        product.list_price = product_price_cad
        product.cadVal = product_price_cad
        product.usdVal = product_price_usd

        if str(can_be_sold).upper() == "TRUE":
            product.sale_ok = True
        else:
            product.sale_ok = False

    def createAndUpdateProducts(
        self,
        external_id,
        product_stringRep,
        product_name_english,
        product_name_french,
        product_description_sale_english,
        product_description_sale_french,
        product_price_cad,
        product_price_usd,
        product_tracking,
        product_type,
        can_be_sold,
    ):
        _logger.debug(f"PRODUCT.PY: Creating and updating product with external ID {external_id}.")
        product = self.createProducts(external_id, product_name_english)
        self.updateProducts(
            product,
            product_stringRep,
            product_name_english,
            product_name_french,
            product_description_sale_english,
            product_description_sale_french,
            product_price_cad,
            product_price_usd,
            product_tracking,
            product_type,
            can_be_sold,
        )

        product_created = self.database.env["product.template"].search(
            [("sku", "=", external_id)]
        )
        return product_created