# -*- coding: utf-8 -*-

import ast
import base64
from email.policy import default
import re
from math import ceil

from datetime import date, datetime, timedelta
import functools
from functools import partial
from itertools import groupby
import logging

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression as exp
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api
from odoo.models import BaseModel as BSM
from collections import defaultdict
from odoo.http import request
from odoo.http import Response as Responseht
from odoo.http import FutureResponse as FutureResponseht

from .translation import name_translation
from odoo.tools import (
    clean_context, config, CountingStream, date_utils, discardattr,
    DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, frozendict,
    get_lang, LastOrderedSet, lazy_classproperty, OrderedSet, ormcache,
    partition, populate, Query, ReversedIterable, split_every, unique, SQL,
)
import werkzeug.datastructures
import werkzeug.exceptions
import werkzeug.local
import werkzeug.routing
import werkzeug.security
import werkzeug.wrappers
import werkzeug.wsgi
from werkzeug.urls import URL, url_parse, url_encode, url_quote
from werkzeug.exceptions import (HTTPException, BadRequest, Forbidden,
                                 NotFound, InternalServerError)
from odoo.addons.sale.models.sale_order import SALE_ORDER_STATE
try:
    from werkzeug.middleware.proxy_fix import ProxyFix as ProxyFix_
    ProxyFix = functools.partial(ProxyFix_, x_for=1, x_proto=1, x_host=1)
except ImportError:
    from werkzeug.contrib.fixers import ProxyFix

try:
    from werkzeug.utils import send_file as _send_file
except ImportError:
    from .tools._vendor.send_file import send_file as _send_file

# Domain operators.
NOT_OPERATOR = '!'
OR_OPERATOR = '|'
AND_OPERATOR = '&'
DOMAIN_OPERATORS = (NOT_OPERATOR, OR_OPERATOR, AND_OPERATOR)

# List of available term operators. It is also possible to use the '<>'
# operator, which is strictly the same as '!='; the later should be preferred
# for consistency. This list doesn't contain '<>' as it is simplified to '!='
# by the normalize_operator() function (so later part of the code deals with
# only one representation).
# Internals (i.e. not available to the user) 'inselect' and 'not inselect'
# operators are also used. In this case its right operand has the form (subselect, params).
TERM_OPERATORS = ('=', '!=', '<=', '<', '>', '>=', '=?', '=like', '=ilike',
                  'like', 'not like', 'ilike', 'not ilike', 'in', 'not in',
                  'child_of', 'parent_of', 'any', 'not any')

# A subset of the above operators, with a 'negative' semantic. When the
# expressions 'in NEGATIVE_TERM_OPERATORS' or 'not in NEGATIVE_TERM_OPERATORS' are used in the code
# below, this doesn't necessarily mean that any of those NEGATIVE_TERM_OPERATORS is
# legal in the processed term.
NEGATIVE_TERM_OPERATORS = ('!=', 'not like', 'not ilike', 'not in')

# Negation of domain expressions
DOMAIN_OPERATORS_NEGATION = {
    AND_OPERATOR: OR_OPERATOR,
    OR_OPERATOR: AND_OPERATOR,
}
TERM_OPERATORS_NEGATION = {
    '<': '>=',
    '>': '<=',
    '<=': '>',
    '>=': '<',
    '=': '!=',
    '!=': '=',
    'in': 'not in',
    'like': 'not like',
    'ilike': 'not ilike',
    'not in': 'in',
    'not like': 'like',
    'not ilike': 'ilike',
    'any': 'not any',
    'not any': 'any',
}
ANY_IN = {'any': 'in', 'not any': 'not in'}

TRUE_LEAF = (1, '=', 1)
FALSE_LEAF = (0, '=', 1)

TRUE_DOMAIN = [TRUE_LEAF]
FALSE_DOMAIN = [FALSE_LEAF]

SQL_OPERATORS = {
    '=': SQL('='),
    '!=': SQL('!='),
    '<=': SQL('<='),
    '<': SQL('<'),
    '>': SQL('>'),
    '>=': SQL('>='),
    'in': SQL('IN'),
    'not in': SQL('NOT IN'),
    '=like': SQL('LIKE'),
    '=ilike': SQL('ILIKE'),
    'like': SQL('LIKE'),
    'ilike': SQL('ILIKE'),
    'not like': SQL('NOT LIKE'),
    'not ilike': SQL('NOT ILIKE'),
}

_logger = logging.getLogger(__name__)


def is_operator(element):
    """ Test whether an object is a valid domain operator. """
    return isinstance(element, str) and element in DOMAIN_OPERATORS


def is_boolean(element):
    return element == TRUE_LEAF or element == FALSE_LEAF


@api.model
def _flush_search(self, domain, fields=None, order=None, seen=None):
    """ Flush all the fields appearing in `domain`, `fields` and `order`.

    Note that ``order=None`` actually means no order, so if you expect some
    fallback order, you have to provide it yourself.
    """
    if seen is None:
        seen = set()
    elif self._name in seen:
        return
    seen.add(self._name)

    to_flush = defaultdict(OrderedSet)  # {model_name: field_names}
    if fields:
        to_flush[self._name].update(fields)

    def collect_from_domain(model, domain):
        # _logger.info('>>>>>>>>>>>>>>>>. model: %s, domain: %s', model, domain)
        if not domain:
            domain = []
        for arg in domain:
            if isinstance(arg, str):
                continue
            if not isinstance(arg[0], str):
                continue
            comodel = collect_from_path(model, arg[0])
            if arg[1] in ('child_of', 'parent_of') and comodel._parent_store:
                # hierarchy operators need the parent field
                collect_from_path(comodel, comodel._parent_name)
            if arg[1] in ('any', 'not any'):
                collect_from_domain(comodel, arg[2])

    def collect_from_path(model, path):
        # path is a dot-separated sequence of field names
        for fname in path.split('.'):
            field = model._fields.get(fname)
            if not field:
                break
            to_flush[model._name].add(fname)
            if field.type == 'one2many' and field.inverse_name:
                to_flush[field.comodel_name].add(field.inverse_name)
                field_domain = field.get_domain_list(model)
                if field_domain:
                    collect_from_domain(self.env[field.comodel_name], field_domain)
            # DLE P111: `test_message_process_email_partner_find`
            # Search on res.users with email_normalized in domain
            # must trigger the recompute and flush of res.partner.email_normalized
            if field.related:
                # DLE P129: `test_transit_multi_companies`
                # `self.env['stock.picking'].search([('product_id', '=', product.id)])`
                # Should flush `stock.move.picking_ids` as `product_id` on `stock.picking` is defined as:
                # `product_id = fields.Many2one('product.product', 'Product', related='move_lines.product_id', readonly=False)`
                collect_from_path(model, field.related)
            if field.relational:
                model = self.env[field.comodel_name]
        # return the model found by traversing all fields (used in collect_from_domain)
        return model

    # flush the order fields
    if order:
        for order_part in order.split(','):
            order_field = order_part.split()[0]
            field = self._fields.get(order_field)
            if field is not None:
                to_flush[self._name].add(order_field)
                if field.relational:
                    comodel = self.env[field.comodel_name]
                    comodel._flush_search([], order=comodel._order, seen=seen)

    if self._active_name and self.env.context.get('active_test', True):
        to_flush[self._name].add(self._active_name)

    collect_from_domain(self, domain)

    # Check access of fields with groups
    for model_name, field_names in to_flush.items():
        self.env[model_name].check_field_access_rights('read', field_names)

    # also take into account the fields in the record rules
    if ir_rule_domain := self.env['ir.rule']._compute_domain(self._name, 'read'):
        collect_from_domain(self, ir_rule_domain)

    # flush model dependencies (recursively)
    if self._depends:
        models = [self]
        while models:
            model = models.pop()
            for model_name, field_names in model._depends.items():
                to_flush[model_name].update(field_names)
                models.append(self.env[model_name])

    for model_name, field_names in to_flush.items():
        self.env[model_name].flush_model(field_names)


BSM._flush_search = _flush_search


# --------------------------------------------------
# Generic domain manipulation
# --------------------------------------------------

def _anyfy_leaves(domain, model):
    """ Return the domain where all conditions on field sequences have been
    transformed into 'any' conditions.
    """
    result = []
    if not domain:
        domain = []
    for item in domain:
        if is_operator(item):
            result.append(item)
            continue

        left, operator, right = item = tuple(item)
        if is_boolean(item):
            result.append(item)
            continue

        path = left.split('.', 1)
        field = model._fields.get(path[0])
        if not field:
            raise ValueError(f"Invalid field {model._name}.{path[0]} in leaf {item}")
        if len(path) > 1 and field.relational:  # skip properties
            subdomain = [(path[1], operator, right)]
            comodel = model.env[field.comodel_name]
            result.append((path[0], 'any', _anyfy_leaves(subdomain, comodel)))
        elif operator in ('any', 'not any'):
            comodel = model.env[field.comodel_name]
            result.append((left, operator, _anyfy_leaves(right, comodel)))
        else:
            result.append(item)

    return result


