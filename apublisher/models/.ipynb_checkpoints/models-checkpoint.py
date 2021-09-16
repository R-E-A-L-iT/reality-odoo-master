# -*- coding: utf-8 -*-
 # Part of Odoo. See LICENSE file for full copyright and licensing details.

 import itertools
 import logging
 from collections import defaultdict

 from odoo import api, fields, models, tools, _, SUPERUSER_ID
 from odoo.exceptions import ValidationError, RedirectWarning, UserError
 from odoo.osv import expression

 _logger = logging.getLogger(__name__)

 class publish_state(models.Model):
     _inherit = "product.template"

     publish_type = fields.selection(
         [
             ('FALSE','False'),
             ('TRUE','True'),
             ('CAN','Canada'),
             ('USA','America')
         ], required=True, default='FALSE', help='publish state region dependency')