# -*- coding: utf-8 -*-
#
# NEUTRALIZED FOR THE ODOO 19 MIGRATION
# -------------------------------------
# This module extended the `mail.wizard.invite` TransientModel to force
# notify=False when adding followers. Odoo 19 removed the `mail.wizard.invite`
# wizard (adding followers no longer goes through it), so the model no longer
# exists and this extension can't be loaded. It is dropped from models/__init__.py
# and its inheriting view was removed from views/Quote/quote_wizard.xml.
#
# If the "don't notify when adding followers" behavior is still needed, reimplement
# it against the v19 follower-adding mechanism.
