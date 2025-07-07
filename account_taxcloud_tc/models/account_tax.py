# Copyright (c) 2015-2023 Odoo S.A.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import re

from odoo import api, models

class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.onchange('name')
    def onchange_name(self):
        name = self.name
        amount_str = "%.3f " % (self.amount)
        if name and amount_str not in name and \
            self.amount and self.amount_type in ('percent','division'):
            self.name = re.sub(r'\s+\d*\.?\d*\s?%', " %.3f %%" % (self.amount), name)

    @api.onchange('amount')
    def onchange_amount(self):
        name = self.name
        if name and self.amount_type in ('percent','division'):
            self.name = re.sub(r'\s+\d*\.?\d*\s?%', " %.3f %%" % (self.amount), name)
