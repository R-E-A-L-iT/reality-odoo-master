# -*- coding: utf-8 -*-
# from odoo import http


# class Mtest(http.Controller):
#     @http.route('/mtest/mtest/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/mtest/mtest/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('mtest.listing', {
#             'root': '/mtest/mtest',
#             'objects': http.request.env['mtest.mtest'].search([]),
#         })

#     @http.route('/mtest/mtest/objects/<model("mtest.mtest"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('mtest.object', {
#             'object': obj
#         })
