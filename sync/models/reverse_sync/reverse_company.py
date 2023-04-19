from .googlesheetsAPI import sheetsAPI
from .email import reverse_sync_email
from odoo import api, fields, models, SUPERUSER_ID, _

import logging

_logger = logging.getLogger(__name__)

dev1_prefix = "dev-ty-"
dev2_prefix = "dev-oli-"


class reverse_sync_company(models.Model):
    _name = "sync.reverse_sync_company"
    _description = "Reverse Company Sync"

    def getSpreadSheetID(self):
        _db_name = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        # Production DB name
        _db_name_prod = "https://www.r-e-a-l.it"

        # R-E-A-L.iT Master Database
        _master_db = "1Tbo0NdMVpva8coych4sgjWo7Zi-EHNdl6EFx2DZ6bJ8"

        # Dev Numbers Set Based on When Developer Joined
        _dev_1_db = "19izgmIl_fg002YfqtNbIgkwSKY3Tk5r32XYEfq7nXT0"
        _dev_2_db = "19izgmIl_fg002YfqtNbIgkwSKY3Tk5r32XYEfq7nXT0"

        # Return the proper GoogleSheet Template ID base on the environement
        if _db_name == _db_name_prod:
            _logger.info("Production")
            return _master_db
        elif dev1_prefix in _db_name:
            _logger.info("Dev 1")
            return _dev_1_db
        elif dev2_prefix in _db_name:
            _logger.info("Dev 2")
            return _dev_2_db
        else:
            _logger.info("Default Dev GS")
            return _master_db

    def createHeader(self):
        return [
            "COMPANY NICK NAME",
            "Company Name",
            "Phone",
            "Email",
            "Website",
            "Street Address",
            "City",
            "State/Region",
            "Country",
            "Postal Code",
            "Industry",
            "Language",
            "Currency",
        ]

    def value(self, headerItem, expected, cellValue):
        if headerItem != expected:
            raise Exception("Invalid Header Item: " + headerItem)
        if cellValue == False:
            return ""
        return str(cellValue)

    def createRow(self, header, company):
        _logger.error("LINE 68")
        row = []
        if company.name == False:
            return None
        row.append(self.value(header[0], "COMPANY NICK NAME", company.company_nickname))
        row.append(self.value(header[1], "Company Name", company.name))
        _logger.error("LINE 74")

        row.append(self.value(header[2], "Phone", company.phone))
        row.append(self.value(header[3], "Email", company.email))
        row.append(self.value(header[4], "Website", company.website))
        row.append(self.value(header[5], "Street Address", company.street))
        row.append(self.value(header[6], "City", company.city))
        row.append(self.value(header[7], "State/Region", company.state_id.code))
        row.append(self.value(header[8], "Country", company.country_id.name))
        row.append(self.value(header[9], "Postal Code", company.zip))
        row.append(self.value(header[10], "Industry", company.industry_id.name))
        row.append(self.value(header[11], "Language", company.lang))

        _logger.error("LINE 87")
        _logger.error(company.property_product_pricelist.name)
        currency = ""
        if "CAD" in company.property_product_pricelist.name:
            currency = "CAD"
        elif "USD" in company.property_product_pricelist.name:
            currency = "USD"
        row.append(self.value(header[12], "Currency", currency))
        _logger.error("LINE 94")

    def createBlank(self, length):
        return ["" for _ in range(length)]

    def reverseSync(self, psw, tabname):
        _logger.info("Reverse Sync Company")
        try:
            spreadSheetID = self.getSpreadSheetID()
            sheet_object = sheetsAPI.getSpreadSheetByName(spreadSheetID, tabname, psw)
            if sheet_object == None:
                raise Exception("Invalid Document or Tabname: " + str(tabname))
            sheet = sheet_object.get_all_values()[2:]
            nicknames = list(map(lambda row: row[0].upper(), sheet))

            header = self.createHeader()
            sheetTable = []
            companies = self.env["res.partner"].search(
                [("is_company", "=", True), ("company_nickname", "!=", "_")]
            )

            for company in companies:
                if (
                    company.company_nickname not in nicknames
                    and company.company_nickname != "_"
                ):
                    _logger.info(company.company_nickname in nicknames)
                    _logger.info(company.company_nickname)
                    row = self.createRow(header, company)
                    if row != None:
                        sheetTable.append(row)
                    _logger.error("LINE: 120")

        except Exception as e:
            _logger.error(e)
            reverse_sync_email.sendReport("Company", e)
        _logger.info("End Reverse Sync Ccompany")
