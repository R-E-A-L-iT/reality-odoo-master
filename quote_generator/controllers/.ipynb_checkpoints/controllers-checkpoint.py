# -*- coding: utf-8 -*-
from odoo import http


class GuoteGenerator(http.Controller):
    @http.route('/guote_generator/guote_generator/', auth='public')
    def index(self, **kw):
        return "Hello, world"

    @http.route('/guote_generator/guote_generator/objects/', auth='public')
    def list(self, **kw):
        return http.request.render('guote_generator.listing', {
            'root': '/guote_generator/guote_generator',
            'objects': http.request.env['guote_generator.guote_generator'].search([]),
        })

    @http.route('/guote_generator/guote_generator/objects/<model("guote_generator.guote_generator"):obj>/', auth='public')
    def object(self, obj, **kw):
        return http.request.render('guote_generator.object', {
            'object': obj
        })
