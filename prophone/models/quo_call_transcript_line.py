# -*- coding: utf-8 -*-

from odoo import fields, models


class QuoCallTranscriptLine(models.Model):
    _name = "quo.call.transcript.line"
    _description = "Quo Call Transcript Line"
    _order = "sequence asc, id asc"

    transcript_id = fields.Many2one("quo.call.transcript", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=1, index=True)

    start_ms = fields.Integer(string="Start (ms)")
    end_ms = fields.Integer(string="End (ms)")
    content = fields.Text(string="Content")

    identifier = fields.Char(string="Identifier")
    user_id = fields.Char(string="User ID")
    speaker_label = fields.Char(string="Speaker")

    partner_id = fields.Many2one("res.partner", string="Partner", index=True)
