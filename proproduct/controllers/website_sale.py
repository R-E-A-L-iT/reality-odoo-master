# -*- coding: utf-8 -*-
import logging
from datetime import datetime

import requests  # still imported in case you want the geoIP logic later

from odoo import fields, http, SUPERUSER_ID, tools, _
# Odoo 19: module-level slug() was removed; use env['ir.http']._slug().
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website_sale.controllers import main
from odoo.http import request
from werkzeug.exceptions import Forbidden, NotFound
from odoo.tools import lazy, str2bool

from odoo.addons.proproduct.controllers.table_compute import TableCompute

_logger = logging.getLogger(__name__)

class PricelistSelectionController(http.Controller):

    @http.route('/shop/set_pricelist', type='http', auth="public", website=True)
    def set_pricelist(self, pricelist_id=None, **kw):
        request.session['pricelist_selected_manually'] = True
        request.session['website_sale_current_pl'] = int(pricelist_id)
        return request.redirect(request.httprequest.referrer or '/shop')

class WebsiteSale(main.WebsiteSale):

    @http.route()
    def get_combination_info(self, product_template_id, product_id, combination, add_qty,
                             parent_combination=None, **kw):
        """Force the AJAX product price to the applicable pricelist rule.

        The product page JS calls this endpoint after load and overwrites the
        server-rendered price. Odoo's own price engine drops valid rules on very
        large pricelists (10k+ items -> list_price fallback), and rental (rent_ok)
        products return the rental price here, so we resolve the matching item
        ourselves (same proven logic as the template) and set the sales price.
        """
        res = super().get_combination_info(
            product_template_id, product_id, combination, add_qty,
            parent_combination=parent_combination, **kw,
        )
        try:
            if isinstance(res, dict):
                tmpl = request.env['product.template'].sudo().browse(int(product_template_id))
                pricelist = request.website.get_current_pricelist()
                variant = request.env['product.product'].sudo().browse(res.get('product_id'))
                if not variant.exists():
                    variant = tmpl.product_variant_id
                item = tmpl._proproduct_resolve_pricelist_item(pricelist, variant)
                if item and item.compute_price == 'fixed':
                    _logger.info(
                        "[proproduct] AJAX combination price for %s on %s -> %s (rule %s, was %s)",
                        variant.display_name, pricelist.display_name, item.fixed_price,
                        item.id, res.get('price'),
                    )
                    res['price'] = item.fixed_price
                    res['list_price'] = item.fixed_price
                    res['has_discounted_price'] = False
                    res['is_rental'] = False
        except Exception as e:
            _logger.warning("[proproduct] AJAX price override failed: %s", e)
        return res

    def _checkout_form_save(self, mode, checkout, all_values):
        partner_id = super()._checkout_form_save(mode, checkout, all_values)

        # IMPORTANT: clear company_id on the partner that was just created/updated
        partner = request.env['res.partner'].sudo().browse(partner_id).exists()
        if partner:
            # also clear on the commercial entity (important if this is a contact under a company)
            targets = (partner | partner.commercial_partner_id | partner.child_ids).sudo()
            locked = targets.filtered(lambda p: p.company_id)
            if locked:
                _logger.info("[pro] Clearing company_id on checkout partner(s): %s", locked.mapped("display_name"))
                locked.write({"company_id": False})

        # Optional: do it again on SO partners (now that some flows may have updated them)
        order = request.website.sale_get_order()
        if order:
            so_partners = (order.partner_id | order.partner_invoice_id | order.partner_shipping_id).sudo()
            locked2 = so_partners.filtered(lambda p: p.company_id)
            if locked2:
                _logger.info("[pro] Clearing company_id on SO partner fields for %s: %s", order.name, locked2.mapped("display_name"))
                locked2.write({"company_id": False})

        return partner_id

    def _get_search_options(self, category=None, attrib_values=None, tags=None,
                           min_price=0.0, max_price=0.0, conversion_rate=1, **post):
        """Override to fix signature compatibility issue with website_sale_renting.

        The enterprise website_sale_renting module has _get_search_options(self, **post)
        which causes 'multiple values for keyword argument' errors when tags are passed.
        This override builds the complete options dict to avoid calling parent.
        """
        # Build complete options dict (same as base website_sale)
        options = {
            'displayDescription': True,
            'displayDetail': True,
            'displayExtraDetail': True,
            'displayExtraLink': True,
            'displayImage': True,
            'allowFuzzy': not post.get('noFuzzy'),
            'category': str(category.id) if category else None,
            'tags': tags,
            'min_price': min_price / conversion_rate if conversion_rate else min_price,
            'max_price': max_price / conversion_rate if conversion_rate else max_price,
            'attrib_values': attrib_values,
            'display_currency': post.get('display_currency'),
        }

        # Add rental-specific options (from website_sale_renting module)
        options.update({
            'from_date': post.get('start_date'),
            'to_date': post.get('end_date'),
            'rent_only': post.get('rent_only') in ('True', 'true', '1'),
        })

        return options

    def sitemap_shop(env, rule, qs):
        if not qs or qs.lower() in '/shop':
            yield {'loc': '/shop'}

        Category = env['product.public.category']
        dom = sitemap_qs2dom(qs, '/shop/category', Category._rec_name)
        dom += env['website'].get_current_website().website_domain()
        for cat in Category.search(dom):
            loc = '/shop/category/%s' % env['ir.http']._slug(cat)
            if not qs or qs.lower() in loc:
                yield {'loc': loc}

    @http.route([
        '''/shop''',
        '''/shop/page/<int:page>''',
        '''/shop/category/<model("product.public.category"):category>''',
        '''/shop/category/<model("product.public.category"):category>/page/<int:page>'''
    ], type='http', auth="public", website=True, sitemap=sitemap_shop)
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):

        website = request.env['website'].get_current_website()
        website_domain = website.website_domain()

        # GEOIP-BASED PRICE LIST AUTODETECTION (DISABLED)
        # ------------------------------------------------
        # All the CAD/USD auto-selection logic has been intentionally disabled
        # to fall back to standard Odoo pricelist behavior.
        #
        # if not request.session.get('pricelist_region_initialized'):
        #     try:
        #         geo = requests.get("https://ipapi.co/json").json()
        #         country_code = geo.get('country_code')
        #
        #         Pricelist = request.env['product.pricelist'].sudo()
        #
        #         if country_code == 'US':
        #             us_pricelist = Pricelist.search([('currency_id.name', '=', 'USD')], limit=1)
        #             if us_pricelist and website.is_pricelist_available(us_pricelist.id):
        #                 request.session['website_sale_current_pl'] = us_pricelist.id
        #                 request.website.sale_get_order(update_pricelist=True)
        #                 _logger.info("[proproduct] Auto-set USD pricelist for US visitor")
        #         elif country_code == 'CA':
        #             ca_pricelist = Pricelist.search([('currency_id.name', '=', 'CAD')], limit=1)
        #             if ca_pricelist and website.is_pricelist_available(ca_pricelist.id):
        #                 request.session['website_sale_current_pl'] = ca_pricelist.id
        #                 request.website.sale_get_order(update_pricelist=True)
        #                 _logger.info("[proproduct] Auto-set CAD pricelist for CA visitor")
        #     except Exception as e:
        #         _logger.warning(f"[proproduct] GeoIP lookup failed: {e}")
        #
        #     request.session['pricelist_region_initialized'] = True

        add_qty = int(post.get('add_qty', 1))
        try:
            min_price = float(min_price)
        except ValueError:
            min_price = 0.0
        try:
            max_price = float(max_price)
        except ValueError:
            max_price = 0.0

        Category = request.env['product.public.category']
        if category:
            category = Category.search([('id', '=', int(category))], limit=1)
            if not category or not category.can_access_from_current_website():
                raise NotFound()
        else:
            category = Category

        if ppg:
            try:
                ppg = int(ppg)
                post['ppg'] = ppg
            except ValueError:
                ppg = False
        if not ppg:
            ppg = website.shop_ppg or 20

        ppr = website.shop_ppr or 4

        request_args = request.httprequest.args
        attrib_list = request_args.getlist('attrib')
        attrib_values = [[int(x) for x in v.split("-")] for v in attrib_list if v]
        attributes_ids = {v[0] for v in attrib_values}
        attrib_set = {v[1] for v in attrib_values}

        filter_by_tags_enabled = website.is_view_active('website_sale.filter_products_tags')
        tags = {}
        if filter_by_tags_enabled:
            tags = request_args.getlist('tags')
            # Allow only numeric tag values to avoid internal error.
            if tags and all(tag.isnumeric() for tag in tags):
                post['tags'] = tags
                tags = {int(tag) for tag in tags}
            else:
                post['tags'] = None
                tags = {}

        keep = QueryURL(
            '/shop',
            **self._shop_get_query_url_kwargs(category and int(category), search, min_price, max_price, **post)
        )

        # ------------------------------------------------------------------
        # PRICELIST & CONVERSION RATE  (FIXED)
        # ------------------------------------------------------------------
        now = datetime.timestamp(datetime.now())

        # Run geo pricelist logic on first landing
        geo_pricelist = website.sale_get_pricelist()

        # Ensure cart (if any) is aligned with current pricelist
        order = request.website.sale_get_order(force_create=False, update_pricelist=True)

        # Use cart pricelist if cart exists; else geo pricelist (NOT website default)
        pricelist = order.pricelist_id if order else geo_pricelist
        display_currency = pricelist.currency_id or website.currency_id

        # Price-filter conversion rate (always defined)
        filter_by_price_enabled = website.is_view_active('website_sale.filter_products_price')
        conversion_rate = 1.0
        if filter_by_price_enabled:
            company_currency = website.company_id.currency_id
            conversion_rate = request.env['res.currency']._get_conversion_rate(
                company_currency,
                website.currency_id,
                website.company_id,
                fields.Date.today(),
            )

        # Old custom caching logic for pricelist has been removed to avoid
        # overriding Odoo's default behavior:
        #
        # pricelist = website.pricelist_id
        # if 'website_sale_pricelist_time' in request.session:
        #     ...
        # else:
        #     ...

        url = '/shop'
        if search:
            post['search'] = search
        if attrib_list:
            post['attrib'] = attrib_list

        # Build search options including tags for proper filtering
        # Extract tags from post to pass explicitly (avoid duplicate parameter error)
        post_without_tags = {k: v for k, v in post.items() if k != 'tags'}
        options = self._get_search_options(
            category=category,
            attrib_values=attrib_values,
            tags=tags,
            min_price=min_price,
            max_price=max_price,
            conversion_rate=conversion_rate,
            display_currency=display_currency,
            **post_without_tags
        )

        # No limit because attributes are obtained from complete product list
        fuzzy_search_term, product_count, search_product = self._shop_lookup_products(
            attrib_set, options, post, search, website
        )

        # CAD / USD PRODUCT VISIBILITY FILTERING REMOVED
        # ------------------------------------------------
        # If you ever want to re-enable region-specific visibility, this is
        # where it used to happen:
        #
        # if pricelist.currency_id:
        #     currency = pricelist.currency_id.name
        #     if currency == 'USD':
        #         search_product = search_product.filtered(lambda e: e.is_us)
        #         product_count = len(search_product)
        #     elif currency == 'CAD':
        #         search_product = search_product.filtered(lambda e: e.is_ca)
        #         product_count = len(search_product)
        # else:
        #     tst = requests.get("https://ipapi.co/json").json()
        #     ...

        # Re-check price filter to compute min/max bounds using SQL
        filter_by_price_enabled = request.website.is_view_active('website_sale.filter_products_price')
        available_min_price = 0.0
        available_max_price = 0.0
        if filter_by_price_enabled:
            Product = request.env['product.template'].with_context(bin_size=True)
            domain = self._get_shop_domain(search, category, attrib_values)

            # This is ~4 times more efficient than searching for cheapest and most expensive products
            query = Product._where_calc(domain)
            Product._apply_ir_rules(query, 'read')
            from_clause, where_clause, where_params = query.get_sql()
            sql = f"""
                SELECT COALESCE(MIN(list_price), 0) * {conversion_rate},
                       COALESCE(MAX(list_price), 0) * {conversion_rate}
                  FROM {from_clause}
                 WHERE {where_clause}
            """
            request.env.cr.execute(sql, where_params)
            available_min_price, available_max_price = request.env.cr.fetchone()

            if min_price or max_price:
                # Ensure filters stay within the available range
                if min_price:
                    min_price = min_price if min_price <= available_max_price else available_min_price
                    post['min_price'] = min_price
                if max_price:
                    max_price = max_price if max_price >= available_min_price else available_max_price
                    post['max_price'] = max_price

        all_tags = []
        if filter_by_tags_enabled:
            if (
                search_product.product_tag_ids
                or search_product.product_variant_ids.additional_product_tag_ids
            ):
                ProductTag = request.env['product.tag']
                all_tags = ProductTag.search(
                    [('product_ids.is_published', '=', True), ('visible_on_ecommerce', '=', True)]
                    + website_domain
                )
            else:
                all_tags = []
        categs_domain = [('parent_id', '=', False)] + website_domain
        if search:
            search_categories = Category.search(
                [('product_tmpl_ids', 'in', search_product.ids)] + website_domain
            ).parents_and_self
            categs_domain.append(('id', 'in', search_categories.ids))
        else:
            search_categories = Category
        categs = lazy(lambda: Category.search(categs_domain))

        if category:
            url = "/shop/category/%s" % request.env['ir.http']._slug(category)

        pager = website.pager(url=url, total=product_count, page=page, step=ppg, scope=7, url_args=post)
        offset = pager['offset']
        products = search_product[offset:offset + ppg]

        ProductAttribute = request.env['product.attribute']
        if products:
            attributes = lazy(lambda: ProductAttribute.search([
                ('product_tmpl_ids', 'in', search_product.ids),
                ('visibility', '=', 'visible'),
            ]))
        else:
            attributes = lazy(lambda: ProductAttribute.browse(attributes_ids))

        layout_mode = request.session.get('website_sale_shop_layout_mode')
        if not layout_mode:
            if website.viewref('website_sale.products_list_view').active:
                layout_mode = 'list'
            else:
                layout_mode = 'grid'
            request.session['website_sale_shop_layout_mode'] = layout_mode

        # Try to fetch geoip based fpos or fallback on partner one
        fiscal_position_sudo = website.fiscal_position_id.sudo()
        products_prices = lazy(lambda: products._get_sales_prices(pricelist, fiscal_position_sudo))

        values = {
            'search': fuzzy_search_term or search,
            'original_search': fuzzy_search_term and search,
            'order': post.get('order', ''),
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': pricelist,
            'fiscal_position': fiscal_position_sudo,
            'add_qty': add_qty,
            'products': products,
            'search_product': search_product,
            'search_count': product_count,  # common for all searchbox
            'bins': lazy(lambda: TableCompute().process(products, ppg, ppr)),
            'ppg': ppg,
            'ppr': ppr,
            'categories': categs,
            'attributes': attributes,
            'keep': keep,
            'search_categories_ids': search_categories.ids,
            'layout_mode': layout_mode,
            'products_prices': products_prices,
            'get_product_prices': lambda product: lazy(lambda: products_prices[product.id]),
            'float_round': tools.float_round,
        }
        if filter_by_price_enabled:
            values['min_price'] = min_price or available_min_price
            values['max_price'] = max_price or available_max_price
            values['available_min_price'] = tools.float_round(available_min_price, 2)
            values['available_max_price'] = tools.float_round(available_max_price, 2)
        if filter_by_tags_enabled:
            values.update({'all_tags': all_tags, 'tags': tags})
        if category:
            values['main_object'] = category
        values.update(self._get_additional_shop_values(values))
        return request.render("website_sale.products", values)
