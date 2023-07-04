from odoo import models
from odoo.tools.translate import _
import logging
from itertools import groupby
from functools import partial
from datetime import datetime, timedelta
from .utilities import utilities

# -*- coding: utf-8 - *-


_logger = logging.getLogger(__name__)

SKIP_NO_CHANGE = True


class syncWeb:
    def __init__(self, name, sheet, database):
        self.name = name
        self.sheet = sheet
        self.database = database

    def syncWebCode(self, sheet):
        # check sheet width to filter out invalid sheets
        # every company tab will have the same amount of columns (Same with others)
        sheetWidth = 13
        columns = dict()
        missingColumn = False

        msg = ""
        # Calculate Indexes
        if "Page ID" in sheet[0]:
            columns["id"] = sheet[0].index("Page ID")
        else:
            msg = utilities.buildMSG(msg, self.name, "Header", "Page ID Missing")
            missingColumn = True

        if "Type" in sheet[0]:
            columns["type"] = sheet[0].index("Type")
        else:
            msg = utilities.buildMSG(msg, self.name, "Header", "Type Missing")
            missingColumn = True

        if "HTML English" in sheet[0]:
            columns["html_en"] = sheet[0].index("HTML English")
        else:
            msg = utilities.buildMSG(msg, self.name, "Header", "HTML English Missing")
            missingColumn = True

        if "Specs English" in sheet[0]:
            columns["specs_en"] = sheet[0].index("Specs English")
        else:
            msg = utilities.buildMSG(msg, self.name, "Header", "Specs English Missing")
            missingColumn = True

        if "HTML French" in sheet[0]:
            columns["html_fr"] = sheet[0].index("HTML French")
        else:
            msg = utilities.buildMSG(msg, self.name, "Header", "HTML French Missing")
            missingColumn = True

        if "Specs French" in sheet[0]:
            columns["specs_fr"] = sheet[0].index("Specs French")
        else:
            msg = utilities.buildMSG(msg, self.name, "Header", "Specs French Missing")
            missingColumn = True

        if "Enabled" in sheet[0]:
            columns["enabled"] = sheet[0].index("Enabled")
        else:
            msg = utilities.buildMSG(msg, self.name, "Header", "Enable Missing")
            missingColumn = True

        if "Valid" in sheet[0]:
            columns["valid"] = sheet[0].index("Valid")
        else:
            msg = utilities.buildMSG(msg, self.name, "Header", "Valid Missing")
            missingColumn = True

        if "Continue" in sheet[0]:
            columns["continue"] = sheet[0].index("Continue")
        else:
            msg = utilities.buildMSG(msg, self.name, "Header", "Continue Missing")
            missingColumn = True

        if len(sheet[0]) != sheetWidth or missingColumn:
            msg = utilities.buildMSG(
                msg,
                self.name,
                "Header",
                f"Sheet Width is {len(sheet[0])}. Expected {sheetWidth}",
            )
            self.database.sendSyncReport(msg)
            _logger.info("Sheet Width: " + str(len(sheet[0])))
            return True, msg

        i = 1

        # loop through all the rows
        while True:
            # check if should continue
            _logger.info("Website: " + str(i))
            if i == len(sheet) or str(sheet[i][columns["continue"]]).upper() != "TRUE":
                break

            # validation checks
            if not utilities.check_id(str(sheet[i][columns["id"]])):
                _logger.info("id")
                msg = utilities.buildMSG(
                    msg, self.name, str(sheet[i][columns["id"]]), "Invalid ID"
                )
                i += 1
                continue

            if not sheet[i][columns["enabled"]].upper() == "TRUE":
                i += 1
                continue

            if not sheet[i][columns["valid"]].upper() == "TRUE":
                _logger.info("Web Valid")
                msg = utilities.buildMSG(
                    msg, self.name, str(sheet[i][columns["id"]]), "Invalid Row"
                )
                i += 1
                continue     
            
            # if it gets here data should be valid
            try:
                # Inititilize values
                _logger.info("step 1")
                _logger.info(sheet[i][columns["id"]])

                _logger.info("step 2")
                external_id = str(sheet[i][columns["id"]])

                _logger.info("step 3")
                page_type = str(sheet[i][columns["type"]])

                _logger.info("step 4")
                msg += self.updatePage(
                    external_id, sheet[i][columns["html_en"]], "English"
                )

                _logger.info("step 5")
                msg += self.updatePage(
                    external_id, sheet[i][columns["html_fr"]], "French"
                )

                # Sync Extras
                _logger.info("step 6")
                msg += self.updateSpecs(
                    external_id, page_type, sheet[i][columns["specs_en"]], "English"
                )

                _logger.info("step 7")
                msg += self.updateSpecs(
                    external_id, page_type, sheet[i][columns["specs_fr"]], "French"
                )

                _logger.info("step 8")
                i += 1
            except Exception as e:
                _logger.error(sheet[i][columns["id"]])
                _logger.error(e)
                msg = utilities.buildMSG(
                    msg, self.name, str(sheet[i][columns["id"]]), str(e)
                )
                msg = ""
                return True, msg
        return False, msg

    def get_page(self, id):
        # Get or create page
        page_list = self.database.env["ir.model.data"].search(
            [("name", "=", id), ("model", "=", "ir.ui.view")]
        )
        page = None
        if len(page_list) == 0:
            page = self.database.env["ir.ui.view"].create(
                {"name": id, "type": "qweb", "arch": "<div></div>"}
            )
            self.database.env["ir.model.data"].create(
                {"name": id, "model": "ir.ui.view", "res_id": page.id}
            )
            page.key = id
            self.database.env["ir.model.data"].create(
                {"name": page.id, "model": "ir.ui.view"}
            )
        elif len(page_list) == 1:
            page = self.database.env["ir.ui.view"].search(
                [("id", "=", page_list[0].res_id)]
            )
        return page

    def updateSpecs(self, id: str, page_type: str, html: str, lang: str) -> str:
        # Update Specs View
        _logger.info("lang_code: " + str(id))
        _logger.info("page_type: " + str(page_type))
        _logger.info("html: " + str(html))
        _logger.info("lang: " + str(lang))

        lang_code = ""
        if lang == "English":
            lang_code = "en"
        elif lang == "French":
            lang_code = "fr"
        _logger.info("lang_code:" + str(lang_code))

        id = str(id) + "_specs_" + str(lang_code)
        _logger.info("id (new): " + str(id))

        if page_type != "product":
            return ""        

        # Get or create page
        page = self.get_page(id)
        _logger.info("page: " + str(page))

        opener = '<?xml version="1.0"?>\n'
        _logger.info("opener: " + str(opener))

        full_html = opener + html

        page.arch = full_html
        return ""

    def updatePage(self, id: str, html: str, lang: str) -> str:
        # Update main page view
        msg = ""
        langOps = None
        if lang == "English":
            external_id = id + "_en"
            langOps = "['en_CA', 'en_US']"
        elif lang == "French":
            external_id = id + "_fr"
            langOps = "['fr_CA']"
        # Get existing Page
        pageIds = self.database.env["ir.model.data"].search(
            [("name", "=", external_id), ("model", "=", "ir.ui.view")]
        )
        if len(pageIds) > 0:
            page = self.database.env["ir.ui.view"].browse(pageIds[-1].res_id)
            opener = '<?xml version="1.0"?>\n<data>\n<xpath expr="//div[@id=&quot;wrap&quot;]" position="inside">\n'
            conditionOpen = '<t t-if="lang in ' + langOps + '">\n'
            footer = '<t t-call="custom.custom-footer"/>\n'
            conditionClose = "</t>\n"
            closer = "</xpath>\n</data>"
            page.arch_base = (
                opener + conditionOpen + html + footer + conditionClose + closer
            )
        else:
            msg = utilities.buildMSG(
                msg, self.name, str(external_id), "Page Not Created"
            )
            _logger.error(str(external_id) + " Page Not Created")
        return msg
