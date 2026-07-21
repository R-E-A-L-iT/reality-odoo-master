# -*- coding: utf-8 -*-
#
# NEUTRALIZED FOR THE ODOO 19 MIGRATION
# -------------------------------------
# This module extended the Enterprise `sale.rental.schedule` report model's
# _query() so the Rental Schedule report only counted selected rental order
# lines (is_rental + is_selected). That model does not exist in this v19 registry
# (the sale_renting rental-schedule report was reworked in v19), so the extension
# can't load. It is dropped from models/__init__.py.
#
# To restore the "only selected lines" filtering, re-implement the _query()
# override against the v19 sale.rental.schedule report structure.
