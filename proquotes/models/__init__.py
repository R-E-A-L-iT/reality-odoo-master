# -*- coding: utf-8 -*-

from . import account_move_line
# account_move_send removed for Odoo 19: the account.move.send / account.move.send.wizard
# invoice-send flow was redesigned (move_id singular, template_id, no checkbox_send_mail/
# mode/move_ids; _get_mail_move_values removed). The customization needs a rebuild.
# from . import account_move_send
from . import account_move
from . import calendar_event
from . import crm_lead
from . import quotation_document
from . import helpdesk_ticket
from . import ir_ui_view
from . import mail_compose_message
from . import mail_thread
# mail_wizard_invite removed for Odoo 19: the mail.wizard.invite model no longer exists.
from . import models
from . import preconfigured_section
from . import product_product
from . import product_template
from . import project_task
from . import purchase_order
from . import renewal_maps
from . import res_company
from . import res_partner
from . import res_users
from . import sale_order_line
from . import sale_order_template_line
from . import sale_order_template
from . import sale_order
from . import sale_renting
# rental_schedule removed for Odoo 19: the sale.rental.schedule model (Enterprise
# sale_renting) is not present in this registry / was reworked in v19.
# from . import rental_schedule
from . import stock_lot
from . import stock_picking
from . import res_config_extend
from . import ccp_period_config
from . import ccp_scanner_config
from . import ccp_type_config
from . import rental_order_wizard
from . import confirmation_activity_template