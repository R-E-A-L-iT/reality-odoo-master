# -*- coding: utf-8 -*-
from odoo import http


class GuoteGenerator(http.Controller):
    @http.route('/quote_generator/quote_generator/', auth='public')
    def index(self, **kw):
        return "Hello, world"

    @http.route('/quote_generator/quote_generator/objects/', auth='public')
    def list(self, **kw):
        return http.request.render('quote_generator.listing', {
            'root': '/quote_generator/quote_generator',
            'objects': http.request.env['quote_generator.quote_generator'].search([]),
        })

    @http.route('/quote_generator/guote_generator/objects/<model("quote_generator.quote_generator"):obj>/', auth='public')
    def object(self, obj, **kw):
        return http.request.render('quote_generator.object', {
            'object': obj
        })