exp._anyfy_leaves = _anyfy_leaves


def is_operator(element):
    """ Test whether an object is a valid domain operator. """
    return isinstance(element, str) and element in DOMAIN_OPERATORS


def is_boolean(element):
    return element == TRUE_LEAF or element == FALSE_LEAF


@api.model
def _flush_search(self, domain, fields=None, order=None, seen=None):
    """ Flush all the fields appearing in `domain`, `fields` and `order`.

    Note that ``order=None`` actually means no order, so if you expect some
    fallback order, you have to provide it yourself.
    """
    if seen is None:
        seen = set()
    elif self._name in seen:
        return
    seen.add(self._name)

    to_flush = defaultdict(OrderedSet)  # {model_name: field_names}
    if fields:
        to_flush[self._name].update(fields)

    def collect_from_domain(model, domain):
        # _logger.info('>>>>>>>>>>>>>>>>. model: %s, domain: %s', model, domain)
        if not domain:
            domain = []
        for arg in domain:
            if isinstance(arg, str):
                continue
            if not isinstance(arg[0], str):
                continue
            comodel = collect_from_path(model, arg[0])
            if arg[1] in ('child_of', 'parent_of') and comodel._parent_store:
                # hierarchy operators need the parent field
                collect_from_path(comodel, comodel._parent_name)
            if arg[1] in ('any', 'not any'):
                collect_from_domain(comodel, arg[2])

    def collect_from_path(model, path):
        # path is a dot-separated sequence of field names
        for fname in path.split('.'):
            field = model._fields.get(fname)
            if not field:
                break
            to_flush[model._name].add(fname)
            if field.type == 'one2many' and field.inverse_name:
                to_flush[field.comodel_name].add(field.inverse_name)
                field_domain = field.get_domain_list(model)
                if field_domain:
                    collect_from_domain(self.env[field.comodel_name], field_domain)
            # DLE P111: `test_message_process_email_partner_find`
            # Search on res.users with email_normalized in domain
            # must trigger the recompute and flush of res.partner.email_normalized
            if field.related:
                # DLE P129: `test_transit_multi_companies`
                # `self.env['stock.picking'].search([('product_id', '=', product.id)])`
                # Should flush `stock.move.picking_ids` as `product_id` on `stock.picking` is defined as:
                # `product_id = fields.Many2one('product.product', 'Product', related='move_lines.product_id', readonly=False)`
                collect_from_path(model, field.related)
            if field.relational:
                model = self.env[field.comodel_name]
        # return the model found by traversing all fields (used in collect_from_domain)
        return model

    # flush the order fields
    if order:
        for order_part in order.split(','):
            order_field = order_part.split()[0]
            field = self._fields.get(order_field)
            if field is not None:
                to_flush[self._name].add(order_field)
                if field.relational:
                    comodel = self.env[field.comodel_name]
                    comodel._flush_search([], order=comodel._order, seen=seen)

    if self._active_name and self.env.context.get('active_test', True):
        to_flush[self._name].add(self._active_name)

    collect_from_domain(self, domain)

    # Check access of fields with groups
    for model_name, field_names in to_flush.items():
        self.env[model_name].check_field_access_rights('read', field_names)

    # also take into account the fields in the record rules
    if ir_rule_domain := self.env['ir.rule']._compute_domain(self._name, 'read'):
        collect_from_domain(self, ir_rule_domain)

    # flush model dependencies (recursively)
    if self._depends:
        models = [self]
        while models:
            model = models.pop()
            for model_name, field_names in model._depends.items():
                to_flush[model_name].update(field_names)
                models.append(self.env[model_name])

    for model_name, field_names in to_flush.items():
        self.env[model_name].flush_model(field_names)


BSM._flush_search = _flush_search


# --------------------------------------------------
# Generic domain manipulation
# --------------------------------------------------

def _anyfy_leaves(domain, model):
    """ Return the domain where all conditions on field sequences have been
    transformed into 'any' conditions.
    """
    result = []
    if not domain:
        domain = []
    for item in domain:
        if is_operator(item):
            result.append(item)
            continue

        left, operator, right = item = tuple(item)
        if is_boolean(item):
            result.append(item)
            continue

        path = left.split('.', 1)
        field = model._fields.get(path[0])
        if not field:
            raise ValueError(f"Invalid field {model._name}.{path[0]} in leaf {item}")
        if len(path) > 1 and field.relational:  # skip properties
            subdomain = [(path[1], operator, right)]
            comodel = model.env[field.comodel_name]
            result.append((path[0], 'any', _anyfy_leaves(subdomain, comodel)))
        elif operator in ('any', 'not any'):
            comodel = model.env[field.comodel_name]
            result.append((left, operator, _anyfy_leaves(right, comodel)))
        else:
            result.append(item)

    return result


exp._anyfy_leaves = _anyfy_leaves


# class Response(Responseht)
# def set_cookie(self, key, value='', max_age=None, expires=-1, path='/', domain=None, secure=False, httponly=False, samesite=None, cookie_type='required'):
#     """
#     The default expires in Werkzeug is None, which means a session cookie.
#     We want to continue to support the session cookie, but not by default.
#     Now the default is arbitrary 1 year.
#     So if you want a cookie of session, you have to explicitly pass expires=None.
#     """
#     if expires == -1:  # not provided value -> default value -> 1 year
#         expires = datetime.now() + timedelta(days=365)

#     if request.db and not request.env['ir.http']._is_allowed_cookie(cookie_type):
#         max_age = 0
#     _logger.info('>>>>>>>>>>>>>>request.httprequest.path: %s', request.httprequest.path)
#     url = request.httprequest.path
#     if ('/website/lang/fr_CA' in url) or ('/website/lang/en' in url):
#         _logger.info('>>>>>>>>>>>>>>inside')
#         if 'fr_CA' not in url:
#             value = 'en_US'
#         else:
#             value = 'fr_CA'
#     else:
#         if ('/web/login' not in url) and request.httprequest.cookies.get('frontend_lang', False):
#             value = request.httprequest.cookies.get('frontend_lang')
#     _logger.info('>>>>>>>>> session language: %s', request.httprequest.cookies.get('frontend_lang'))
#     _logger.info('>>>>>>>>>>>> cookie_value 2: %s', value)

#     super(Responseht, self).set_cookie(key, value=value, max_age=max_age, expires=expires, path=path, domain=domain, secure=secure, httponly=httponly, samesite=samesite)

# Responseht.set_cookie = set_cookie

@functools.wraps(werkzeug.Response.set_cookie)
def set_cookie(self, key, value='', max_age=None, expires=-1, path='/', domain=None, secure=False, httponly=False, samesite=None, cookie_type='required'):
    if expires == -1:  # not forced value -> default value -> 1 year
        expires = datetime.now() + timedelta(days=365)

    if request.db and not request.env['ir.http']._is_allowed_cookie(cookie_type):
        max_age = 0
    _logger.info('>>>>>>>>>>>>>>request.httprequest.path 1: %s', request.httprequest.path)
    url = request.httprequest.path
    if ('/website/lang/fr_CA' in url) or ('/website/lang/en' in url):
        _logger.info('>>>>>>>>>>>>>>inside')
        if 'fr_CA' not in url:
            value = 'en_US'
        else:
            value = 'fr_CA'
    else:
        if (url.startswith('/web')) and key=='frontend_lang' and request.httprequest.cookies.get('frontend_lang', False):
            value = request.httprequest.cookies.get('frontend_lang')
    _logger.info('>>>>>>>>> session language 1: %s', request.httprequest.cookies.get('frontend_lang'))
    _logger.info('>>>>>>>>>>>> cookie_value 1: %s', value)
    werkzeug.Response.set_cookie(self, key, value=value, max_age=max_age, expires=expires, path=path, domain=domain, secure=secure, httponly=httponly, samesite=samesite)

FutureResponseht.set_cookie = set_cookie

class CustomViewModifier(models.Model):
    _inherit = 'ir.ui.view'

    @api.model
    def modify_view(self):
        # Get the view you want to modify (replace 'view_id_or_xmlid' with the actual ID or XMLID)
        view = self.env.ref('sale.sale_order_portal_content')
        if view:
            # Modify the arch (the XML structure) of the view
            arch_tree = etree.XML(view.arch_db)
            
            # Find and remove the elements with id='taxes_header' and id='taxes'
            taxes_header_element = arch_tree.xpath("//th[@id='taxes_header']")
            taxes_element = arch_tree.xpath("//td[@id='taxes']")

            # Remove the 'taxes_header' element if it exists
            if taxes_header_element:
                parent = taxes_header_element[0].getparent()
                if parent is not None:
                    parent.remove(taxes_header_element[0])

            # Remove the 'taxes' element if it exists
            if taxes_element:
                parent = taxes_element[0].getparent()
                if parent is not None:
                    parent.remove(taxes_element[0])

            # Update the view arch with the modified version
            view.write({'arch_db': etree.tostring(arch_tree, pretty_print=True).decode()})

        return True


