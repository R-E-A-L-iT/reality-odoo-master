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

class variant(models.Model):
    _name = "proquotes.variant"
    _description = "Model that Represents Variants for Customer Multi-Level Choices"

    name = fields.Char(
        string="Variant Group", required=True, copy=False, index=True, default="New"
    )

    rule = fields.Char(string="Variant Rule", required=True, default="None")


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    def _get_placeholder_mail_attachments_data(self, move):
        """Override to only show placeholder when template has invoice reports configured."""
        # If no mail template is selected, use default behavior
        if not hasattr(self, 'mail_template_id') or not self.mail_template_id:
            return super()._get_placeholder_mail_attachments_data(move)
        
        # Check if the mail template has invoice reports configured
        if not self._should_attach_invoice_pdf(self.mail_template_id):
            return []
        
        # Use original behavior if reports are configured
        return super()._get_placeholder_mail_attachments_data(move)

    @api.model
    def _get_invoice_extra_attachments_data(self, move):
        """Override to only include PDF when mail template has reports configured."""
        # For single invoice mode, check the current wizard's template
        if hasattr(self, 'mode') and self.mode == 'invoice_single' and hasattr(self, 'mail_template_id'):
            if not self._should_attach_invoice_pdf(self.mail_template_id):
                return []
        # For multi invoice mode or cron processing, check the move's stored template
        elif move.send_and_print_values and move.send_and_print_values.get('mail_template_id'):
            mail_template = self.env['mail.template'].browse(move.send_and_print_values.get('mail_template_id'))
            if not self._should_attach_invoice_pdf(mail_template):
                return []
        
        # Use original behavior if reports are configured or no template context
        return super()._get_invoice_extra_attachments_data(move)

    def _should_attach_invoice_pdf(self, mail_template):
        """
        Check if the mail template has invoice reports configured in Dynamic Reports field.
        
        :param mail_template: mail.template record
        :return: True if invoice reports are configured, False otherwise
        """
        if not mail_template:
            return False
        
        # Check if the template has any reports configured in report_template_ids (Dynamic Reports)
        if mail_template.report_template_ids:
            # Check if any of the configured reports are invoice reports
            invoice_reports = mail_template.report_template_ids.filtered(
                lambda r: r.model == 'account.move' and 'invoice' in r.report_name.lower()
            )
            return bool(invoice_reports)
        
        return False

    def _get_mail_move_values(self, move, wizard=None):
        """Override to handle template-based attachment logic for background processing."""
        result = super()._get_mail_move_values(move, wizard)
        
        # For background processing (when wizard is None), we need to check the stored template
        if not wizard and move.send_and_print_values:
            mail_template_id = move.send_and_print_values.get('mail_template_id')
            if mail_template_id:
                mail_template = self.env['mail.template'].browse(mail_template_id)
                # Rebuild attachment widget based on template configuration
                result['mail_attachments_widget'] = self._get_default_mail_attachments_widget(move, mail_template)
        
        return result