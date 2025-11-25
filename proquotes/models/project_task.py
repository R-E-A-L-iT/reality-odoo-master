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

class ProjectTask(models.Model):
    _inherit = 'project.task'

    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Medium'),
        ('2', 'High'),
        ('3', 'Very High'),
    ], default='0', index=True, string="Priority", tracking=True)

    simple_email_layout = fields.Boolean(
        string='Send Simple Email',
        default=False,
        help='If enabled, emails will be sent without project/task details header'
    )

    def message_post(self, **kwargs):
        """
        Override message_post to detect if the email is being sent to non-followers.
        If recipients are not followers, set simple_email_layout to True temporarily.
        """
        # Store original value
        original_layout = self.simple_email_layout

        # Check if this is an email (not internal note)
        subtype_xmlid = kwargs.get('subtype_xmlid', 'mail.mt_comment')
        is_note = subtype_xmlid == 'mail.mt_note'

        # Get partner_ids from kwargs
        partner_ids = kwargs.get('partner_ids', [])

        # If partner_ids is provided and this is not a note
        if partner_ids and not is_note:
            # Normalize partner_ids to a list of IDs
            if isinstance(partner_ids, (list, tuple)):
                # Handle command format [(4, id), (4, id)] or direct IDs [id, id]
                recipient_ids = []
                for item in partner_ids:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        # Command format (4, id) or (6, 0, [ids])
                        if item[0] == 4:  # Link command
                            recipient_ids.append(item[1])
                        elif item[0] == 6:  # Set command
                            recipient_ids.extend(item[2] if len(item) > 2 else [])
                    elif isinstance(item, int):
                        recipient_ids.append(item)
            else:
                recipient_ids = []

            # Get current followers
            follower_ids = self.message_partner_ids.ids

            # Check if any recipient is not a follower
            has_non_follower = any(pid not in follower_ids for pid in recipient_ids)

            # If sending to non-followers, enable simple layout
            if has_non_follower:
                self.simple_email_layout = True

        # Call parent method
        result = super(ProjectTask, self).message_post(**kwargs)

        # Restore original value
        if self.simple_email_layout != original_layout:
            self.simple_email_layout = original_layout

        return result

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        """
        Override to customize recipient groups for project tasks.
        Adds portal access button with task-specific title for followers.
        """
        groups = super(ProjectTask, self)._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )

        if not self:
            return groups

        self.ensure_one()

        # Check if model has portal mixin (project.task inherits from portal.mixin)
        if not isinstance(self, self.env.registry['portal.mixin']):
            return groups

        # Get portal access link
        access_link = self.get_portal_url()

        # Update follower group to add "View Task" button
        for group in groups:
            group_name, match_func, options = group

            if group_name == 'follower':
                options['has_button_access'] = True
                options['button_access'] = {
                    'url': access_link,
                    'title': _('View Task')
                }

        return groups