class purchase_order(models.Model):
    _inherit = "purchase.order"
    footer = fields.Selection(
        [
            ("ABtechFooter_Atlantic_Derek", "Abtech_Atlantic_Derek"),
            ("ABtechFooter_Atlantic_Ryan", "Abtech_Atlantic_Ryan"),
            ("ABtechFooter_Ontario_Derek", "Abtech_Ontario_Derek"),
            ("ABtechFooter_Ontario_Justin", "Abtech_Ontario_Justin"),
            ("ABtechFooter_Ontario_Phil", "Abtech_Ontario_Phil"),
            ("ABtechFooter_Ontario_Justin", "Abtech_Ontario_Justin"),
            ("ABtechFooter_Quebec_Alexandre", "Abtech_Quebec_Alexandre"),
            ("ABtechFooter_Quebec_Benoit_Carl", "ABtechFooter_Quebec_Benoit_Carl"),
            ("ABtechFooter_Quebec_Derek", "Abtech_Quebec_Derek"),
            ("GeoplusFooterCanada", "Geoplus_Canada"),
            ("GeoplusFooterUS", "Geoplus_America"),
            ("Leica_Footer_Ali", "Leica Ali"),
            ("REALiTFooter_Derek_US", "REALiTFooter_Derek_US"),
            ("REALiTFooter_Martin", "REALiTFooter_Martin"),
            ("REALiTSOLUTIONSLLCFooter_Derek_US", "R-E-A-L.iT Solutions Derek"),
            ("REALiTFooter_Derek", "REALiTFooter_Derek"),
            ("REALiTFooter_Derek_Transcanada", "REALiTFooter_Derek_Transcanada"),
        ],
        default="REALiTFooter_Derek",
        required=True,
        string="Footer OLD",
        help="Footer selection field",
    )

    def _get_default_footer(self):
        # Get Company
        company = None
        if self.company_id == False or self.company_id == None:
            company = self.company_id
        else:
            company = self.env.company

        # Get User
        user = None
        if self.user_id == False or self.user_id == None:
            user = self.user_id
        else:
            user = self.env.user

        # Get Prefered Footers
        result_raw = user.prefered_quote_footers

        if result_raw != False:
            result = []
            for item in result_raw:
                # Verify footers are applicable for company
                if company in item.company_ids or len(item.company_ids) == 0:
                    result.append(item)
            if len(result) != 0:
                return result[-1]
        # Check for default footer that matches company
        defaults = self.env["header.footer"].search(
            [
                ("active", "=", True),
                ("record_type", "=", "Footer"),
                ("default", "=", True),
                ("company_ids", "=", company.id),
            ]
        )
        if len(defaults) != 0:
            return defaults[-1]
        else:
            return False
            raise UserError("No Default Footer Available")

    footer_id = fields.Many2one(
        "header.footer", default=_get_default_footer, required="True"
    )


class invoice(models.Model):
    _inherit = "account.move"
    footer = fields.Selection(
        [
            ("ABtechFooter_Atlantic_Derek", "Abtech_Atlantic_Derek"),
            ("ABtechFooter_Atlantic_Ryan", "Abtech_Atlantic_Ryan"),
            ("ABtechFooter_Ontario_Derek", "Abtech_Ontario_Derek"),
            ("ABtechFooter_Ontario_Justin", "Abtech_Ontario_Justin"),
            ("ABtechFooter_Ontario_Phil", "Abtech_Ontario_Phil"),
            ("ABtechFooter_Ontario_Justin", "Abtech_Ontario_Justin"),
            ("ABtechFooter_Quebec_Alexandre", "Abtech_Quebec_Alexandre"),
            ("ABtechFooter_Quebec_Benoit_Carl", "ABtechFooter_Quebec_Benoit_Carl"),
            ("ABtechFooter_Quebec_Derek", "Abtech_Quebec_Derek"),
            ("GeoplusFooterCanada", "Geoplus_Canada"),
            ("GeoplusFooterUS", "Geoplus_America"),
            ("Leica_Footer_Ali", "Leica Ali"),
            ("REALiTFooter_Derek_US", "REALiTFooter_Derek_US"),
            ("REALiTFooter_Martin", "REALiTFooter_Martin"),
            ("REALiTSOLUTIONSLLCFooter_Derek_US", "R-E-A-L.iT Solutions Derek"),
            ("REALiTFooter_Derek", "REALiTFooter_Derek"),
            ("REALiTFooter_Derek_Transcanada", "REALiTFooter_Derek_Transcanada"),
        ],
        default="REALiTFooter_Derek",
        required=True,
        string="Footer OLD",
        help="Footer selection field",
    )
    
    def get_translated_term(self, title, lang):
        if "translate" in title:

            _logger.info("PDF QUOTE - TRANSLATION FUNCTION ACTIVATED")
            terms =  title.split("+",2)

            if terms[0] == "#translate":
                english = terms[1]
                french = terms[2]

                if lang == 'fr_CA':
                    return french
                else:
                    return english

    @api.depends("company_id")
    def _get_default_footer(self):
        # Get Company
        company = None
        if self.company_id == False or self.company_id == None:
            company = self.company_id
        else:
            company = self.env.company

        # Get User
        user = None
        if self.user_id == False or self.user_id == None:
            user = self.user_id
        else:
            user = self.env.user

        # Get Prefered Footers
        result_raw = user.prefered_quote_footers

        if result_raw != False:
            result = []
            for item in result_raw:
                # Verify footers are applicable for company
                if company in item.company_ids or len(item.company_ids) == 0:
                    result.append(item)
            if len(result) != 0:
                return result[-1]

        # Check for default footer that matches company
        defaults = self.env["header.footer"].search(
            [
                ("active", "=", True),
                ("record_type", "=", "Footer"),
                ("default", "=", True),
                ("company_ids", "=", company.id),
            ]
        )
        if len(defaults) != 0:
            return defaults[-1]
        defaults = self.env["header.footer"].search(
            [
                ("active", "=", True),
                ("record_type", "=", "Footer"),
                ("default", "=", True),
                ("company_ids", "=", False),
            ]
        )
        if len(defaults) != 0:
            return defaults[-1]
        else:
            return False
            raise UserError("No Default Footer Available")

    footer_id = fields.Many2one(
        "header.footer", required=True, default=_get_default_footer
    )

    payment_date = fields.Char(string="Date of Payment", compute="_compute_payment_date", copy=False)

    def _compute_payment_date(self):
        for rec in self:
            rec.payment_date = False
            if rec.invoice_payments_widget:
                data = rec.invoice_payments_widget
                if data.get('content'):
                    payment_dates = set()
                    for payment in data['content']:
                        payment_date = payment['date']
                        formatted_date = payment_date.strftime('%d/%m/%Y')
                        payment_dates.add(formatted_date)
                    # For multi payment.
                    rec.payment_date = ', '.join(sorted(payment_dates))
                else:
                    rec.payment_date = False


