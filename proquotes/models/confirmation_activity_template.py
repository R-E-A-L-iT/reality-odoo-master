# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProquotesConfirmationActivityTemplate(models.Model):
    """
    A reusable template that defines an activity to be created automatically
    when a sales or rental quote is confirmed via action_confirm.

    One record = one activity that will be spawned on every matching order.
    Add as many records as needed (one per employee / per task type).
    """
    _name = 'proquotes.confirmation.activity.template'
    _description = 'Confirmation Activity Template'
    _order = 'sequence, id'

    name = fields.Char(
        string='Activity Summary',
        required=True,
        help='Short title shown on the activity card (e.g. "Prepare delivery", "Send invoice").',
    )
    description = fields.Html(
        string='Note',
        help='Detailed instructions or notes attached to the activity.',
    )
    activity_type_id = fields.Many2one(
        'mail.activity.type',
        string='Activity Type',
        required=True,
        default=lambda self: self.env.ref(
            'mail.mail_activity_data_todo', raise_if_not_found=False
        ),
        help='The Odoo activity type (e.g. To-Do, Email, Phone Call).',
    )
    user_id = fields.Many2one(
        'res.users',
        string='Assigned To',
        required=True,
        help='The user who will receive this activity when the order is confirmed.',
    )
    days_after_confirmation = fields.Integer(
        string='Days After Confirmation',
        default=0,
        help=(
            'Deadline = confirmation date + this many days.  '
            'Use 0 to set the deadline on the same day as confirmation.'
        ),
    )
    order_type = fields.Selection(
        selection=[
            ('sale',   'Sales Orders Only'),
            ('rental', 'Rental Orders Only'),
            ('both',   'Both Sales & Rentals'),
        ],
        string='Apply To',
        default='both',
        required=True,
        help='Controls whether this activity is created for sales orders, rental orders, or both.',
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order; activities with lower sequence numbers appear first.',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Uncheck to disable this template without deleting it.',
    )
