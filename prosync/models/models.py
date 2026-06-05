from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = "product.template"

    sku = fields.Char(string="SKU", readonly=False, index=True, help="Stock Keeping Unit")
    discontinued = fields.Boolean(string="Discontinued", default=False, index=True, help="If checked, this product has been discontinued by the manufacturer but remains in the system for backward compatibility.")

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        """Include SKU in the default name search so typing a SKU in any
        product selector or search bar surfaces the matching product without
        needing a manual 'Search by SKU' filter."""
        ids = super()._name_search(name=name, domain=domain, operator=operator, limit=limit, order=order)

        if name and operator in ('ilike', 'like', '=', '=like', '=ilike'):
            sku_ids = list(self._search(
                (domain or []) + [('sku', operator, name)],
                limit=limit,
                order=order,
            ))
            if sku_ids:
                existing = set(ids)
                for sid in sku_ids:
                    if sid not in existing:
                        ids.append(sid)
                        existing.add(sid)
                if limit:
                    ids = ids[:limit]

        return ids


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        """Mirror the SKU search on product.product (used by many2one dropdowns
        such as the product selector on sale/purchase order lines)."""
        ids = super()._name_search(name=name, domain=domain, operator=operator, limit=limit, order=order)

        if name and operator in ('ilike', 'like', '=', '=like', '=ilike'):
            # product.product delegates to product.template via _inherits so
            # ('sku', ...) automatically joins the template table.
            sku_ids = list(self._search(
                (domain or []) + [('sku', operator, name)],
                limit=limit,
                order=order,
            ))
            if sku_ids:
                existing = set(ids)
                for sid in sku_ids:
                    if sid not in existing:
                        ids.append(sid)
                        existing.add(sid)
                if limit:
                    ids = ids[:limit]

        return ids

class ResPartner(models.Model):
    _inherit = "res.partner"

    pricelist_id = fields.Many2one("product.pricelist", "Pricelist_Sync")

    @api.depends("pricelist_id")
    def _compute_product_pricelist(self):
        for p in self:
            p.property_product_pricelist = p.pricelist_id