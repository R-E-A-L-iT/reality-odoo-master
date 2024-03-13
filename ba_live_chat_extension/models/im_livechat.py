# -*- coding: utf-8 -*-
##############################################################################
#    Copyright (C) 2015 - Present, Braincrew Apps (<http://www.braincrewapps.com>). All Rights Reserved

# Odoo Proprietary License v1.0
#
# This software and associated files (the "Software") may only be used (executed,
# modified, executed after modifications) if you have purchased a valid license
# from the authors, typically via Odoo Apps,  braincrewapps.com, or if you have received a written
# agreement from the authors of the Software.
#
# You may develop Odoo modules that use the Software as a library (typically
# by depending on it, importing it and using its resources), but without copying
# any source code or material from the Software. You may distribute those
# modules under the license of your choice, provided that this license is
# compatible with the terms of the Odoo Proprietary License (For example:
# LGPL, MIT, or proprietary licenses similar to this one).
#
# It is forbidden to publish, distribute, sublicense, or sell copies of the Software
# or modified copies of the Software.
#
# The above copyright notice and this permission notice must be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

##############################################################################
from odoo import fields, models, api, tools
import random

class ImLivechatuserSequence(models.Model):
    _name = 'im_livechat.user.sequence'
    _description = 'IM LiveChat User Sequence'
    _order = 'sequence'

    name = fields.Many2one('res.users', string='User')
    sequence = fields.Integer(string='Sequence', default=1)
    livechat_id = fields.Many2one('im_livechat.channel', string='Live Chat')


class ImLivechatChannel(models.Model):
    _inherit = 'im_livechat.channel'

    user_sequences = fields.One2many('im_livechat.user.sequence', 'livechat_id', string='Live Chat')

    def _get_random_operator(self):
        operators = self._get_available_users()
        if len(operators) == 0:
            return False

        self.env.cr.execute("""SELECT COUNT(DISTINCT c.id), c.livechat_operator_id
            FROM mail_channel c
            LEFT OUTER JOIN mail_message m ON c.id = m.res_id AND m.model = 'mail.channel'
            WHERE c.channel_type = 'livechat'
            AND c.livechat_operator_id in %s
            AND m.create_date > ((now() at time zone 'UTC') - interval '30 minutes')
            GROUP BY c.livechat_operator_id
            ORDER BY COUNT(DISTINCT c.id) asc""", (tuple(operators.mapped('partner_id').ids),))
        active_channels = self.env.cr.dictfetchall()

        # If inactive operator(s), return one of them
        active_channel_operator_ids = [active_channel['livechat_operator_id'] for active_channel in active_channels]
        inactive_operators = [operator for operator in operators if operator.partner_id.id not in active_channel_operator_ids]
        if inactive_operators:
            return random.choice(inactive_operators)

        # If no inactive operator, active_channels is not empty as len(operators) > 0 (see above).
        # Get the less active operator using the active_channels first element's count (since they are sorted 'ascending')
        lowest_number_of_conversations = active_channels[0]['count']
        less_active_operator = random.choice([
            active_channel['livechat_operator_id'] for active_channel in active_channels
            if active_channel['count'] == lowest_number_of_conversations])

        next_operator_as_per_sequence = False
        if operators and self.sudo().user_sequences:
            for user_next_in_sequence in self.sudo().user_sequences:
                if user_next_in_sequence and user_next_in_sequence.name and user_next_in_sequence.name.id in operators:
                    next_operator_as_per_sequence = user_next_in_sequence.name
                    break
        if next_operator_as_per_sequence:
            return next(next_operator_as_per_sequence)
        else:
            # convert the selected 'partner_id' to its corresponding res.users
            return next(operator for operator in operators if operator.partner_id.id == less_active_operator)


