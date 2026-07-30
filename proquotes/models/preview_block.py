# -*- coding: utf-8 -*-

from odoo import fields, models


class PreviewBlock(models.Model):
    """A selectable, optional content block for the online quote preview
    (e.g. the APPROVE financing banner, the OmniGO advertisement). Chosen per
    quote in the Quote Builder tab ("Other Blocks"), replacing the old
    per-block checkboxes / specially-named sections."""

    _name = "proquotes.preview.block"
    _description = "Quote Preview Block"
    _order = "sequence, name"

    name = fields.Char(string="Name", required=True, translate=True)
    code = fields.Char(
        string="Code",
        required=True,
        help="Technical code the quote preview template checks to render this block.",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
