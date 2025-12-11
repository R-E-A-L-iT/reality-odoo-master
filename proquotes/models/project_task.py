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
        Override message_post to handle mixed follower/non-follower recipients.
        Send separate emails: followers get default template, non-followers get simple layout.
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

            # Separate followers and non-followers
            follower_recipients = [pid for pid in recipient_ids if pid in follower_ids]
            non_follower_recipients = [pid for pid in recipient_ids if pid not in follower_ids]

            # If we have both types, we need to send separate emails
            if follower_recipients and non_follower_recipients:
                # First, send to followers with default layout
                kwargs_followers = dict(kwargs)
                kwargs_followers['partner_ids'] = [(6, 0, follower_recipients)]
                super(ProjectTask, self).message_post(**kwargs_followers)

                # Then, send to non-followers with simple layout
                self.simple_email_layout = True
                kwargs_non_followers = dict(kwargs)
                kwargs_non_followers['partner_ids'] = [(6, 0, non_follower_recipients)]
                self = self.with_context(project_task_non_followers=non_follower_recipients)
                result = super(ProjectTask, self).message_post(**kwargs_non_followers)

                # Restore original value
                self.simple_email_layout = original_layout
                return result

            # If only non-followers
            elif non_follower_recipients:
                self.simple_email_layout = True
                self = self.with_context(project_task_non_followers=non_follower_recipients)

        # Call parent method
        result = super(ProjectTask, self).message_post(**kwargs)

        # Restore original value
        if self.simple_email_layout != original_layout:
            self.simple_email_layout = original_layout

        return result

    def _message_post_after_hook(self, message, msg_vals):
        """
        Override to prevent auto-following of recipients who were non-followers
        when the email was sent via composer.
        """
        # Get non-follower IDs from context
        non_follower_ids = self.env.context.get('project_task_non_followers', [])

        # Call parent method
        result = super(ProjectTask, self)._message_post_after_hook(message, msg_vals)

        # Remove non-followers who were auto-added by the parent method
        if non_follower_ids:
            # Find followers that were just added (non-followers)
            followers_to_remove = self.env['mail.followers'].search([
                ('res_model', '=', 'project.task'),
                ('res_id', '=', self.id),
                ('partner_id', 'in', non_follower_ids)
            ])
            if followers_to_remove:
                followers_to_remove.sudo().unlink()
                _logger.info(f"Removed auto-added followers: {non_follower_ids} from task {self.id}")

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