class order(models.Model):
    _inherit = "sale.order"

    # partner_ids = fields.Many2many("res.partner", "display_name", string="Contacts")
    email_contacts = fields.Many2many("res.partner", "display_name", string="Email Contacts")

    products = fields.One2many(related="partner_id.products", readonly=True)

    customer_po_number = fields.Char(string="PO Number")

    company_name = fields.Char(
        related="company_id.name", string="company_name", required=True
    )
    manual_invoice_status = fields.Selection([
        ("full_invoice", "Fully Invoiced"),
        ("partially_invoiced", "Partially Invoiced"),
        ("not_invoiced", "Not Invoiced"),
    ], )
    financing_available = fields.Boolean(string="Financing Available")
    footer = fields.Selection(
        [
            ("ABtechFooter_Atlantic_Derek", "Abtech_Atlantic_Derek"),
            ("ABtechFooter_Atlantic_Ryan", "Abtech_Atlantic_Ryan"),
            ("ABtechFooter_Ontario_Derek", "Abtech_Ontario_Derek"),
            ("ABtechFooter_Ontario_Justin", "Abtech_Ontario_Justin"),
            ("ABtechFooter_Ontario_Phil", "Abtech_Ontario_Phil"),
            ("ABtechFooter_Ontario_Justin", "Abtech_Ontario_Justin"),
            ("ABtechFooter_Quebec_Alexandre", "Abtech_Quebec_Alexandre"),
            ("ABtechFooter_Quebec_Benoit_Carl", "ABtechFooter_Quebec_Benoit_Carl"),
            ("ABtechFooter_Quebec_Derek", "Abtech_Quebec_Derek"),
            ("GeoplusFooterCanada", "Geoplus_Canada"),
            ("GeoplusFooterUS", "Geoplus_America"),
            ("Leica_Footer_Ali", "Leica Ali"),
            ("REALiTFooter_Derek_US", "REALiTFooter_Derek_US"),
            ("REALiTFooter_Martin", "REALiTFooter_Martin"),
            ("REALiTSOLUTIONSLLCFooter_Derek_US", "R-E-A-L.iT Solutions Derek"),
            ("REALiTFooter_Derek", "REALiTFooter_Derek"),
            ("REALiTFooter_Derek_Transcanada", "REALiTFooter_Derek_Transcanada"),
        ],
        help="Footer selection field",
        string="Footer OLD",
    )

    header = fields.Selection(
        [
            ("QH_REALiT+Abtech.mp4", "QH_REALiT+Abtech.mp4"),
            ("ChurchXRAY.jpg", "ChurchXRAY.jpg"),
            ("Architecture.jpg", "Architecture.jpg"),
            ("Software.jpg", "Software.jpg"),
        ],
        string="Header OLD",
        help="Header selection field",
    )
    
    @api.model
    def default_get(self, fields_list):
        defaults = super(order, self).default_get(fields_list)

        # Search for the "Immediate Payment" payment term
        immediate_payment_term = self.env['account.payment.term'].search([('name', '=', 'Immediate Payment')], limit=1)
        
        # If found, set it as the default payment term
        if immediate_payment_term:
            defaults['payment_term_id'] = immediate_payment_term.id

        return defaults
    
    @api.onchange('pricelist_id')
    def _onchange_pricelist_id(self):
        if self.pricelist_id:
            # Check if the selected pricelist contains the word "RENTAL"
            if 'RENTAL' in self.pricelist_id.name.upper():
                self.is_rental = True
            else:
                self.is_rental = False
            for line in self.order_line:
                line.tax_id = [(5, 0, 0)]
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                'type': 'danger',
                'title': _("Warning"),
                'message': _('Taxes have been removed. Please set them manually for this order..'),
            })

    # @api.onchange('sale_order_template_id')
    # def _onchange_sale_order_template_id(self):
    #     if self.sale_order_template_id:
    #         if 'RENTAL' in self.sale_order_template_id.name.upper():
    #             self.is_rental = False
    #         else:
    #             self.is_rental = True
    
    @api.onchange('is_rental', 'partner_id')
    def _onchange_is_rental(self):
        if self.is_rental and self.partner_id:
            # Check the country of the customer
            if self.partner_id.country_id.code == 'CA':  # Canada
                rental_pricelist = self.env['product.pricelist'].search([('name', '=', 'CAD RENTAL')], limit=1)
            elif self.partner_id.country_id.code == 'US':  # USA
                rental_pricelist = self.env['product.pricelist'].search([('name', '=', 'USD RENTAL')], limit=1)

            if rental_pricelist:
                self.pricelist_id = rental_pricelist.id
        # else:
        #     # Reset pricelist if not rental
        #     self.pricelist_id = False

    @api.onchange('email_contacts')
    def _onchange_email_contacts(self):
        current_follower_ids = self.message_follower_ids.mapped('partner_id.id')
        new_partner_ids = []
        for contact in self.email_contacts:
            if isinstance(contact._origin.id, int):  # Real database ID
                new_partner_ids.append(contact._origin.id)
            else:
                _logger.warning("Skipping unsaved contact with NewId: %s", contact._origin.id)
        to_add = list(set(new_partner_ids) - set(current_follower_ids))
        if to_add:
            _logger.info('Adding new followers: %s', to_add)
            self.message_subscribe(partner_ids=to_add)
        to_remove = list(set(current_follower_ids) - set(new_partner_ids))
        if to_remove:
            _logger.info('Removing followers: %s', to_remove)
            self.message_unsubscribe(partner_ids=to_remove)

        if not to_add and not to_remove:
            _logger.info('No changes in followers.')

        for contact in self.email_contacts:
            try:
                if self.partner_ids:
                    if contact not in self.partner_ids:
                        self.partner_ids.append(contact.id)
            except:
                _logger.info("Failed to add contacts to the partner_ids from the email_contacts table")

    def _action_confirm(self):
        selected_lines = self.order_line.sudo().filtered(lambda line: line.selected == 'true')
        selected_lines._action_launch_stock_rule()
        # self.order_line._action_launch_stock_rule()
        # return super(order, self)._action_confirm()

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id and not self.is_rental:
            # Set domain for non-rental pricelists
            return {
                'domain': {
                    'pricelist_id': [('name', 'not ilike', 'rental')]
                }
            }
        elif self.partner_id and self.is_rental:
            # Set domain for rental pricelists
            return {
                'domain': {
                    'pricelist_id': [('name', 'ilike', 'rental')]
                }
            }

    def action_quotation_send(self):
        """ Opens a wizard to compose an email, with relevant mail template loaded by default """
        self.ensure_one()
        self.order_line._validate_analytic_distribution()
        lang = self.env.context.get('lang')
        template = self.env['mail.template'].sudo().search([('name', '=', 'General Sales')], limit=1)
        if template:
            mail_template = template
        else:
            mail_template = self._find_mail_template()
        if mail_template and mail_template.lang:
            lang = mail_template._render_lang(self.ids)[self.id]
        ctx = {
            'default_model': 'sale.order',
            'default_res_ids': self.ids,
            'default_template_id': mail_template.id if mail_template else None,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
            'proforma': self.env.context.get('proforma', False),
            'force_email': True,
            'model_description': self.with_context(lang=lang).type_name,
            'default_partner_ids': [(6, 0, self.email_contacts.ids)],
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }
    
    def _recompute_prices(self):
        lines_to_recompute = self._get_update_prices_lines()
        lines_to_recompute.invalidate_recordset(['pricelist_item_id'])
        lines_to_recompute._compute_price_unit()
        # Special case: we want to overwrite the existing discount on _recompute_prices call
        # i.e. to make sure the discount is correctly reset
        # if pricelist discount_policy is different than when the price was first computed.
        for lines in lines_to_recompute:
            if not lines.discount:
                lines.discount = 0.0
        lines_to_recompute._compute_discount()
        self.show_update_pricelist = False
    
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('mark_so_as_sent'):
            self.filtered(lambda o: o.state == 'draft').with_context(tracking_disable=True).write({'state': 'sent'})
        so_ctx = {'mail_post_autofollow': self.env.context.get('mail_post_autofollow', True)}
        if self.env.context.get('mark_so_as_sent') and 'mail_notify_author' not in kwargs:
            kwargs['notify_author'] = self.env.user.partner_id.id in (kwargs.get('partner_ids') or [])
        if 'tracking_value_ids' not in kwargs:
            return super(order, self.with_context(**so_ctx)).message_post(**kwargs)
        else:
            pass


    # def message_post(self, **kwargs):
        
    #     # Variable mail_post_autofollow is true when using send message function but not when log note
    #     mail_post_autofollow = self.env.context.get('mail_post_autofollow', True)
        
    #     message_type = kwargs.get('message_type', False)
        
    #     if 'body' not in kwargs:
    #         kwargs['body'] = ''
            
    #     # DEBUGGING
        
    #     # kwargs['body'] += f"<br/><br/>[DEBUG] mail_post_autofollow: {mail_post_autofollow}, message_type: {kwargs.get('message_type', 'undefined')}"

    #     # internal note feature
    #     if not mail_post_autofollow:
    #         # Call super without adding any email contacts, since it's a log note
    #         return super(order, self).message_post(**kwargs)
        
    #     elif "Quotation viewed by customer" in kwargs['body']:
    #         # only send to salesperson (user_id = salesperson)
    #         # sales_partner = self.env['res.partner'].sudo().search([('email', '=', 'sales@r-e-a-l.it')], limit=1)
    #         if order.user_id:
    #             kwargs['partner_ids'] = [order.user_id.id]
    #         else:
    #             kwargs['partner_ids'] = []
                
    #         return super(order, self).message_post(**kwargs)
        
    #     elif "Product prices have been recomputed" in kwargs['body']:
    #         return False
        
    #     elif "Signed by" in kwargs['body'] or "Bon signé" in kwargs['body']:
    #         if order.user_id:
    #             kwargs['partner_ids'] = [order.user_id.id]
    #         else:
    #             kwargs['partner_ids'] = []
                
    #         return super(order, self).message_post(**kwargs)

    #     # send message feature
    #     else:
    #         if 'partner_ids' not in kwargs:
    #             kwargs['partner_ids'] = []

    #         # Add email contacts from the many2many field
    #         contacts = [partner.id for partner in self.email_contacts]

    #         # Add static email partner 'sales@r-e-a-l.it'
    #         sales_partner = self.env['res.partner'].sudo().search([('email', '=', 'sales@r-e-a-l.it')], limit=1)
    #         if sales_partner:
    #             contacts.append(sales_partner.id)
                
    #         filtered_partner_ids = kwargs['partner_ids'][0:] if len(kwargs['partner_ids']) > 1 else []

    #         all_contacts = list(set(filtered_partner_ids + contacts))
    #         kwargs['partner_ids'] = all_contacts
            
    #         # if kwargs['partner_ids']:
    #         #     contacts += kwargs['partner_ids'][1:] 
            
    #         # kwargs['partner_ids'] = contacts

    #         # Call the super method to proceed with posting the message
    #         return super(order, self).message_post(**kwargs)
    
    @api.depends('rental_start', 'rental_end')
    def _compute_duration(self):
        self.duration_days = 0
        self.remaining_hours = 0
        for order in self:
            if order.rental_start and order.rental_end:
                duration = order.rental_end - order.rental_start
                order.duration_days = duration.days
                order.remaining_hours = ceil(duration.seconds / 3600)
    
    def get_translated_term(self, title, lang):
        if "translate" in title:

            terms = title.split("+", 2)

            if terms[0] == "#translate":
                english = terms[1]
                french = terms[2]

                if lang == 'fr_CA':
                    return french
                else:
                    return english

    def _default_footer(self):
        # Get Company
        company = None
        if self.company_id == False or self.company_id == None:
            company = self.company_id
        else:
            company = self.env.company

        # Get User
        user = None
        if self.user_id == False or self.user_id == None:
            user = self.user_id
        else:
            user = self.env.user

        # Get Prefered Footers
        result_raw = user.prefered_quote_footers

        if result_raw != False:
            result = []
            for item in result_raw:
                # Verify footers are applicable for company
                if company in item.company_ids or len(item.company_ids) == 0:
                    result.append(item)
            if len(result) != 0:
                return result[-1]

        # Check for default footer that matches company
        defaults = self.env["header.footer"].search(
            [
                ("active", "=", True),
                ("record_type", "=", "Footer"),
                ("default", "=", True),
                ("company_ids", "=", company.id),
            ]
        )
        if len(defaults) != 0:
            return defaults[-1]

        defaults = self.env["header.footer"].search(
            [
                ("active", "=", True),
                ("record_type", "=", "Footer"),
                ("default", "=", True),
                ("company_ids", "=", False),
            ]
        )
        if len(defaults) != 0:
            return defaults[-1]
        else:
            return False
            raise UserError("No Default Footer Available")

    def _default_header(self):
        # Get Company
        company = None
        if self.company_id == False or self.company_id == None:
            company = self.company_id
        else:
            company = self.env.company

        # Get User
        user = None
        if self.user_id == False or self.user_id == None:
            user = self.user_id
        else:
            user = self.env.user

        # Get Prefered Headers
        result_raw = user.prefered_headers

        if result_raw != False:
            result = []
            for item in result_raw:
                # Verify headers are applicable for company
                if company in item.company_ids or len(item.company_ids) == 0:
                    result.append(item)
            if len(result) != 0:
                return result[-1]

        # Check for default footer that matches company
        defaults = self.env["header.footer"].search(
            [
                ("active", "=", True),
                ("record_type", "=", "Header"),
                ("default", "=", True),
                ("company_ids", "=", company.id),
            ]
        )
        if len(defaults) != 0:
            return defaults[-1]
        defaults = self.env["header.footer"].search(
            [
                ("active", "=", True),
                ("record_type", "=", "Header"),
                ("default", "=", True),
                ("company_ids", "=", False),
            ]
        )
        if len(defaults) != 0:
            return defaults[-1]
        else:
            return False
            raise UserError("No Default Header Available")

    header_id = fields.Many2one("header.footer", default=_default_header, required=True)
    footer_id = fields.Many2one("header.footer", default=_default_footer, required=True)

    is_rental = fields.Boolean(string="Rental Quote", default=False)
    is_renewal = fields.Boolean(string="Renewal Quote", default=False)

    rental_diff_add = fields.Boolean(string="Rental Address", default=False)
    rental_street = fields.Char(string="Street Address")
    rental_city = fields.Char(string="City")
    rental_zip = fields.Char(string="ZIP/Postal Code")
    rental_state = fields.Many2one(
        "res.country.state", string="State/Province", store="true"
    )
    rental_country = fields.Many2one("res.country", string="Country", store="true")

    rental_start = fields.Date(string="Rental Start Date", default=False)
    rental_end = fields.Date(string="Rental End Date", default=False)

    renewal_product_items = fields.Many2many(
        string="Renewal Items", comodel_name="stock.lot"
    )

    # rental_insurance = fields.Binary(string="Insurance")

    @api.onchange("sale_order_template_id")
    def set_is_rental(self):
        # Set a flag if quotes is a rental quote
        if self.sale_order_template_id.name == "Rental":
            self.is_rental = True
        else:
            self.is_rental = False
        if (
                self.sale_order_template_id.name != False
                and "Renewal" in self.sale_order_template_id.name
        ):
            self.is_renewal = True
        else:
            self.is_renewal = False

    def test_action(self, *args):
        _logger.error("HELLO THERE" + str(args[0]))

    def generate_section_line(self, name, *, special="regular", selected="true"):
        section = self.env["sale.order.line"].new(
            {
                "name": name,
                "special": special,
                "display_type": "line_section",
                "order_id": self._origin.id,
                "selected": selected,
            }
        )
        return section

    def generate_product_line(
            self,
            product_id,
            *,
            selected=False,
            uom="Units",
            locked_qty="yes",
            optional="no"
    ):
        if selected == True:
            selected = "true"
        elif selected == False:
            selected = "false"

        product = self.env["product.product"].search([
            ("id", "=", product_id.id)])

        # Get Price
        pricelist = self.pricelist_id.id
        pricelist_entry = self.env["product.pricelist.item"].search(
            [
                ("pricelist_id.id", "=", pricelist),
                ("product_tmpl_id.sku", "=", product.sku),
            ]
        )
        price = 0
        if len(pricelist_entry) > 1:
            return "Duplicate Pricelist Rules: " + str(product_id.sku)
        elif len(pricelist_entry) == 1:
            price = pricelist_entry[-1].fixed_price
        uomitem = self.env["uom.uom"].search([("name", "=", uom)])
        if len(product) != 1:
            return "Invalid Responses for: sku=" + str(product_id.sku)
        line = self.env["sale.order.line"].new(
            {
                "name": product.name,
                "selected": selected,
                "optional": optional,
                "quantityLocked": locked_qty,
                "product_id": product.id,
                "product_uom_qty": 1,
                "product_uom": uomitem,
                "price_unit": price,
                "order_id": self._origin.id,
            }
        )
        return line

    def hardwareCCP(self, hardware_lines, product):
        eid = product.name

        # Generate lines based on renewal_map entries specifing what to offer
        # Initilize Hardware Line Section if Needed
        if len(hardware_lines) == 0:
            hardware_lines.append(self.generate_section_line("$hardware").id)
            hardware_lines.append(self.generate_section_line("$block").id)

        renewal_maps = self.env["renewal.map"].search(
            [("product_id", "=", product.product_id.id)])

        if len(renewal_maps) != 1:
            return "Hardware CCP: Invalid Match Count (" + str(len(renewal_maps)) + ") for \n[stock.lot].name: " + str(
                eid) + "\n[product.product].name: " + str(product.product_id.name) + "\n\n"

        renewal_map = renewal_maps[0]
        hardware_lines.append(
            self.generate_section_line(product.formated_label, special="multiple").id
        )
        section_lines = []
        for map_product in renewal_map.product_offers:
            if (map_product.product_id.sale_ok):
                line = self.generate_product_line(
                    map_product.product_id, selected=map_product.selected
                )
                if str(type(line)) == "<class 'str'>":
                    return line
                section_lines.append(line.id)
        hardware_lines.extend(section_lines)

    def softwareCCP(self, software_lines, product):
        eid = product.name

        # Initilize Software Line Section If Needed
        if len(software_lines) == 0:
            software_lines.append(self.generate_section_line("$software").id)
            software_lines.append(self.generate_section_line("$block").id)

        product_list = self.env["product.product"].search(
            [("sku", "like", eid),
             ("active", "=", True),
             ("sale_ok", "=", True)])

        if len(product_list) != 1:
            return "Software CCP: Invalid Match Count (" + str(len(product_list)) + ") for \n[stock.lot].name: " + str(
                eid) + "\n[product.product].name: " + str(product.product_id.name) + "\n\n"

        line = self.generate_product_line(
            product_list[0], selected=True, optional="yes"
        )
        if str(type(line)) == "<class 'str'>":
            return line

        software_lines.append(line.id)

    def softwareSubCCP(self, software_sub_lines, product):
        eid = product.name

        # Initilize Sub Line Section If Needed
        if len(software_sub_lines) == 0:
            software_sub_lines.append(self.generate_section_line("$subscription").id)
            software_sub_lines.append(self.generate_section_line("$block").id)

        product_list = self.env["product.product"].search(
            [("sku", "like", eid),
             ("active", "=", True),
             ("sale_ok", "=", True)])

        if len(product_list) != 1:
            return "Software Subscritption CCP: Invalid Match Count (" + str(
                len(product_list)) + ") for\n[stock.lot].name: " + str(eid) + "\n[product.product].name: " + str(
                product.product_id.name) + "\n\n"

        if len(product_list) != 1:
            return "Software Subscritption CCP: Invalid Match Count (" + str(
                len(product_list)) + ") for\n[stock.lot].name: " + str(eid) + "\n[product.product].name: " + str(
                product.product_id.name) + "\n\n"

        line = self.generate_product_line(
            product_list[0], selected=True, optional="yes"
        )
        if str(type(line)) == "<class 'str'>":
            return line

        software_sub_lines.append(line.id)

    @api.onchange("sale_order_template_id", "renewal_product_items")
    def renewalQuoteAutoFill(self):
        # Verify Correct Template
        if self.sale_order_template_id.name == False:
            return
        if "Renewal Auto" not in self.sale_order_template_id.name:
            self.renewal_product_items = False
            return
        # Initilize Sections
        software_lines = []
        software_sub_lines = []
        hardware_lines = []
        error_msg = ""
        # For every product added to the quote add it to the correct section
        for product in self.renewal_product_items:

            _logger.error("------product display_name: " + str(product.display_name))
            _logger.error("------product product_id.name: " + str(product.product_id.name))
            _logger.error("------product.sku: " + str(product.sku))

            # only add product that can be sold
            if (product.product_id.sale_ok):
                if product.product_id.type_selection == "H":
                    _logger.info("Hardware")
                    msg = self.hardwareCCP(hardware_lines, product)
                elif product.product_id.type_selection == "S":
                    msg = self.softwareCCP(software_lines, product)
                    _logger.info("Software")
                elif product.product_id.type_selection == "SS":
                    msg = self.softwareSubCCP(software_sub_lines, product)
                    _logger.info("Software Subscription")
                else:
                    msg = (
                            "Product: "
                            + str(product.product_id.name)
                            + ' has unknown type "'
                            + str(product.product_id.type_selection)
                            + '"\n'
                    )
                if msg != None:
                    error_msg += msg + "\n"
            else:
                _logger.error("------product product_id.sale_ok is false, should not add product: ")

        # Combine Sections and add to quote
        lines = []
        lines.extend(hardware_lines)
        lines.extend(software_lines)
        lines.extend(software_sub_lines)
        self.order_line = [(6, 0, lines)]

        if error_msg != "":
            return {"warning": {"title": "Renewal Automation", "message": error_msg}}

    def calc_rental_price(self, price):
        # Take into account length of rental
        if self.rental_start == False or self.rental_end == False:
            return price

        # Calculate Rental Length
        sdate = str(self.rental_start).split("-")
        edate = str(self.rental_end).split("-")
        rentalDays = (
                date(int(edate[0]), int(edate[1]), int(edate[2]))
                - date(int(sdate[0]), int(sdate[1]), int(sdate[2]))
        ).days
        rentalMonths = rentalDays // 30
        rentalDays = rentalDays % 30
        rentalWeeks = rentalDays // 7
        rentalDays = rentalDays % 7

        # Calulate Rental Price based on rental length
        rentalRate = 0
        rentalDayRate = price * rentalDays
        if rentalDayRate > price * 4:
            rentalDayRate = price * 4
        rentalWeekDayRate = 4 * price * rentalWeeks + rentalDayRate
        if rentalWeekDayRate > price * 12:
            rentalDayRate = price * 12
        rentalMonthRate = 12 * price * rentalMonths
        return rentalRate + rentalMonthRate + rentalWeekDayRate

    @api.depends_context('lang')
    @api.depends('order_line.tax_id', 'order_line.price_unit', 'amount_total', 'amount_untaxed', 'currency_id')
    def _compute_tax_totals(self):
        for order in self:
            order = order.with_company(order.company_id)
            order_lines = order.order_line.filtered(lambda x: not x.display_type and x.selected == "true")
            order.tax_totals = order.env['account.tax']._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in order_lines],
                order.currency_id or order.company_id.currency_id,
            )
            order.sudo().update({'amount_total': float(order.tax_totals['amount_total'])})
            _logger.info('>>>>>>>>>>>>>>>>. order.tax_totals: %s,', order.tax_totals)

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        """ Give access button to all users and portal customers to view the quote in the portal. """

        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        if not self:
            return groups
        self.ensure_one()
        # Get the base URL for the portal
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        portal_url = self.get_portal_url()

        for group in groups:
            group_name = group[0]

            # enable the access button for all groups
            group[2]['has_button_access'] = True
            access_opt = group[2].setdefault('button_access', {})

            # set the title for the access button based on the state of the order
            if self.state in ('draft', 'sent'):
                if self.partner_id.lang == 'fr_CA':
                    access_opt['title'] = _("Voir le devis")
                else:
                    access_opt['title'] = _("View Quotation")
            else:
                if self.partner_id.lang == 'fr_CA':
                    access_opt['title'] = _("Voir la commande")
                else:
                    access_opt['title'] = _("View Order")

            # set the portal access URL for the button
            access_opt['url'] = f"{base_url}{portal_url}"
            if message.is_internal:
                access_opt['url'] = f"{base_url}/web#id={self.id}&model={self._name}&view_type=form"
            elif access_opt['title'] == _("View Quotation"):
                access_opt['url'] = f"{base_url}/web#id={self.id}&model={self._name}&view_type=form"
            else:
                if self.partner_id.lang == 'fr_CA':
                    access_opt['url'] = f"{base_url}/fr_CA{portal_url}"
                else:
                    access_opt['url'] = f"{base_url}{portal_url}"

        # return the modified recipient groups with the updated access options
        return groups

    def _amount_all(self):
        # Ensure sale order lines are selected to included in calculation
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                if line.selected == "true" and line.sectionSelected == "true":
                    if order.is_rental == False or line.product_id.is_software:
                        amount_untaxed += line.price_subtotal
                        amount_tax += line.price_tax
                    elif order.is_rental and line.product_id.is_software == False:
                        price = self.calc_rental_price(line.price_subtotal)
                        amount_untaxed += price
                        amount_tax += self.calc_rental_price(line.price_tax)

            order.update(
                {
                    "amount_untaxed": amount_untaxed,
                    "amount_tax": amount_tax,
                    "amount_total": amount_untaxed + amount_tax,
                }
            )

    def _compute_amount_undiscounted(self):
        # Ensure sale order lines are selected to included in calculation
        for order in self:
            total = 0.0
            for line in order.order_line:
                if line.selected == "true" and line.sectionSelected == "true":
                    # why is there a discount in a field named amount_undiscounted ??
                    total += (
                            line.price_subtotal
                            + line.price_unit
                            * ((line.discount or 0.0) / 100.0)
                            * line.product_uom_qty
                    )
            order.amount_undiscounted = total

    def _amount_by_group(self):
        #  Overden Method to Ensure sale order lines are selected to included in calculation
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            fmt = partial(
                formatLang,
                self.with_context(lang=order.partner_id.lang).env,
                currency_obj=currency,
            )
            res = {}
            for line in order.order_line:
                price_reduce = line.price_unit * (1.0 - line.discount / 100.0)
                taxes = line.tax_id.compute_all(
                    price_reduce,
                    quantity=line.product_uom_qty,
                    product=line.product_id,
                    partner=order.partner_shipping_id,
                )["taxes"]
                for tax in line.tax_id:
                    group = tax.tax_group_id
                    res.setdefault(group, {"amount": 0.0, "base": 0.0})
                    for t in taxes:
                        if line.selected != "true" or line.sectionSelected != "true":
                            break
                        if t["id"] == tax.id or t["id"] in tax.children_tax_ids.ids:
                            res[group]["amount"] += t["amount"]
                            res[group]["base"] += t["base"]
            res = sorted(res.items(), key=lambda l: l[0].sequence)
            order.amount_by_group = [
                (
                    l[0].name,
                    l[1]["amount"],
                    l[1]["base"],
                    fmt(l[1]["amount"]),
                    fmt(l[1]["base"]),
                    len(res),
                )
                for l in res
            ]


