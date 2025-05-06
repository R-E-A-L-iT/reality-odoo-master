# -*- coding: utf-8 -*-
# from odoo import http


# class DeApolloConnector(http.Controller):
#     @http.route('/de_apollo_connector/de_apollo_connector', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/de_apollo_connector/de_apollo_connector/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('de_apollo_connector.listing', {
#             'root': '/de_apollo_connector/de_apollo_connector',
#             'objects': http.request.env['de_apollo_connector.de_apollo_connector'].search([]),
#         })

#     @http.route('/de_apollo_connector/de_apollo_connector/objects/<model("de_apollo_connector.de_apollo_connector"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('de_apollo_connector.object', {
#             'object': obj
#         })
