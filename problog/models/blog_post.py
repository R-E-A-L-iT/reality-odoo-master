# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.addons.http_routing.models.ir_http import slug, unslug
from odoo.addons.website.tools import text_from_html
from odoo.tools.json import scriptsafe as json_scriptsafe
from odoo.tools.translate import html_translate


class BlogPost(models.Model):
    _inherit = "blog.post"
    post_date = fields.Date(string="Post Date")
