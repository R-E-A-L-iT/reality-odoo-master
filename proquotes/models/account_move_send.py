# -*- coding: utf-8 -*-
#
# NEUTRALIZED FOR THE ODOO 19 MIGRATION
# -------------------------------------
# This module customized the invoice send-&-print flow on account.move.send
# (v17: a single TransientModel wizard). Odoo 19 split and redesigned it into an
# abstract mixin `account.move.send` plus a concrete `account.move.send.wizard`
# that now operates per single move (`move_id`, `template_id`) with no `move_ids`,
# `checkbox_send_mail`, `mode`, or `mail_template_id`, and removed helpers such as
# `_get_mail_move_values`. Several overridden mixin methods also changed signature.
#
# The whole customization is therefore incompatible and is dropped from
# models/__init__.py so the database can boot.
#
# REBUILD (custom invoice-emailing behavior to re-implement against the v19
# account.move.send / account.move.send.wizard API):
#   - Make the Send button readonly when every invoice's customer lacks an email
#     (send_mail_readonly + warning message).
#   - Fall back to sending to followers with an email when the customer has none.
#   - Only attach the invoice PDF when the mail template configures invoice reports
#     (report_template_ids / Dynamic Reports gating).
