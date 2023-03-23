from .googlesheetsAPI import sheetsAPI
from .email import reverse_sync_email
from odoo import api, fields, models, SUPERUSER_ID, _

import logging
_logger = logging.getLogger(__name__)


class reverse_sync_contacts(models.Model):
    _name = "sync.reverse_sync_contact"
    _description = "Reverse Contact Sync"

    def getSpreadSheetID(self):
        return "1pDPKv2bH8_Be5aCCyU4bqTuwJNcXsADlAYDAGG8P1Ls"

    def createHeader(self):
        return ["First Name", "Last Name", "Phone", "Email", "Company", "Street Address", "City", "State/Region", "Country", "Postal Code", "Industry", "Job Title", "Mobile"]

    def value(self, headerItem, expected, cellValue):
        _logger.warning(headerItem)
        if (headerItem != expected):
            raise Exception("Invalid Header Item: " + headerItem)
        if (cellValue == False):
            return ""
        return str(cellValue)

    def createRow(self, header, contact):
        row = []
        _logger.error(str(contact.name))
        if (contact.name == False):
            return None
        row.append(self.value(
            header[0], "First Name", contact.name.split(" ")[0]))

        row.append(self.value(
            header[1], "Last Name", " ".join(contact.name.split(" ")[1:])))

        row.append(self.value(header[2], "Phone", contact.phone))
        row.append(self.value(header[3], "Email", contact.email))
        row.append(self.value(header[4], "Company", contact.company_id.name))
        row.append(self.value(header[5], "Street Address", contact.street))
        row.append(self.value(header[6], "City", contact.city))
        row.append(self.value(
            header[7], "State/Region", contact.state_id.code))
        row.append(self.value(header[8], "Country", contact.country_id.name))
        row.append(self.value(header[9], "Postal Code", contact.zip))
        row.append(self.value(
            header[10], "Industry", contact.industry_id.name))
        row.append(self.value(header[11], "Job Title", contact.function))
        row.append(self.value(header[12], "Mobile", contact.mobile))
        return row

    def createBlank(self, length):
        return ['' for _ in range(length)]

    def reverseSync(self, psw):
        _logger.info("Reverse Sync Contacts")
        try:
            spreadSheetID = self.getSpreadSheetID()
            sheet = sheetsAPI.getSpreadSheet(
                spreadSheetID, sheetIndex=0, auth=psw)
            header = self.createHeader()
            width = len(header)
            sheetTable = [header]
            contacts = self.env['res.partner'].search(
                [('is_company', '=', False)])

            for contact in contacts:
                row = self.createRow(header, contact)
                if (row != None):
                    sheetTable.append(row)
            height = len(sheet.get_all_values())

            while (len(sheetTable) < height):
                sheetTable.append(self.createBlank(width))
            writeRange = 'A1:M' + str(len(sheetTable))
            sheet.update(writeRange, sheetTable)
            reverse_sync_email.sendReport("Contacts", "Succsess")
        except Exception as e:
            _logger.error(e)
            reverse_sync_email.sendReport("Contacts", e)
        _logger.info("End Reverse Sync Contacts")