class orderLineProquotes(models.Model):
    _inherit = "sale.order.line"

    variant = fields.Many2one("proquotes.variant", string="Variant Group")

    # applied_name = fields.Char(compute="get_applied_name", string="Applied Name")
    applied_name = fields.Char(string="Applied Name")

    selected = fields.Selection(
        [("true", "Yes"), ("false", "No")],
        default="true",
        required=True,
        help="Field to Mark Wether Customer has Selected Product",
    )

    sectionSelected = fields.Selection(
        [("true", "Yes"), ("false", "No")],
        default="true",
        required=True,
        help="Field to Mark Wether Container Section is Selected",
    )

    special = fields.Selection(
        [("regular", "regular"), ("multiple", "Multiple"), ("optional", "Optional")],
        default="regular",
        required=True,
        help="Technical field for UX purpose.",
    )

    hiddenSection = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        default="no",
        required=True,
        help="Field To Track if Sections are folded",
    )

    optional = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        default="no",
        required=True,
        help="Field to Mark Product as Optional",
    )

    quantityLocked = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Lock Quantity",
        default="yes",
        required=True,
        help="Field to Lock Quantity on Products",
    )

    is_optional = fields.Boolean(
        required=True, string="Optional",
        help="Field to Mark Product as Optional",
    )
    is_selected = fields.Boolean(
        required=True, string="Selected",
        help="Field to Mark Wether Customer has Selected Product",
    )
    is_quantityLocked = fields.Boolean(
        string="Lock Quantity",
        required=True,
        help="Field to Lock Quantity on Products",
    )

    demo_selected = fields.Boolean(string="Selected", compute="_check_selected_line",
                                   help="Field to Mark Wether Customer has Selected Product",
                                   )

    @api.onchange('is_selected', 'is_quantityLocked', 'is_optional')
    def _onchange_selected_line(self):
        if self.is_selected:
            self.selected = 'true'
        else:
            self.selected = 'false'
        if self.quantityLocked == 'yes':
            self.is_quantityLocked = True
        else:
            self.is_quantityLocked = False
        if self.optional == 'yes':
            self.is_optional = True
        else:
            self.is_optional = False

    def _check_selected_line(self):
        for rec in self:
            rec.demo_selected = False
            rec.is_quantityLocked = False
            if rec.selected == 'true':
                rec.is_selected = True
            else:
                rec.is_selected = False
            if rec.optional == 'yes':
                rec.is_optional = True
            else:
                rec.is_optional = False
            if rec.quantityLocked == 'yes':
                rec.is_quantityLocked = True
            else:
                rec.is_quantityLocked = False

    def get_applied_name(self):
        return True
        # n = name_translation(self)
        # n.get_applied_name()

    def get_sale_order_line_multiline_description_sale(self, product):
        if product.description_sale:
            return product.description_sale
        else:
            return "<span></span>"

    @api.depends('product_uom_qty', 'selected', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            tax_results = self.env['account.tax'].with_company(line.company_id)._compute_taxes([
                line._convert_to_tax_base_line_dict()
            ])
            totals = list(tax_results['totals'].values())[0]
            if line.selected == 'false' or line.product_uom_qty == 0:
                amount_untaxed = 0.00
                _logger.info('>>>>>>>>>>iff>>>>>>.amount_untaxed: %s,', amount_untaxed)

            else:
                amount_untaxed = totals['amount_untaxed']
                _logger.info('>>>>>>>>else>>>>>>>>. amount_untaxed: %s,', amount_untaxed)
            amount_tax = totals['amount_tax']

            line.update({
                'price_subtotal': amount_untaxed,
                'price_tax': amount_tax,
                'price_total': amount_untaxed + amount_tax,
            })

class proquotesMail(models.TransientModel):
    _inherit = "mail.compose.message"
    
    from odoo import models, api

class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'
    
    template_id = fields.Many2one(
        'mail.template',
        string='Use Template',
        domain=lambda self: [('name', 'in', ['General Sales', 'Rental', 'Renewal'])]
    )
    
    @api.model
    def default_get(self, fields_list):
        res = super(MailComposeMessage, self).default_get(fields_list)

        if self.env.context.get('default_model') == 'sale.order':
            # set template
            template = self.env['mail.template'].search([('name', '=', 'General Sales')], limit=1)
            if template:
                res['template_id'] = template.id
                
            # set recipients
            order = self.env['sale.order'].search([('id', '=', self.env.context.get('default_res_id'))], limit=1)
            if order and order.email_contacts:
                res['partner_ids'] = [(4, order.user_id)]
        
        return res
    
    # @api.onchange('template_id')
    # def _onchange_template_id(self):
    #     return {
    #         'domain': {
    #             'template_id': [('name', 'in', ['General Sales', 'Rental', 'Renewal'])]
    #         }
    #     }

    # @api.onchange('model')
    # def _onchange_recipients(self):
    #     if self.model == 'sale.order' and self.env.context.get('default_res_id'):
            
    #         sale_order = self.env['sale.order'].browse(self.env.context.get('default_res_id'))
            
    #         if sale_order.email_contacts:
    #             self.partner_ids = sale_order.email_contacts
    #         else:
    #             self.partner_ids = [(5, 0, 0)]

    # def send_mail(self, auto_commit=False):
        
    #     result = super(MailComposeMessage, self).send_mail(auto_commit=auto_commit)

    #     if self.model == 'sale.order' and self.res_id:
    #         sale_order = self.env['sale.order'].browse(self.res_id)
            
    #         # Update email_contacts with the selected recipients from the wizard
    #         sale_order.email_contacts = [(6, 0, self.partner_ids.ids)]

    #     return result

    def generate_email_for_composer(self, template_id, res_ids, fields):
        """Call email_template.generate_email(), get fields relevant for
        mail.compose.message, transform email_cc and email_to into partner_ids"""
        multi_mode = True
        if isinstance(res_ids, int):
            multi_mode = False
            res_ids = [res_ids]

        returned_fields = fields + ["partner_ids", "attachments"]
        values = dict.fromkeys(res_ids, False)

        template_values = (
            self.env["mail.template"]
            .with_context(tpl_partners_only=True)
            .browse(template_id)
            .generate_email(res_ids, fields)
        )
        for res_id in res_ids:
            res_id_values = dict(
                (field, template_values[res_id][field])
                for field in returned_fields
                if template_values[res_id].get(field)
            )
            res_id_values["body"] = res_id_values.pop("body_html", "")
            if template_values[res_id].get("model") == "sale.order":
                res_id_values["partner_ids"] = self.env["sale.order"].browse(
                    res_id
                ).partner_ids + self.env["res.partner"].search(
                    [("email", "=", "sales@r-e-a-l.it")]
                )
            values[res_id] = res_id_values
        return multi_mode and values or values[res_ids[0]]


class variant(models.Model):
    _name = "proquotes.variant"
    _description = "Model that Represents Variants for Customer Multi-Level Choices"

    name = fields.Char(
        string="Variant Group", required=True, copy=False, index=True, default="New"
    )

    rule = fields.Char(string="Variant Rule", required=True, default="None")


class person(models.Model):
    _inherit = "res.partner"

    products = fields.One2many("stock.lot", "owner", string="Products")


class owner(models.Model):
    _inherit = "stock.lot"

    owner = fields.Many2one("res.partner", string="Owner")

    def copy_label(self):
        # Form Button Needs a Python Target Function
        return


# pdf footer


# class pdf_quote(models.Model):
#     _inherit = "sale.report"

#     footer_field = fields.Selection("")
#     # footer_field = fields.Selection(related="order_id.footer")


class SaleReport(models.Model):
    _name = "sale.report"
    _description = "Sales Analysis Report"
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    @api.model
    def _get_done_states(self):
        return ['sale']

    # sale.order fields
    name = fields.Char(string="Order Reference", readonly=True)
    date = fields.Datetime(string="Order Date", readonly=True)
    partner_id = fields.Many2one(comodel_name='res.partner', string="Customer", readonly=True)
    company_id = fields.Many2one(comodel_name='res.company', readonly=True)
    pricelist_id = fields.Many2one(comodel_name='product.pricelist', readonly=True)
    team_id = fields.Many2one(comodel_name='crm.team', string="Sales Team", readonly=True)
    user_id = fields.Many2one(comodel_name='res.users', string="Salesperson", readonly=True)
    state = fields.Selection(selection=SALE_ORDER_STATE, string="Status", readonly=True)
    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account', string="Analytic Account", readonly=True)
    invoice_status = fields.Selection(
        selection=[
            ('upselling', "Upselling Opportunity"),
            ('invoiced', "Fully Invoiced"),
            ('to invoice', "To Invoice"),
            ('no', "Nothing to Invoice"),
        ], string="Invoice Status", readonly=True)

    campaign_id = fields.Many2one(comodel_name='utm.campaign', string="Campaign", readonly=True)
    medium_id = fields.Many2one(comodel_name='utm.medium', string="Medium", readonly=True)
    source_id = fields.Many2one(comodel_name='utm.source', string="Source", readonly=True)

    # res.partner fields
    commercial_partner_id = fields.Many2one(
        comodel_name='res.partner', string="Customer Entity", readonly=True)
    country_id = fields.Many2one(
        comodel_name='res.country', string="Customer Country", readonly=True)
    industry_id = fields.Many2one(
        comodel_name='res.partner.industry', string="Customer Industry", readonly=True)
    partner_zip = fields.Char(string="Customer ZIP", readonly=True)
    state_id = fields.Many2one(comodel_name='res.country.state', string="Customer State", readonly=True)

    # sale.order.line fields
    order_reference = fields.Reference(string='Related Order', selection=[('sale.order', 'Sales Order')], group_operator="count_distinct")

    categ_id = fields.Many2one(
        comodel_name='product.category', string="Product Category", readonly=True)
    product_id = fields.Many2one(
        comodel_name='product.product', string="Product Variant", readonly=True)
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template', string="Product", readonly=True)
    product_uom = fields.Many2one(comodel_name='uom.uom', string="Unit of Measure", readonly=True)
    product_uom_qty = fields.Float(string="Qty Ordered", readonly=True)
    qty_to_deliver = fields.Float(string="Qty To Deliver", readonly=True)
    qty_delivered = fields.Float(string="Qty Delivered", readonly=True)
    qty_to_invoice = fields.Float(string="Qty To Invoice", readonly=True)
    qty_invoiced = fields.Float(string="Qty Invoiced", readonly=True)
    price_subtotal = fields.Monetary(string="Untaxed Total", readonly=True)
    price_total = fields.Monetary(string="Total", readonly=True)
    untaxed_amount_to_invoice = fields.Monetary(string="Untaxed Amount To Invoice", readonly=True)
    untaxed_amount_invoiced = fields.Monetary(string="Untaxed Amount Invoiced", readonly=True)

    weight = fields.Float(string="Gross Weight", readonly=True)
    volume = fields.Float(string="Volume", readonly=True)

    discount = fields.Float(string="Discount %", readonly=True, group_operator='avg')
    discount_amount = fields.Monetary(string="Discount Amount", readonly=True)

    # aggregates or computed fields
    nbr = fields.Integer(string="# of Lines", readonly=True)
    currency_id = fields.Many2one(comodel_name='res.currency', compute='_compute_currency_id')
    # footer_field = fields.Selection("")

    @api.depends_context('allowed_company_ids')
    def _compute_currency_id(self):
        self.currency_id = self.env.company.currency_id

    def _with_sale(self):
        return ""

    def _select_sale(self):
        select_ = f"""
            MIN(l.id) AS id,
            l.product_id AS product_id,
            t.uom_id AS product_uom,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.product_uom_qty / u.factor * u2.factor) ELSE 0 END AS product_uom_qty,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.qty_delivered / u.factor * u2.factor) ELSE 0 END AS qty_delivered,
            CASE WHEN l.product_id IS NOT NULL THEN SUM((l.product_uom_qty - l.qty_delivered) / u.factor * u2.factor) ELSE 0 END AS qty_to_deliver,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.qty_invoiced / u.factor * u2.factor) ELSE 0 END AS qty_invoiced,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.qty_to_invoice / u.factor * u2.factor) ELSE 0 END AS qty_to_invoice,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_total
                / {self._case_value_or_one('s.currency_rate')}
                * {self._case_value_or_one('currency_table.rate')}
                ) ELSE 0
            END AS price_total,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_subtotal
                / {self._case_value_or_one('s.currency_rate')}
                * {self._case_value_or_one('currency_table.rate')}
                ) ELSE 0
            END AS price_subtotal,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.untaxed_amount_to_invoice
                / {self._case_value_or_one('s.currency_rate')}
                * {self._case_value_or_one('currency_table.rate')}
                ) ELSE 0
            END AS untaxed_amount_to_invoice,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.untaxed_amount_invoiced
                / {self._case_value_or_one('s.currency_rate')}
                * {self._case_value_or_one('currency_table.rate')}
                ) ELSE 0
            END AS untaxed_amount_invoiced,
            COUNT(*) AS nbr,
            s.name AS name,
            s.date_order AS date,
            s.state AS state,
            s.invoice_status as invoice_status,
            s.partner_id AS partner_id,
            s.user_id AS user_id,
            s.company_id AS company_id,
            s.campaign_id AS campaign_id,
            s.medium_id AS medium_id,
            s.source_id AS source_id,
            t.categ_id AS categ_id,
            s.pricelist_id AS pricelist_id,
            s.analytic_account_id AS analytic_account_id,
            s.team_id AS team_id,
            p.product_tmpl_id,
            partner.commercial_partner_id AS commercial_partner_id,
            partner.country_id AS country_id,
            partner.industry_id AS industry_id,
            partner.state_id AS state_id,
            partner.zip AS partner_zip,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(p.weight * l.product_uom_qty / u.factor * u2.factor) ELSE 0 END AS weight,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(p.volume * l.product_uom_qty / u.factor * u2.factor) ELSE 0 END AS volume,
            l.discount AS discount,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_unit * l.product_uom_qty * l.discount / 100.0
                / {self._case_value_or_one('s.currency_rate')}
                * {self._case_value_or_one('currency_table.rate')}
                ) ELSE 0
            END AS discount_amount,
            concat('sale.order', ',', s.id) AS order_reference"""

        additional_fields_info = self._select_additional_fields()
        template = """,
            %s AS %s"""
        for fname, query_info in additional_fields_info.items():
            select_ += template % (query_info, fname)

        return select_

    def _case_value_or_one(self, value):
        return f"""CASE COALESCE({value}, 0) WHEN 0 THEN 1.0 ELSE {value} END"""

    def _select_additional_fields(self):
        """Hook to return additional fields SQL specification for select part of the table query.

        :returns: mapping field -> SQL computation of field, will be converted to '_ AS _field' in the final table definition
        :rtype: dict
        """
        return {}

    def _from_sale(self):
        return """
            sale_order_line l
            LEFT JOIN sale_order s ON s.id=l.order_id
            JOIN res_partner partner ON s.partner_id = partner.id
            LEFT JOIN product_product p ON l.product_id=p.id
            LEFT JOIN product_template t ON p.product_tmpl_id=t.id
            LEFT JOIN uom_uom u ON u.id=l.product_uom
            LEFT JOIN uom_uom u2 ON u2.id=t.uom_id
            JOIN {currency_table} ON currency_table.company_id = s.company_id
            """.format(
            currency_table=self.env['res.currency']._get_query_currency_table(self.env.companies.ids, fields.Date.today())
            )

    def _where_sale(self):
        return """
            l.display_type IS NULL"""

    def _group_by_sale(self):
        return """
            l.product_id,
            l.order_id,
            t.uom_id,
            t.categ_id,
            s.name,
            s.date_order,
            s.partner_id,
            s.user_id,
            s.state,
            s.invoice_status,
            s.company_id,
            s.campaign_id,
            s.medium_id,
            s.source_id,
            s.pricelist_id,
            s.analytic_account_id,
            s.team_id,
            p.product_tmpl_id,
            partner.commercial_partner_id,
            partner.country_id,
            partner.industry_id,
            partner.state_id,
            partner.zip,
            l.discount,
            s.id,
            currency_table.rate"""

    def _query(self):
        with_ = self._with_sale()
        return f"""
            {"WITH" + with_ + "(" if with_ else ""}
            SELECT {self._select_sale()}
            FROM {self._from_sale()}
            WHERE {self._where_sale()}
            GROUP BY {self._group_by_sale()}
            {")" if with_ else ""}
        """

    @property
    def _table_query(self):
        return self._query()

class ProjectTask(models.Model):
    _inherit = 'project.task'

    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Medium'),
        ('2', 'High'),
        ('3', 'Very High'),
    ], default='0', index=True, string="Priority", tracking=True)


class SOMailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.onchange('partner_ids')
    def _onchange_contacts_email_send(self):
        res_ids_list = ast.literal_eval(self.res_ids)
        sale_ids = self.env['sale.order'].sudo().search([('id', 'in', res_ids_list)])
        if sale_ids:
            for sale in sale_ids:
                if sale.email_contacts.ids != self.partner_ids.ids:
                    sale.email_contacts = [(6, 0, self.partner_ids.ids)]
                    existing_partner_ids = set(self.partner_ids.ids)
                    followers_to_remove = sale.message_follower_ids.filtered(lambda follower: follower.partner_id.id not in existing_partner_ids)
                    followers_to_remove.unlink()
                    self.update({'partner_ids': list(existing_partner_ids)})
