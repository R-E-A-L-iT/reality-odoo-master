# -*- coding: utf-8 -*-


import logging

from odoo import api, fields, models
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    hide_on_portal = fields.Boolean(
        string="Hide on Portal",
        default=False,
    )

    rental_sale_order_id = fields.Many2one(
        'sale.order',
        string='Rental Order',
        index=True,
        copy=False,
        ondelete='set null',
    )

    rental_operation = fields.Selection(
        [('pickup', 'Rental Pickup'), ('return', 'Rental Return')],
        string='Rental Operation',
        copy=False,
    )

    def _get_available_footer_domain(self):
        return [
            ("active", "=", True),
            ("record_type", "=", "Footer"),
        ]

    @api.model
    def _get_first_available_footer(self, company=False):
        domain = self._get_available_footer_domain()
        footers = self.env["header.footer"].search(domain, order="id asc")
        if company:
            company_specific = footers.filtered(
                lambda f: not f.company_ids or company in f.company_ids
            )
            if company_specific:
                return company_specific[0]
        return footers[:1]

    @api.model
    def _get_user_company_footer(self, user=False, company=False):
        user = user or self.env.user
        company = company or self.env.company

        if not user or not company:
            return self.env["header.footer"]

        # New per-company mapping model from the previous change
        line = self.env["res.users.company.footer"].search(
            [
                ("user_id", "=", user.id),
                ("company_id", "=", company.id),
                ("active", "=", True),
            ],
            limit=1,
        )

        if line and line.footer_id and line.footer_id.active and line.footer_id.record_type == "Footer":
            return line.footer_id

        return self.env["header.footer"]

    @api.model
    def _get_company_default_footer(self, company=False):
        company = company or self.env.company
        if (
            company
            and company.default_footer_id
            and company.default_footer_id.active
            and company.default_footer_id.record_type == "Footer"
        ):
            return company.default_footer_id
        return self.env["header.footer"]

    @api.model
    def _default_footer_id(self):
        user = self.env.user
        company = self.env.company

        footer = self._get_user_company_footer(user=user, company=company)
        if footer:
            return footer.id

        footer = self._get_company_default_footer(company=company)
        if footer:
            return footer.id

        footer = self._get_first_available_footer(company=company)
        return footer.id if footer else False

    footer_id = fields.Many2one(
        "header.footer",
        string="Footer",
        required=True,
        domain="[('active', '=', True), ('record_type', '=', 'Footer')]",
        default=_default_footer_id,
    )

    def _ensure_moves_have_sale_line(self):
        """For every unlinked move in a custom rental picking, assign sale_line_id
        to the matching kit-component SOL (or any matching SOL as fallback).

        Called both at action_confirm time and _action_done time because sale_renting
        scans for moves with sale_line_id=False at both points to create "extra" SOLs.
        """
        for picking in self.filtered(
            lambda p: p.rental_sale_order_id and p.rental_operation in ('pickup', 'return')
        ):
            order = picking.rental_sale_order_id
            for move in picking.move_ids.filtered(lambda m: not m.sale_line_id and m.product_id):
                kit_comp = order.order_line.filtered(
                    lambda l: l.product_id.id == move.product_id.id
                        and not l.display_type
                        and l.x_is_rental_kit_component
                )
                matching = kit_comp or order.order_line.filtered(
                    lambda l: l.product_id.id == move.product_id.id and not l.display_type
                )
                if matching:
                    move.sudo().write({'sale_line_id': matching[0].id})
                    _logger.info(
                        "Assigned sale_line_id=%s on move %s (product %s, picking %s)",
                        matching[0].id, move.id,
                        move.product_id.display_name, picking.name,
                    )

    def action_confirm(self):
        # Pre-assign sale_line_id before sale_renting's action_confirm hook fires.
        # sale_renting scans for moves with sale_line_id=False at confirm time and
        # creates "Extra line" SOLs for any it finds — pre-assigning here prevents that.
        self._ensure_moves_have_sale_line()
        return super().action_confirm()

    def _action_done(self):
        # Capture rental references before super() clears transient state
        rental_pickups = self.filtered(
            lambda p: p.rental_sale_order_id and p.rental_operation == 'pickup'
        )
        rental_returns = self.filtered(
            lambda p: p.rental_sale_order_id and p.rental_operation == 'return'
        )

        # Run a second pass in case action_confirm split or re-created any moves.
        self._ensure_moves_have_sale_line()

        res = super()._action_done()

        for picking in rental_pickups:
            if picking.state == 'done':
                picking._process_rental_pickup_done()

        for picking in rental_returns:
            if picking.state == 'done':
                picking._process_rental_return_done()

        return res

    def _process_rental_pickup_done(self):
        order = self.rental_sale_order_id
        if not order:
            return

        kit_lines = order.order_line.filtered(
            lambda l: (
                not l.display_type
                and l.selected == 'true'
                and not l.x_is_rental_kit_component
                and order._get_phantom_bom_for_line(l)
            )
        )
        for kit_line in kit_lines:
            kit_line.with_context(
                bypass_sol_lock=True,
                skip_apply_canadian_sales_taxes=True,
                skip_company_consistency=True,
            ).write({'qty_delivered': kit_line.product_uom_qty})

        non_kit_lines = order.order_line.filtered(
            lambda l: (
                not l.display_type
                and l.selected == 'true'
                and not l.x_is_rental_kit_component
                and not order._get_phantom_bom_for_line(l)
                and l.product_id
                and l.product_id.rent_ok
            )
        )
        for line in non_kit_lines:
            line.with_context(
                bypass_sol_lock=True,
                skip_apply_canadian_sales_taxes=True,
                skip_company_consistency=True,
            ).write({'qty_delivered': line.product_uom_qty})

        self._force_rental_status_sql(order, 'return')
        _logger.info("Rental pickup transfer %s validated → order %s set to 'return'", self.name, order.name)

    def _process_rental_return_done(self):
        order = self.rental_sale_order_id
        if not order:
            return

        kit_lines = order.order_line.filtered(
            lambda l: (
                not l.display_type
                and l.selected == 'true'
                and not l.x_is_rental_kit_component
                and order._get_phantom_bom_for_line(l)
            )
        )
        for kit_line in kit_lines:
            kit_line.with_context(
                bypass_sol_lock=True,
                skip_apply_canadian_sales_taxes=True,
                skip_company_consistency=True,
            ).write({
                'qty_delivered': kit_line.product_uom_qty,
                'qty_returned': kit_line.product_uom_qty,
            })

        non_kit_lines = order.order_line.filtered(
            lambda l: (
                not l.display_type
                and l.selected == 'true'
                and not l.x_is_rental_kit_component
                and not order._get_phantom_bom_for_line(l)
                and l.product_id
                and l.product_id.rent_ok
            )
        )
        for line in non_kit_lines:
            line.with_context(
                bypass_sol_lock=True,
                skip_apply_canadian_sales_taxes=True,
                skip_company_consistency=True,
            ).write({
                'qty_delivered': line.product_uom_qty,
                'qty_returned': line.product_uom_qty,
            })

        self._force_rental_status_sql(order, 'returned')
        _logger.info("Rental return transfer %s validated → order %s set to 'returned'", self.name, order.name)

    def _force_rental_status_sql(self, order, target_status):
        self.env.flush_all()
        self.env.cr.execute("""
            UPDATE sale_order
            SET rental_status = %s,
                write_date = NOW(),
                write_uid = %s
            WHERE id = %s
        """, [target_status, self.env.uid, order.id])
        order.invalidate_recordset(["rental_status"])

    def button_validate(self):
        res = super(StockPicking, self).button_validate()

        for picking in self:
            if picking.picking_type_code != 'outgoing':
                continue

            attachment_ids = []
            lots_for_body = []

            for ml in picking.move_line_ids:
                lot = ml.lot_id
                if lot and lot.document_pdf:
                    att = self.env['ir.attachment'].create({
                        'name': lot.document_pdf_filename or f'{lot.name}.pdf',
                        'type': 'binary',
                        'datas': lot.document_pdf,
                        'res_model': 'sale.order',
                        'res_id': picking.sale_id.id if picking.sale_id else False,
                        'mimetype': 'application/pdf',
                    })
                    attachment_ids.append(att.id)
                    lots_for_body.append((ml.product_id.display_name, lot.name))

            if not attachment_ids or not picking.sale_id:
                continue

            sale_order = picking.sale_id

            partners = sale_order.message_follower_ids.mapped('partner_id').filtered(lambda p: p.email)
            if not partners:
                continue

            body_html = self.env['ir.qweb']._render(
                'proquotes.software_license_email_body',
                {
                    'sale_order': sale_order,
                    'picking': picking,
                    'lots': lots_for_body,
                },
            )

            sale_order.with_context(
                lang=sale_order.partner_id.lang,
                mail_notify_force_send=True,
            ).message_post(
                partner_ids=partners.ids,
                subject=f"Software Licenses for {sale_order.name}",
                body=body_html,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                email_layout_xmlid='mail.mail_notification_layout',
                attachment_ids=attachment_ids,
            )

        return res
