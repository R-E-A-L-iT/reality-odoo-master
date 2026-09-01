# -*- coding: utf-8 -*-

import ast
import base64
from email.policy import default
import re

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class SaleOrderTemplateLine(models.Model):
    _inherit = "sale.order.template.line"
    
    # Per-language section titles carried by the template so quotes created from
    # it preserve the correct translations. See sale.order.line.section_name_translations.
    section_name_translations = fields.Json(string="Section Name Translations")

    hiddenSection = fields.Selection([
        ('yes', "Yes"),
        ('no', "No")], default='no', required=True, help="Field To Track if Sections are folded")

    quantityLocked = fields.Selection([
        ('yes', "Yes"),
        ('no', "No")], string="Lock Quantity", default="yes", required=True, help="Field to Lock Quantity on Products")

    def init(self):
        # This environment does not reliably create new columns on rebuild (same
        # problem proleads/proportal solve for their re-declared `mobile` fields).
        # Without the column, ANY read of a template line explodes with
        # "column sale_order_template_line.x_single_choice does not exist" — which
        # took out the whole "change the quotation template" onchange, since core's
        # _prepare_order_line_values reads every field on the line. init() runs on
        # every module -u, after base has fully loaded, so the column is guaranteed.
        super().init()
        self.env.cr.execute(
            "ALTER TABLE sale_order_template_line "
            "ADD COLUMN IF NOT EXISTS x_single_choice boolean"
        )

    # ── Single-choice sections on TEMPLATES ─────────────────────────────────
    # Mirrors sale.order.line.x_single_choice so a template can blueprint a
    # "customer picks exactly one" section. Only the FLAG lives here: a template
    # holds no customer selection, so there is no member tagging or quantity
    # cascade at this level. The flag is copied onto the generated order line
    # (see sale_order_template._prepare_sale_order_line_values) and the order
    # side then tags the members and enforces the one-selected invariant in
    # sale.order.line._link_selection_section_members().
    x_single_choice = fields.Boolean(
        string="Single Choice Section",
        default=False,
        copy=True,
        help="When set on a section, the customer may select only one of its "
             "products on the generated quote.",
    )

    def action_make_single_choice(self):
        """Flag this template section as single choice (mutually exclusive with
        the native optional mode, same rule as on the order line)."""
        self.ensure_one()
        if self.display_type not in ("line_section", "line_subsection"):
            return False
        if self.is_optional:
            return False
        self.x_single_choice = True
        return True

    def action_unset_single_choice(self):
        self.ensure_one()
        self.x_single_choice = False
        return True

    def action_make_optional(self):
        """Optional on a SUBSECTION — native "Set Optional" is only offered on
        top-level sections, so this backs the custom dropdown item."""
        self.ensure_one()
        if self.display_type not in ("line_section", "line_subsection"):
            return False
        self.is_optional = True
        self.x_single_choice = False
        return True

    def action_unset_optional(self):
        self.ensure_one()
        self.is_optional = False
        return True

    @api.onchange("name")
    def _proquotes_sync_section_translation(self):
        # Same seeding as sale.order.line: keep the current UI language's entry in
        # step with inline edits of a section title. Without this the Translate
        # dialog opened on a TEMPLATE line found an empty translations map and so
        # showed an empty English box, forcing the name to be retyped — whereas on
        # a quote it came pre-filled.
        for line in self:
            if line.display_type in ("line_section", "line_subsection"):
                lang = self.env.context.get("lang") or self.env.user.lang or "en_US"
                translations = dict(line.section_name_translations or {})
                if line.name:
                    if translations.get(lang) != line.name:
                        translations[lang] = line.name
                        line.section_name_translations = translations

    def _proquotes_section_name(self, lang=None):
        """Resolve a template section's display name for ``lang``, falling back to
        the raw name."""
        self.ensure_one()
        lang = lang or self.env.context.get("lang") or self.env.user.lang or "en_US"
        translations = self.section_name_translations or {}
        return translations.get(lang) or self.name or ""

    discount = fields.Float(
        string='Discount (%)',
        digits='Discount',
        default=0.0,
        help='Default percentage discount to apply when this template is used.'
    )