# -*- coding: utf-8 -*-

from .utilities import utilities
from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo.tools.translate import _
from odoo import models

_logger = logging.getLogger(__name__)

SKIP_NO_CHANGE = True


class syncWeb():

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
        if ("Page ID" in sheet[0]):
            columns["id"] = sheet[0].index("Page ID")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "Page ID Missing")
            missingColumn = True

        if ("Type" in sheet[0]):
            columns["type"] = sheet[0].index("Type")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "Type Missing"
            )
            missingColumn = True

        if ("HTML English" in sheet[0]):
            columns["html_en"] = sheet[0].index("HTML English")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "HTML English Missing")
            missingColumn = True

        if ("Specs English" in sheet[0]):
            columns["specs_en"] = sheet[0].index("Specs English")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "Specs English Missing"
            )
            missingColumn = True

        if ("HTML French" in sheet[0]):
            columns["html_fr"] = sheet[0].index("HTML French")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "HTML French Missing")
            missingColumn = True

        if ("Specs French" in sheet[0]):
            columns["specs_fr"] = sheet[0].index("Specs French")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "Specs French Missing"
            )
            missingColumn = True

        if ("Enabled" in sheet[0]):
            columns["enabled"] = sheet[0].index("Enabled")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "Enable Missing")
            missingColumn = True

        if ("Valid" in sheet[0]):
            columns["valid"] = sheet[0].index("Valid")
        else:
            msg = utilities.buildMSG(msg, self.name, "Header", "Valid Missing")
            missingColumn = True

        if ("Continue" in sheet[0]):
            columns["continue"] = sheet[0].index("Continue")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "Continue Missing")
            missingColumn = True

        if (len(sheet[0]) != sheetWidth or missingColumn):
            msg = utilities.buildMSG(
                msg, self.name, "Header", f'Sheet Width is {len(sheet[0])}. Expected {sheetWidth}')
            self.database.sendSyncReport(msg)
            _logger.info("Sheet Width: " + str(len(sheet[0])))
            return True, msg

        i = 1

        while (True):
            _logger.info("Website: " + str(i))
            if (i == len(sheet) or str(sheet[i][columns["continue"]]).upper() != "TRUE"):
                break

            if (not utilities.check_id(str(sheet[i][columns["id"]]))):
                _logger.info("id")
                msg = utilities.buildMSG(
                    msg, self.name, str(sheet[i][columns["id"]]), "Invalid ID")
                i += 1
                continue

            if (not sheet[i][columns["enabled"]].upper() == "TRUE"):
                i += 1
                continue

            if (not sheet[i][columns["valid"]].upper() == "TRUE"):
                _logger.info("Web Valid")
                msg = utilities.buildMSG(
                    msg, self.name, str(sheet[i][columns["id"]]), "Invalid Row")
                i += 1
                continue

            try:
                _logger.info(sheet[i][columns["id"]])
                external_id = str(sheet[i][columns["id"]])
                page_type = str(sheet[i][columns["type"]])
                # _logger.info(external_id)
                msg += self.updatePage(
                    external_id, sheet[i][columns["html_en"]], "English")
                msg += self.updatePage(
                    external_id, sheet[i][columns["html_fr"]], "French")
                # Sync Extras
                msg += self.updateSpecs(external_id, page_type,
                                        sheet[i][columns["specs_en"]], "English")
                msg += self.updateSpecs(external_id, page_type,
                                        sheet[i][columns["specs_fr"]], "French")
                i += 1
            except Exception as e:
                _logger.info(sheet[i][columns['id']])
                _logger.error(e)
                msg = utilities.buildMSG(msg, self.name, str(
                    sheet[i][columns['id']]), str(e))
                msg = ""
                return True, msg
        return False, msg

    def get_page(self, id):
        page_list = self.database.env['ir.model.data'].search(
            [('name', '=', id), ('model', '=', 'ir.ui.view')])
        page = None
        if len(page_list) == 0:
            _logger.warning("Create")
            page = self.database.env['ir.ui.view'].create(
                {'name': id, 'arch': "<div></div>"})
            self.database.env['ir.model.data'].create(
                {'name': page.id, 'model': 'ir.ui.view'})
        elif len(page_list) == 1:
            _logger.warning("Get")
            # page = page_list[0]
        return page

    def updateSpecs(self, id: str, page_type: str, html: str, lang: str) -> str:
        lang_code = ""
        if (lang == "English"):
            lang_code = "en"
        elif (lang == "French"):
            lang_code = "fr"
        id = str(id) + "_specs_" + str(lang_code)
        if (page_type != "product"):
            return ""
        page = self.get_page(id)

        return ""

    def updatePage(self, id: str, html: str, lang: str) -> str:
        msg = ""
        langOps = None
        if lang == "English":
            external_id = id + "_en"
            langOps = "['en_CA', 'en_US']"
        elif lang == "French":
            external_id = id + "_fr"
            langOps = "['fr_CA']"
        pageIds = self.database.env['ir.model.data'].search(
            [('name', '=', external_id), ('model', '=', 'ir.ui.view')])
        # _logger.info(pageIds)
        if (len(pageIds) > 0):
            page = self.database.env['ir.ui.view'].browse(
                pageIds[-1].res_id)
            opener = "<?xml version=\"1.0\"?>\n<data>\n<xpath expr=\"//div[@id=&quot;wrap&quot;]\" position=\"inside\">\n"
            conditionOpen = "<t t-if=\"lang in " + langOps + "\">\n"
            footer = "<t t-call=\"custom.custom-footer\"/>\n"
            conditionClose = "</t>\n"
            closer = "</xpath>\n</data>"
            _logger.error(page.name)
            _logger.error(page.active)
            page.arch_base = opener + conditionOpen + \
                html + footer + conditionClose + closer
        else:
            msg = utilities.buildMSG(msg, self.name, str(
                external_id), "Page Not Created")
            _logger.info(str(external_id) + " Page Not Created")
        return (msg)
