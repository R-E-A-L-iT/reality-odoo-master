# -*- coding: utf-8 -*-
from . import models
from . import controllers
from . import report

import logging
_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Make 'Has Bill of Materials' a default chip-filter on the Scheduled Rentals view.

    The "Confirmed Orders" chip works because the search view has a named filter
    (name="Rentals") and the action's context carries search_default_Rentals=1.
    We use the same mechanism:
      1. Create an ir.ui.view inheritance on the search view to add our named filter.
      2. Set search_default_proquotes_has_bom=1 in the action's context.

    Everything is done by searching at runtime so we don't need hard-coded external IDs.
    """
    import ast as _ast
    from lxml import etree as _etree

    # ── 1. Find the Scheduled Rentals action ────────────────────────────────
    action = env['ir.actions.act_window'].sudo().search([
        ('res_model', '=', 'sale.order.line'),
        ('name', 'ilike', 'Scheduled Rental'),
    ], limit=1)

    if not action:
        _logger.warning(
            "proquotes post_init_hook: could not find a 'Scheduled Rentals' "
            "action on sale.order.line — the BOM default filter was not applied."
        )
        return

    # ── 2. Locate the search view used by this action ────────────────────────
    search_view = action.search_view_id
    if not search_view:
        # Fall back: find the highest-priority active search view for this model.
        search_view = env['ir.ui.view'].sudo().search([
            ('model', '=', 'sale.order.line'),
            ('type', '=', 'search'),
            ('active', '=', True),
        ], order='priority asc', limit=1)

    if not search_view:
        _logger.warning(
            "proquotes post_init_hook: no search view found for sale.order.line "
            "— the BOM filter chip was not added."
        )
        return

    # ── 3. Inject our named filter via an ir.ui.view inheritance ────────────
    View = env['ir.ui.view'].sudo()
    INHERIT_NAME = 'sale.order.line.search.proquotes.bom.filter'

    existing_inherit = View.search([
        ('name', '=', INHERIT_NAME),
        ('model', '=', 'sale.order.line'),
    ], limit=1)

    filter_arch = (
        '<data>'
        '<xpath expr="//search" position="inside">'
        '<filter name="proquotes_has_bom"'
        ' string="Has Bill of Materials"'
        ' domain="[(\'product_id.product_tmpl_id.bom_ids\', \'!=\', False)]"/>'
        '</xpath>'
        '</data>'
    )

    if existing_inherit:
        existing_inherit.write({'arch_base': filter_arch})
        _logger.info("proquotes post_init_hook: updated search-view inheritance '%s'.", INHERIT_NAME)
    else:
        View.create({
            'name': INHERIT_NAME,
            'model': 'sale.order.line',
            'type': 'search',
            'inherit_id': search_view.id,
            'arch_base': filter_arch,
            'active': True,
        })
        _logger.info(
            "proquotes post_init_hook: created search-view inheritance '%s' on '%s'.",
            INHERIT_NAME, search_view.name,
        )

    # ── 4. Set search_default_proquotes_has_bom=1 in the action's context ───
    try:
        ctx = _ast.literal_eval(action.context or '{}')
        if not isinstance(ctx, dict):
            ctx = {}
    except Exception:
        ctx = {}

    if ctx.get('search_default_proquotes_has_bom') != 1:
        ctx['search_default_proquotes_has_bom'] = 1
        action.write({'context': str(ctx)})
        _logger.info(
            "proquotes post_init_hook: set search_default_proquotes_has_bom=1 "
            "on action '%s'.", action.name,
        )
