from .googlesheetsAPI import sheetsAPI
from .email import reverse_sync_email
from odoo import api, fields, models, SUPERUSER_ID, _
import re

import logging

_logger = logging.getLogger(__name__)

dev1_prefix = "dev-ty-"
dev2_prefix = "dev-oli-"


class reverse_sync_contacts(models.Model):
    _name = "sync.reverse_sync_contact"
    _description = "Reverse Contact Sync"

    def getSpreadSheetID(self):
        _db_name = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        # Production DB name
        _db_name_prod = "https://www.r-e-a-l.it"

        # R-E-A-L.iT Master Database
        _master_contacts = "1pDPKv2bH8_Be5aCCyU4bqTuwJNcXsADlAYDAGG8P1Ls"

        # Dev Numbers Set Based on When Developer Joined
        _dev_1_contacts = "1guw41PVLezHrYxvjdhfswCJc6wzI6JlITynZH9BK5Mg"
        _dev_2_contacts = "1guw41PVLezHrYxvjdhfswCJc6wzI6JlITynZH9BK5Mg"

        # Return the proper GoogleSheet Template ID base on the environement
        if _db_name == _db_name_prod:
            _logger.info("Production")
            return _master_contacts
        elif dev1_prefix in _db_name:
            _logger.info("Dev 1")
            return _dev_1_contacts
        elif dev2_prefix in _db_name:
            _logger.info("Dev 2")
            return _dev_2_contacts
        else:
            _logger.info("Default Dev GS")
            return _master_contacts

    def createHeader(self):
        return [
            "First Name",
            "Last Name",
            "Phone",
            "Email",
            "Company",
            "Street Address",
            "City",
            "State/Region",
            "Country",
            "Postal Code",
            "Industry",
            "Job Title",
            "Mobile",
        ]

    def value(self, headerItem, expected, cellValue):
        if headerItem != expected:
            raise Exception("Invalid Header Item: " + headerItem)
        if cellValue == False:
            return ""
        return str(cellValue)

    def createRow(self, header, contact):
        row = []
        if contact.name == False:
            return None
        digit_search = re.compile("\\d")
        if digit_search.search(contact.name) != None:
            return None

        row.append(self.value(header[0], "First Name", contact.name.split(" ")[0]))

        row.append(
            self.value(header[1], "Last Name", " ".join(contact.name.split(" ")[1:]))
        )

        row.append(self.value(header[2], "Phone", contact.phone))
        row.append(self.value(header[3], "Email", contact.email))
        row.append(self.value(header[4], "Company", contact.parent_id.name))
        row.append(self.value(header[5], "Street Address", contact.street))
        row.append(self.value(header[6], "City", contact.city))
        row.append(self.value(header[7], "State/Region", contact.state_id.code))
        row.append(self.value(header[8], "Country", contact.country_id.name))
        row.append(self.value(header[9], "Postal Code", contact.zip))
        row.append(self.value(header[10], "Industry", contact.industry_id.name))
        row.append(self.value(header[11], "Job Title", contact.function))
        row.append(self.value(header[12], "Mobile", contact.mobile))
        return row

    def createBlank(self, length):
        return ["" for _ in range(length)]

    def reverseSync(self, psw):
        _logger.info("Reverse Sync Contacts")
        try:
            spreadSheetID = self.getSpreadSheetID()
            sheet = sheetsAPI.getSpreadSheet(spreadSheetID, sheetIndex=0, auth=psw)
            header = self.createHeader()
            width = len(header)
            sheetTable = [header]
            contacts = self.env["res.partner"].search([("is_company", "=", False)])

            for contact in contacts:
                row = self.createRow(header, contact)
                if row != None:
                    sheetTable.append(row)
            height = len(sheet.get_all_values())

            while len(sheetTable) < height:
                sheetTable.append(self.createBlank(width))
            writeRange = "A1:M" + str(len(sheetTable))
            sheet.update(writeRange, sheetTable)
        except Exception as e:
            _logger.error(e)
            reverse_sync_email.sendReport("Contacts", e)
        _logger.info("End Reverse Sync Contacts")
