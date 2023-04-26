# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import binascii

from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers.portal import (
    pager as portal_pager,
    get_records_pager,
)
from odoo.addons.sale.controllers.portal import CustomerPortal
from odoo.osv import expression
import logging

_logger = logging.getLogger(__name__)


class CustomerPortalINH(CustomerPortal):
    def _prepare_portal_layout_values(self):
        values = super(CustomerPortalINH, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id

        SaleOrder = request.env["sale.order"].sudo()
        quotation_count = SaleOrder.search_count(
            [
                ("partner_id", "child_of", [partner.id]),
                ("state", "in", ["sent", "cancel"]),
            ]
        )
        values["quotation_count"] = quotation_count
        order_count = SaleOrder.search_count(
            [
                ("partner_id", "child_of", [partner.id]),
                ("state", "in", ["sale", "done"]),
            ]
        )
        values["order_count"] = order_count
        return values

    #
    # Quotations and Sales Orders
    #

    @http.route(["/my/orders/<int:order_id>"], type="http", auth="public", website=True)
    def portal_order_page(
        self,
        order_id,
        report_type=None,
        access_token=None,
        message=False,
        download=False,
        **kw
    ):
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if report_type in ("html", "pdf", "text"):
            return self._show_report(
                model=order_sudo,
                report_type=report_type,
                report_ref="sale.action_report_saleorder",
                download=download,
            )

        # use sudo to allow accessing/viewing orders for public user
        # only if he knows the private token
        if order_sudo:
            # Const ID is the ID assigneg to Derek DeBlois
            constId = [58319]
            # store the date as a string in the session to allow serialization
            now = fields.Date.today().isoformat()
            session_obj_date = request.session.get("view_quote_%s" % order_sudo.id)
            if request.env.user.share and access_token:
                request.session["view_quote_%s" % order_sudo.id] = now
                body = _(
                    "Quotation %s viewed by customer %s",
                    order_sudo.name,
                    request.env.user.partner_id.name,
                )
                _message_post_helper(
                    "sale.order",
                    order_sudo.id,
                    body,
                    token=order_sudo.access_token,
                    message_type="notification",
                    subtype_xmlid="mail.mt_note",
                    partner_ids=order_sudo.user_id.sudo().partner_id.ids,
                )
                _message_post_helper(
                    "sale.order",
                    order_sudo.id,
                    body,
                    token=order_sudo.access_token,
                    message_type="notification",
                    subtype_xmlid="mail.mt_note",
                    partner_ids=constId,
                )

        values = {
            "sale_order": order_sudo,
            "token": access_token,
            "return_url": "/shop/payment/validate",
            "bootstrap_formatting": True,
            "partner_id": order_sudo.partner_id.id,
            "report_type": "html",
            "action": order_sudo._get_portal_return_action(),
            "message": message,
        }

        return request.render("sale.sale_order_portal_template", values)

    @http.route(
        ["/my/quotes", "/my/quotes/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_quotes(
        self, page=1, date_begin=None, date_end=None, sortby=None, **kw
    ):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleOrder = request.env["sale.order"].sudo()

        domain = [
            ("partner_id", "child_of", [partner.id]),
            ("state", "in", ["sent", "cancel"]),
        ]

        searchbar_sortings = {
            "date": {"label": _("Order Date"), "order": "date_order desc"},
            "name": {"label": _("Reference"), "order": "name"},
            "stage": {"label": _("Stage"), "order": "state"},
        }

        # default sortby order
        if not sortby:
            sortby = "date"
        sort_order = searchbar_sortings[sortby]["order"]

        if date_begin and date_end:
            domain += [
                ("create_date", ">", date_begin),
                ("create_date", "<=", date_end),
            ]

        # count for pager
        quotation_count = SaleOrder.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/quotes",
            url_args={"date_begin": date_begin, "date_end": date_end, "sortby": sortby},
            total=quotation_count,
            page=page,
            step=self._items_per_page,
        )
        # search the count to display, according to the pager data
        quotations = SaleOrder.search(
            domain, order=sort_order, limit=self._items_per_page, offset=pager["offset"]
        )
        request.session["my_quotations_history"] = quotations.ids[:100]

        values.update(
            {
                "date": date_begin,
                "quotations": quotations.sudo(),
                "page_name": "quote",
                "pager": pager,
                "default_url": "/my/quotes",
                "searchbar_sortings": searchbar_sortings,
                "sortby": sortby,
            }
        )

        return request.render("sale.portal_my_quotations", values)
