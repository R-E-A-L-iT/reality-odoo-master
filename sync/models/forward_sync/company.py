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

SKIP_NO_CHANGE = False


class sync_companies():
    def __init__(self, sheetName, sheet, database):
        self.sheetName = sheetName
        self.sheet = sheet
        self.database = database

    def syncCompanies(self):

        # check sheet width to filter out invalid sheets
        # every company tab will have the same amount of columns (Same with others)
        sheetWidth = 18
        columns = dict()
        missingColumn = False
        msg = ""

        # Calculate Indexes
        if ("Company Name" in self.sheet[0]):
            columns["companyName"] = self.sheet[0].index("Company Name")
        else:
            msg = utilities.buildMSG(
                msg, self.sheetName, "Header", "Company Name Missing")
            missingColumn = True

        if ("Phone" in self.sheet[0]):
            columns["phone"] = self.sheet[0].index("Phone")
        else:
            msg = utilities.buildMSG(
                msg, self.sheetName, "Header", "Phone Missing")
            missingColumn = True

        if ("Website" in self.sheet[0]):
            columns["website"] = self.sheet[0].index("Website")
        else:
            msg = utilities.buildMSG(
                msg, self.sheetName, "Header", "Phone Missing")
            missingColumn = True

        if ("Street" in self.sheet[0]):
            columns["street"] = self.sheet[0].index("Street")
        else:
            msg = utilities.buildMSG(
                msg, self.sheetName, "Header", "Street Missing")
            missingColumn = True

        if ("City" in self.sheet[0]):
            columns["city"] = self.sheet[0].index("City")
        else:
            msg = utilities.buildMSG(
                msg, self.sheetName, "Header", "City Missing")
            missingColumn = True

        if ("State" in self.sheet[0]):
            columns["state"] = self.sheet[0].index("State")
        else:
            msg = utilities.buildMSG(
                msg, self.sheetName, "Header", "State Missing")
            missingColumn = True

        if ("Country Code" in self.sheet[0]):
            columns["country"] = self.sheet[0].index("Country Code")
        else:
            msg = utilities.buildMSG(
                msg, self.sheetName, "Header", "Country Code Missing")
            missingColumn = True

        if ("Postal Code" in self.sheet[0]):
            columns["postalCode"] = self.sheet[0].index("Postal Code")
        else:
            msg = utilities.buildMSG(
                msg, self.sheetName, "Header", "Postal Code Missing")
            missingColumn = True

        if ("Language" in self.sheet[0]):
            columns["language"] = self.sheet[0].index("Language")
        else:
            msg = utilities.buildMSG(
                msg, self.sheetName, "Header", "Language Missing")
            missingColumn = True

        if ("Email" in self.sheet[0]):
            columns["email"] = self.sheet[0].index("Email")
        else:
            msg = utilities.buildMSG(
                msg, self.sheetName, "Header", "Email Missing")
            missingColumn = True

        if ("Pricelist" in self.sheet[0]):
            columns["pricelist"] = self.sheet[0].index("Pricelist")
        else:
            msg = utilities.buildMSG(
                msg, self.sheetName, "Header", "Pricelist Missing")
            missingColumn = True

        if ("Industry" in self.sheet[0]):
            columns["industry"] = self.sheet[0].index("Industry")
        else:
            msg = utilities.buildMSG(
                msg, self.sheetName, "Header", "Industry Missing")
            missingColumn = True

        if ("OCOMID" in self.sheet[0]):
            columns["id"] = self.sheet[0].index("OCOMID")
        else:
            msg = utilities.buildMSG(
                msg, self.sheetName, "Header", "OCOMID Missing")
            missingColumn = True

        if ("Valid" in self.sheet[0]):
            columns["valid"] = self.sheet[0].index("Valid")
        else:
            msg = utilities.buildMSG(
                msg, self.sheetName, "Header", "Valid Missing")
            missingColumn = True

        if ("Continue" in self.sheet[0]):
            columns["continue"] = self.sheet[0].index("Continue")
        else:
            msg = utilities.buildMSG(
                msg, self.sheetName, "Header", "Continue Missing")
            missingColumn = True

        i = 1
        if (len(self.sheet[i]) != sheetWidth or missingColumn):
            msg = "<h1>Company page Invalid</h1>\n<p>" + str(self.sheetName) + " width is: " + str(len(self.sheet[i])) + " Expected " + \
                str(sheetWidth) + "</p>\n" + msg
            self.database.sendSyncReport(msg)
            return True, msg

        # loop through all the rows
        while (True):

            # check if should continue
            if (str(self.sheet[i][columns["continue"]]).upper() != "TRUE"):
                break

            # validation checks (vary depending on tab/function)
            if (str(self.sheet[i][columns["valid"]]).upper() != "TRUE"):
                msg = utilities.buildMSG(
                    msg, self.sheetName, self.sheet[i][columns["id"]], "Invalid Row")
                i += 1
                continue

            if (not utilities.check_id(str(self.sheet[i][columns["id"]]))):
                msg = utilities.buildMSG(
                    msg, self.sheetName, self.sheet[i][columns["id"]], "Invalid ID")
                i += 1
                continue

            industry = self.industry_name_format(
                self.sheet[i][columns["industry"]])
            if (industry != ""):
                industry_ids = self.database.env['res.partner.industry'].search(
                    [('name', '=', industry)])
                if (len(industry_ids) > 1):
                    msg = utilities.buildMSG(
                        msg, self.sheetName, self.sheet[i][columns["id"]], "Invalid Industry: " + str(industry))
                    i += 1
                    continue

            # if it gets here data should be valid
            external_id = str(self.sheet[i][columns["id"]])
            try:

                # attempts to access existing item (item/row)
                company_ids = self.database.env['ir.model.data'].search(
                    [('name', '=', external_id), ('model', '=', 'res.partner')])
                if (len(company_ids) > 0):
                    self.updateCompany(self.database.env['res.partner'].browse(
                        company_ids[len(company_ids) - 1].res_id), i, columns)
                else:
                    self.createCompany(external_id,
                                       i, columns)
            except Exception as e:
                _logger.info("Companies")
                _logger.info(e)
                msg = utilities.buildMSG(
                    msg, self.sheetName, external_id, str(e))
                return True, msg
            i += 1
        return False, msg

    def industry_name_format(self, industry: str) -> str:
        words = industry.lower().split(" ")
        result = ""
        for word in words:
            if word == "":
                continue
            result += word[0].upper() + word[1:] + " "
        return result[:-1]

    def updateCompany(self, company, i, columns):

        # check if any update to item is needed and skips if there is none
        if (company.stringRep == str(self.sheet[i][:]) and SKIP_NO_CHANGE):
            return

        # reads values and puts them in appropriate fields
        company.name = self.sheet[i][columns["companyName"]]
        company.phone = self.sheet[i][columns["phone"]]
        company.website = self.sheet[i][columns["website"]]
        company.street = self.sheet[i][columns["street"]]
        company.city = self.sheet[i][columns["city"]]

        name = self.sheet[i][columns["country"]]
        if (name != ""):
            if (name == "US"):
                name = "United States"
            company.country_id = int(
                self.database.env['res.country'].search([('name', '=', name)])[0].id)

        if (self.sheet[i][columns["state"]] != ""):
            stateTup = self.database.env['res.country.state'].search(
                [('code', '=', self.sheet[i][columns["state"]]), ('country_id', '=', company.country_id.id)])
            if (len(stateTup) > 0):
                company.state_id = int(stateTup[0].id)
        company.zip = self.sheet[i][columns["postalCode"]]
        company.lang = self.sheet[i][columns["language"]]
        company.email = self.sheet[i][columns["email"]]
        if (self.sheet[i][columns["pricelist"]] != ""):
            pricelist = self.database.env['product.pricelist'].search(
                [('name', '=', self.sheet[i][columns["pricelist"]])])[0]

            company.pricelist_id = pricelist

        industry = self.industry_name_format(
            self.sheet[i][columns["industry"]])
        if (industry != ""):
            industry_ids = self.database.env['res.partner.industry'].search(
                [('name', '=', industry)])
            if (len(industry_ids) > 1):
                raise Exception("Invalid Industry: " + industry)
            elif (len(industry_ids) == 0):
                company.industry_id = self.database.env['res.partner.industry'].create(
                    {"name": industry, "display_name": industry})
            else:
                company.industry_id = industry_ids[0]
        company.is_company = True

        company.stringRep = str(self.sheet[i][:])

    # creates object and updates it

    def createCompany(self, external_id, i, columns):
        ext = self.database.env['ir.model.data'].create(
            {'name': external_id, 'model': "res.partner"})[0]
        company = self.database.env['res.partner'].create(
            {'name': self.sheet[i][columns["companyName"]]})[0]
        ext.res_id = company.id
        self.updateCompany(company, i, columns)
