# -*- coding: utf-8 -*-

from odoo import api, models
from odoo import models, api
from odoo import api, models


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

    _inherit = 'ir.ui.view'
