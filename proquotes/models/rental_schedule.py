# -*- coding: utf-8 -*-
#
# NEUTRALIZED FOR THE ODOO 19 MIGRATION
# -------------------------------------
# This module extended the Enterprise `sale.rental.schedule` report model's
# _query() to filter rental order lines. That model does not exist in this v19
# registry (the sale_renting rental-schedule report was reworked in v19), so the
# extension can't load. It is dropped from models/__init__.py.
#
# The custom line-selection system it relied on has since been removed entirely
# (Odoo 19 native optional sections replace it), so there is nothing to restore.
