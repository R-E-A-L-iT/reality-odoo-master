# -*- coding: utf-8 -*-

from .utilities import utilities
from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo.tools.translate import _
from odoo import models

_logger = logging.getLogger(__name__)


class product_sync_common:
    @classmethod
    def translatePricelist(cls, database, product, name, description, lang):
        # Create or Update Translations
        product_name = database.env["ir.translation"].search(
            [
                ("res_id", "=", product.id),
                ("name", "=", "product.template,name"),
                ("lang", "=", lang),
            ]
        )
        if len(product_name) > 0:
            for name_record in product_name:
                name_record.value = name

        else:
            product_name_new = database.env["ir.translation"].create(
                {"name": "product.template,name", "lang": lang, "res_id": product.id}
            )[0]
            product_name_new.value = name
            product_name_new.type = "model"

        product_description = database.env["ir.translation"].search(
            [
                ("res_id", "=", product.id),
                ("name", "=", "product.template,description_sale"),
                ("lang", "=", lang),
            ]
        )

        if len(product_description) > 0:
            for description_record in product_description:
                description_record.value = description
        else:
            product_description_new = database.env["ir.translation"].create(
                {
                    "name": "product.template,description_sale",
                    "lang": lang,
                    "res_id": product.id,
                }
            )[0]
            product_description_new.value = description
            product_description_new.type = "model"
        return

    # Methode to add a product to a pricelist
    # Input
    #   database        Variable that provides Access to the Active Database
    #   produt:         Product generated by Odoo
    #   pricelistName:  The name of the list to add the product
    #   price           The price

    @classmethod
    def addProductToPricelist(cls, database, product, pricelistName, price):
        pricelist_id = (
            database.env["product.pricelist"]
            .search([("name", "=", pricelistName)])[0]
            .id
        )
        pricelist_item_ids = database.env["product.pricelist.item"].search(
            [("product_tmpl_id", "=", product.id), ("pricelist_id", "=", pricelist_id)]
        )

        if len(pricelist_item_ids) > 0:
            pricelist_item = pricelist_item_ids[len(pricelist_item_ids) - 1]
        else:
            pricelist_item = database.env["product.pricelist.item"].create(
                {"pricelist_id": pricelist_id, "product_tmpl_id": product.id}
            )[0]

        pricelist_item.product_tmpl_id = product.id
        pricelist_item.applied_on = "1_product"
        if (str(price) != " ") and (str(price) != ""):
            pricelist_item.fixed_price = float(price)
