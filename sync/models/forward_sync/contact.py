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


class sync_contacts:
    def __init__(self, sheetName, sheet, database):
        self.sheet = sheet
        self.sheetName = sheetName
        self.database = database

    def syncContacts(self):
        # Confirm GS Tab is in the correct Format
        sheetWidth = 17
        columns = dict()
        columnsMissing = False

        msg = ""

        # Calculate Indexes
        if "Name" in self.sheet[0]:
            columns["name"] = self.sheet[0].index("Name")
        else:
            msg = utilities.buildMSG(msg, self.sheetName, "Header", "Name Missing")
            columnsMissing = True

        if "Phone" in self.sheet[0]:
            columns["phone"] = self.sheet[0].index("Phone")
        else:
            msg = utilities.buildMSG(msg, self.sheetName, "Header", "Phone Missing")
            columnsMissing = True

        if "Email" in self.sheet[0]:
            columns["email"] = self.sheet[0].index("Email")
        else:
            msg = utilities.buildMSG(msg, self.sheetName, "Header", "Email Missing")
            columnsMissing = True

        if "Company" in self.sheet[0]:
            columns["company"] = self.sheet[0].index("Company")
        else:
            msg = utilities.buildMSG(msg, self.sheetName, "Header", "Company Missing")
            columnsMissing = True

        if "Street Address" in self.sheet[0]:
            columns["streetAddress"] = self.sheet[0].index("Street Address")
        else:
            msg = utilities.buildMSG(
                msg, self.sheetName, "Header", "Street Address Missing"
            )
            columnsMissing = True

        if "City" in self.sheet[0]:
            columns["city"] = self.sheet[0].index("City")
        else:
            msg = utilities.buildMSG(msg, self.sheetName, "Header", "City Missing")
            columnsMissing = True

        if "State/Region" in self.sheet[0]:
            columns["state"] = self.sheet[0].index("State/Region")
        else:
            msg = utilities.buildMSG(
                msg, self.sheetName, "Header", "State/Region Missing"
            )
            columnsMissing = True

        if "Country Code" in self.sheet[0]:
            columns["country"] = self.sheet[0].index("Country Code")
        else:
            msg = utilities.buildMSG(
                msg, self.sheetName, "Header", "Country Code Missing"
            )
            columnsMissing = True

        if "Postal Code" in self.sheet[0]:
            columns["postalCode"] = self.sheet[0].index("Postal Code")
        else:
            msg = utilities.buildMSG(
                msg, self.sheetName, "Header", "Postal Code Missing"
            )
            columnsMissing = True

        if "Pricelist" in self.sheet[0]:
            columns["pricelist"] = self.sheet[0].index("Pricelist")
        else:
            msg = utilities.buildMSG(msg, self.sheetName, "Header", "Pricelist Missing")
            columnsMissing = True

        if "Language" in self.sheet[0]:
            columns["language"] = self.sheet[0].index("Language")
        else:
            msg = utilities.buildMSG(msg, self.sheetName, "Header", "Language Missing")
            columnsMissing = True

        if "OCID" in self.sheet[0]:
            columns["id"] = self.sheet[0].index("OCID")
        else:
            msg = utilities.buildMSG(msg, self.sheetName, "Header", "OCID Missing")
            columnsMissing = True

        if "Valid" in self.sheet[0]:
            columns["valid"] = self.sheet[0].index("Valid")
        else:
            msg = utilities.buildMSG(msg, self.sheetName, "Header", "Valid Missing")
            columnsMissing = True

        if "Continue" in self.sheet[0]:
            columns["continue"] = self.sheet[0].index("Continue")
        else:
            msg = utilities.buildMSG(msg, self.sheetName, "Header", "Continue Missing")
            columnsMissing = True

        i = 1
        if len(self.sheet[i]) != sheetWidth or columnsMissing:
            msg = (
                "<h1>Company page Invalid</h1>\n<p>"
                + str(self.sheetName)
                + " width is: "
                + str(len(self.sheet[i]))
                + " Expected "
                + str(sheetWidth)
                + "</p>\n"
                + msg
            )
            self.database.sendSyncReport(msg)
            return True, msg

        # loop through all the rows
        while True:
            # check if should continue
            if (
                i == len(self.sheet)
                or str(self.sheet[i][columns["continue"]]).upper() != "TRUE"
            ):
                break

            # validation checks
            if str(self.sheet[i][columns["valid"]]).upper() != "TRUE":
                msg = utilities.buildMSG(
                    msg, self.sheetName, self.sheet[i][columns["id"]], "Invalid Row"
                )
                i += 1
                continue

            if not utilities.check_id(str(self.sheet[i][columns["id"]])):
                msg = utilities.buildMSG(
                    msg, self.sheetName, self.sheet[i][columns["id"]], "Invalid ID"
                )
                i += 1
                continue

            if not utilities.check_id(str(self.sheet[i][columns["company"]])):
                msg = utilities.buildMSG(
                    msg,
                    self.sheetName,
                    self.sheet[i][columns["id"]],
                    "Invalid Company ID",
                )
                i += 1
                continue

            if str(self.sheet[i][columns["company"]]) != 0:
                companies = self.database.env["ir.model.data"].search(
                    [
                        ("name", "=", self.sheet[i][columns["company"]]),
                        ("model", "=", "res.partner"),
                    ]
                )
                if len(companies) == 0:
                    msg = utilities.buildMSG(
                        msg,
                        self.sheetName,
                        self.sheet[i][columns["id"]],
                        "Unknown Company ID: " + str(self.sheet[i][columns["company"]]),
                    )
                    i += 1
                    continue

            # if it gets here data should be valid
            external_id = str(self.sheet[i][columns["id"]])
            try:
                # attempts to access existing item (item/row)
                contact_ids = self.database.env["ir.model.data"].search(
                    [("name", "=", external_id), ("model", "=", "res.partner")]
                )
                if len(contact_ids) > 0:
                    self.updateContacts(
                        self.database.env["res.partner"].browse(
                            contact_ids[len(contact_ids) - 1].res_id
                        ),
                        i,
                        columns,
                    )
                else:
                    self.createContacts(self.sheet, external_id, i, columns)
            except Exception as e:
                _logger.info("Contacts")
                _logger.info(e)
                msg = utilities.buildMSG(msg, self.sheetName, external_id, e)
                return True, msg
            i += 1
        return False, msg

    def updateContacts(self, contact, i, columns):
        # check if any update to item is needed and skips if there is none
        if contact.stringRep == str(self.sheet[i][:]) and SKIP_NO_CHANGE:
            return

        # reads values and puts them in appropriate fields
        contact.name = self.sheet[i][columns["name"]]
        contact.phone = self.sheet[i][columns["phone"]]
        contact.email = self.sheet[i][columns["email"]]
        if self.sheet[i][columns["company"]] != "":
            contact.parent_id = int(
                self.database.env["ir.model.data"]
                .search(
                    [
                        ("name", "=", self.sheet[i][columns["company"]]),
                        ("model", "=", "res.partner"),
                    ]
                )[0]
                .res_id
            )
        else:
            contact.parent_id = False
        contact.street = self.sheet[i][columns["streetAddress"]]
        contact.city = self.sheet[i][columns["city"]]
        if self.sheet[i][columns["state"]] != "":
            stateTup = self.database.env["res.country.state"].search(
                [("code", "=", self.sheet[i][columns["state"]])]
            )
            if len(stateTup) > 0:
                contact.state_id = int(stateTup[0].id)

        name = self.sheet[i][columns["country"]]
        if name != "":
            if name == "US":
                name = "United States"
            contact.country_id = int(
                self.database.env["res.country"].search([("name", "=", name)])[0].id
            )
        contact.zip = self.sheet[i][columns["postalCode"]]

        contact.lang = self.sheet[i][columns["language"]]

        if self.sheet[i][columns["pricelist"]] != "":
            contact.property_product_pricelist = int(
                self.database.env["product.pricelist"]
                .search([("name", "=", self.sheet[i][columns["pricelist"]])])[0]
                .id
            )
        contact.is_company = False

        _logger.info("Contact String Rep")
        contact.stringRep = str(self.sheet[i][:])

    # creates record and updates it

    def createContacts(self, sheet, external_id, i, columns):
        ext = self.database.env["ir.model.data"].create(
            {"name": external_id, "model": "res.partner"}
        )[0]
        contact = self.database.env["res.partner"].create(
            {"name": self.sheet[i][columns["name"]]}
        )[0]
        ext.res_id = contact.id
        self.updateContacts(contact, i, columns)

    

