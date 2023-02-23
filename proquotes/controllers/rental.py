# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import binascii
from random import sample

from odoo import http, _, registry
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
import re
from odoo.addons.portal.controllers.portal import CustomerPortal as cPortal
import datetime

import logging
_logger = logging.getLogger(__name__)


class RentalCustomerPortal(cPortal):

    def validate(self, string):
        reg = "^[a-zA-Z0-9- ]*$"
        return not (re.search(reg, string) == None)

    @http.route(["/my/orders/<int:order_id>/newAddress"], type='json', auth="public", website=True)
    def newAdd(self, order_id, newAdd, access_token=None, **post):

        try:
            order_sudo = self._document_check_access(
                'sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if (str(newAdd) == "True" or str(newAdd) == "False"):
            order_sudo.rental_diff_add = True if str(
                newAdd) == "True" else False

        return

    @http.route(["/my/orders/<int:order_id>/street"], type='json', auth="public", website=True)
    def street(self, order_id, street, access_token=None, **post):

        try:
            order_sudo = self._document_check_access(
                'sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if (not self.validate(street)):
            return

        order_sudo.rental_street = street

        return

    @http.route(["/my/orders/<int:order_id>/city"], type='json', auth="public", website=True)
    def city(self, order_id, city, access_token=None, **post):

        try:
            order_sudo = self._document_check_access(
                'sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if (not self.validate(city)):
            return

        order_sudo.rental_city = city

        return

    @http.route(["/my/orders/<int:order_id>/zip"], type='json', auth="public", website=True)
    def zip(self, order_id, zip, access_token=None, **post):

        try:
            order_sudo = self._document_check_access(
                'sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if (not self.validate(zip)):
            return

        order_sudo.rental_zip = zip

        return

    @http.route(["/my/orders/<int:order_id>/state"], type='json', auth="public", website=True)
    def state(self, order_id, state, access_token=None, **post):

        try:
            order_sudo = self._document_check_access(
                'sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if (state == "Select"):
            order_sudo.rental_state = False
            return
        if (not self.validate(state)):
            return

            # Canada
        stateCodes = dict()
        stateCodes['Alberta'] = 533
        stateCodes['British Columbia'] = 534
        stateCodes['Manitoba'] = 535
        stateCodes['New Brunswick'] = 536
        stateCodes['Newfoundland and Labrador'] = 537
        stateCodes['Northwest Territories'] = 538
        stateCodes['Nova Scotia'] = 539
        stateCodes['Nunavut'] = 540
        stateCodes['Ontario'] = 541
        stateCodes['Prince Edward Island'] = 542
        stateCodes['Quebec'] = 543
        stateCodes['Saskatchewan'] = 544
        stateCodes['Yukon'] = 545

        stateCodes['Alabama'] = 9
        stateCodes['Alaska'] = 10
        stateCodes['Arizona'] = 11
        stateCodes['Arkansas'] = 12
        stateCodes['California'] = 13
        stateCodes['Colorado'] = 14
        stateCodes['Connecticut'] = 15
        stateCodes['Delaware'] = 16
        stateCodes['District of Columbia'] = 17
        stateCodes['Florida'] = 18
        stateCodes['Georgia'] = 19
        stateCodes['Hawaii'] = 20
        stateCodes['Idaho'] = 21
        stateCodes['Illinois'] = 22
        stateCodes['Indiana'] = 23
        stateCodes['Iowa'] = 24
        stateCodes['Kansas'] = 25
        stateCodes['Kentucky'] = 26
        stateCodes['Louisiana'] = 27
        stateCodes['Maine'] = 28
        stateCodes['Montana'] = 29
        stateCodes['Nebraska'] = 30
        stateCodes['Nevada'] = 31
        stateCodes['New Hampshire'] = 32
        stateCodes['New Jersey'] = 33
        stateCodes['New Mexico'] = 34
        stateCodes['New York'] = 35
        stateCodes['North Carolina'] = 36
        stateCodes['North Dakota'] = 37
        stateCodes['Ohio'] = 38
        stateCodes['Oklahoma'] = 39
        stateCodes['Oregon'] = 40
        stateCodes['Maryland'] = 41
        stateCodes['Massachusetts'] = 42
        stateCodes['Michigan'] = 43
        stateCodes['Minnesota'] = 44
        stateCodes['Mississippi'] = 45
        stateCodes['Missouri'] = 46
        stateCodes['Pennsylvania'] = 47
        stateCodes['Rhode Island'] = 48
        stateCodes['South Carolina'] = 49
        stateCodes['South Dakota'] = 50
        stateCodes['Tennessee'] = 51
        stateCodes['Texas'] = 52
        stateCodes['Utah'] = 53
        stateCodes['Vermont'] = 54
        stateCodes['Virginia'] = 55
        stateCodes['Washington'] = 56
        stateCodes['West Virginia'] = 57
        stateCodes['Wisconsin'] = 58
        stateCodes['Wyoming'] = 59

        if (state not in stateCodes):
            order_sudo.rental_state = False

        order_sudo.rental_state = stateCodes[state]

        return

    @http.route(["/my/orders/<int:order_id>/country"], type='json', auth="public", website=True)
    def country(self, order_id, country, access_token=None, **post):

        try:
            order_sudo = self._document_check_access(
                'sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if (not self.validate(country)):
            return

        if country == "Canada":
            order_sudo.rental_state = False
            order_sudo.rental_country = 38
        elif country == "United States":
            order_sudo.rental_state = False
            order_sudo.rental_country = 233

        return

    def checkDates(self, order):
        _logger.error("Here")
        if (order.rental_end == False):
            return
        if (order.rental_start == False):
            order.rental_end = False

        start_year, start_month, start_day = str(
            order.rental_start()).split('-')
        end_year, end_month, end_day = str(order.rental_end()).split('-')

        # start_date = datetime.datetime(start_year, start_month, start_day)
        # end_date = datetime.datetime(end_year, end_month, end_day)
        _logger.error("Line: 211")
        # if (start_date > end_date):
        # _logger.warning("Valid")
        # else:
        # _logger.warning("Invalid")
        # return

    @ http.route(["/my/orders/<int:order_id>/start_date"], type='json', auth="public", website=True)
    def start(self, order_id, start, access_token=None, **post):

        try:
            order_sudo = self._document_check_access(
                'sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if (not self.validate(start)):
            return

        order_sudo.rental_start = start
        self.checkDates(order_sudo)
        return

    @ http.route(["/my/orders/<int:order_id>/end_date"], type='json', auth="public", website=True)
    def end(self, order_id, end, access_token=None, **post):

        try:
            order_sudo = self._document_check_access(
                'sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if (not self.validate(end)):
            return

        order_sudo.rental_end = end
        self.checkDates(order_sudo)
        return
